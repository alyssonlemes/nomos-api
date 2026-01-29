"""
Script de migração de dados para o sistema de organizações
Execute APÓS aplicar a migração do Alembic

Uso: python migrate_data.py
"""

from app.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.client import Client
from app.models.legal_action import LegalAction


def main():
    print("="*60)
    print("MIGRAÇÃO PARA SISTEMA DE ORGANIZAÇÕES")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 1. Criar organização padrão
        print("\n1. Criando organização padrão...")
        org = Organization(
            name="Escritório Principal",
            document=None,
            is_active=True
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        print(f"   ✅ Organização criada: ID={org.id}, Nome='{org.name}'")
        
        # 2. Atualizar usuários
        print("\n2. Atualizando usuários...")
        users = db.query(User).all()
        for user in users:
            user.organization_id = org.id
            print(f"   - {user.username} → Organização {org.id}")
        print(f"   ✅ {len(users)} usuário(s) atualizado(s)")
        
        # 3. Atualizar clientes  
        print("\n3. Atualizando clientes...")
        clients = db.query(Client).all()
        for client in clients:
            client.organization_id = org.id
            print(f"   - {client.name} → Organização {org.id}")
        print(f"   ✅ {len(clients)} cliente(s) atualizado(s)")
        
        # 4. Atualizar ações jurídicas
        print("\n4. Atualizando ações jurídicas...")
        actions = db.query(LegalAction).all()
        for action in actions:
            action.organization_id = org.id
            print(f"   - {action.title} → Organização {org.id}")
        print(f"   ✅ {len(actions)} ação(ões) atualizada(s)")
        
        # Commit final
        db.commit()
        
        print("\n" + "="*60)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*60)
        print(f"\nOrganização criada: {org.name} (ID: {org.id})")
        print(f"Usuários: {len(users)}")
        print(f"Clientes: {len(clients)}")
        print(f"Ações: {len(actions)}")
        print("\nTodos os dados agora pertencem à organização!")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    response = input("\n⚠️  Este script modificará dados no banco. Continuar? (sim/não): ")
    if response.lower() in ['sim', 's', 'yes', 'y']:
        main()
    else:
        print("Operação cancelada.")
