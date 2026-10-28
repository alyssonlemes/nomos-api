from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.perfis import eh_administrador, montar_permissoes_do_perfil, tem_permissao_usuario
from app.database import get_db
from app.models.access_profile import AccessProfile
from app.models.user import User
from app.schemas.access_profile import AccessProfileListResponse, AccessProfileResponse, AccessProfileUpdate
from app.services.access_profile_service import AccessProfileService

router = APIRouter()


def _resposta(perfil: AccessProfile) -> AccessProfileResponse:
    return AccessProfileResponse(
        id=perfil.id,
        name=perfil.name,
        description=perfil.description,
        is_system=bool(perfil.is_system),
        isolate_data=bool(perfil.isolate_data),
        permissions=montar_permissoes_do_perfil(perfil.name, perfil.permissions),
    )


def _pode_listar(usuario: User) -> bool:
    if eh_administrador(usuario) or usuario.is_superuser:
        return True
    return any(
        tem_permissao_usuario(usuario, "usuarios", acao)
        for acao in ("visualizar", "criar", "editar")
    )


@router.get("", response_model=AccessProfileListResponse, summary="Listar perfis da organização")
def list_access_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você precisa ter uma organização.")
    if not _pode_listar(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para ver os perfis.")
    perfis = AccessProfileService.listar(db, current_user.organization_id)
    return AccessProfileListResponse(profiles=[_resposta(perfil) for perfil in perfis])


@router.put("/{profile_id}", response_model=AccessProfileResponse, summary="Atualizar permissões do perfil")
def update_access_profile(
    profile_id: int,
    payload: AccessProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você precisa ter uma organização.")
    if not eh_administrador(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem alterar a matriz de permissões.",
        )
    atualizado = AccessProfileService.atualizar(
        db,
        profile_id=profile_id,
        organization_id=current_user.organization_id,
        permissions=[item.model_dump() for item in payload.permissions],
        isolate_data=payload.isolate_data,
    )
    if atualizado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado.")
    return _resposta(atualizado)
