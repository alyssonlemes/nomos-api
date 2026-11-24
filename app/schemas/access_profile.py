from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.user import PermissaoModulo

class AccessProfileUpdate(BaseModel):
    isolate_data: bool = False
    permissions: list[PermissaoModulo]

class AccessProfileResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool
    isolate_data: bool
    permissions: list[PermissaoModulo]

    model_config = ConfigDict(from_attributes=True)

class AccessProfileListResponse(BaseModel):
    profiles: list[AccessProfileResponse]
