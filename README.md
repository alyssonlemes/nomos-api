# Nomos API 📚⚖️

API para gerenciamento de escritórios de advocacia, incluindo gestão de usuários, organizações, clientes, ações jurídicas e convites.

## 🚀 Tecnologias

- **Python 3.9+**
- **FastAPI** - Framework web moderno e rápido
- **SQLAlchemy** - ORM para banco de dados
- **PostgreSQL** - Banco de dados relacional
- **Alembic** - Gerenciamento de migrations
- **JWT** - Autenticação via tokens
- **Pydantic** - Validação de dados

## ⚙️ Setup e Configuração

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

Configure o arquivo `.env` com as credenciais do banco de dados:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/nomos_db
SECRET_KEY=your-secret-key-here
```

### 3. Aplicar Migrations com Alembic

**IMPORTANTE:** Esta API usa Alembic para gerenciar o schema do banco de dados.

```bash
# Aplicar todas as migrations
alembic upgrade head

# Verificar o status do banco
python init_db.py
```

### 4. Comandos Úteis do Alembic

```bash
# Ver versão atual das migrations
alembic current

# Ver histórico de migrations
alembic history

# Criar uma nova migration (após alterar modelos)
alembic revision --autogenerate -m "descrição da mudança"

# Aplicar próxima migration
alembic upgrade +1

# Reverter última migration
alembic downgrade -1

# Ir para uma revisão específica
alembic upgrade <revision_id>
```

### 5. Iniciar Servidor

```bash
uvicorn app.main:app --reload
```

## 📋 Fluxo da Aplicação

1. **Criar conta** → Registrar usuário
2. **Fazer login** → Obter token JWT
3. **Criar/vincular organização** → Associar a um escritório
4. **Acessar recursos** → Gerenciar clientes, ações jurídicas, etc.

---

## 👤 Usuários (Users)

Endpoints para gerenciamento de usuários.

### 1. Registrar Usuário (Sem Organização)

Cria uma nova conta de usuário **sem** organização obrigatória. Ideal para primeira etapa do fluxo.

**Endpoint:** `POST /api/v1/users/register`

**Body:**
```json
{
  "email": "usuario@example.com",
  "password": "senha123",
  "full_name": "Nome Completo",
  "organization_id": null
}
```

**Campos:**
- `email` (obrigatório) - Email válido e único
- `password` (obrigatório) - Senha com no mínimo 6 caracteres
- `full_name` (opcional) - Nome completo do usuário
- `organization_id` (opcional) - ID de organização existente (pode ser definido depois)

**Resposta (201):**
```json
{
  "id": 1,
  "email": "usuario@example.com",
  "full_name": "Nome Completo",
  "organization_id": null,
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": null
}
```

**Erros:**
- `400` - Email já registrado
- `404` - Organização não encontrada (se organization_id fornecido)

---

### 2. Registrar Usuário com Organização

Cria um novo usuário **E** uma nova organização simultaneamente. Ideal para o primeiro usuário de um novo escritório.

**Endpoint:** `POST /api/v1/users/register-with-organization`

**Body:**
```json
{
  "email": "advogado@escritorio.com",
  "password": "senha123",
  "full_name": "Dr. Advogado Silva",
  "organization_name": "Silva & Associados Advocacia",
  "organization_document": "12.345.678/0001-99"
}
```

**Campos:**
- `email` (obrigatório) - Email válido e único
- `password` (obrigatório) - Senha com no mínimo 6 caracteres
- `full_name` (opcional) - Nome completo
- `organization_name` (obrigatório) - Nome da organização/escritório (3-200 caracteres)
- `organization_document` (opcional) - CNPJ da organização (máx 20 caracteres)

**Resposta (201):**
```json
{
  "id": 1,
  "email": "advogado@escritorio.com",
  "full_name": "Dr. Advogado Silva",
  "organization_id": 1,
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": null
}
```

**Erros:**
- `400` - Email ou documento da organização já existem

---

### 3. Obter Usuário Atual

Retorna as informações do usuário autenticado.

**Endpoint:** `GET /api/v1/users/me`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Resposta (200):**
```json
{
  "id": 1,
  "email": "usuario@example.com",
  "full_name": "Nome Completo",
  "organization_id": 1,
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": "2026-02-04T11:15:00"
}
```

**Erros:**
- `401` - Token inválido ou não fornecido
- `400` - Usuário inativo

---

### 4. Listar Usuários da Organização

Lista todos os usuários da mesma organização do usuário autenticado.

**Endpoint:** `GET /api/v1/users?skip=0&limit=100`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Query Parameters:**
- `skip` (opcional) - Número de registros a pular (padrão: 0)
- `limit` (opcional) - Número máximo de registros (padrão: 100)

**Resposta (200):**
```json
[
  {
    "id": 1,
    "email": "usuario1@example.com",
    "full_name": "Usuário Um",
    "organization_id": 1,
    "is_active": true,
    "is_superuser": false,
    "created_at": "2026-02-04T10:30:00",
    "updated_at": null
  },
  {
    "id": 2,
    "email": "usuario2@example.com",
    "full_name": "Usuário Dois",
    "organization_id": 1,
    "is_active": true,
    "is_superuser": false,
    "created_at": "2026-02-04T11:00:00",
    "updated_at": null
  }
]
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização

