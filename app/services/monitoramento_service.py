"""Ativa e encerra o acompanhamento de um processo e aplica a cota do plano."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, desc, nulls_last, or_
from sqlalchemy.orm import Session

from app.domain.planos import obter_plano
from app.domain.prazo_processual import STATUS_CUMPRIDO, apenas_digitos
from app.models.legal_action import LegalAction
from app.models.organization import Organization
from app.models.processo_monitoramento import ProcessoMonitoramento
from app.models.processo_movimento import ProcessoMovimento
from app.models.processo_prazo import ProcessoPrazo
from app.models.user import User
from app.services.jurimai_client import (
    JurimaiClient,
    JurimaiError,
    monitoramento_existente,
    url_de_callback,
)

STATUS_ATIVOS = ("PENDENTE", "ENCONTRADO")

class MonitoramentoIndisponivel(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code

class MonitoramentoService:
    @staticmethod
    def limite(db: Session, organization_id: int) -> int:
        organizacao = db.query(Organization).filter(Organization.id == organization_id).first()
        return obter_plano(organizacao.plano if organizacao else None).processos

    @staticmethod
    def em_uso(db: Session, organization_id: int) -> int:
        return (
            db.query(ProcessoMonitoramento)
            .filter(
                ProcessoMonitoramento.organization_id == organization_id,
                ProcessoMonitoramento.ativo.is_(True),
                ProcessoMonitoramento.status.in_(STATUS_ATIVOS),
            )
            .count()
        )

    @staticmethod
    def obter(db: Session, legal_action_id: int, organization_id: int) -> Optional[ProcessoMonitoramento]:
        return (
            db.query(ProcessoMonitoramento)
            .filter(
                ProcessoMonitoramento.legal_action_id == legal_action_id,
                ProcessoMonitoramento.organization_id == organization_id,
            )
            .first()
        )

    @staticmethod
    def listar_publicacoes(
        db: Session,
        organization_id: int,
        *,
        user_id: Optional[int],
        situacao: str,
        skip: int,
        limit: int,
        search: Optional[str] = None,
    ) -> tuple[list[tuple[ProcessoMovimento, LegalAction, Optional[ProcessoPrazo]]], int, int]:
        pendentes = (
            _consulta_publicacoes(db, organization_id, user_id)
            .filter(ProcessoMovimento.tratado_em.is_(None))
            .count()
        )
        consulta = _consulta_publicacoes(db, organization_id, user_id)
        if situacao == "pendente":
            consulta = consulta.filter(ProcessoMovimento.tratado_em.is_(None))
        elif situacao == "tratada":
            consulta = consulta.filter(ProcessoMovimento.tratado_em.isnot(None))
        if search and search.strip():
            termo = f"%{search.strip()}%"
            consulta = consulta.filter(
                or_(
                    LegalAction.number.ilike(termo),
                    LegalAction.title.ilike(termo),
                    ProcessoMovimento.nome.ilike(termo),
                )
            )
        total = consulta.count()
        itens = (
            consulta.order_by(
                nulls_last(desc(ProcessoMovimento.data_hora)),
                desc(ProcessoMovimento.id),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return itens, total, pendentes

    @staticmethod
    def tratar_publicacao(
        db: Session,
        *,
        movimento_id: int,
        organization_id: int,
        user_id: Optional[int],
    ) -> Optional[tuple[ProcessoMovimento, LegalAction, Optional[ProcessoPrazo]]]:
        encontrado = (
            _consulta_publicacoes(db, organization_id, user_id)
            .filter(ProcessoMovimento.id == movimento_id)
            .first()
        )
        if not encontrado:
            return None
        registro = encontrado[0]
        if registro.tratado_em is None:
            registro.tratado_em = datetime.now(timezone.utc)
            db.add(registro)
            db.commit()
            db.refresh(registro)
        return encontrado

    @staticmethod
    def listar_prazos(db: Session, legal_action_id: int, organization_id: int) -> list[ProcessoPrazo]:
        return (
            db.query(ProcessoPrazo)
            .filter(
                ProcessoPrazo.legal_action_id == legal_action_id,
                ProcessoPrazo.organization_id == organization_id,
            )
            .order_by(ProcessoPrazo.created_at.desc())
            .all()
        )

    @staticmethod
    def ativar(
        db: Session,
        legal_action: LegalAction,
        client: JurimaiClient | None = None,
    ) -> ProcessoMonitoramento:
        numero = (legal_action.number or "").strip()
        digitos = apenas_digitos(numero)
        if len(digitos) != 20:
            raise MonitoramentoIndisponivel(
                "O acompanhamento exige o número CNJ completo, com 20 dígitos."
            )

        existente = MonitoramentoService.obter(db, legal_action.id, legal_action.organization_id)
        if existente and existente.ativo and existente.status in STATUS_ATIVOS:
            return existente

        if existente and existente.ativo and existente.status == "NAO_ENCONTRADO":
            MonitoramentoService._encerrar_remoto(db, existente, client)

        em_uso = MonitoramentoService.em_uso(db, legal_action.organization_id)
        conta_vaga = not (existente and existente.ativo and existente.status in STATUS_ATIVOS)
        if conta_vaga and em_uso >= MonitoramentoService.limite(db, legal_action.organization_id):
            teto = MonitoramentoService.limite(db, legal_action.organization_id)
            raise MonitoramentoIndisponivel(
                f"Este plano acompanha até {teto} processos. "
                "Encerre um acompanhamento para liberar vaga.",
                status_code=409,
            )

        api = client or JurimaiClient()
        try:
            remoto = api.criar_monitoramento(numero, url_de_callback())
        except JurimaiError as exc:
            remoto = _reaproveitar(api, numero, exc)
            if remoto is None:
                raise MonitoramentoIndisponivel(str(exc), _status_publico(exc.status_code)) from exc

        registro = existente or ProcessoMonitoramento(
            organization_id=legal_action.organization_id,
            legal_action_id=legal_action.id,
            numero_cnj=numero,
            numero_digitos=digitos,
        )
        registro.numero_cnj = numero
        registro.numero_digitos = digitos
        registro.escavador_id = _inteiro(remoto.get("id"))
        registro.status = str(remoto.get("status") or "PENDENTE")
        registro.frequencia = _frequencia(remoto.get("frequencia"))
        registro.ativo = True
        registro.data_ultima_verificacao = _data_hora(remoto.get("data_ultima_verificacao"))
        db.add(registro)
        db.commit()
        db.refresh(registro)
        return registro

    @staticmethod
    def encerrar(
        db: Session,
        legal_action: LegalAction,
        client: JurimaiClient | None = None,
    ) -> Optional[ProcessoMonitoramento]:
        registro = MonitoramentoService.obter(db, legal_action.id, legal_action.organization_id)
        if not registro or not registro.ativo:
            return registro
        MonitoramentoService._encerrar_remoto(db, registro, client)
        registro.ativo = False
        db.add(registro)
        db.commit()
        db.refresh(registro)
        return registro

    @staticmethod
    def cumprir_prazo(
        db: Session,
        *,
        legal_action_id: int,
        organization_id: int,
        prazo_id: int,
    ) -> Optional[ProcessoPrazo]:
        prazo = (
            db.query(ProcessoPrazo)
            .filter(
                ProcessoPrazo.id == prazo_id,
                ProcessoPrazo.legal_action_id == legal_action_id,
                ProcessoPrazo.organization_id == organization_id,
            )
            .first()
        )
        if not prazo:
            return None
        prazo.status = STATUS_CUMPRIDO
        db.add(prazo)
        db.commit()
        db.refresh(prazo)
        return prazo

    @staticmethod
    def _encerrar_remoto(
        db: Session,
        registro: ProcessoMonitoramento,
        client: JurimaiClient | None,
    ) -> None:
        if not registro.escavador_id:
            return
        outros = (
            db.query(ProcessoMonitoramento)
            .filter(
                ProcessoMonitoramento.escavador_id == registro.escavador_id,
                ProcessoMonitoramento.id != registro.id,
                ProcessoMonitoramento.ativo.is_(True),
            )
            .count()
        )
        if outros:
            return
        api = client or JurimaiClient()
        try:
            api.remover_monitoramento(int(registro.escavador_id))
        except JurimaiError as exc:
            if exc.status_code == 404:
                return
            raise MonitoramentoIndisponivel(str(exc), _status_publico(exc.status_code)) from exc

def _consulta_publicacoes(db: Session, organization_id: int, user_id: Optional[int]):
    consulta = (
        db.query(ProcessoMovimento, LegalAction, ProcessoPrazo)
        .join(LegalAction, LegalAction.id == ProcessoMovimento.legal_action_id)
        .outerjoin(
            ProcessoPrazo,
            and_(
                ProcessoPrazo.legal_action_id == ProcessoMovimento.legal_action_id,
                ProcessoPrazo.escavador_movimentacao_id == ProcessoMovimento.codigo,
            ),
        )
        .filter(
            LegalAction.organization_id == organization_id,
            ProcessoMovimento.codigo.like("juri-%"),
        )
    )
    if user_id is not None:
        consulta = consulta.filter(
            or_(
                LegalAction.user_id == user_id,
                LegalAction.assigned_users.any(User.id == user_id),
            )
        )
    return consulta


def _reaproveitar(api: JurimaiClient, numero: str, erro: JurimaiError) -> dict | None:
    if erro.status_code not in (409, 422):
        return None
    try:
        return monitoramento_existente(api.listar_monitoramentos(), numero)
    except JurimaiError:
        return None


def _frequencia(valor: object) -> str:
    texto = str(valor or "diaria").strip().upper()
    if texto == "DIÁRIA":
        return "DIARIA"
    return texto[:16]


def _status_publico(status_code: int) -> int:
    if status_code in (401, 402, 409, 422, 503, 504):
        return status_code
    if status_code >= 500:
        return 502
    return 400

def _inteiro(valor: object) -> Optional[int]:
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str) and valor.isdigit():
        return int(valor)
    return None

def _data_hora(valor: object) -> Optional[datetime]:
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
