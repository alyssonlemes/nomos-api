from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    """
    Serviço para operações de usuário (Business Logic Layer)
    """
    
    @staticmethod
    def get_by_id(db: Session, user_id: int, organization_id: int) -> Optional[User]:
        """Busca usuário por ID (apenas da organização)"""
        return db.query(User).filter(
            User.id == user_id,
            User.organization_id == organization_id
        ).first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Busca usuário por email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_all(db: Session, organization_id: int = None, skip: int = 0, limit: int = 100) -> List[User]:
        """Lista todos os usuários com paginação (opcionalmente filtrados por organização)"""
        query = db.query(User)
        if organization_id:
            query = query.filter(User.organization_id == organization_id)
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def create(db: Session, user_in: UserCreate) -> User:
        """
        Cria um novo usuário
        
        Args:
            db: Sessão do banco de dados
            user_in: Dados do usuário a ser criado
        
        Returns:
            Usuário criado
        """
        hashed_password = get_password_hash(user_in.password)
        
        db_user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            hashed_password=hashed_password,
            organization_id=user_in.organization_id,
            is_active=True,
            is_superuser=False
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def update(db: Session, user_id: int, user_in: UserUpdate, organization_id: int) -> Optional[User]:
        """
        Atualiza um usuário existente
        
        Args:
            db: Sessão do banco de dados
            user_id: ID do usuário
            user_in: Dados para atualização
            organization_id: ID da organização (validação de propriedade)
        
        Returns:
            Usuário atualizado ou None se não encontrado
        """
        db_user = UserService.get_by_id(db, user_id, organization_id)
        if not db_user:
            return None
        
        update_data = user_in.model_dump(exclude_unset=True)
        
        # Se a senha foi fornecida, fazer hash
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.add(db_user)  # Marca como modificado
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def delete(db: Session, user_id: int, organization_id: int) -> Optional[User]:
        """
        Deleta um usuário
        
        Args:
            db: Sessão do banco de dados
            user_id: ID do usuário
            organization_id: ID da organização (validação de propriedade)
        
        Returns:
            Usuário deletado ou None se não encontrado
        """
        db_user = UserService.get_by_id(db, user_id, organization_id)
        if not db_user:
            return None
        
        db.delete(db_user)
        db.commit()
        return db_user
    
    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Optional[User]:
        """
        Autentica um usuário
        
        Args:
            db: Sessão do banco de dados
            email: Email do usuário
            password: Senha em texto plano
        
        Returns:
            Usuário autenticado ou None se credenciais inválidas
        """
        user = UserService.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    @staticmethod
    def is_active(user: User) -> bool:
        """Verifica se o usuário está ativo"""
        return user.is_active
    
    @staticmethod
    def is_superuser(user: User) -> bool:
        """Verifica se o usuário é superusuário"""
        return user.is_superuser
