# Nomos API

API REST moderna com arquitetura escalável para gerenciamento de organizações, usuários, clientes e ações jurídicas usando FastAPI.

## 🚀 Funcionalidades

- ✅ Arquitetura limpa e escalável (Clean Architecture)
- ✅ Autenticação JWT com tokens Bearer
- ✅ CRUD completo de usuários, organizações, clientes e ações jurídicas
- ✅ Sistema de convites para organização
- ✅ Hash de senhas com bcrypt
- ✅ Validação de dados com Pydantic v2
- ✅ Versionamento de API (v1)
- ✅ Separação em camadas (Models, Schemas, Services, Controllers)
- ✅ Documentação automática (Swagger/OpenAPI)
- ✅ CORS configurável
- ✅ Health check endpoint

## 📊 Fluxo de Funcionamento

A API segue um fluxo em **3 etapas principais**:

### **Etapa 1: Registrar Conta** (SEM organização)
```
POST /api/v1/users/register
{
  "email": "user@example.com",
  "username": "username",
  "password": "senha123",
  "full_name": "Nome Completo"
}
```
- Cria uma nova conta de usuário
- Usuário ainda NÃO está vinculado a nenhuma organização
- Necessário para acessar o sistema

### **Etapa 2A: Criar Organização** (Primeira opção)
```
POST /api/v1/auth/login
{
  "username": "username",
  "password": "senha123"
}
```
Após login com JWT token:
```
POST /api/v1/organizations
{
  "name": "Nome da Organização",
  "document": "12.345.678/0001-00"
}
```
- Cria uma nova organização
- Usuário fica como proprietário (owner)
- Usuário é vinculado automaticamente

### **Etapa 2B: Aceitar Convite** (Segunda opção)
```
GET /api/v1/invitations/my-invitations
```
- Listar convites pendentes
- Convites são criados pelo proprietário da organização

```
POST /api/v1/invitations/{invitation_id}/accept
```
- Aceitar convite e ser vinculado à organização

### **Etapa 3: Acessar Outras Telas**
Após ter organização criada:

```
# Gerenciar clientes
GET /api/v1/clients
POST /api/v1/clients
GET /api/v1/clients/{client_id}

# Gerenciar ações jurídicas
GET /api/v1/legal-actions
POST /api/v1/legal-actions
GET /api/v1/legal-actions/{action_id}

# Convidar novos usuários (apenas proprietário)
POST /api/v1/invitations
GET /api/v1/invitations
```

## 📁 Estrutura do Projeto

```
nomos-api/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Aplicação FastAPI principal
│   ├── database.py                # Configuração do banco de dados
│   │
│   ├── core/                      # Configurações centrais
│   │   ├── __init__.py
│   │   ├── config.py              # Settings e variáveis de ambiente
│   │   └── security.py            # Funções de segurança (JWT, hash)
│   │
│   ├── models/                    # Modelos SQLAlchemy (ORM)
│   │   ├── __init__.py
│   │   ├── user.py                # Usuário
│   │   ├── organization.py        # Organização
│   │   ├── invitation.py          # Convite para organização
│   │   ├── client.py              # Cliente
│   │   └── legal_action.py        # Ação Jurídica
│   │
│   ├── schemas/                   # Schemas Pydantic (validação)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── invitation.py
│   │   ├── client.py
│   │   └── legal_action.py
│   │
│   ├── services/                  # Lógica de negócio
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── auth_service.py
│   │   ├── organization_service.py
│   │   ├── invitation_service.py
│   │   ├── client_service.py
│   │   └── legal_action_service.py
│   │
│   └── api/                       # Rotas e endpoints
│       ├── __init__.py
│       ├── api_router.py          # Router agregador
│       ├── deps.py                # Dependencies (auth, db)
│       └── endpoints/
│           ├── __init__.py
│           ├── auth.py            # Autenticação
│           ├── users.py           # Usuários
│           ├── organizations.py   # Organizações
│           ├── invitations.py     # Convites
│           ├── clients.py         # Clientes
│           └── legal_actions.py   # Ações Jurídicas
│           └── endpoints/
│               ├── __init__.py
│               ├── auth.py        # Endpoints de autenticação
│               └── users.py       # Endpoints de usuários
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🏗️ Arquitetura

A aplicação segue uma arquitetura em camadas:

1. **API Layer** (`app/api/`): Endpoints e controllers
2. **Service Layer** (`app/services/`): Lógica de negócio
3. **Data Layer** (`app/models/`): Modelos de banco de dados
4. **Schema Layer** (`app/schemas/`): Validação de entrada/saída
5. **Core Layer** (`app/core/`): Configurações e utilitários

## 📋 Pré-requisitos

- Python 3.8+
- pip

## 🔧 Instalação

1. **Clone o repositório e entre na pasta:**
```bash
cd nomos-api
```

2. **Crie um ambiente virtual (recomendado):**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente:**
```bash
cp .env.example .env
```

Edite o arquivo `.env` e configure:
- `SECRET_KEY`: Gere uma chave segura com `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Outras configurações conforme necessário

