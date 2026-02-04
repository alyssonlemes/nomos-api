# Fluxo do Sistema - Nomos API 🔄

Documentação dos fluxos principais do sistema de gerenciamento jurídico.

---

## 🎯 Visão Geral

O sistema opera em **3 etapas principais**:

1. **Autenticação** → Criar conta e fazer login
2. **Organização** → Criar ou vincular-se a um escritório
3. **Operação** → Gerenciar clientes e processos

---

## 📊 Fluxo 1: Primeiro Acesso (Novo Usuário)

### Opção A: Criar Conta → Criar Organização

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Registrar Usuário                                        │
│    POST /api/v1/users/register                              │
│    • Email, username, password                              │
│    • organization_id: null (ainda não tem)                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Fazer Login                                              │
│    POST /api/v1/auth/login                                  │
│    • Retorna: access_token (JWT)                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Criar Organização                                        │
│    POST /api/v1/organizations                               │
│    • Nome do escritório, CNPJ                               │
│    • Usuário vira proprietário automaticamente              │
│    • organization_id é atualizado no perfil                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ ✅ Pronto! Agora pode:                                      │
│    • Convidar outros usuários                               │
│    • Cadastrar clientes                                     │
│    • Criar ações jurídicas                                  │
└─────────────────────────────────────────────────────────────┘
```

### Opção B: Registro Completo (Tudo de Uma Vez)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Registrar Usuário + Organização                          │
│    POST /api/v1/users/register-with-organization            │
│    • Email, username, password                              │
│    • organization_name, organization_document               │
│    • Cria usuário E organização simultaneamente             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Fazer Login                                              │
│    POST /api/v1/auth/login                                  │
│    • Retorna: access_token (JWT)                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ ✅ Pronto! Já tem organização vinculada                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Fluxo 2: Convite para Organização

### Perspectiva do Proprietário (Owner)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Proprietário Convida Novo Membro                         │
│    POST /api/v1/invitations                                 │
│    • Informa email do convidado                             │
│    • Status: "pending"                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Acompanhar Convites Enviados                             │
│    GET /api/v1/invitations                                  │
│    • Ver status: pending, accepted, rejected                │
└─────────────────────────────────────────────────────────────┘
```

### Perspectiva do Convidado

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Novo Usuário Cria Conta                                  │
│    POST /api/v1/users/register                              │
│    • Usa o MESMO email que recebeu o convite                │
│    • organization_id: null                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Fazer Login                                              │
│    POST /api/v1/auth/login                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Ver Convites Pendentes                                   │
│    GET /api/v1/my-invitations                               │
│    • Lista convites recebidos                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Aceitar Convite                                          │
│    POST /api/v1/invitations/{id}/accept                     │
│    • organization_id é atualizado automaticamente           │
│    • Status do convite: "accepted"                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ ✅ Agora faz parte da organização!                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Fluxo 3: Operação Diária

### Cadastrar Cliente e Criar Processo

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Cadastrar Cliente                                        │
│    POST /api/v1/clients                                     │
│    • Nome, documento (CPF/CNPJ), contatos                   │
│    • Tipo: individual ou business                           │
│    • Status: prospect, active, inactive, archived           │
│    • Retorna: client_id                                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Criar Ação Jurídica                                      │
│    POST /api/v1/legal-actions                               │
│    • Número do processo, título, descrição                  │
│    • Tipo: labor, civil, criminal, etc                      │
│    • Vincula ao client_id                                   │
│    • Status inicial: pre_trial                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Acompanhar Processo                                      │
│    PUT /api/v1/legal-actions/{id}                           │
│    • Atualizar status: filing → litigation → execution      │
│    • Adicionar datas: filing_date, closing_date             │
│    • Alterar informações conforme andamento                 │
└─────────────────────────────────────────────────────────────┘
```

### Consultar Informações

```
┌─────────────────────────────────────────────────────────────┐
│ Listar Clientes                                             │
│    GET /api/v1/clients?search=joão&skip=0&limit=50          │
│    • Buscar por nome, email ou documento                    │
│    • Paginação disponível                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Listar Ações Jurídicas                                      │
│    GET /api/v1/legal-actions?client_id=1&legal_status=...   │
│    • Filtrar por cliente                                    │
│    • Filtrar por status jurídico                            │
│    • Buscar por número ou título                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Ver Membros da Equipe                                       │
│    GET /api/v1/users                                        │
│    GET /api/v1/organizations/users                          │
│    • Lista todos da organização                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Regras de Acesso

