"""Ativa e encerra o acompanhamento de um processo e aplica a cota do plano."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.planos import obter_plano
from app.domain.prazo_processual import STATUS_CUMPRIDO, apenas_digitos
from app.models.legal_action import LegalAction
from app.models.organization import Organization
from app.models.processo_monitoramento import ProcessoMonitoramento
from app.models.processo_prazo import ProcessoPrazo
from app.services.escavador_client import (
    EscavadorClient,
    EscavadorError,
    monitoramento_de_conflito,
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
        client: EscavadorClient | None = None,
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

        api = client or EscavadorClient()
        try:
            remoto = api.criar_monitoramento(numero)
        except EscavadorError as exc:
            remoto = monitoramento_de_conflito(exc)
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
        registro.frequencia = str(remoto.get("frequencia") or "DIARIA")
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
        client: EscavadorClient | None = None,
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
        client: EscavadorClient | None,
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
        api = client or EscavadorClient()
        try:
            api.remover_monitoramento(int(registro.escavador_id))
        except EscavadorError as exc:
            if exc.status_code == 404:
                return
            raise MonitoramentoIndisponivel(str(exc), _status_publico(exc.status_code)) from exc

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
