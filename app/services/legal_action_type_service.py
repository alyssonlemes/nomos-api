from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.legal_action_type import LegalActionType
from app.schemas.legal_action_type import LegalActionTypeCreate, LegalActionTypeUpdate


class LegalActionTypeService:
    """Serviço para CRUD de tipos de ação jurídica."""

    @staticmethod
    def get_by_id(db: Session, type_id: int) -> Optional[LegalActionType]:
        """Busca tipo por ID."""
        return db.query(LegalActionType).filter(LegalActionType.id == type_id).first()

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[LegalActionType]:
        """Busca tipo por código."""
        return db.query(LegalActionType).filter(LegalActionType.code == code).first()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> Tuple[List[LegalActionType], int]:
        """Lista tipos com paginação e busca opcional por nome/código."""
        query = db.query(LegalActionType)
        if search:
            term = f"%{search}%"
            query = query.filter(
                LegalActionType.name.ilike(term) | LegalActionType.code.ilike(term)
            )
        total = query.count()
        items = query.order_by(LegalActionType.name).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def create(db: Session, data_in: LegalActionTypeCreate) -> LegalActionType:
        """Cria um novo tipo."""
        code = data_in.code.strip().lower()
        if LegalActionTypeService.get_by_code(db, code):
            return None  # caller should check and raise 400
        db_type = LegalActionType(
            name=data_in.name,
            code=code,
            description=data_in.description,
        )
        db.add(db_type)
        db.commit()
        db.refresh(db_type)
        return db_type

    @staticmethod
    def update(
        db: Session,
        type_id: int,
        data_in: LegalActionTypeUpdate,
    ) -> Optional[LegalActionType]:
        """Atualiza um tipo."""
        db_type = LegalActionTypeService.get_by_id(db, type_id)
        if not db_type:
            return None
        update_data = data_in.model_dump(exclude_unset=True)
        if "code" in update_data:
            update_data["code"] = update_data["code"].strip().lower()
        for field, value in update_data.items():
            setattr(db_type, field, value)
        db.add(db_type)
        db.commit()
        db.refresh(db_type)
        return db_type

    @staticmethod
    def delete(db: Session, type_id: int) -> Optional[LegalActionType]:
        """Remove um tipo (falha se houver legal_actions usando)."""
        db_type = LegalActionTypeService.get_by_id(db, type_id)
        if not db_type:
            return None
        db.delete(db_type)
        db.commit()
        return db_type
