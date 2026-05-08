# Jurimetria em Producao - DataJud + ML

Este documento descreve o fluxo atual em producao: coleta no DataJud, preparacao do dataset, treino do modelo e predicao por processo.

## 1) Configuracao

Defina a variavel de ambiente:

```env
DATAJUD_API_KEY=seu_token
```

A chave e usada pelos servicos:
- app/services/datajud_batch_service.py
- app/services/process_analysis_service.py
- app/services/jurimetria_prediction_service.py

---

## 2) Integracao com DataJud

Atualmente existem dois fluxos de coleta.

### 2.1 Coleta batch simples (integracao)

Endpoint:

```http
POST /api/v1/integracao/datajud/batch/processos
```

Body (exemplo):

```json
{
  "tribunal_alias": "tjsp",
  "data_inicio": "2023-01-01",
  "data_fim": "2023-12-31",
  "classe_processual": "Procedimento Comum",
  "assunto_codigo": "10010",
  "size": 100
}
```

Este fluxo:
- pagina com from/size
- persiste dados basicos no PostgreSQL
- nao calcula duracao_dias automaticamente

### 2.2 Coleta + analise de processos (recomendado para ML)

Endpoint:

```http
POST /api/v1/analise/processos/coletar-analisar
```

Body (exemplo):

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

Este fluxo:
- coleta no DataJud (com suporte a search_after)
- identifica movimento de encerramento
- infere data_fim
- calcula duracao_dias para processos finalizados
- classifica area_juridica_principal
- persiste dataset enriquecido para treino

Endpoint auxiliar:

```http
GET /api/v1/analise/processos/areas-juridicas
```

Permite consultar as areas juridicas disponiveis no mapeamento TPU.

---

## 3) Tabela jurimetria_dataset

A tabela de treino e inferencia e:
- jurimetria_dataset

Campos relevantes no fluxo atual:
- tribunal
- numero_processo
- classe_processual
- assunto_codigo
- data_ajuizamento
- data_fim
- status_processo
- movimento_encerramento
- duracao_dias
- area_juridica_principal

Observacao importante:
- o treino usa duracao_dias como variavel alvo (target)

---

## 4) Dataset e features de ML

Modulo de dataset:
- app/ml/dataset.py

Regra de carregamento:
- usa somente registros com duracao_dias IS NOT NULL

Modulo de features:
- app/ml/features.py

Features utilizadas no modelo atual:
- tribunal
- classe_processual
- assunto_codigo
- ano_ajuizamento
- mes_ajuizamento

Transformacoes:
- derivacao de ano_ajuizamento e mes_ajuizamento a partir de data_ajuizamento
- One-Hot Encoding para colunas categoricas

---

## 5) Treinamento do modelo

Endpoint:

```http
POST /api/v1/ml/train
```

Modulo principal:
- app/ml/train.py

Pipeline atual:
- carrega dataset com duracao_dias valido
- exige minimo de 500 registros
- ordena por data_ajuizamento
- faz split temporal 80/20 (mais antigos para treino)
- treina RandomForestRegressor
- calcula MAE e RMSE
- salva modelo versionado e ativa a nova versao

Modelo atual:
- RandomForestRegressor

Resposta esperada do endpoint:
- version
- metrics
- total_records

---

## 6) Registro e versionamento de modelo

Modulo:
- app/ml/model_registry.py

Estrutura:
- app/ml/models/{timestamp}/model.joblib
- app/ml/models/{timestamp}/metadata.json
- app/ml/models/active_model.json

Metadata salva:
- version
- trained_at
- total_records
- metrics
- feature_columns
- active

---

## 7) Predicao em producao

Endpoint:

```http
POST /api/v1/jurimetria/previsao-tempo/{tribunal}/{numero_processo}
```

Fluxo:
1. Consulta DataJud pelo numero do processo
2. Normaliza dados para as mesmas features do treino
3. Carrega modelo ativo + feature_columns
4. Prediz tempo_total_estimado_dias
5. Calcula tempo_decorrido_dias
6. Calcula tempo_estimado_restante_dias

Resposta:
- numero_processo
- tribunal
- tempo_total_estimado_dias
- tempo_decorrido_dias
- tempo_estimado_restante_dias
- fonte_dados = DataJud

---

## 8) Ordem recomendada de operacao

1. Coletar e enriquecer dados via /api/v1/analise/processos/coletar-analisar
2. Conferir se ha registros suficientes com duracao_dias preenchido
3. Treinar via /api/v1/ml/train
4. Consumir predicoes via /api/v1/jurimetria/previsao-tempo/{tribunal}/{numero_processo}

---

## 9) Boas praticas

- Treinar em horario de baixa carga
- Monitorar MAE/RMSE a cada versao
- Versionar dados e modelos para reprodutibilidade
- Monitorar drift de distribuicao por tribunal, classe e assunto
