"""Recebe o aviso da Juri+ e grava a movimentação nova no processo.

O webhook documentado traz o evento monitoramento.novidade, sem o texto do andamento.
Quando o texto não vem no aviso, buscamos só a lista de movimentações.
"""

from __future__ import annotations

import hashlib
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
)
from app.models.escavador_callback import EscavadorCallback
from app.models.legal_action import LegalAction
from app.models.notification import Notification
from app.models.processo_monitoramento import ProcessoMonitoramento
from app.models.processo_movimento import ProcessoMovimento
from app.models.processo_prazo import ProcessoPrazo
from app.services.jurimai_client import JurimaiClient, JurimaiError

logger = logging.getLogger(__name__)

_LIMITE_TEXTO = 280


class JurimaiCallbackService:
    @staticmethod
    def processar(db: Session, payload: dict[str, Any], client: JurimaiClient | None = None) -> None:
        evento = payload.get("evento") or payload.get("event")
        if evento != "monitoramento.novidade":
            return

        chave = _chave(payload)
        db.add(EscavadorCallback(uuid=chave, event="monitoramento.novidade"))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            logger.info("Aviso da Juri+ já processado")
            return

        registros = _localizar(db, payload)
        if not registros:
            db.commit()
            return

        try:
            movimentos = _movimentos(payload, registros[0], client or JurimaiClient())
        except JurimaiError:
            db.rollback()
            raise

        for registro in registros:
            registro.status = "ENCONTRADO"
            verificado = _data_hora(payload.get("em"))
            if verificado:
                registro.data_ultima_verificacao = verificado
            _aplicar_lista(db, registro, movimentos)
            db.add(registro)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.info("Aviso concorrente da Juri+ ignorado")


def movimentos_no_aviso(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """A documentação manda uma lista de números. Se um dia vier o andamento, usamos ele e não consultamos de novo."""
    novidades = payload.get("novidades")
    if not isinstance(novidades, list) or not novidades:
        return None
    if all(_eh_andamento(item) for item in novidades):
        return [item for item in novidades if isinstance(item, dict)]
    return None


def codigo_movimentacao(movimentacao: dict[str, Any]) -> str:
    base = "|".join(
        str(movimentacao.get(campo) or "")
        for campo in ("data", "nome", "descricao", "conteudo", "grau")
    )
    resumo = hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]
    return f"juri-{resumo}"


def _eh_andamento(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    return any(isinstance(item.get(campo), str) and item.get(campo).strip() for campo in ("nome", "descricao", "conteudo"))


def _movimentos(
    payload: dict[str, Any],
    registro: ProcessoMonitoramento,
    client: JurimaiClient,
) -> list[dict[str, Any]]:
    embutidos = movimentos_no_aviso(payload)
    if embutidos is not None:
        return embutidos
    return client.listar_movimentacoes(registro.numero_cnj)


def _chave(payload: dict[str, Any]) -> str:
    bruto = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:80]


def _localizar(db: Session, payload: dict[str, Any]) -> list[ProcessoMonitoramento]:
    consulta = db.query(ProcessoMonitoramento).options(
        selectinload(ProcessoMonitoramento.legal_action).selectinload(LegalAction.assigned_users)
    ).filter(ProcessoMonitoramento.ativo.is_(True))

    monitoramento_id = payload.get("monitoramento_id")
    if isinstance(monitoramento_id, int) or (isinstance(monitoramento_id, str) and monitoramento_id.isdigit()):
        por_id = consulta.filter(ProcessoMonitoramento.escavador_id == int(monitoramento_id)).all()
        if por_id:
            return por_id

    alvo = payload.get("alvo")
    digitos = apenas_digitos(alvo) if isinstance(alvo, str) else ""
    if len(digitos) != 20:
        return []
    return consulta.filter(ProcessoMonitoramento.numero_digitos == digitos).all()


def permanecer_a_tratar(movimentos: list[dict[str, Any]], primeira_carga: bool) -> list[dict[str, Any]]:
    """Na primeira carga o histórico inteiro chega junto. Só a mais recente fica a tratar."""
    if primeira_carga and len(movimentos) > 1:
        return [_mais_recente(movimentos)]
    return list(movimentos)


