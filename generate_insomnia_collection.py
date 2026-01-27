#!/usr/bin/env python3
"""
Script para gerar coleção do Insomnia automaticamente
Gera um arquivo JSON que pode ser importado diretamente no Insomnia
"""

import json
import uuid
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"

def generate_uuid():
    """Gera um UUID único para cada item do Insomnia"""
    return f"req_{uuid.uuid4().hex[:16]}"

def generate_collection():
    """Gera a coleção completa do Insomnia"""
    
    collection = {
        "_type": "export",
        "__export_format": 4,
        "__export_date": datetime.now().isoformat(),
        "__export_source": "nomos-api-generator",
        "resources": []
    }
    
    # Workspace principal
    workspace_id = f"wrk_{uuid.uuid4().hex[:16]}"
    workspace = {
        "_id": workspace_id,
        "parentId": None,
        "modified": int(datetime.now().timestamp() * 1000),
        "created": int(datetime.now().timestamp() * 1000),
        "name": "Nomos API",
        "description": "API REST para gerenciamento jurídico com autenticação JWT",
        "_type": "workspace",
        "scope": "collection"
    }
    collection["resources"].append(workspace)
    
    # Environment
    env_id = f"env_{uuid.uuid4().hex[:16]}"
    environment = {
        "_id": env_id,
        "parentId": workspace_id,
        "modified": int(datetime.now().timestamp() * 1000),
        "created": int(datetime.now().timestamp() * 1000),
        "name": "Base Environment",
        "data": {
            "base_url": BASE_URL,
            "api_prefix": API_PREFIX,
            "token": ""
        },
        "dataPropertyOrder": {
            "&": ["base_url", "api_prefix", "token"]
        },
        "_type": "environment",
        "isPrivate": False
    }
    collection["resources"].append(environment)
    
    # Criar pastas para organizar
    folders = {
        "auth": {
            "_id": f"fld_{uuid.uuid4().hex[:16]}",
            "parentId": workspace_id,
            "name": "🔐 Autenticação",
            "_type": "request_group"
        },
        "users": {
            "_id": f"fld_{uuid.uuid4().hex[:16]}",
            "parentId": workspace_id,
            "name": "👥 Usuários",
            "_type": "request_group"
        },
        "clients": {
            "_id": f"fld_{uuid.uuid4().hex[:16]}",
            "parentId": workspace_id,
            "name": "👤 Clientes",
            "_type": "request_group"
        },
        "legal_actions": {
            "_id": f"fld_{uuid.uuid4().hex[:16]}",
            "parentId": workspace_id,
            "name": "⚖️ Ações Jurídicas",
            "_type": "request_group"
        }
    }
    
    for folder in folders.values():
        folder["modified"] = int(datetime.now().timestamp() * 1000)
        folder["created"] = int(datetime.now().timestamp() * 1000)
        folder["environment"] = {}
        folder["metaSortKey"] = -int(datetime.now().timestamp() * 1000)
        collection["resources"].append(folder)
    
    # Requisições
    requests = []
    
    # ========== AUTENTICAÇÃO ==========
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["auth"]["_id"],
        "name": "Login",
        "description": "Autentica um usuário e retorna um token JWT",
        "method": "POST",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/auth/login",
        "body": {
            "mimeType": "application/json",
            "text": json.dumps({
                "username": "admin",
                "password": "admin123"
            }, indent=2)
        },
        "headers": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    })
    
    # ========== USUÁRIOS ==========
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["users"]["_id"],
        "name": "Registrar Usuário",
        "description": "Cria um novo usuário no sistema",
        "method": "POST",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/users/register",
        "body": {
            "mimeType": "application/json",
            "text": json.dumps({
                "email": "usuario@example.com",
                "username": "novousuario",
                "password": "senha123",
                "full_name": "Nome Completo"
            }, indent=2)
        },
        "headers": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["users"]["_id"],
        "name": "Obter Usuário Atual (Me)",
        "description": "Retorna informações do usuário autenticado",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/users/me",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["users"]["_id"],
        "name": "Listar Usuários",
        "description": "Lista todos os usuários com paginação",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/users?skip=0&limit=100",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["users"]["_id"],
        "name": "Buscar Usuário por ID",
        "description": "Retorna um usuário específico",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/users/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["users"]["_id"],
        "name": "Atualizar Usuário",
        "description": "Atualiza informações de um usuário",
        "method": "PUT",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/users/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "body": {
            "mimeType": "application/json",
            "text": json.dumps({
                "email": "novoemail@example.com",
                "full_name": "Novo Nome Completo"
            }, indent=2)
        },
        "headers": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["users"]["_id"],
        "name": "Deletar Usuário",
        "description": "Remove um usuário do sistema",
        "method": "DELETE",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/users/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    # ========== CLIENTES ==========
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["clients"]["_id"],
        "name": "Criar Cliente",
        "description": "Cria um novo cliente",
        "method": "POST",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/clients",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "body": {
            "mimeType": "application/json",
            "text": json.dumps({
                "name": "João Silva",
                "email": "joao.silva@example.com",
                "phone": "(11) 98765-4321",
                "document": "123.456.789-00",
                "client_type": "individual",
                "status": "active",
                "address": "Rua das Flores, 123",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01234-567",
                "notes": "Cliente novo"
            }, indent=2)
        },
        "headers": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["clients"]["_id"],
        "name": "Listar Clientes",
        "description": "Lista todos os clientes com filtros",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/clients?skip=0&limit=100",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["clients"]["_id"],
        "name": "Listar Clientes com Filtro",
        "description": "Lista clientes filtrando por status e busca",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/clients?skip=0&limit=100&status=active&search=silva",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["clients"]["_id"],
        "name": "Estatísticas de Clientes",
        "description": "Retorna estatísticas dos clientes",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/clients/statistics",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["clients"]["_id"],
        "name": "Buscar Cliente por ID",
        "description": "Retorna um cliente específico",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/clients/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["clients"]["_id"],
        "name": "Atualizar Cliente",
        "description": "Atualiza informações de um cliente",
        "method": "PUT",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/clients/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "body": {
            "mimeType": "application/json",
            "text": json.dumps({
                "name": "João Silva Santos",
                "phone": "(11) 99999-8888",
                "status": "inactive"
            }, indent=2)
        },
        "headers": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["clients"]["_id"],
        "name": "Deletar Cliente",
        "description": "Remove um cliente",
        "method": "DELETE",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/clients/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    # ========== AÇÕES JURÍDICAS ==========
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["legal_actions"]["_id"],
        "name": "Criar Ação Jurídica",
        "description": "Cria uma nova ação jurídica/processo",
        "method": "POST",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/legal-actions",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "body": {
            "mimeType": "application/json",
            "text": json.dumps({
                "number": "1234567-89.2024.8.26.0100",
                "title": "Ação de Cobrança",
                "action_type": "civil",
                "client_id": 1,
                "court": "1ª Vara Cível",
                "judge": "Dr. João da Silva",
                "value": 50000.00,
                "legal_status": "in_progress",
                "description": "Ação de cobrança de valores devidos"
            }, indent=2)
        },
        "headers": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["legal_actions"]["_id"],
        "name": "Listar Ações Jurídicas",
        "description": "Lista todas as ações jurídicas",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/legal-actions?skip=0&limit=100",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["legal_actions"]["_id"],
        "name": "Listar Ações com Filtros",
        "description": "Lista ações filtrando por status e cliente",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/legal-actions?skip=0&limit=100&legal_status=in_progress&client_id=1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["legal_actions"]["_id"],
        "name": "Buscar Ação por ID",
        "description": "Retorna uma ação com todos os detalhes",
        "method": "GET",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/legal-actions/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["legal_actions"]["_id"],
        "name": "Atualizar Ação Jurídica",
        "description": "Atualiza informações de uma ação",
        "method": "PUT",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/legal-actions/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "body": {
            "mimeType": "application/json",
            "text": json.dumps({
                "legal_status": "completed",
                "value": 55000.00,
                "description": "Ação finalizada com acordo"
            }, indent=2)
        },
        "headers": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    })
    
    requests.append({
        "_id": generate_uuid(),
        "parentId": folders["legal_actions"]["_id"],
        "name": "Deletar Ação Jurídica",
        "description": "Remove uma ação jurídica",
        "method": "DELETE",
        "url": "{{ _.base_url }}{{ _.api_prefix }}/legal-actions/1",
        "authentication": {
            "type": "bearer",
            "token": "{{ _.token }}"
        },
        "headers": []
    })
    
    # Adicionar todas as requisições
    for i, req in enumerate(requests):
        req["_type"] = "request"
        req["modified"] = int(datetime.now().timestamp() * 1000)
        req["created"] = int(datetime.now().timestamp() * 1000)
        req["metaSortKey"] = -int(datetime.now().timestamp() * 1000) + i
        req["isPrivate"] = False
        req["settingStoreCookies"] = True
        req["settingSendCookies"] = True
        req["settingDisableRenderRequestBody"] = False
        req["settingEncodeUrl"] = True
        req["settingRebuildPath"] = True
        req["settingFollowRedirects"] = "global"
        collection["resources"].append(req)
    
    return collection


def main():
    """Função principal"""
    print("🚀 Gerando coleção do Insomnia para Nomos API...")
    
    collection = generate_collection()
    
    output_file = "insomnia_collection.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Coleção gerada com sucesso: {output_file}")
    print(f"📦 Total de requisições: {len([r for r in collection['resources'] if r['_type'] == 'request'])}")
    print("\n📖 Para usar:")
    print("   1. Abra o Insomnia")
    print("   2. Clique em 'Import/Export' > 'Import Data' > 'From File'")
    print(f"   3. Selecione o arquivo '{output_file}'")
    print("   4. Faça login primeiro e copie o token retornado")
    print("   5. Cole o token na variável 'token' do Environment")
    print("\n🔐 Não esqueça de:")
    print("   - Iniciar o banco de dados PostgreSQL")
    print("   - Iniciar a API (uvicorn app.main:app --reload)")
    print("   - Criar um usuário ou usar as credenciais de teste")


if __name__ == "__main__":
    main()