## ▶️ Executar

```bash
python -m app.main
```

Ou usando uvicorn diretamente:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em: **http://localhost:8000**

## 📚 Documentação

Acesse a documentação interativa:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 🔑 Endpoints

### 🏠 Root & Health

- `GET /` - Informações da API
- `GET /health` - Health check

### 🔐 Autenticação (`/api/v1/auth`)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/api/v1/auth/login` | Login e obtenção de token | ❌ |

### 👤 Usuários (`/api/v1/users`)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/api/v1/users/register` | Registrar novo usuário | ❌ |
| GET | `/api/v1/users/me` | Obter usuário autenticado | ✅ |
| GET | `/api/v1/users` | Listar todos os usuários | ✅ |
| GET | `/api/v1/users/{id}` | Buscar usuário por ID | ✅ |
| PUT | `/api/v1/users/{id}` | Atualizar usuário | ✅ |
| DELETE | `/api/v1/users/{id}` | Deletar usuário | ✅ |

## 📝 Exemplos de Uso

### 1. Registrar um usuário

```bash
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "username": "usuario123",
    "password": "senhaforte123",
    "full_name": "Nome Completo"
  }'
```

### 2. Fazer login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "usuario123",
    "password": "senhaforte123"
  }'
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Acessar endpoint protegido

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### 4. Listar usuários

```bash
curl -X GET "http://localhost:8000/api/v1/users?skip=0&limit=10" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### 5. Atualizar usuário

```bash
curl -X PUT "http://localhost:8000/api/v1/users/1" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Novo Nome",
    "email": "novoemail@example.com"
  }'
```

## 🛡️ Segurança

- ✅ Senhas hasheadas com **bcrypt**
- ✅ Tokens **JWT** com expiração configurável
- ✅ Validação robusta com **Pydantic v2**
- ✅ Proteção contra duplicação de email/username
- ✅ CORS configurável
- ✅ Bearer token authentication
- ✅ Middleware de segurança

## 🔄 Adicionar Novos Recursos

Para adicionar novos recursos (ex: produtos, pedidos), siga esta estrutura:

1. **Model**: Criar em `app/models/nome_recurso.py`
2. **Schema**: Criar em `app/schemas/nome_recurso.py`
3. **Service**: Criar em `app/services/nome_recurso_service.py`
4. **Endpoint**: Criar em `app/api/v1/endpoints/nome_recurso.py`
5. **Registrar**: Adicionar router em `app/api/v1/api.py`

Exemplo:
```python
# app/api/v1/api.py
from app.api.v1.endpoints import produto_router

api_router.include_router(
    produto_router,
    prefix="/produtos",
    tags=["Produtos"]
)
```

## 📦 Tecnologias

- **FastAPI** - Framework web moderno e rápido
- **SQLAlchemy** - ORM para Python
- **Pydantic v2** - Validação de dados
- **python-jose** - Implementação JWT
- **passlib** - Hash de senhas
- **uvicorn** - Servidor ASGI
- **pydantic-settings** - Gerenciamento de configurações

## 🧪 Testes (Futuro)

```bash
# Instalar pytest
pip install pytest pytest-asyncio httpx

# Executar testes
pytest
```

## 📄 Licença

Este projeto é open source e está disponível sob a licença MIT.