---

### 5. Buscar Usuário por ID

Busca um usuário específico da mesma organização.

**Endpoint:** `GET /api/v1/users/{user_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `user_id` - ID do usuário

**Resposta (200):**
```json
{
  "id": 2,
  "email": "usuario2@example.com",
  "full_name": "Usuário Dois",
  "organization_id": 1,
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-02-04T11:00:00",
  "updated_at": null
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `404` - Usuário não encontrado

---

### 6. Atualizar Usuário

Atualiza os dados de um usuário. Usuários só podem atualizar seus próprios dados (exceto superusuários).

**Endpoint:** `PUT /api/v1/users/{user_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `user_id` - ID do usuário

**Body:**
```json
{
  "email": "novoemail@example.com",
  "full_name": "Novo Nome Completo",
  "password": "novasenha123",
  "is_active": true
}
```

**Campos (todos opcionais):**
- `email` - Novo email
- `full_name` - Novo nome completo
- `password` - Nova senha (mínimo 6 caracteres)
- `is_active` - Status ativo/inativo

**Resposta (200):**
```json
{
  "id": 1,
  "email": "novoemail@example.com",
  "full_name": "Novo Nome Completo",
  "organization_id": 1,
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": "2026-02-04T12:00:00"
}
```

**Erros:**
- `401` - Token inválido
- `403` - Tentativa de atualizar outro usuário
- `400` - Email já existe
- `404` - Usuário não encontrado

---

### 7. Deletar Usuário

Deleta um usuário. Usuários só podem deletar seus próprios perfis (exceto superusuários).

**Endpoint:** `DELETE /api/v1/users/{user_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `user_id` - ID do usuário

**Resposta (204):**
```
No Content
```

**Erros:**
- `401` - Token inválido
- `403` - Tentativa de deletar outro usuário
- `404` - Usuário não encontrado

---

## 🔐 Autenticação

### Login

Autentica um usuário e retorna um token JWT.

**Endpoint:** `POST /api/v1/auth/login`

**Body:**
```json
{
  "email": "usuario@example.com",
  "password": "senha123"
}
```

**Resposta (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Erros:**
- `401` - Email ou senha incorretos

**Como usar o token:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📝 Notas Importantes

### Fluxo Recomendado

1. **Novo Usuário:**
   - Opção A: `POST /api/v1/users/register` → `POST /api/v1/auth/login` → `POST /api/v1/organizations`
   - Opção B: `POST /api/v1/users/register-with-organization` → `POST /api/v1/auth/login`

2. **Após Login:**
   - Todas as requisições devem incluir o token JWT no header `Authorization`
   - Recursos como clientes e ações jurídicas requerem que o usuário tenha uma organização

3. **Proteção de Rotas:**
   - ✅ Não requer organização: Login, Registro, Atualizar próprio perfil
   - 🔒 Requer organização: Listar usuários, Criar clientes, Criar ações jurídicas

---

## 🏢 Organizações (Organizations)

Endpoints para gerenciamento de organizações/escritórios de advocacia.

### 1. Criar Organização

Cria uma nova organização e vincula automaticamente o usuário autenticado como proprietário.

**Endpoint:** `POST /api/v1/organizations`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Body:**
```json
{
  "name": "Silva & Associados Advocacia",
  "document": "12.345.678/0001-99"
}
```

**Campos:**
- `name` (obrigatório) - Nome da organização/escritório (3-200 caracteres)
- `document` (opcional) - CNPJ da organização (máx 20 caracteres)

**Resposta (201):**
```json
{
  "id": 1,
  "name": "Silva & Associados Advocacia",
  "document": "12.345.678/0001-99",
  "owner_id": 1,
  "is_active": true,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": null
}
```

**Erros:**
- `401` - Token inválido
- `400` - Usuário já possui uma organização
- `400` - Documento (CNPJ) já cadastrado

**Observações:**
- Cada usuário pode criar apenas **uma** organização
- O usuário que cria se torna automaticamente o proprietário
- Após criar, o `organization_id` do usuário é atualizado automaticamente

---

### 2. Obter Minha Organização

Retorna a organização do usuário autenticado.

**Endpoint:** `GET /api/v1/organizations`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Resposta (200):**
```json
{
  "id": 1,
  "name": "Silva & Associados Advocacia",
  "document": "12.345.678/0001-99",
  "owner_id": 1,
  "is_active": true,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": "2026-02-04T11:00:00"
}
```

**Erros:**
- `401` - Token inválido
- `404` - Usuário não possui uma organização

---

### 3. Atualizar Organização

Atualiza os dados da organização do usuário autenticado.

**Endpoint:** `PUT /api/v1/organizations`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Body:**
```json
{
  "name": "Silva Advocacia Ltda",
  "document": "98.765.432/0001-11",
  "is_active": true
}
```

**Campos (todos opcionais):**
- `name` - Novo nome (3-200 caracteres)
- `document` - Novo documento/CNPJ (máx 20 caracteres)
- `is_active` - Status ativo/inativo

**Resposta (200):**
```json
{
  "id": 1,
  "name": "Silva Advocacia Ltda",
  "document": "98.765.432/0001-11",
  "owner_id": 1,
  "is_active": true,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": "2026-02-04T14:30:00"
}
```

**Erros:**
- `401` - Token inválido
- `404` - Usuário não possui organização
- `400` - Documento já cadastrado em outra organização

---

### 4. Listar Usuários da Organização

Lista todos os usuários/membros da organização.

**Endpoint:** `GET /api/v1/organizations/users`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Resposta (200):**
```json
[
  {
    "id": 1,
    "email": "advogado@escritorio.com",
    "full_name": "Dr. Advogado Silva",
    "organization_id": 1,
    "is_active": true,
    "is_superuser": false,
    "created_at": "2026-02-04T10:00:00",
    "updated_at": null
  },
  {
    "id": 2,
    "email": "secretaria@escritorio.com",
    "full_name": "Maria Secretária",
    "organization_id": 1,
    "is_active": true,
    "is_superuser": false,
    "created_at": "2026-02-04T11:30:00",
    "updated_at": null
  }
]
```

**Erros:**
- `401` - Token inválido
- `404` - Usuário não possui organização

---

## ✉️ Convites (Invitations)

Sistema de convites para adicionar usuários a organizações existentes.

### 1. Convidar Usuário

Convida um usuário (por email) para fazer parte da organização. **Apenas superusuários** podem enviar convites.

**Endpoint:** `POST /api/v1/invitations`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Body:**
```json
{
  "email": "novomembro@example.com"
}
```

**Campos:**
- `email` (obrigatório) - Email do usuário a convidar

**Resposta (201):**
```json
{
  "id": 1,
  "email": "novomembro@example.com",
  "organization_id": 1,
  "status": "pending",
  "created_at": "2026-02-04T10:30:00",
  "updated_at": null
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização ou não é superusuário
- `400` - Convite pendente já existe para este email
- `400` - Usuário já faz parte da organização

---

### 2. Listar Convites da Organização

Lista todos os convites enviados pela organização. **Apenas superusuários** podem listar.

**Endpoint:** `GET /api/v1/invitations?status=pending&skip=0&limit=100`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Query Parameters:**
- `status` (opcional) - Filtrar por status: `pending`, `accepted`, `rejected`
- `skip` (opcional) - Número de registros a pular (padrão: 0)
- `limit` (opcional) - Número máximo de registros (padrão: 100)

**Resposta (200):**
```json
{
  "total": 2,
  "invitations": [
    {
      "id": 1,
      "email": "novomembro@example.com",
      "organization_id": 1,
      "organization_name": "Silva & Associados Advocacia",
      "invited_by_email": "advogado@escritorio.com",
      "status": "pending",
      "created_at": "2026-02-04T10:30:00",
      "updated_at": null
    },
    {
      "id": 2,
      "email": "outro@example.com",
      "organization_id": 1,
      "organization_name": "Silva & Associados Advocacia",
      "invited_by_email": "advogado@escritorio.com",
      "status": "accepted",
      "created_at": "2026-02-04T09:00:00",
      "updated_at": "2026-02-04T09:30:00"
    }
  ]
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização ou não é superusuário

---

### 3. Listar Meus Convites Pendentes

Lista todos os convites pendentes recebidos pelo usuário autenticado. Estes são convites que o usuário pode aceitar para entrar em organizações.

**Endpoint:** `GET /api/v1/my-invitations?skip=0&limit=100`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Query Parameters:**
- `skip` (opcional) - Número de registros a pular (padrão: 0)
- `limit` (opcional) - Número máximo de registros (padrão: 100)

**Resposta (200):**
```json
{
  "total": 1,
  "invitations": [
    {
      "id": 3,
      "email": "meu@email.com",
      "organization_id": 5,
      "organization_name": "Escritório XYZ Advogados",
      "invited_by_email": "proprietario@xyz.com",
      "status": "pending",
      "created_at": "2026-02-04T11:00:00",
      "updated_at": null
    }
  ]
}
```

**Erros:**
- `401` - Token inválido

---

### 4. Aceitar Convite

Aceita um convite e vincula o usuário à organização. Esta é a **Opção 2** para vincular-se a uma organização (alternativa a criar a própria).

**Endpoint:** `POST /api/v1/invitations/{invitation_id}/accept`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `invitation_id` - ID do convite

**Resposta (200):**
```json
{
  "id": 3,
  "email": "meu@email.com",
  "organization_id": 5,
  "status": "accepted",
  "created_at": "2026-02-04T11:00:00",
  "updated_at": "2026-02-04T11:30:00"
}
```

**Erros:**
- `401` - Token inválido
- `403` - Convite não é para o usuário autenticado
- `404` - Convite não encontrado
- `400` - Convite já foi aceito/rejeitado
- `400` - Usuário já possui organização

**Observações:**
- Após aceitar, o `organization_id` do usuário é automaticamente atualizado
- Usuários só podem estar em **uma** organização por vez
- Apenas o destinatário (email do convite) pode aceitar

---

### 5. Rejeitar Convite

Rejeita um convite de organização.

**Endpoint:** `POST /api/v1/invitations/{invitation_id}/reject`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `invitation_id` - ID do convite

**Resposta (200):**
```json
{
  "id": 3,
  "email": "meu@email.com",
  "organization_id": 5,
  "status": "rejected",
  "created_at": "2026-02-04T11:00:00",
  "updated_at": "2026-02-04T12:00:00"
}
```

**Erros:**
- `401` - Token inválido
- `403` - Convite não é para o usuário autenticado
- `404` - Convite não encontrado
- `400` - Convite já foi aceito/rejeitado

---

## 👥 Clientes (Clients)

Gerenciamento de clientes da organização. **Requer que o usuário tenha uma organização.**

### 1. Criar Cliente

Cria um novo cliente vinculado à organização do usuário autenticado.

**Endpoint:** `POST /api/v1/clients`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Body:**
```json
{
  "name": "João da Silva",
  "email": "joao@example.com",
  "phone": "(11) 98765-4321",
  "document": "123.456.789-00",
  "client_type": "individual",
  "status": "prospect",
  "address": "Rua das Flores, 123",
  "city": "São Paulo",
  "state": "SP",
  "zip_code": "01234-567",
  "company_name": null
}
```

**Campos:**
- `name` (obrigatório) - Nome do cliente (3-200 caracteres)
- `email` (opcional) - Email do cliente
- `phone` (opcional) - Telefone (máx 20 caracteres)
- `document` (obrigatório) - CPF/CNPJ do cliente
- `client_type` (opcional) - Tipo: `individual` (pessoa física) ou `business` (pessoa jurídica), padrão: `individual`
- `status` (opcional) - Status: `active`, `inactive`, `prospect`, `archived`, padrão: `prospect`
- `address` (opcional) - Endereço completo
- `city` (opcional) - Cidade
- `state` (opcional) - Estado (2 caracteres, ex: SP)
- `zip_code` (opcional) - CEP
- `company_name` (opcional) - Nome da empresa (para pessoa jurídica)

**Resposta (201):**
```json
{
  "id": 1,
  "name": "João da Silva",
  "email": "joao@example.com",
  "phone": "(11) 98765-4321",
  "document": "123.456.789-00",
  "client_type": "individual",
  "status": "prospect",
  "address": "Rua das Flores, 123",
  "city": "São Paulo",
  "state": "SP",
  "zip_code": "01234-567",
  "company_name": null,
  "organization_id": 1,
  "user_id": 1,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": null
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `400` - Cliente com este documento já cadastrado na organização

---

### 2. Listar Clientes

Lista todos os clientes da organização com suporte a paginação e busca.

**Endpoint:** `GET /api/v1/clients?skip=0&limit=100&search=joão`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Query Parameters:**
- `skip` (opcional) - Número de registros a pular (padrão: 0)
- `limit` (opcional) - Número máximo de registros (padrão: 100, máx: 500)
- `search` (opcional) - Busca por nome, email ou documento

**Resposta (200):**
```json
{
  "total": 2,
  "clients": [
    {
      "id": 1,
      "name": "João da Silva",
      "email": "joao@example.com",
      "phone": "(11) 98765-4321",
      "document": "123.456.789-00",
      "client_type": "individual",
      "status": "active",
      "address": "Rua das Flores, 123",
      "city": "São Paulo",
      "state": "SP",
      "zip_code": "01234-567",
      "company_name": null,
      "organization_id": 1,
      "user_id": 1,
      "created_at": "2026-02-04T10:30:00",
      "updated_at": "2026-02-04T11:00:00"
    },
    {
      "id": 2,
      "name": "Maria Santos",
      "email": "maria@example.com",
      "phone": "(11) 91234-5678",
      "document": "987.654.321-00",
      "client_type": "individual",
      "status": "prospect",
      "address": null,
      "city": "Rio de Janeiro",
      "state": "RJ",
      "zip_code": null,
      "company_name": null,
      "organization_id": 1,
      "user_id": 1,
      "created_at": "2026-02-04T11:30:00",
      "updated_at": null
    }
  ]
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização

---

### 3. Buscar Cliente por ID

Busca um cliente específico da organização.

**Endpoint:** `GET /api/v1/clients/{client_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `client_id` - ID do cliente

**Resposta (200):**
```json
{
  "id": 1,
  "name": "João da Silva",
  "email": "joao@example.com",
  "phone": "(11) 98765-4321",
  "document": "123.456.789-00",
  "client_type": "individual",
  "status": "active",
  "address": "Rua das Flores, 123",
  "city": "São Paulo",
  "state": "SP",
  "zip_code": "01234-567",
  "company_name": null,
  "organization_id": 1,
  "user_id": 1,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": "2026-02-04T11:00:00"
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `404` - Cliente não encontrado

---

### 4. Atualizar Cliente

Atualiza os dados de um cliente da organização.

**Endpoint:** `PUT /api/v1/clients/{client_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `client_id` - ID do cliente

**Body:**
```json
{
  "name": "João da Silva Souza",
  "email": "joao.novo@example.com",
  "phone": "(11) 99999-9999",
  "document": "123.456.789-00",
  "client_type": "individual",
  "status": "active"
}
```

**Campos (todos opcionais):**
- `name` - Novo nome (3-200 caracteres)
- `email` - Novo email
- `phone` - Novo telefone
- `document` - Novo documento
- `client_type` - Novo tipo (`individual` ou `business`)
- `status` - Novo status (`active`, `inactive`, `prospect`, `archived`)

**Resposta (200):**
```json
{
  "id": 1,
  "name": "João da Silva Souza",
  "email": "joao.novo@example.com",
  "phone": "(11) 99999-9999",
  "document": "123.456.789-00",
  "client_type": "individual",
  "status": "active",
  "address": "Rua das Flores, 123",
  "city": "São Paulo",
  "state": "SP",
  "zip_code": "01234-567",
  "company_name": null,
  "organization_id": 1,
  "user_id": 1,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": "2026-02-04T15:00:00"
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `404` - Cliente não encontrado
- `400` - Documento já cadastrado para outro cliente

---

### 5. Deletar Cliente

Deleta um cliente da organização.

**Endpoint:** `DELETE /api/v1/clients/{client_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `client_id` - ID do cliente

**Resposta (204):**
```
No Content
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `404` - Cliente não encontrado

---

**Observações sobre Clientes:**
- Clientes são isolados por organização
- Documentos (CPF/CNPJ) devem ser únicos **dentro da organização**
- Suporta busca por nome, email ou documento
- Tipos: `individual` (pessoa física) ou `business` (pessoa jurídica)
- Status: `active`, `inactive`, `prospect`, `archived`

---

## ⚖️ Ações Jurídicas (Legal Actions)

Gerenciamento de ações jurídicas/processos da organização. **Requer que o usuário tenha uma organização.**

### 1. Criar Ação Jurídica

Cria uma nova ação jurídica/processo vinculada à organização e a um cliente.

**Endpoint:** `POST /api/v1/legal-actions`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Body:**
```json
{
  "number": "1234567-89.2026.8.26.0100",
  "title": "Ação Trabalhista - Horas Extras",
  "description": "Ação de cobrança de horas extras não pagas",
  "action_type": "labor",
  "legal_status": "pre_trial",
  "court_name": "1ª Vara do Trabalho de São Paulo",
  "filing_date": "2026-02-01",
  "client_id": 1
}
```

**Campos:**
- `number` (obrigatório) - Número único do processo (mínimo 3 caracteres)
- `title` (obrigatório) - Título da ação (mínimo 3 caracteres)
- `description` (opcional) - Descrição detalhada
- `action_type` (obrigatório) - Tipo da ação:
  - `labor` - Trabalhista
  - `civil` - Cível
  - `criminal` - Criminal
  - `admin` - Administrativa
  - `tax` - Tributária
  - `commercial` - Comercial
  - `family` - Família
  - `real_estate` - Imóvel
  - `other` - Outra
- `legal_status` (opcional) - Status jurídico, padrão: `pre_trial`:
  - `pre_trial` - Pré-processual
  - `filing` - Ajuizamento
  - `litigation` - Contencioso
  - `execution` - Execução
  - `appeal` - Recurso
  - `finalized` - Finalizado
  - `archived` - Arquivado
- `court_name` (opcional) - Nome do tribunal/vara
- `filing_date` (opcional) - Data de ajuizamento (formato: YYYY-MM-DD)
- `client_id` (obrigatório) - ID do cliente relacionado

**Resposta (201):**
```json
{
  "id": 1,
  "number": "1234567-89.2026.8.26.0100",
  "title": "Ação Trabalhista - Horas Extras",
  "description": "Ação de cobrança de horas extras não pagas",
  "action_type": "labor",
  "legal_status": "pre_trial",
  "court_name": "1ª Vara do Trabalho de São Paulo",
  "filing_date": "2026-02-01",
  "closing_date": null,
  "client_id": 1,
  "organization_id": 1,
  "user_id": 1,
  "is_active": true,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": null
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `400` - Número de processo já existe

---

### 2. Listar Ações Jurídicas

Lista todas as ações jurídicas da organização com suporte a filtros e busca.

**Endpoint:** `GET /api/v1/legal-actions?skip=0&limit=100&legal_status=litigation&client_id=1&search=trabalhista`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Query Parameters:**
- `skip` (opcional) - Número de registros a pular (padrão: 0)
- `limit` (opcional) - Número máximo de registros (padrão: 100, máx: 500)
- `legal_status` (opcional) - Filtrar por status: `pre_trial`, `filing`, `litigation`, `execution`, `appeal`, `finalized`, `archived`
- `client_id` (opcional) - Filtrar por ID do cliente
- `search` (opcional) - Buscar por número ou título

**Resposta (200):**
```json
{
  "total": 2,
  "legal_actions": [
    {
      "id": 1,
      "number": "1234567-89.2026.8.26.0100",
      "title": "Ação Trabalhista - Horas Extras",
      "description": "Ação de cobrança de horas extras não pagas",
      "action_type": "labor",
      "legal_status": "litigation",
      "court_name": "1ª Vara do Trabalho de São Paulo",
      "filing_date": "2026-02-01",
      "closing_date": null,
      "client_id": 1,
      "organization_id": 1,
      "user_id": 1,
      "is_active": true,
      "created_at": "2026-02-04T10:30:00",
      "updated_at": "2026-02-04T11:00:00"
    },
    {
      "id": 2,
      "number": "9876543-21.2026.8.26.0200",
      "title": "Ação Cível - Cobrança",
      "description": "Cobrança de valores não pagos",
      "action_type": "civil",
      "legal_status": "pre_trial",
      "court_name": "2ª Vara Cível de São Paulo",
      "filing_date": "2026-02-03",
      "closing_date": null,
      "client_id": 2,
      "organization_id": 1,
      "user_id": 1,
      "is_active": true,
      "created_at": "2026-02-04T11:30:00",
      "updated_at": null
    }
  ]
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização

---

### 3. Buscar Ação Jurídica por ID

Busca uma ação jurídica específica da organização.

**Endpoint:** `GET /api/v1/legal-actions/{action_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `action_id` - ID da ação jurídica

**Resposta (200):**
```json
{
  "id": 1,
  "number": "1234567-89.2026.8.26.0100",
  "title": "Ação Trabalhista - Horas Extras",
  "description": "Ação de cobrança de horas extras não pagas",
  "action_type": "labor",
  "legal_status": "litigation",
  "court_name": "1ª Vara do Trabalho de São Paulo",
  "filing_date": "2026-02-01",
  "closing_date": null,
  "client_id": 1,
  "organization_id": 1,
  "user_id": 1,
  "is_active": true,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": "2026-02-04T11:00:00"
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `404` - Ação jurídica não encontrada

---

### 4. Atualizar Ação Jurídica

Atualiza os dados de uma ação jurídica da organização.

**Endpoint:** `PUT /api/v1/legal-actions/{action_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `action_id` - ID da ação jurídica

**Body:**
```json
{
  "title": "Ação Trabalhista - Horas Extras e Adicionais",
  "description": "Ação de cobrança de horas extras e adicional noturno",
  "action_type": "labor",
  "legal_status": "litigation",
  "court_name": "1ª Vara do Trabalho de São Paulo",
  "filing_date": "2026-02-01",
  "closing_date": null
}
```

**Campos (todos opcionais):**
- `title` - Novo título (mínimo 3 caracteres)
- `description` - Nova descrição
- `action_type` - Novo tipo
- `legal_status` - Novo status
- `court_name` - Novo tribunal
- `filing_date` - Nova data de ajuizamento
- `closing_date` - Data de encerramento

**Resposta (200):**
```json
{
  "id": 1,
  "number": "1234567-89.2026.8.26.0100",
  "title": "Ação Trabalhista - Horas Extras e Adicionais",
  "description": "Ação de cobrança de horas extras e adicional noturno",
  "action_type": "labor",
  "legal_status": "litigation",
  "court_name": "1ª Vara do Trabalho de São Paulo",
  "filing_date": "2026-02-01",
  "closing_date": null,
  "client_id": 1,
  "organization_id": 1,
  "user_id": 1,
  "is_active": true,
  "created_at": "2026-02-04T10:30:00",
  "updated_at": "2026-02-04T15:00:00"
}
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `404` - Ação jurídica não encontrada

---

### 5. Deletar Ação Jurídica

Deleta uma ação jurídica da organização.

**Endpoint:** `DELETE /api/v1/legal-actions/{action_id}`

**Headers:**
```
Authorization: Bearer <token_jwt>
```

**Parâmetros:**
- `action_id` - ID da ação jurídica

**Resposta (204):**
```
No Content
```

**Erros:**
- `401` - Token inválido
- `403` - Usuário não possui organização
- `404` - Ação jurídica não encontrada

---

**Observações sobre Ações Jurídicas:**
- Ações são isoladas por organização
- Número do processo deve ser único **no sistema todo**
- Deve estar vinculada a um cliente existente
- Suporta busca por número ou título
- 9 tipos de ações disponíveis
- 7 status jurídicos para acompanhamento do processo
- Campos de data (filing_date, closing_date) em formato ISO (YYYY-MM-DD)

---

*Documentação completa!* 🎉
