from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.legal_action import (
    LegalActionCreate,
    LegalActionUpdate,
    LegalActionResponse,
    LegalActionListResponse,
)
from app.schemas.monitoramento import (
    MonitoramentoResponse,
    ProcessoPrazoResponse,
    PublicacaoItem,
    PublicacaoListResponse,
)
from app.services.legal_action_service import LegalActionService
from app.services.monitoramento_service import MonitoramentoIndisponivel, MonitoramentoService
from app.services.plano_service import LimiteDoPlano, PlanoService
from app.models.user import User
from app.api.deps import exigir_permissao, get_data_filter_user_id

router = APIRouter()

@router.post(
    "",
    response_model=LegalActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova ação jurídica"
)
def create_legal_action(
    action_in: LegalActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "criar"))
):
    """
    Cria uma nova ação jurídica/processo (Etapa 3 do fluxo)
    
    Requer que o usuário tenha uma organização criada.
    
    - **number**: Número único do processo
    - **title**: Título da ação
    - **action_type_id**: ID do tipo de ação (listar em GET /legal-action-types)
    - **legal_status_id**: ID do status jurídico (listar em GET /legal-action-statuses). Se vazio, usa 'pre_trial'.
    - **client_id**: ID do cliente envolvido
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para criar ações jurídicas. Crie uma organização primeiro."
        )
    
    if LegalActionService.get_by_number(db, number=action_in.number, organization_id=current_user.organization_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ação jurídica com este número já existe"
        )
    
    try:
        PlanoService.garantir_novo_processo(db, current_user.organization_id)
        action = LegalActionService.create(
            db=db,
            action_in=action_in,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
    except LimiteDoPlano as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de ação jurídica (action_type_id) inválido ou não encontrado",
        )
    return action

@router.get(
    "",
    response_model=LegalActionListResponse,
    summary="Listar ações jurídicas"
)
def list_legal_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=500),
    legal_status_id: Optional[int] = Query(None, description="Filtrar por status jurídico (ID)"),
    legal_status: Optional[str] = Query(None, description="Filtrar por código do status jurídico"),
    client_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    search: Optional[str] = Query(None, description="Buscar por número ou título"),
    sort_by: Optional[str] = Query(None, description="Campo de ordenação"),
    sort_dir: Optional[str] = Query("desc", description="Direção: asc ou desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "visualizar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id)
):
    """
    Lista todas as ações jurídicas da organização com filtros (Etapa 3 do fluxo)
    
    Requer que o usuário tenha uma organização criada.
    
    - ADMIN/OWNER: Veem todos os processos
    - MEMBER/VIEWER: Veem apenas seus processos
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar ações jurídicas. Crie uma organização primeiro."
        )
    
    actions, total = LegalActionService.get_all(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        legal_status_id=legal_status_id,
        legal_status_code=legal_status,
        client_id=client_id,
        search=search,
        user_id=filter_user_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    
    return LegalActionListResponse(total=total, legal_actions=actions)

@router.get(
    "/publicacoes",
    response_model=PublicacaoListResponse,
    summary="Listar atualizações recebidas do acompanhamento",
)
def listar_publicacoes(
    situacao: str = Query("pendente", pattern="^(pendente|tratada|todas)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "visualizar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id),
):
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar ações jurídicas.",
        )
    itens, total, pendentes = MonitoramentoService.listar_publicacoes(
        db,
        current_user.organization_id,
        user_id=filter_user_id,
        situacao=situacao,
        skip=skip,
        limit=limit,
        search=search,
    )
    return PublicacaoListResponse(
        total=total,
        pendentes=pendentes,
        publicacoes=[_item_publicacao(movimento, acao, prazo) for movimento, acao, prazo in itens],
    )

@router.patch(
    "/publicacoes/{movimento_id}/tratar",
    response_model=PublicacaoItem,
    summary="Marcar atualização como tratada",
)
def tratar_publicacao(
    movimento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "editar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id),
):
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar ações jurídicas.",
        )
    registro = MonitoramentoService.tratar_publicacao(
        db,
        movimento_id=movimento_id,
        organization_id=current_user.organization_id,
        user_id=filter_user_id,
    )
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publicação não encontrada")
    movimento, acao, prazo = registro
    return _item_publicacao(movimento, acao, prazo)

def _item_publicacao(movimento, acao, prazo) -> PublicacaoItem:
    return PublicacaoItem(
        id=movimento.id,
        legal_action_id=acao.id,
        numero=acao.number,
        titulo=acao.title,
        conteudo=movimento.nome,
        data_movimentacao=movimento.data_hora,
        tratado_em=movimento.tratado_em,
        prazo_status=prazo.status if prazo else None,
        prazo_vencimento=prazo.data_vencimento if prazo else None,
        dias_prazo=prazo.dias_prazo if prazo else None,
    )

