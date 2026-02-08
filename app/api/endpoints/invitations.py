from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.invitation import InvitationCreate, InvitationResponse, InvitationDetailResponse, InvitationListResponse
from app.services.invitation_service import InvitationService
from app.services.user_service import UserService
from app.services.organization_service import OrganizationService
from app.models.user import User
from app.models.invitation import InvitationStatus
from app.api.deps import get_current_active_user, get_current_superuser

router = APIRouter()


@router.post(
    "/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Convidar usuário para organização"
)
def invite_user(
    invite_in: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Convida um usuário para fazer parte da organização (por email)
    
    Apenas superusuários podem convidar.
    
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
        invited_by_id=current_user.id
    )
    
    return invitation


@router.get(
    "/invitations",
    response_model=InvitationListResponse,
    summary="Listar convites da organização"
)
def list_organization_invitations(
    status_filter: Optional[str] = Query(None, description="Filtrar por status (pending/accepted/rejected)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Lista todos os convites da organização
    
    Apenas superusuários podem listar convites.
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
            "organization_name": org.name if org else None,
            "invited_by_email": inv.invited_by.email if inv.invited_by else None,
            "status": inv.status,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at
        })
    
    return InvitationListResponse(total=len(detailed_invitations), invitations=detailed_invitations)


@router.post(
    "/invitations/{invitation_id}/accept",
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
    current_user.organization_id = invitation.organization_id
    db.commit()
    db.refresh(current_user)
    
    return invitation


@router.post(
    "/invitations/{invitation_id}/reject",
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
