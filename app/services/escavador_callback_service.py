"""Recebe o callback do Escavador e avisa os advogados do processo.

Eventos tratados, conforme https://api.escavador.com/v2/docs/callbacks :
nova_movimentacao, processo_encontrado, processo_nao_encontrado e processo_verificado.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domain.prazo_processual import (
    STATUS_ABERTO,
    STATUS_CONFERIR,
    STATUS_NENHUM,
    apenas_digitos,
    decidir_prazo,
    normalizar_tipo,
)
from app.models.escavador_callback import EscavadorCallback
from app.models.legal_action import LegalAction
from app.models.notification import Notification
from app.models.processo_monitoramento import ProcessoMonitoramento
from app.models.processo_movimento import ProcessoMovimento
from app.models.processo_prazo import ProcessoPrazo

logger = logging.getLogger(__name__)

_LIMITE_TEXTO = 280

class EscavadorCallbackService:
    @staticmethod
    def processar(db: Session, payload: dict[str, Any]) -> None:
        event = payload.get("event")
        if not isinstance(event, str) or not event.strip():
            return

        chave = _chave(payload)
        db.add(EscavadorCallback(uuid=chave, event=event[:64]))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            logger.info("Callback já processado: event=%s", event)
            return

        monitoramento = payload.get("monitoramento") if isinstance(payload.get("monitoramento"), dict) else {}
        registros = _localizar(db, monitoramento)
        if event == "nova_movimentacao":
            movimentacao = payload.get("movimentacao") if isinstance(payload.get("movimentacao"), dict) else {}
            for registro in registros:
                _aplicar_movimentacao(db, registro, movimentacao)
                if registro.status == "PENDENTE":
                    registro.status = "ENCONTRADO"
        elif event == "processo_encontrado":
            for registro in registros:
                registro.status = "ENCONTRADO"
                _notificar(db, registro, "Processo localizado", "O acompanhamento deste processo começou.")
        elif event == "processo_nao_encontrado":
            for registro in registros:
                registro.status = "NAO_ENCONTRADO"
                _notificar(
                    db,
                    registro,
                    "Processo não localizado",
                    "O tribunal não localizou este número. O acompanhamento não foi iniciado.",
                )
        elif event == "processo_verificado":
            verificado = _data_hora(payload.get("verificado_em"))
            for registro in registros:
                if verificado:
                    registro.data_ultima_verificacao = verificado

        for registro in registros:
            db.add(registro)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.info("Callback concorrente ignorado: event=%s", event)

def _chave(payload: dict[str, Any]) -> str:
    uuid = payload.get("uuid")
    if isinstance(uuid, str) and uuid.strip():
        return uuid.strip()[:80]
    monitoramento = payload.get("monitoramento") if isinstance(payload.get("monitoramento"), dict) else {}
    movimentacao = payload.get("movimentacao") if isinstance(payload.get("movimentacao"), dict) else {}
    return f"{payload.get('event')}:{monitoramento.get('id')}:{movimentacao.get('id')}"[:80]

def _localizar(db: Session, monitoramento: dict[str, Any]) -> list[ProcessoMonitoramento]:
    escavador_id = monitoramento.get("id")
    consulta = db.query(ProcessoMonitoramento).options(
        selectinload(ProcessoMonitoramento.legal_action).selectinload(LegalAction.assigned_users)
    ).filter(ProcessoMonitoramento.ativo.is_(True))

    if isinstance(escavador_id, int) or (isinstance(escavador_id, str) and escavador_id.isdigit()):
        por_id = consulta.filter(ProcessoMonitoramento.escavador_id == int(escavador_id)).all()
        if por_id:
            return por_id

    numero = monitoramento.get("numero")
    digitos = apenas_digitos(numero) if isinstance(numero, str) else ""
    if len(digitos) != 20:
        return []
    return consulta.filter(ProcessoMonitoramento.numero_digitos == digitos).all()

def _aplicar_movimentacao(
    db: Session,
    registro: ProcessoMonitoramento,
    movimentacao: dict[str, Any],
) -> None:
    acao = registro.legal_action
    identificador = movimentacao.get("id")
    if identificador is None:
        return
    codigo = f"escavador-{identificador}"
    ja_existe = (
        db.query(ProcessoMovimento.id)
        .filter(
            ProcessoMovimento.legal_action_id == acao.id,
            ProcessoMovimento.codigo == codigo,
        )
        .first()
    )
    if ja_existe:
        return

    conteudo = str(movimentacao.get("conteudo") or "").strip() or "Movimentação sem texto"
    tipo = normalizar_tipo(movimentacao.get("tipo") if isinstance(movimentacao.get("tipo"), str) else None)
    data_mov = _data(movimentacao.get("data"))
    extra = _texto_extra(movimentacao)
    calculado = decidir_prazo(
        tipo=tipo,
        conteudo=conteudo,
        texto_extra=extra,
        data_movimentacao=data_mov,
    )

    db.add(
        ProcessoMovimento(
            legal_action_id=acao.id,
            codigo=codigo,
            nome=conteudo[:4000],
            data_hora=datetime.combine(data_mov, datetime.min.time(), tzinfo=timezone.utc) if data_mov else None,
            complemento_json=json.dumps(
                {
                    "origem": tipo or None,
                    "tipo_publicacao": movimentacao.get("tipo_publicacao"),
                    "classificacao": _nome_classificacao(movimentacao),
                },
                ensure_ascii=False,
            ),
        )
    )

    if calculado.status != STATUS_NENHUM:
        db.add(
            ProcessoPrazo(
                organization_id=acao.organization_id,
                legal_action_id=acao.id,
                escavador_movimentacao_id=str(identificador),
                origem=tipo or "ANDAMENTO",
                conteudo=conteudo,
                data_movimentacao=data_mov,
                dias_prazo=calculado.dias,
                data_vencimento=calculado.data_vencimento,
                status=calculado.status,
            )
        )

    titulo, mensagem = _texto_alerta(acao.number, conteudo, calculado.status, calculado.data_vencimento, calculado.dias)
    _notificar(db, registro, titulo, mensagem)

def _texto_alerta(
    numero: str,
    conteudo: str,
    status: str,
    vencimento: Optional[date],
    dias: Optional[int],
) -> tuple[str, str]:
    trecho = conteudo.replace("\n", " ").strip()
    if len(trecho) > _LIMITE_TEXTO:
        trecho = trecho[: _LIMITE_TEXTO - 1] + "…"
    if status == STATUS_ABERTO and vencimento and dias:
        return (
            f"Prazo de {dias} dias no processo {numero}",
            f"{trecho} Vencimento estimado: {vencimento.strftime('%d/%m/%Y')}. Confira o texto oficial.",
        )
    if status == STATUS_CONFERIR:
        return (
            f"Movimentação para conferir prazo — {numero}",
            f"{trecho} O texto não informa a quantidade de dias. Abra o processo e confira o prazo.",
        )
    return (f"Nova movimentação no processo {numero}", trecho)

def _notificar(db: Session, registro: ProcessoMonitoramento, titulo: str, mensagem: str) -> None:
    acao = registro.legal_action
    destinatarios = {usuario.id for usuario in acao.assigned_users}
    if acao.user_id:
        destinatarios.add(acao.user_id)
    for user_id in destinatarios:
        db.add(
            Notification(
                user_id=user_id,
                organization_id=acao.organization_id,
                legal_action_id=acao.id,
                title=titulo[:255],
                message=mensagem[:1000],
            )
        )

def _texto_extra(movimentacao: dict[str, Any]) -> str:
    partes = [
        movimentacao.get("tipo_publicacao"),
        movimentacao.get("texto_categoria"),
    ]
    classificacao = movimentacao.get("classificacao_predita")
    if isinstance(classificacao, dict):
        partes.append(classificacao.get("nome"))
        partes.append(classificacao.get("hierarquia"))
    return " ".join(str(parte) for parte in partes if isinstance(parte, str))

def _nome_classificacao(movimentacao: dict[str, Any]) -> Optional[str]:
    classificacao = movimentacao.get("classificacao_predita")
    if isinstance(classificacao, dict) and isinstance(classificacao.get("nome"), str):
        return classificacao["nome"]
    return None

def _data(valor: object) -> Optional[date]:
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return date.fromisoformat(valor[:10])
    except ValueError:
        return None

def _data_hora(valor: object) -> Optional[datetime]:
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
