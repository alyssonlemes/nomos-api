"""
Script para criar um superuser inicial no sistema

Uso: python create_superuser.py
"""

from app.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization
from app.core.security import get_password_hash


def create_superuser():
    print("="*60)
    print("CRIAR SUPERUSER")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # Dados do superuser
        print("\nDigite os dados do superuser:")
        email = input("Email: ")
        username = input("Username: ")
        password = input("Senha: ")
        full_name = input("Nome completo: ")
        
        # Verificar se já existe
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            print(f"\n❌ ERRO: Usuário com email '{email}' ou username '{username}' já existe!")
            return
        
        # Buscar ou criar organização admin
        org = db.query(Organization).filter(Organization.name == "Admin").first()
        if not org:
            print("\n📦 Criando organização Admin...")
            org = Organization(
                name="Admin",
                document=None,
                is_active=True
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"   ✅ Organização Admin criada (ID: {org.id})")
        
        # Criar superuser
        print("\n👤 Criando superuser...")
        superuser = User(
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            organization_id=org.id,
            is_active=True,
            is_superuser=True  # ← SUPERUSER!
        )
        
        db.add(superuser)
        db.commit()
        db.refresh(superuser)
        
        print("\n" + "="*60)
        print("✅ SUPERUSER CRIADO COM SUCESSO!")
        print("="*60)
        print(f"\nID: {superuser.id}")
        print(f"Email: {superuser.email}")
        print(f"Username: {superuser.username}")
        print(f"Nome: {superuser.full_name}")
        print(f"Organização: {org.name} (ID: {org.id})")
        print(f"Superuser: {superuser.is_superuser}")
        print(f"\n🔑 Você pode fazer login com:")
        print(f"   Username: {superuser.username}")
        print(f"   Password: (a senha que você digitou)")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_superuser()
