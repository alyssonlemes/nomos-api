"""
Script para verificar e inicializar o banco de dados com as tabelas corretas
"""
from app.database import engine, Base
from app.models import User, Organization, Invitation, Client, LegalAction

def create_tables():
    """
    Cria todas as tabelas no banco de dados
    """
    print("🔍 Verificando estrutura do banco de dados...")
    print("📋 Modelos registrados:")
    print(f"  - User")
    print(f"  - Organization")
    print(f"  - Invitation")
    print(f"  - Client")
    print(f"  - LegalAction")
    
    print("\n🔨 Criando tabelas (se não existirem)...")
    Base.metadata.create_all(bind=engine)
    
    print("\n✅ Banco de dados inicializado com sucesso!")
    print("\n📊 Tabelas criadas:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
    
    print("\n🔐 Constraints e índices aplicados:")
    for table_name, table in Base.metadata.tables.items():
        if table.constraints:
            print(f"\n  {table_name}:")
            for constraint in table.constraints:
                constraint_type = type(constraint).__name__
                if hasattr(constraint, 'name') and constraint.name:
                    print(f"    - {constraint_type}: {constraint.name}")
        
        if table.indexes:
            for index in table.indexes:
                if index.name:
                    columns = ', '.join([col.name for col in index.columns])
                    print(f"    - Index: {index.name} ({columns})")

def verify_tables():
    """
    Verifica se todas as tabelas existem
    """
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    expected_tables = ['users', 'organizations', 'invitations', 'clients', 'legal_actions']
    
    print("\n🔍 Verificando tabelas existentes...")
    all_exist = True
    
    for table in expected_tables:
        if table in existing_tables:
            print(f"  ✅ {table}")
        else:
            print(f"  ❌ {table} (não encontrada)")
            all_exist = False
    
    if all_exist:
        print("\n✅ Todas as tabelas estão presentes!")
    else:
        print("\n⚠️  Algumas tabelas estão faltando. Execute create_tables().")
    
    return all_exist

def check_constraints():
    """
    Verifica se as constraints importantes estão aplicadas
    """
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    
    print("\n🔍 Verificando constraints importantes...")
    
    # Verificar constraints em clients
    print("\n  Tabela: clients")
    constraints = inspector.get_unique_constraints('clients')
    has_doc_org_constraint = any(
        set(c.get('column_names', [])) == {'document', 'organization_id'} 
        for c in constraints
    )
    if has_doc_org_constraint:
        print("    ✅ UniqueConstraint(document, organization_id)")
    else:
        print("    ⚠️  UniqueConstraint(document, organization_id) - não encontrada")
    
    # Verificar constraints em invitations
    print("\n  Tabela: invitations")
    constraints = inspector.get_unique_constraints('invitations')
    has_invite_constraint = any(
        set(c.get('column_names', [])) == {'email', 'organization_id', 'status'} 
        for c in constraints
    )
    if has_invite_constraint:
        print("    ✅ UniqueConstraint(email, organization_id, status)")
    else:
        print("    ⚠️  UniqueConstraint(email, organization_id, status) - não encontrada")
    
    # Verificar índices em clients
    print("\n  Índices em clients:")
    indexes = inspector.get_indexes('clients')
    for idx in indexes:
        cols = ', '.join(idx.get('column_names', []))
        print(f"    - {idx.get('name')}: [{cols}]")
    
    # Verificar índices em legal_actions
    print("\n  Índices em legal_actions:")
    indexes = inspector.get_indexes('legal_actions')
    for idx in indexes:
        cols = ', '.join(idx.get('column_names', []))
        print(f"    - {idx.get('name')}: [{cols}]")

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("   NOMOS API - Database Initialization")
    print("=" * 60)
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--verify":
            verify_tables()
            check_constraints()
        else:
            create_tables()
            print("\n" + "=" * 60)
            verify_tables()
            check_constraints()
            print("=" * 60)
            print("\n💡 Dica: Execute 'python init_db.py --verify' para verificar sem criar tabelas")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
