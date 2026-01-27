# Nomos CRM/Jurimetria API

Base URL: `/api`

Autenticação: JWT Bearer. Faça login em `/api/auth/login` e envie `Authorization: Bearer <token>` em todas as rotas protegidas.

## Usuários
- POST `/api/auth/login` — Login
- POST `/api/users/register` — Registrar
- GET `/api/users/me` — Perfil logado
- GET `/api/users` — Listar (paginado)
- GET `/api/users/{id}` — Buscar por ID
- PUT `/api/users/{id}` — Atualizar (apenas o próprio ou superuser)
- DELETE `/api/users/{id}` — Deletar (apenas o próprio ou superuser)

### Exemplo de registro
```json
{
  "email": "alice@example.com",
  "username": "alice",
  "password": "secret123",
  "full_name": "Alice Doe"
}
```

### Payloads
- Login: `{ "username": "alice", "password": "secret123" }`
- Registrar usuário: `{ "email", "username", "password", "full_name?" }

## Clientes (CRM)
- POST `/api/clients` — Criar cliente
- GET `/api/clients` — Listar com filtros (`status`, `search`, `skip`, `limit`)
- GET `/api/clients/statistics` — Estatísticas do usuário
- GET `/api/clients/{id}` — Detalhar
- PUT `/api/clients/{id}` — Atualizar
- DELETE `/api/clients/{id}` — Remover

Campos principais: `name`, `email`, `phone`, `document` (CPF/CNPJ), `client_type` (individual/business), `status` (prospect/active/inactive/archived), endereço, `company_name`, `notes`.

### Payloads
- Criar cliente: `{
  "name": "Cliente X",
  "email": "cliente@example.com",
  "phone": "11999999999",
  "document": "12345678900",
  "client_type": "individual" | "business",
  "status": "prospect" | "active" | "inactive" | "archived",
  "address?": "Rua...",
  "city?": "SP",
  "state?": "SP",
  "zip_code?": "00000-000",
  "notes?": "Observações",
  "company_name?": "Empresa SA"
}`
- Atualizar cliente: mesmos campos, todos opcionais + `is_active?`

## Ações Jurídicas (Case Management)
- POST `/api/legal-actions` — Criar ação
- GET `/api/legal-actions` — Listar com filtros (`legal_status`, `client_id`, `search`, paginação)
- GET `/api/legal-actions/{id}` — Detalhar com partes, movimentações e prazos
- PUT `/api/legal-actions/{id}` — Atualizar
- DELETE `/api/legal-actions/{id}` — Remover
- GET `/api/legal-actions/{id}/statistics` — Estatísticas da ação

Campos principais: `number`, `title`, `description`, `action_type` (labor, civil, criminal, admin, tax, commercial, family, real_estate, other), `legal_status` (pre_trial, filing, litigation, execution, appeal, finalized, archived), `client_id`, tribunal (`court_name`, `court_segment`), datas (`filing_date`, `closing_date`).

### Payloads
- Criar ação: `{
  "number": "0001234-56.2024.8.26.0100",
  "title": "Reclamação trabalhista",
  "description?": "Resumo do caso",
  "action_type": "labor" | "civil" | "criminal" | "admin" | "tax" | "commercial" | "family" | "real_estate" | "other",
  "legal_status": "pre_trial" | "filing" | "litigation" | "execution" | "appeal" | "finalized" | "archived",
  "client_id": 1,
  "court_name?": "TRT 2ª Região",
  "court_segment?": "2ª Vara",
  "filing_date?": "2024-05-10"
}`
- Atualizar ação: mesmos campos, todos opcionais + `closing_date?`, `is_active?`

### Partes (Parties)
- POST `/api/legal-actions/{id}/parties` — Adicionar parte
- PUT `/api/legal-actions/{id}/parties/{party_id}` — Atualizar
- DELETE `/api/legal-actions/{id}/parties/{party_id}` — Remover

Campos: `name`, `party_type` (plaintiff, defendant, third_party, appellant, appellee), `email`, `phone`, `document`, `legal_representative`.

### Payloads
- Criar parte: `{
  "name": "João da Silva",
  "party_type": "plaintiff" | "defendant" | "third_party" | "appellant" | "appellee",
  "email?": "joao@example.com",
  "phone?": "11988887777",
  "document?": "12345678900",
  "legal_representative?": "Dr. Fulano"
}`
- Atualizar parte: mesmos campos, todos opcionais

### Movimentações / Andamentos
- POST `/api/legal-actions/{id}/movements` — Registrar
- PUT `/api/legal-actions/{id}/movements/{movement_id}` — Atualizar
- DELETE `/api/legal-actions/{id}/movements/{movement_id}` — Remover

Campos: `title`, `description`, `movement_type` (hearing, decision, judgment, etc), `movement_date`, `notification_date`, `source`.

### Payloads
- Criar movimentação: `{
  "title": "Audiência inicial",
  "description?": "Descrição do andamento",
  "movement_type": "hearing" | "decision" | "judgment" | "filing" | "appeal" | "compliance" | "notification" | "other",
  "movement_date": "2024-06-01",
  "notification_date?": "2024-06-05",
  "source?": "TJSP"
}`
- Atualizar movimentação: mesmos campos, todos opcionais

### Prazos
- POST `/api/legal-actions/{id}/deadlines` — Criar prazo
- PUT `/api/legal-actions/{id}/deadlines/{deadline_id}` — Atualizar
- DELETE `/api/legal-actions/{id}/deadlines/{deadline_id}` — Remover
- GET `/api/legal-actions/user/pending-deadlines` — Prazos pendentes do usuário
- GET `/api/legal-actions/user/overdue-deadlines` — Prazos vencidos do usuário

Campos: `title`, `description`, `deadline_type`, `due_date`, `status` (pending/completed/overdue/cancelled), `completion_date`.

### Payloads
- Criar prazo: `{
  "title": "Apresentar contestação",
  "description?": "Detalhes do prazo",
  "deadline_type?": "contestacao",
  "due_date": "2024-06-15",
  "status": "pending" | "completed" | "overdue" | "cancelled"
}`
- Atualizar prazo: mesmos campos, todos opcionais + `completion_date?`: "2024-06-10"

## Regras de Segurança
- Todas as rotas (exceto login/registro) exigem token JWT.
- Dados são isolados por usuário: clientes e ações pertencem ao `user_id` logado.
- Validações de unicidade: usuários (email/username), clientes (document), ações (number).

## Checklist de Execução
1. Configurar `.env` com `DATABASE_URL` (ex.: `postgresql://usuario:senha@localhost:5432/nomos`).
2. Instalar dependências: `pip install -r requirements.txt`.
3. Rodar a API: `uvicorn app.main:app --reload`.
4. Abrir docs interativas: `http://localhost:8000/docs`.
