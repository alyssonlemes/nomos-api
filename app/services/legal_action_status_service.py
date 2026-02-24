from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.legal_action_status import LegalActionStatus
from app.schemas.legal_action_status import LegalActionStatusCreate, LegalActionStatusUpdate


class LegalActionStatusService:
    """Serviço para CRUD de status jurídicos de ação."""

    @staticmethod
    def get_by_id(db: Session, status_id: int) -> Optional[LegalActionStatus]:
        return db.query(LegalActionStatus).filter(LegalActionStatus.id == status_id).first()

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[LegalActionStatus]:
        """Busca por código (comparação case-insensitive no banco)."""
        code_normalized = code.strip().lower() if code else ""
        return (
            db.query(LegalActionStatus)
            .filter(func.lower(LegalActionStatus.code) == code_normalized)
            .first()
        )

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> Tuple[List[LegalActionStatus], int]:
        query = db.query(LegalActionStatus)
        if search:
            term = f"%{search}%"
            query = query.filter(
                (LegalActionStatus.name.ilike(term)) | (LegalActionStatus.code.ilike(term))
            )
        total = query.count()
        items = query.order_by(LegalActionStatus.name).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def create(db: Session, data_in: LegalActionStatusCreate) -> Optional[LegalActionStatus]:
        code = data_in.code.strip().lower()
        if not code:
            return None
        if LegalActionStatusService.get_by_code(db, code):
            return None
        db_status = LegalActionStatus(
            name=data_in.name,
            code=code,
            description=data_in.description,
        )
        db.add(db_status)
        db.commit()
        db.refresh(db_status)
        return db_status

    @staticmethod
    def update(
        db: Session,
        status_id: int,
        data_in: LegalActionStatusUpdate,
    ) -> Optional[LegalActionStatus]:
        db_status = LegalActionStatusService.get_by_id(db, status_id)
        if not db_status:
            return None

        update_data = data_in.model_dump(exclude_unset=True)
        if "code" in update_data:
            update_data["code"] = update_data["code"].strip().lower()
            existing = LegalActionStatusService.get_by_code(db, update_data["code"])
            if existing and existing.id != status_id:
                return None

        for field, value in update_data.items():
            setattr(db_status, field, value)

        db.add(db_status)
        db.commit()
        db.refresh(db_status)
        return db_status

    @staticmethod
    def delete(db: Session, status_id: int) -> Optional[LegalActionStatus]:
        db_status = LegalActionStatusService.get_by_id(db, status_id)
        if not db_status:
            return None

        db.delete(db_status)
        db.commit()
        return db_status

