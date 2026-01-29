# Gerenciamento de Organizações - Nomos API

## 📋 Visão Geral

Foram implementados endpoints completos para **criar e gerenciar organizações** e **vincular usuários a elas**. O sistema agora permite tanto o registro tradicional quanto o registro automatizado com criação de organização.

---

## 🆕 Novos Recursos

### ✅ Módulo de Organizações Completo

- **CRUD completo** de organizações
- **Vincular/desvincular** usuários
- **Estatísticas** por organização
- **Listagem de usuários** por organização
- **Permissões** baseadas em superuser

### ✅ Dois Fluxos de Registro

1. **Registro Tradicional**: Usuário em organização existente
2. **Registro com Organização**: Cria usuário + organização simultaneamente

---

## 🔗 Endpoints Criados

### **Organizações** (`/api/v1/organizations`)

| Método | Rota | Descrição | Permissão |
|--------|------|-----------|-----------|
| `POST` | `/organizations` | Criar organização | Superuser |
| `GET` | `/organizations` | Listar organizações | Superuser |
| `GET` | `/organizations/me` | Minha organização (com stats) | Autenticado |
| `GET` | `/organizations/{id}` | Buscar por ID | Superuser ou próprio |
| `PUT` | `/organizations/{id}` | Atualizar organização | Superuser |
| `DELETE` | `/organizations/{id}` | Deletar (soft delete) | Superuser |
| `POST` | `/organizations/{id}/users/{user_id}` | Vincular usuário | Superuser |
| `GET` | `/organizations/{id}/users` | Listar usuários | Autenticado ou Superuser |

### **Registro de Usuários** (atualizado)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/users/register` | Registrar em org existente |
| `POST` | `/users/register-with-organization` | Registrar + criar organização |

---

## 📝 Exemplos de Uso

### 1️⃣ Criar Nova Organização (Requer Superuser)

```bash
POST /api/v1/organizations
Authorization: Bearer {token_superuser}
Content-Type: application/json

{
  "name": "Escritório Silva & Associados",
  "document": "12345678000190"
}
```

**Resposta:**
```json
{
  "id": 1,
  "name": "Escritório Silva & Associados",
  "document": "12345678000190",
  "is_active": true,
  "created_at": "2026-01-29T10:00:00Z",
  "updated_at": null
}
```

---

### 2️⃣ Registrar Usuário com Criação de Organização

**Ideal para o primeiro usuário de um novo escritório!**

```bash
POST /api/v1/users/register-with-organization
Content-Type: application/json

{
  "email": "admin@escritorio.com",
  "username": "admin_escritorio",
  "password": "senha123",
  "full_name": "João Silva",
  "organization_name": "Escritório Silva Advocacia",
  "organization_document": "98765432000190"
}
```

**O que acontece:**
1. ✅ Cria a organização "Escritório Silva Advocacia"
2. ✅ Cria o usuário vinculado automaticamente
3. ✅ Retorna o usuário criado

---

### 3️⃣ Registrar Usuário em Organização Existente

```bash
POST /api/v1/users/register
Content-Type: application/json

{
  "email": "advogado@escritorio.com",
  "username": "joao_advogado",
  "password": "senha123",
  "full_name": "João Advogado",
  "organization_id": 1
}
```

---

### 4️⃣ Ver Minha Organização (com Estatísticas)

```bash
GET /api/v1/organizations/me
Authorization: Bearer {token}
```

**Resposta:**
```json
{
  "id": 1,
  "name": "Escritório Silva & Associados",
  "document": "12345678000190",
  "is_active": true,
  "created_at": "2026-01-29T10:00:00Z",
  "updated_at": null,
  "total_users": 5,
  "total_clients": 120,
  "total_legal_actions": 45
}
```

---

### 5️⃣ Vincular Usuário a Outra Organização (Superuser)

```bash
POST /api/v1/organizations/1/users/5
Authorization: Bearer {token_superuser}
```

Move o usuário ID 5 para a organização ID 1.

---

### 6️⃣ Listar Usuários da Organização

```bash
GET /api/v1/organizations/1/users?skip=0&limit=100
Authorization: Bearer {token}
```

---

## 🔐 Permissões

### **Operações de Superuser**
- Criar organizações
- Listar todas as organizações
- Atualizar/deletar qualquer organização
- Vincular usuários entre organizações

### **Operações de Usuário Normal**
- Ver **apenas** sua própria organização
- Ver estatísticas da sua organização
- Listar usuários **apenas** da sua organização

---

## 📊 Arquivos Criados/Modificados

### Novos Arquivos
- ✅ `app/schemas/organization.py` - Schemas Pydantic
- ✅ `app/services/organization_service.py` - Lógica de negócio
- ✅ `app/api/endpoints/organizations.py` - Endpoints REST

### Arquivos Modificados
- ✅ `app/api/api_router.py` - Registrou rotas de organizações
- ✅ `app/api/endpoints/__init__.py` - Exportou router
- ✅ `app/api/endpoints/users.py` - Adicionou registro com org
- ✅ `app/schemas/user.py` - Adicionou `UserRegisterWithOrg`
- ✅ `Insomnia_Nomos_API.json` - Atualizou coleção

---

## 🧪 Testes no Insomnia

A coleção foi atualizada com **8 novas requisições** na pasta "Organizações":

1. ✅ Criar Organização
2. ✅ Listar Organizações
3. ✅ Minha Organização (com stats)
4. ✅ Buscar Organização por ID
5. ✅ Atualizar Organização
6. ✅ Deletar Organização
7. ✅ Vincular Usuário à Organização
8. ✅ Listar Usuários da Organização

E na pasta "Usuários":

9. ✅ Registrar Usuário com Organização (nova rota)

---

## 🚀 Fluxos Recomendados

### **Cenário 1: Novo Escritório**
1. Use `/users/register-with-organization`
2. Primeiro usuário vira admin do escritório
3. Promova-o a superuser manualmente no banco (se necessário)
4. Convide outros advogados via `/users/register`

### **Cenário 2: Escritório Existente**
1. Admin cria organização via `/organizations` (se for superuser)
2. Convida usuários via `/users/register` com `organization_id`

### **Cenário 3: Migração de Usuário**
1. Superuser usa `/organizations/{id}/users/{user_id}`
2. Usuário é transferido entre organizações

---

## 💡 Dicas

1. **Primeiro Usuário**: Use `register-with-organization` para facilitar
2. **Soft Delete**: Deletar organização apenas desativa (`is_active = false`)
3. **Estatísticas**: Endpoint `/me` mostra totais de usuários, clientes e ações
4. **CNPJ Único**: Sistema valida duplicação de documentos
5. **Isolamento**: Usuários só veem dados da própria organização

---

## ⚠️ Observações

- **Superuser**: Precisa ser criado manualmente no banco ou via script
- **Token**: Todas as rotas (exceto registro) precisam de autenticação
- **Organization ID**: Obrigatório em todas as entidades (User, Client, LegalAction)

---

## 🎯 Próximos Passos (Opcional)

- [ ] Sistema de convites por email
- [ ] Dashboard administrativo para superusers
- [ ] Logs de auditoria em transferências
- [ ] Permissões granulares (roles/permissions)
- [ ] Planos/limites por organização (SaaS)
