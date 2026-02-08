from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import DataError

from app.database import get_db
from app.schemas.invitation import InvitationCreate, InvitationResponse, InvitationDetailResponse, InvitationListResponse
from app.services.invitation_service import InvitationService
from app.services.user_service import UserService
from app.services.organization_service import OrganizationService
from app.models.user import User
from app.models.invitation import InvitationStatus, Invitation
from app.api.deps import get_current_active_user, get_admin_or_owner

router = APIRouter()


@router.post(
    "",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Convidar usuário para organização"
)
def invite_user(
    invite_in: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_owner)
):
    """
    Convida um usuário para fazer parte da organização (por email)
    
    Apenas administradores ou proprietários podem convidar.
    
    - **email**: Email do usuário a convidar
    """
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para convidar usuários."
        )
    
    # Verificar se organização existe
    organization = OrganizationService.get_by_id(db, organization_id=current_user.organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada."
        )
    
    # Verificar se já existe convite pendente
    existing_invitations = db.query(Invitation).filter(
        Invitation.email == invite_in.email,
        Invitation.organization_id == current_user.organization_id,
        Invitation.status == InvitationStatus.PENDING
    ).all()
    
    if existing_invitations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um convite pendente para este email nesta organização."
        )
    
    # Verificar se usuário já está na organização
    user = UserService.get_by_email(db, email=invite_in.email)
    if user and user.organization_id == current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuário já faz parte da organização."
        )
    
    # Criar convite
    invitation = InvitationService.create(
        db=db,
        email=invite_in.email,
        organization_id=current_user.organization_id,
        invited_by_id=current_user.id,
        role=invite_in.role.value if hasattr(invite_in, 'role') and invite_in.role is not None else None
    )
    
    return invitation


@router.get(
    "",
    response_model=InvitationListResponse,
    summary="Listar convites da organização"
)
def list_organization_invitations(
    status_filter: Optional[str] = Query(None, description="Filtrar por status (pending/accepted/rejected)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_owner)
):
    """
    Lista todos os convites da organização
    
    Apenas administradores ou proprietários podem listar convites.
    """
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )
    
    # Verificar se organização existe
    organization = OrganizationService.get_by_id(db, organization_id=current_user.organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada."
        )
    
    # Buscar convites
    query = db.query(Invitation).filter(Invitation.organization_id == current_user.organization_id)
    
    if status_filter:
        query = query.filter(Invitation.status == status_filter)
    
    total = query.count()
    invitations = query.offset(skip).limit(limit).all()
    
    # Montar response detalhado
    detailed_invitations = []
    for inv in invitations:
        detailed_invitations.append({
            "id": inv.id,
            "email": inv.email,
            "organization_id": inv.organization_id,
            "role": inv.role,
            "organization_name": organization.name,
            "invited_by_email": inv.invited_by.email if inv.invited_by else None,
            "status": inv.status,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at
        })
    
    return InvitationListResponse(total=total, invitations=detailed_invitations)


@router.get(
    "/my-invitations",
    response_model=InvitationListResponse,
    summary="Listar meus convites pendentes"
)
def list_my_invitations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todos os convites pendentes do usuário autenticado
    
    Estes são os convites que ele pode aceitar para se juntar a organizações.
    """
    # Buscar convites pendentes
    invitations = InvitationService.get_pending_by_email(db, email=current_user.email)
    
    # Montar response detalhado
    detailed_invitations = []
    for inv in invitations:
        org = OrganizationService.get_by_id(db, organization_id=inv.organization_id)
        detailed_invitations.append({
            "id": inv.id,
            "email": inv.email,
            "organization_id": inv.organization_id,
            "role": inv.role,
            "organization_name": org.name if org else None,
            "invited_by_email": inv.invited_by.email if inv.invited_by else None,
            "status": inv.status,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at
        })
    
    return InvitationListResponse(total=len(detailed_invitations), invitations=detailed_invitations)


@router.post(
    "/{invitation_id}/accept",
    response_model=InvitationResponse,
    summary="Aceitar convite"
)
def accept_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Aceita um convite e vincula o usuário à organização (Opção 2 da Etapa 2)
    
    O usuário será adicionado à organização após aceitar.
    """
    # Buscar convite
    invitation = InvitationService.get_by_id(db, invitation_id=invitation_id)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado"
        )
    
    # Verificar se convite é para este usuário
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este convite não é para você"
        )
    
    # Verificar se convite ainda está pendente
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este convite já foi {invitation.status}"
        )
    
    # Verificar se usuário já está em outra organização
    if current_user.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já faz parte de uma organização. Não é possível aceitar outro convite."
        )
    
    # Aceitar convite
    invitation = InvitationService.accept(db=db, invitation_id=invitation_id)
    
    # Vincular usuário à organização
    # Garantir que estamos usando a mesma sessão DB: anexar/mesclar o objeto `current_user`
    current_user = db.merge(current_user)
    current_user.organization_id = invitation.organization_id

    # Atribuir role enviada no convite (não atribuir owner aqui)
    if invitation.role:
        current_user.role = invitation.role

    # Tentar commitar; se houver incompatibilidade com um ENUM no Postgres,
    # tentar mapear a label correta (case-insensitive) a partir de pg_enum.
    try:
        db.commit()
        db.refresh(current_user)
    except DataError:
        db.rollback()
        try:
            # Obter labels do enum userrole no Postgres
            res = db.execute(text("SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'userrole'"))
            labels = [r[0] for r in res.fetchall()]
            match = next((lbl for lbl in labels if lbl.lower() == (invitation.role or "").lower()), None)
            if match:
                # Reaplicar organization_id após rollback antes de commitar novamente
                current_user.organization_id = invitation.organization_id
                current_user.role = match
                db.add(current_user)
                db.commit()
                db.refresh(current_user)
            else:
                # Se não achar correspondência, limpar role e reaplicar organization_id
                current_user.organization_id = invitation.organization_id
                current_user.role = None
                db.add(current_user)
                db.commit()
                db.refresh(current_user)
        except Exception:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atribuir role compatível com o banco")
    
    return invitation


@router.post(
    "/{invitation_id}/reject",
    response_model=InvitationResponse,
    summary="Rejeitar convite"
)
def reject_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Rejeita um convite de organização
    """
    # Buscar convite
    invitation = InvitationService.get_by_id(db, invitation_id=invitation_id)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado"
        )
    
    # Verificar se convite é para este usuário
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este convite não é para você"
        )
    
    # Verificar se convite ainda está pendente
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este convite já foi {invitation.status}"
        )
    
    # Rejeitar convite
    invitation = InvitationService.reject(db=db, invitation_id=invitation_id)
    
    return invitation