### Endpoints Públicos (Sem Token)
- ✅ `POST /api/v1/users/register`
- ✅ `POST /api/v1/users/register-with-organization`
- ✅ `POST /api/v1/auth/login`

### Endpoints Autenticados (Requer Token)
- 🔒 Todos os demais endpoints
- 🔑 Header obrigatório: `Authorization: Bearer {token}`

### Endpoints que Requerem Organização
- 🏢 Listar usuários
- 🏢 Criar/listar/atualizar/deletar clientes
- 🏢 Criar/listar/atualizar/deletar ações jurídicas
- 🏢 Convidar usuários (apenas proprietário)
- 🏢 Listar convites da organização (apenas proprietário)

### Permissões Especiais
- 👑 **Convidar usuários**: Apenas proprietário da organização
- 👑 **Listar convites enviados**: Apenas proprietário
- 👤 **Atualizar/deletar usuário**: Apenas próprio perfil (ou superuser)
- 📋 **Aceitar convite**: Apenas destinatário do email

---

## 📌 Regras de Negócio

### Usuários
- ✅ Email e username devem ser únicos no sistema
- ✅ Usuário pode estar em **apenas uma** organização
- ✅ Pode criar conta sem organização
- ✅ Pode aceitar convite para entrar em organização existente

### Organizações
- ✅ Cada usuário pode criar **apenas uma** organização
- ✅ Quem cria vira **proprietário** automaticamente
- ✅ CNPJ deve ser único (se fornecido)
- ✅ Proprietário pode convidar novos membros

### Clientes
- ✅ Isolados por organização
- ✅ Documento (CPF/CNPJ) único **dentro da organização**
- ✅ Tipos: Pessoa Física ou Pessoa Jurídica
- ✅ Status: Prospect, Active, Inactive, Archived

### Ações Jurídicas
- ✅ Isoladas por organização
- ✅ Número do processo único **no sistema todo**
- ✅ Deve estar vinculada a um cliente
- ✅ 9 tipos: labor, civil, criminal, admin, tax, commercial, family, real_estate, other
- ✅ 7 status: pre_trial, filing, litigation, execution, appeal, finalized, archived

### Convites
- ✅ Apenas proprietário pode convidar
- ✅ Email deve ser o mesmo usado no registro
- ✅ Não pode aceitar se já tiver organização
- ✅ Status: pending, accepted, rejected

---

## 🚀 Exemplo de Uso Completo

```bash
# 1. Criar conta
POST /api/v1/users/register-with-organization
{
  "email": "advogado@escritorio.com",
  "username": "advogado",
  "password": "senha123",
  "full_name": "Dr. Advogado Silva",
  "organization_name": "Silva & Associados",
  "organization_document": "12.345.678/0001-99"
}

# 2. Login
POST /api/v1/auth/login
{
  "username": "advogado",
  "password": "senha123"
}
# Retorna: { "access_token": "eyJhbG..." }

# 3. Cadastrar cliente
POST /api/v1/clients
Authorization: Bearer eyJhbG...
{
  "name": "João da Silva",
  "email": "joao@example.com",
  "document": "123.456.789-00",
  "client_type": "individual",
  "status": "prospect"
}
# Retorna: { "id": 1, ... }

# 4. Criar ação jurídica
POST /api/v1/legal-actions
Authorization: Bearer eyJhbG...
{
  "number": "1234567-89.2026.8.26.0100",
  "title": "Ação Trabalhista - Horas Extras",
  "action_type": "labor",
  "legal_status": "pre_trial",
  "client_id": 1
}

# 5. Convidar secretária
POST /api/v1/invitations
Authorization: Bearer eyJhbG...
{
  "email": "secretaria@escritorio.com"
}

# 6. Listar processos
GET /api/v1/legal-actions?legal_status=litigation&client_id=1
Authorization: Bearer eyJhbG...
```

---

## ✅ Checklist de Setup

### Para Proprietário (Primeiro Usuário)
- [ ] Criar conta (com ou sem organização)
- [ ] Fazer login e guardar token
- [ ] Criar organização (se não criou no registro)
- [ ] Convidar membros da equipe
- [ ] Cadastrar primeiros clientes
- [ ] Criar ações jurídicas

### Para Membro Convidado
- [ ] Criar conta usando o email convidado
- [ ] Fazer login e guardar token
- [ ] Ver convites pendentes
- [ ] Aceitar convite da organização
- [ ] Acessar clientes e processos da equipe

---

**Documentação atualizada em:** 04/02/2026
