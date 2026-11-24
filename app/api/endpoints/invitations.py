from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import DataError

from app.database import get_db
from app.schemas.invitation import InvitationCreate, InvitationResponse, InvitationDetailResponse, InvitationListResponse
from app.services.invitation_service import InvitationService
from app.services.user_service import UserService
from app.services.organization_service import OrganizationService
from app.services.plano_service import LimiteDoPlano, PlanoService
from app.models.user import User
from app.models.invitation import InvitationStatus, Invitation
from app.api.deps import get_current_active_user, exigir_permissao
from app.core.perfis import eh_administrador, papel_convite, papel_legado
from app.services.access_profile_service import AccessProfileService

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
    current_user: User = Depends(exigir_permissao("usuarios", "criar"))
):
    """
    Convida um usuário para a organização com um perfil de acesso.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para convidar usuários."
        )
    
    organization = OrganizationService.get_by_id(db, organization_id=current_user.organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada."
        )
    
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
    
    user = UserService.get_by_email(db, email=invite_in.email)
    if user and user.organization_id == current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuário já faz parte da organização."
        )

    try:
        PlanoService.garantir_novo_usuario(db, current_user.organization_id)
    except LimiteDoPlano as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    
    perfil = None
    if invite_in.profile_id is not None:
        perfil = AccessProfileService.buscar(db, invite_in.profile_id, current_user.organization_id)
    elif invite_in.role is not None:
        perfil = AccessProfileService.resolver_por_papel(db, current_user.organization_id, invite_in.role.value)
    else:
        perfil = AccessProfileService.resolver_por_papel(db, current_user.organization_id, "member")

    if perfil is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Perfil inválido para esta organização.")
    if perfil.name == "Administrador" and not eh_administrador(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o administrador pode convidar outro administrador.",
        )

    invitation = InvitationService.create(
        db=db,
        email=invite_in.email,
        organization_id=current_user.organization_id,
        invited_by_id=current_user.id,
        role=papel_convite(perfil.name),
        profile_id=perfil.id,
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
    current_user: User = Depends(exigir_permissao("usuarios", "visualizar"))
):
    """
    Lista todos os convites da organização
    
    Apenas administradores ou proprietários podem listar convites.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )
    
    organization = OrganizationService.get_by_id(db, organization_id=current_user.organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada."
        )
    
    query = db.query(Invitation).filter(Invitation.organization_id == current_user.organization_id)
    
    if status_filter:
        query = query.filter(Invitation.status == status_filter)
    
    total = query.count()
    invitations = query.offset(skip).limit(limit).all()
    
    detailed_invitations = []
    for inv in invitations:
        detailed_invitations.append({
            "id": inv.id,
            "email": inv.email,
            "organization_id": inv.organization_id,
            "role": inv.role,
            "profile_id": inv.profile_id,
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
    invitations = InvitationService.get_pending_by_email(db, email=current_user.email)
    
    detailed_invitations = []
    for inv in invitations:
        org = OrganizationService.get_by_id(db, organization_id=inv.organization_id)
        detailed_invitations.append({
            "id": inv.id,
            "email": inv.email,
            "organization_id": inv.organization_id,
            "role": inv.role,
            "profile_id": inv.profile_id,
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
    invitation = InvitationService.get_by_id(db, invitation_id=invitation_id)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado"
        )
    
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este convite não é para você"
        )
    
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este convite já foi {invitation.status}"
        )
    
    if current_user.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já faz parte de uma organização. Não é possível aceitar outro convite."
        )

    try:
        PlanoService.garantir_aceite(db, invitation.organization_id)
    except LimiteDoPlano as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    
    invitation = InvitationService.accept(db=db, invitation_id=invitation_id)

    perfil = None
    if invitation.profile_id:
        perfil = AccessProfileService.buscar(db, invitation.profile_id, invitation.organization_id)
    if perfil is None:
        perfil = AccessProfileService.resolver_por_papel(db, invitation.organization_id, invitation.role or "member")

    current_user = db.merge(current_user)
    current_user.organization_id = invitation.organization_id
    current_user.profile_id = perfil.id if perfil else None
    current_user.role = papel_legado(perfil.name if perfil else None, eh_dono=False)

    try:
        db.commit()
        db.refresh(current_user)
    except DataError:
        db.rollback()
        current_user = db.merge(current_user)
        current_user.organization_id = invitation.organization_id
        current_user.profile_id = perfil.id if perfil else None
        current_user.role = None
        db.add(current_user)
        db.commit()
        db.refresh(current_user)

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
    invitation = InvitationService.get_by_id(db, invitation_id=invitation_id)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado"
        )
    
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este convite não é para você"
        )
    
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este convite já foi {invitation.status}"
        )
    
    invitation = InvitationService.reject(db=db, invitation_id=invitation_id)
    
    return invitation
