# Guia Passo a Passo: Coleta, Treino e Teste da IA de Análise de Processos

> **Pré-requisito:** Banco PostgreSQL gratuito (Neon, Supabase, ElephantSQL, Railway ou local).

---

## Passo 0 — Preparar o Ambiente

### 0.1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 0.2. Configurar o `.env`

Crie o arquivo `.env` na raiz do projeto (copie do `.env.example`):

```env
# Banco PostgreSQL gratuito — cole a URL do seu provider
# Exemplos:
# Neon:       postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/nomos?sslmode=require
# Supabase:   postgresql://postgres:pass@db.xxxx.supabase.co:5432/postgres
# Local:      postgresql://postgres:postgres@localhost:5432/nomos
DATABASE_URL=postgresql://SEU_USER:SUA_SENHA@SEU_HOST:5432/SEU_BANCO

# Chave da API pública do DataJud (obtenha em https://datajud-wiki.cnj.jus.br/api-publica/acesso)
DATAJUD_API_KEY=SUA_CHAVE_AQUI

SECRET_KEY=gere-uma-chave-com-secrets-token-urlsafe
```

> **Dica:** Para gerar a SECRET_KEY rode `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### 0.3. Aplicar todas as migrações no banco

```bash
alembic upgrade head
```

Isso cria todas as tabelas, incluindo `jurimetria_dataset` com os campos de análise.

### 0.4. Subir o servidor

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Passo 1 — Obter um Token de Acesso

Todas as rotas exigem autenticação. Primeiro, faça login:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "seu@email.com", "password": "sua_senha"}'
```

Copie o `access_token` da resposta. Nas próximas chamadas, use:
```
-H "Authorization: Bearer SEU_TOKEN_AQUI"
```

> **Se não tem um usuário ainda**, crie um via `POST /api/auth/register`.

---

## Passo 2 — Verificar Áreas Jurídicas Disponíveis

Antes de coletar, veja quais áreas estão mapeadas:

```bash
curl http://localhost:8000/api/analise/processos/areas-juridicas \
  -H "Authorization: Bearer SEU_TOKEN"
```

**Áreas disponíveis:** Criminal, Família, Cível, Trabalhista, Militar, Tributário, Consumidor, Administrativo.

---

## Passo 3 — Coletar Processos do DataJud (Alimentar o Banco)

### 3.1. Primeira coleta — quantidade pequena para teste

Comece com poucos processos para validar que tudo funciona:

```bash
curl -X POST http://localhost:8000/api/analise/processos/coletar-analisar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tribunal_alias": "tjsp",
    "area_juridica": "Criminal",
    "data_inicio": "2023-01-01",
    "data_fim": "2023-06-30",
    "size": 50,
    "max_paginas": 1
  }'
```

**O que esperar na resposta:**
- `total_processos_encontrados`: quantos existem no DataJud com esse filtro
- `total_processos_processados`: quantos foram baixados nesta chamada
- `total_finalizados`: quantos têm data de encerramento identificada
- `processos`: lista com dados enriquecidos de cada processo
- `estatisticas`: tempo médio, desvio padrão, percentis

### 3.2. Coleta em volume (para treinar o modelo)

O modelo precisa de **no mínimo 500 registros** para treinar. Para um resultado bom, recomendo **2.000+**.

> **⚠️ ATENÇÃO com banco gratuito:** A maioria dos planos free tem limite de linhas/storage. Colete de forma gradual.

**Estratégia de coleta para banco gratuito:**

```bash
# Lote 1 — Criminal TJSP (2023)
curl -X POST http://localhost:8000/api/analise/processos/coletar-analisar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tribunal_alias": "tjsp",
    "area_juridica": "Criminal",
    "data_inicio": "2023-01-01",
    "data_fim": "2023-01-02",
    "size": 200,
    "max_paginas": 3
  }'
```

```bash
# Lote 2 — Cível TJSP (2023)
curl -X POST http://localhost:8000/api/analise/processos/coletar-analisar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tribunal_alias": "tjsp",
    "area_juridica": "Cível",
    "data_inicio": "2023-01-01",
    "data_fim": "2023-12-31",
    "size": 200,
    "max_paginas": 3
  }'
```

