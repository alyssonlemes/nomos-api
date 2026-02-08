"""
Script para verificar o estado do banco de dados e migrations Alembic
IMPORTANTE: Este script NÃO cria tabelas. Use Alembic para gerenciar o schema.
"""
from app.database import engine
from sqlalchemy import text

def check_alembic_version():
    """
    Verifica se o Alembic está inicializado e qual a versão atual
    """
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print("🔍 Verificando status do Alembic...")
    
    if 'alembic_version' not in existing_tables:
        print("  ❌ Tabela 'alembic_version' não encontrada")
        print("\n💡 Para inicializar o banco, execute:")
        print("     alembic upgrade head")
        return False
    
    # Verificar versão atual
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        
        if version:
            print(f"  ✅ Alembic inicializado (versão: {version})")
            return True
        else:
            print("  ⚠️  Alembic configurado mas sem versão aplicada")
            return False

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
    
    print("=" * 70)
    print("   NOMOS API - Database Status Check")
    print("=" * 70)
    print("\n⚠️  Este script apenas VERIFICA o banco. Não cria tabelas.")
    print("   Use Alembic para gerenciar migrations.\n")
    
    try:
        check_alembic_version()
        print()
        all_tables_exist = verify_tables()
        check_constraints()
        
        print("\n" + "=" * 70)
        
        if not all_tables_exist:
            print("\n📝 Comandos úteis do Alembic:")
            print("   alembic upgrade head        # Aplicar todas as migrations")
            print("   alembic downgrade -1        # Reverter última migration")
            print("   alembic current             # Ver versão atual")
            print("   alembic history             # Ver histórico de migrations")
            print("   alembic revision --autogenerate -m 'description'  # Criar nova migration")
        else:
            print("\n✅ Banco de dados está configurado corretamente!")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