@router.get(
    "/{action_id}",
    response_model=LegalActionResponse,
    summary="Obter ação jurídica"
)
def get_legal_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "visualizar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id)
):
    """
    Retorna uma ação jurídica específica
    
    - ADMIN/OWNER: Pode acessar qualquer processo
    - MEMBER/VIEWER: Pode acessar apenas seus processos
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar ações jurídicas."
        )
    
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id, user_id=filter_user_id)
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada"
        )
    
    return action

@router.put(
    "/{action_id}",
    response_model=LegalActionResponse,
    summary="Atualizar ação jurídica"
)
def update_legal_action(
    action_id: int,
    action_in: LegalActionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "editar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id)
):
    """
    Atualiza uma ação jurídica existente
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )
    
    try:
        action = LegalActionService.update(
            db,
            action_id=action_id,
            action_in=action_in,
            organization_id=current_user.organization_id,
            user_id=filter_user_id,
            actor_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada",
        )
    return action

@router.delete(
    "/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar ação jurídica"
)
def delete_legal_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "excluir")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id)
):
    """
    Deleta uma ação jurídica
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )
    
    action = LegalActionService.get_by_id(
        db,
        action_id=action_id,
        organization_id=current_user.organization_id,
        user_id=filter_user_id,
    )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada",
        )

    try:
        MonitoramentoService.encerrar(db, action)
    except MonitoramentoIndisponivel as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    LegalActionService.delete(
        db,
        action_id=action_id,
        organization_id=current_user.organization_id,
        user_id=filter_user_id,
    )

def _resposta_monitoramento(db, action) -> MonitoramentoResponse:
    registro = MonitoramentoService.obter(db, action.id, action.organization_id)
    prazos = MonitoramentoService.listar_prazos(db, action.id, action.organization_id)
    return MonitoramentoResponse(
        ativo=bool(registro and registro.ativo),
        status=registro.status if registro and registro.ativo else None,
        frequencia=registro.frequencia if registro and registro.ativo else None,
        limite=MonitoramentoService.limite(db, action.organization_id),
        em_uso=MonitoramentoService.em_uso(db, action.organization_id),
        prazos=prazos,
    )

def _carregar_acao(db, action_id, current_user, filter_user_id):
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar ações jurídicas.",
        )
    action = LegalActionService.get_by_id(
        db,
        action_id=action_id,
        organization_id=current_user.organization_id,
        user_id=filter_user_id,
    )
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação jurídica não encontrada")
    return action

@router.get(
    "/{action_id}/monitoramento",
    response_model=MonitoramentoResponse,
    summary="Ver acompanhamento e prazos do processo",
)
def obter_monitoramento(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "visualizar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id),
):
    action = _carregar_acao(db, action_id, current_user, filter_user_id)
    return _resposta_monitoramento(db, action)

@router.post(
    "/{action_id}/monitoramento",
    response_model=MonitoramentoResponse,
    summary="Passar a acompanhar movimentações do processo",
)
def ativar_monitoramento(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "editar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id),
):
    action = _carregar_acao(db, action_id, current_user, filter_user_id)
    try:
        MonitoramentoService.ativar(db, action)
    except MonitoramentoIndisponivel as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _resposta_monitoramento(db, action)

@router.delete(
    "/{action_id}/monitoramento",
    response_model=MonitoramentoResponse,
    summary="Encerrar o acompanhamento do processo",
)
def encerrar_monitoramento(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "editar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id),
):
    action = _carregar_acao(db, action_id, current_user, filter_user_id)
    try:
        MonitoramentoService.encerrar(db, action)
    except MonitoramentoIndisponivel as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _resposta_monitoramento(db, action)

@router.patch(
    "/{action_id}/prazos/{prazo_id}/cumprir",
    response_model=ProcessoPrazoResponse,
    summary="Marcar prazo como cumprido",
)
def cumprir_prazo(
    action_id: int,
    prazo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("processos", "editar")),
    filter_user_id: Optional[int] = Depends(get_data_filter_user_id),
):
    action = _carregar_acao(db, action_id, current_user, filter_user_id)
    prazo = MonitoramentoService.cumprir_prazo(
        db,
        legal_action_id=action.id,
        organization_id=action.organization_id,
        prazo_id=prazo_id,
    )
    if not prazo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prazo não encontrado")
    return prazo