def _aplicar_lista(db: Session, registro: ProcessoMonitoramento, movimentos: list[dict[str, Any]]) -> None:
    ja_tinha = (
        db.query(ProcessoMovimento.id)
        .filter(
            ProcessoMovimento.legal_action_id == registro.legal_action_id,
            ProcessoMovimento.codigo.like("juri-%"),
        )
        .count()
    )
    novos: list[tuple[ProcessoMovimento, dict[str, Any]]] = []
    for movimentacao in movimentos:
        salvo = _gravar(db, registro, movimentacao)
        if salvo is not None:
            novos.append((salvo, movimentacao))
    if not novos:
        return

    em_aberto = permanecer_a_tratar([item for _, item in novos], ja_tinha == 0)
    abertos = {id(item) for item in em_aberto}
    if len(abertos) < len(novos):
        agora = datetime.now(timezone.utc)
        for salvo, item in novos:
            if id(item) not in abertos:
                salvo.tratado_em = agora
    for item in em_aberto:
        _avisar(db, registro, item)


def _gravar(db: Session, registro: ProcessoMonitoramento, movimentacao: dict[str, Any]) -> Optional[ProcessoMovimento]:
    acao = registro.legal_action
    codigo = codigo_movimentacao(movimentacao)
    ja_existe = (
        db.query(ProcessoMovimento.id)
        .filter(
            ProcessoMovimento.legal_action_id == acao.id,
            ProcessoMovimento.codigo == codigo,
        )
        .first()
    )
    if ja_existe:
        return None

    conteudo = _conteudo(movimentacao)
    data_mov = _data(movimentacao.get("data"))
    calculado = decidir_prazo(
        tipo="ANDAMENTO",
        conteudo=conteudo,
        texto_extra=str(movimentacao.get("nome") or ""),
        data_movimentacao=data_mov,
    )
    movimento = ProcessoMovimento(
        legal_action_id=acao.id,
        codigo=codigo,
        nome=conteudo[:4000],
        data_hora=datetime.combine(data_mov, datetime.min.time(), tzinfo=timezone.utc) if data_mov else None,
        complemento_json=json.dumps(
            {"origem": "ANDAMENTO", "grau": movimentacao.get("grau")},
            ensure_ascii=False,
        ),
    )
    db.add(movimento)
    if calculado.status != STATUS_NENHUM:
        db.add(
            ProcessoPrazo(
                organization_id=acao.organization_id,
                legal_action_id=acao.id,
                escavador_movimentacao_id=codigo,
                origem="ANDAMENTO",
                conteudo=conteudo,
                data_movimentacao=data_mov,
                dias_prazo=calculado.dias,
                data_vencimento=calculado.data_vencimento,
                status=calculado.status,
            )
        )
    return movimento


def _avisar(db: Session, registro: ProcessoMonitoramento, movimentacao: dict[str, Any]) -> None:
    conteudo = _conteudo(movimentacao)
    data_mov = _data(movimentacao.get("data"))
    calculado = decidir_prazo(
        tipo="ANDAMENTO",
        conteudo=conteudo,
        texto_extra=str(movimentacao.get("nome") or ""),
        data_movimentacao=data_mov,
    )
    titulo, mensagem = _texto_alerta(
        registro.legal_action.number,
        conteudo,
        calculado.status,
        calculado.data_vencimento,
        calculado.dias,
    )
    _notificar(db, registro, titulo, mensagem)


def _mais_recente(movimentos: list[dict[str, Any]]) -> dict[str, Any]:
    def ordem(item: dict[str, Any]) -> date:
        return _data(item.get("data")) or date.min

    return max(movimentos, key=ordem)


def _conteudo(movimentacao: dict[str, Any]) -> str:
    nome = str(movimentacao.get("nome") or "").strip()
    descricao = str(movimentacao.get("descricao") or movimentacao.get("conteudo") or "").strip()
    if nome and descricao and descricao not in nome:
        return f"{nome}. {descricao}"
    return descricao or nome or "Movimentação sem texto"


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