```bash
# Lote 3 — Família TJSP (2023)
curl -X POST http://localhost:8000/api/analise/processos/coletar-analisar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tribunal_alias": "tjsp",
    "area_juridica": "Família",
    "data_inicio": "2023-01-01",
    "data_fim": "2023-12-31",
    "size": 200,
    "max_paginas": 3
  }'
```

### 3.3. Coleta com o endpoint batch original (alternativa)

O endpoint antigo também funciona e alimenta o mesmo banco:

```bash
curl -X POST http://localhost:8000/api/integracao/datajud/batch/processos \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tribunal_alias": "tjsp",
    "data_inicio": "2023-01-01",
    "data_fim": "2023-12-31",
    "size": 500
  }'
```

### 3.4. Verificar quantos registros tem no banco

Conecte no seu PostgreSQL e rode:

```sql
-- Total de registros
SELECT COUNT(*) FROM jurimetria_dataset;

-- Registros válidos para treino (com duracao_dias preenchido)
SELECT COUNT(*) FROM jurimetria_dataset WHERE duracao_dias IS NOT NULL;

-- Distribuição por área
SELECT area_juridica_principal, status_processo, COUNT(*)
FROM jurimetria_dataset
GROUP BY area_juridica_principal, status_processo
ORDER BY area_juridica_principal;

-- Distribuição por tribunal
SELECT tribunal, COUNT(*) FROM jurimetria_dataset GROUP BY tribunal;
```

> **Precisa de pelo menos 500 registros com `duracao_dias` preenchido para treinar.**

---

## Passo 4 — Consultar Estatísticas (Sem precisar treinar)

Mesmo sem treinar o modelo, você já pode ver estatísticas dos processos coletados:

```bash
# Estatísticas gerais (todas as áreas)
curl -X POST http://localhost:8000/api/analise/processos/estatisticas \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

```bash
# Estatísticas só de Criminal
curl -X POST http://localhost:8000/api/analise/processos/estatisticas \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"area_juridica": "Criminal"}'
```

```bash
# Estatísticas do TJSP
curl -X POST http://localhost:8000/api/analise/processos/estatisticas \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tribunal": "tjsp"}'
```

**O que a resposta traz:**
```
tempo_medio_dias: 150.5      → "Em média, processos criminais levam 150 dias"
desvio_padrao_dias: 30.2     → "Variação típica de ±30 dias"
percentil_50_dias: 140.0     → "Metade dos processos termina em até 140 dias"
percentil_75_dias: 180.0     → "75% dos processos termina em até 180 dias"
percentil_90_dias: 220.0     → "90% dos processos termina em até 220 dias"
```

---

## Passo 5 — Treinar o Modelo de ML

Quando tiver **500+ registros válidos** no banco:

```bash
curl -X POST http://localhost:8000/api/ml/train \
  -H "Authorization: Bearer SEU_TOKEN"
```

**Resposta esperada:**
```json
{
  "version": "20260302143022",
  "metrics": {
    "mae": 45.2,
    "rmse": 62.8
  },
  "total_records": 1523
}
```

**Interpretando as métricas:**
- `mae` (Mean Absolute Error) = 45.2 → O modelo erra, em média, 45 dias na previsão
- `rmse` (Root Mean Squared Error) = 62.8 → Penaliza erros grandes
- Quanto **menor**, melhor. MAE < 60 dias é um bom começo

> O modelo é salvo automaticamente em `app/ml/models/{version}/` e marcado como ativo.

---

## Passo 6 — Testar Predição da IA

Com o modelo treinado, teste a predição de tempo para um processo real:

### 6.1. Pegar um número de processo

Use um número de processo que exista no DataJud. Você pode pegar da coleta:

```sql
SELECT numero_processo, tribunal FROM jurimetria_dataset LIMIT 5;
```

### 6.2. Fazer a predição

```bash
curl -X POST http://localhost:8000/api/jurimetria/previsao-tempo/tjsp/0001234-56.2023.8.26.0001 \
  -H "Authorization: Bearer SEU_TOKEN"
