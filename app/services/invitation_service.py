from sqlalchemy.orm import Session
from app.models.invitation import Invitation, InvitationStatus
from app.schemas.invitation import InvitationCreate


class InvitationService:
    """Service para operações com convites"""
    
    @staticmethod
    def create(db: Session, email: str, organization_id: int, invited_by_id: int, role: str = None) -> Invitation:
        """Cria um novo convite"""
        # Se já existe um convite aceito para esse email e organização, não criar outro
        existing_accepted = db.query(Invitation).filter(
            Invitation.email == email,
            Invitation.organization_id == organization_id,
            Invitation.status == InvitationStatus.ACCEPTED
        ).first()

        if existing_accepted:
            raise ValueError("User already accepted an invitation for this organization")

        # Se já existe um convite pendente, retorne-o em vez de criar duplicado
        existing_pending = db.query(Invitation).filter(
            Invitation.email == email,
            Invitation.organization_id == organization_id,
            Invitation.status == InvitationStatus.PENDING
        ).first()

        if existing_pending:
            return existing_pending

        invitation = Invitation(
            email=email,
            organization_id=organization_id,
            invited_by_id=invited_by_id,
            status=InvitationStatus.PENDING,
            role=role
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return invitation
    
    @staticmethod
    def get_by_id(db: Session, invitation_id: int) -> Invitation:
        """Busca convite por ID"""
        return db.query(Invitation).filter(Invitation.id == invitation_id).first()
    
    @staticmethod
    def get_pending_by_email(db: Session, email: str) -> list[Invitation]:
        """Busca convites pendentes por email"""
        return db.query(Invitation).filter(
            Invitation.email == email,
            Invitation.status == InvitationStatus.PENDING
        ).all()
    
    @staticmethod
    def get_by_organization(db: Session, organization_id: int, status: str = None) -> list[Invitation]:
        """Busca convites por organização"""
        query = db.query(Invitation).filter(Invitation.organization_id == organization_id)
        
        if status:
            query = query.filter(Invitation.status == status)
        
        return query.all()
    
    @staticmethod
    def accept(db: Session, invitation_id: int) -> Invitation:
        """Aceita um convite"""
        invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()

        if invitation:
            invitation.status = InvitationStatus.ACCEPTED
            db.commit()
            db.refresh(invitation)

        return invitation
    
    @staticmethod
    def reject(db: Session, invitation_id: int) -> Invitation:
        """Rejeita um convite"""
        invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
        
        if invitation:
            invitation.status = InvitationStatus.REJECTED
            db.commit()
            db.refresh(invitation)
        
        return invitation
    
    @staticmethod
    def delete(db: Session, invitation_id: int) -> bool:
        """Deleta um convite"""
        invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
        
        if invitation:
            db.delete(invitation)
            db.commit()
            return True
        
        return False
