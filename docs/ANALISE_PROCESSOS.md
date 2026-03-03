# Análise de Processos Judiciais - Feature de IA

## Visão Geral

Feature que permite a um modelo de IA interagir com advogados fornecendo análise completa de processos judiciais, incluindo filtragem por área jurídica e cálculo de tempo médio de tramitação.

## Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                    API REST (FastAPI)                         │
│                                                              │
│  POST /api/analise/processos/coletar-analisar               │
│  POST /api/analise/processos/estatisticas                   │
│  GET  /api/analise/processos/areas-juridicas                │
└──────────┬───────────────────────────────────┬───────────────┘
           │                                   │
           ▼                                   ▼
┌─────────────────────┐          ┌──────────────────────────┐
│ ProcessAnalysis     │          │  TPU Mapping             │
│ Service             │◄────────►│  (tpu_mapping.py)        │
│                     │          │                          │
│ • Coleta DataJud    │          │ • Áreas → Códigos TPU    │
│ • search_after      │          │ • Termos encerramento    │
│ • Análise moviment. │          │ • Classificação auto.    │
│ • Estatísticas      │          └──────────────────────────┘
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐          ┌──────────────────────────┐
│ API DataJud (CNJ)   │          │  PostgreSQL              │
│                     │          │  jurimetria_dataset      │
│ search_after pag.   │          │  (campos enriquecidos)   │
└─────────────────────┘          └──────────────────────────┘
```

## Endpoints

### 1. `POST /api/analise/processos/coletar-analisar`

Coleta processos do DataJud e realiza análise completa.

**Request Body:**
```json
{
    "tribunal_alias": "tjsp",
    "area_juridica": "Criminal",
    "data_inicio": "2023-01-01",
    "data_fim": "2023-12-31",
    "size": 100,
    "usar_search_after": true,
    "max_paginas": 5
}
```

**Campos do filtro:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `tribunal_alias` | string | Sim | Alias do tribunal (tjsp, tjrj, tjmg, etc.) |
| `area_juridica` | string | Não | Área jurídica (Criminal, Família, Cível, Trabalhista, Militar, Tributário, Administrativo, Consumidor) |
| `classe_codigo` | string | Não | Código TPU da classe processual |
| `assunto_codigo` | string | Não | Código TPU do assunto |
| `data_inicio` | date | Não | Data mínima de ajuizamento |
| `data_fim` | date | Não | Data máxima de ajuizamento |
| `size` | int | Não | Processos por página (1-10000, default: 100) |
| `usar_search_after` | bool | Não | Paginação search_after (default: true) |
| `max_paginas` | int | Não | Máximo de páginas (1-100, default: 10) |

**Response:**
```json
{
    "total_processos_encontrados": 15420,
    "total_processos_processados": 500,
    "total_finalizados": 312,
    "total_em_andamento": 188,
    "processos": [
        {
            "numero_processo": "0001234-56.2023.8.26.0000",
            "tribunal": "tjsp",
            "area_juridica_principal": "Criminal",
            "classe_principal": {
                "codigo": "268",
                "nome": "PROCESSO CRIMINAL"
            },
            "assuntos_relacionados": [
                {"codigo": "287", "nome": "DIREITO PENAL"}
            ],
            "data_ajuizamento": "2023-01-01",
            "data_fim": "2023-04-20",
            "duracao_dias": 109,
            "status_processo": "finalizado",
            "movimento_encerramento": "Trânsito em Julgado",
            "movimentos_principais": [
                {"nome": "Trânsito em Julgado", "data_hora": "2023-04-20T16:00:00", "codigo": "848"}
            ]
        }
    ],
    "estatisticas": {
        "area": "Criminal",
        "tempo_medio_dias": 150.5,
        "desvio_padrao_dias": 30.2,
        "total_processos_finalizados": 312,
        "total_processos_em_andamento": 188,
        "percentil_25_dias": 90.0,
        "percentil_50_dias": 140.0,
        "percentil_75_dias": 180.0,
        "percentil_90_dias": 220.0,
        "duracao_minima_dias": 15,
        "duracao_maxima_dias": 730
    }
}
```

### 2. `POST /api/analise/processos/estatisticas`

Consulta estatísticas agregadas dos processos já persistidos no banco.

**Request Body:**
```json
{
    "tribunal": "tjsp",
    "area_juridica": "Criminal"
}
```

**Response:**
```json
{
    "total_geral": 5000,
    "total_finalizados": 3200,
    "total_em_andamento": 1800,
    "estatisticas_por_area": [
        {
            "area": "Criminal",
            "tempo_medio_dias": 150.5,
            "desvio_padrao_dias": 30.2,
            "total_processos_finalizados": 3200,
            "total_processos_em_andamento": 1800,
            "percentil_25_dias": 90.0,
            "percentil_50_dias": 140.0,
            "percentil_75_dias": 180.0,
            "percentil_90_dias": 220.0,
            "duracao_minima_dias": 15,
            "duracao_maxima_dias": 730
        }
    ],
    "estatisticas_por_tribunal": [
        {
            "tribunal": "tjsp",
            "total_processos": 5000,
            "total_finalizados": 3200,
            "total_em_andamento": 1800,
            "tempo_medio_dias": 150.5,
            "areas": [...]
        }
    ]
}
```

### 3. `GET /api/analise/processos/areas-juridicas`

Lista as áreas jurídicas disponíveis com seus códigos TPU.

**Response:**
```json
{
    "areas": [
        {
            "nome": "Criminal",
            "total_classes": 12,
            "total_assuntos": 14,
            "codigos_classes": ["268", "269", "270", ...],
            "codigos_assuntos": ["287", "288", "3603", ...]
        },
        {
            "nome": "Família",
            "total_classes": 16,
            "total_assuntos": 11,
            "codigos_classes": ["22", "23", "25", ...],
            "codigos_assuntos": ["5626", "6105", "6106", ...]
        }
    ]
}
```

## Componentes Criados

### Arquivos Novos

| Arquivo | Descrição |
|---------|-----------|
| `app/services/tpu_mapping.py` | Mapeamento TPU do CNJ - áreas jurídicas → códigos de classe/assunto, termos de encerramento, classificação automática |
| `app/services/process_analysis_service.py` | Serviço principal - coleta DataJud com search_after, análise de movimentos, cálculo de estatísticas |
| `app/schemas/process_analysis.py` | Schemas Pydantic para requests/responses da análise |
| `app/api/endpoints/process_analysis.py` | Endpoints REST da feature |
| `alembic/versions/e2f3g4h5i6j7_add_process_analysis_fields.py` | Migração que adiciona campos ao jurimetria_dataset |

### Arquivos Modificados

| Arquivo | Alteração |
|---------|-----------|
| `app/models/jurimetria_dataset.py` | Adicionados 7 novos campos (area_juridica, data_fim, status, etc.) |
| `app/api/endpoints/__init__.py` | Exporta `process_analysis_router` |
| `app/api/api_router.py` | Registra rota `/analise/processos` |
| `app/schemas/__init__.py` | Exporta novos schemas |
| `app/services/__init__.py` | Exporta `ProcessAnalysisService` |

## Lógica de Negócio

### Inferência de Data de Fim (Seção 3.2 do MD)

A API DataJud não tem campo `dataFim`. A data é inferida dos movimentos:

1. Itera sobre o array `movimentos` de cada processo
2. Busca por nomes contendo termos de encerramento:
   - "Baixa Definitiva", "Arquivamento", "Trânsito em Julgado"
   - "Extinção do Processo", "Julgado Extinto", etc.
3. Também verifica por códigos TPU de movimentação (22, 245, 848, etc.)
4. A `dataHora` do movimento mais recente é a data de fim
5. Se nenhum encontrado → processo em andamento (não entra no cálculo de média)

### Classificação por Área Jurídica (Seção 2)

Ordem de prioridade:
1. **Classe processual** (mais precisa) — ex: código 268 → "Criminal"  
2. **Assuntos** (fallback) — ex: código 287 (DIREITO PENAL) → "Criminal"
3. Se múltiplos assuntos apontam para áreas diferentes, a área com mais matches vence

### Paginação search_after (Seção 1.3)

Diferente de `from/size` (limite 10k), `search_after` permite paginação ilimitada:
- Sort por `@timestamp` + `numeroProcesso.keyword`
- Cada página envia o sort value do último hit como `search_after`
- Rate limiting de 0.5s entre requisições

## Como Usar

### 1. Executar migração
```bash
alembic upgrade head
```

### 2. Configurar variável de ambiente
```env
DATAJUD_API_KEY=sua_chave_aqui
```

### 3. Coletar processos criminais do TJSP
```bash
curl -X POST http://localhost:8000/api/analise/processos/coletar-analisar \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tribunal_alias": "tjsp",
    "area_juridica": "Criminal",
    "data_inicio": "2023-01-01",
    "data_fim": "2023-12-31",
    "size": 100,
    "max_paginas": 5
  }'