```

**Resposta:**
```json
{
  "numero_processo": "0001234-56.2023.8.26.0001",
  "tribunal": "tjsp",
  "tempo_total_estimado_dias": 185,
  "tempo_decorrido_dias": 790,
  "tempo_estimado_restante_dias": 0,
  "fonte_dados": "DataJud"
}
```

**Interpretação:**
- `tempo_total_estimado_dias`: a IA prevê que esse processo levará ~185 dias no total
- `tempo_decorrido_dias`: já se passaram 790 dias desde o ajuizamento
- `tempo_estimado_restante_dias`: 0 = provável que já deveria ter encerrado

---

## Passo 7 — Melhorar o Modelo (Iterativo)

### 7.1. Coletar mais dados

Quanto mais dados, melhor o modelo. Colete de mais tribunais e áreas:

```bash
# TJRJ
curl -X POST http://localhost:8000/api/analise/processos/coletar-analisar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tribunal_alias": "tjrj", "area_juridica": "Cível", "data_inicio": "2022-01-01", "data_fim": "2023-12-31", "size": 200, "max_paginas": 5}'

# TJMG
curl -X POST http://localhost:8000/api/analise/processos/coletar-analisar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tribunal_alias": "tjmg", "area_juridica": "Trabalhista", "data_inicio": "2022-01-01", "data_fim": "2023-12-31", "size": 200, "max_paginas": 5}'
```

### 7.2. Retreinar

Cada vez que coletar mais dados, retreine:

```bash
curl -X POST http://localhost:8000/api/ml/train \
  -H "Authorization: Bearer SEU_TOKEN"
```

O novo modelo substitui o anterior automaticamente. Compare o MAE/RMSE entre versões.

### 7.3. Ciclo de melhoria

```
 Coletar (+dados) → Treinar → Avaliar métricas → Repetir
      ↑                                              │
      └──────────────────────────────────────────────┘
```

---

## Limites do Banco Gratuito

| Provider | Limite Free | Recomendação |
|----------|-------------|-------------|
| **Neon** | 512 MB storage | ~50k processos tranquilo |
| **Supabase** | 500 MB storage | ~50k processos tranquilo |
| **ElephantSQL** | 20 MB (Tiny Turtle) | ~2k processos, suficiente para MVP |
| **Railway** | $5 crédito/mês | ~20k processos |
| **Local** | Sem limite | Recomendado para dev |

### Dica para economizar espaço

Se estiver apertado no storage, colete menos processos por vez e foque em **1-2 áreas**:

```bash
# Foco apenas em Criminal para MVP
curl -X POST http://localhost:8000/api/analise/processos/coletar-analisar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tribunal_alias": "tjsp",
    "area_juridica": "Criminal",
    "data_inicio": "2023-06-01",
    "data_fim": "2023-12-31",
    "size": 100,
    "max_paginas": 6
  }'
```

---

## Checklist Resumido

- [ ] `.env` configurado com `DATABASE_URL` e `DATAJUD_API_KEY`
- [ ] `alembic upgrade head` executado
- [ ] Servidor rodando (`uvicorn app.main:app --reload`)
- [ ] Token obtido via `/api/auth/login`
- [ ] Áreas verificadas via `GET /api/analise/processos/areas-juridicas`
- [ ] Coleta teste (50 processos) via `POST /api/analise/processos/coletar-analisar`
- [ ] Coleta em volume (500+ processos válidos)
- [ ] Estatísticas consultadas via `POST /api/analise/processos/estatisticas`
- [ ] Modelo treinado via `POST /api/ml/train`
- [ ] Predição testada via `POST /api/jurimetria/previsao-tempo/{tribunal}/{numero}`
- [ ] Ciclo de melhoria: coletar mais → retreinar → comparar métricas

---

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| `DATAJUD_API_KEY não configurada` | Falta a variável no `.env` | Adicione `DATAJUD_API_KEY=sua_chave` |
| `Erro DataJud: HTTP 401` | Chave inválida ou expirada | Gere nova chave em datajud-wiki.cnj.jus.br |
| `Erro DataJud: HTTP 429` | Rate limit | Aguarde 1 min e tente com `size` menor |
| `Registros insuficientes para treino` | Menos de 500 registros válidos | Colete mais processos (Passo 3) |
| `Modelo ativo não encontrado` | Nenhum modelo treinado | Execute o treino primeiro (Passo 5) |
| `Connection refused` no banco | PostgreSQL offline ou URL errada | Verifique `DATABASE_URL` no `.env` |
| `relation "jurimetria_dataset" does not exist` | Migração não aplicada | Rode `alembic upgrade head` |