```

### 4. Consultar estatísticas
```bash
curl -X POST http://localhost:8000/api/analise/processos/estatisticas \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"area_juridica": "Criminal"}'
```

### 5. Listar áreas disponíveis
```bash
curl http://localhost:8000/api/analise/processos/areas-juridicas \
  -H "Authorization: Bearer <token>"
```

## Integração com Pipeline de ML Existente

Os dados persistidos com os novos campos são automaticamente compatíveis com o pipeline de ML existente:

- O `load_jurimetria_dataset()` continua funcionando (campos originais mantidos)
- O campo `duracao_dias` pode ser usado como target alternativo para treinamento
- O campo `area_juridica_principal` permite treinar modelos especializados por área
- O campo `status_processo` permite filtrar apenas processos finalizados para treino

## Áreas Jurídicas Mapeadas

| Área | Classes TPU | Assuntos TPU |
|------|------------|-------------|
| Criminal | 12 códigos | 14 códigos |
| Família | 16 códigos | 11 códigos |
| Cível | 26 códigos | 12 códigos |
| Trabalhista | 13 códigos | 10 códigos |
| Militar | 6 códigos | 4 códigos |
| Tributário | 6 códigos | 6 códigos |
| Consumidor | 5 códigos | - |
| Administrativo | 5 códigos | 6 códigos |
