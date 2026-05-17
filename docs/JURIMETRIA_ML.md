# Jurimetria em Produção – DataJud + ML

Este documento descreve o fluxo completo: integração com o DataJud, geração de dataset, treinamento do modelo e consumo das previsões.

## 1) Integração com o DataJud (CNJ)

### 1.1 Configuração

Defina a variável de ambiente:

```
DATAJUD_API_KEY=seu_token
```

A chave é usada pelos serviços:
- Coleta em lote: app/services/datajud_batch_service.py
- Predição por processo: app/services/jurimetria_prediction_service.py

### 1.2 Coleta em lote (batch)

Endpoint:

```
POST /api/v1/jurimetria/batch/tempo-tramitacao
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

O serviço:
- Monta query DSL para o Elasticsearch do DataJud
- Pagina usando size + from
- Aplica rate limit entre páginas
- Calcula duracao_dias (data_fim - data_ajuizamento)
- Persiste no PostgreSQL

Tabela de persistência:
- jurimetria_dataset

Campos principais:
- tribunal, numero_processo
- classe_processual, assunto_codigo
- data_ajuizamento, data_fim
- duracao_dias

### 1.3 Fonte de dados

Toda a base para treino e inferência é obtida do DataJud, garantindo rastreabilidade jurídica e reprodutibilidade dos experimentos.

---

## 2) Dataset e Engenharia de Features

### 2.1 Carregamento do dataset

Módulo:
- app/ml/dataset.py

Regra:
- Usa somente registros com duracao_dias NOT NULL

### 2.2 Features utilizadas

Módulo:
- app/ml/features.py

Features:
- tribunal
- classe_processual
- assunto_codigo
- ano_ajuizamento
- mes_ajuizamento

Justificativa jurídica:
- Tribunais têm dinâmica e tempos médios distintos
- Classe processual define o rito e a complexidade
- Assunto indica matéria jurídica e variabilidade de duração
- Ano/mês capturam sazonalidade e mudanças normativas

Categóricas são codificadas com One-Hot Encoding.

---

## 3) Treinamento do Modelo

Endpoint:

```
POST /api/v1/ml/train
```

Pipeline:
- Split temporal (processos mais antigos → treino)
- Treina modelo de regressão
- Avalia com MAE e RMSE
- Registra o modelo ativo

Modelo atual:
- RandomForestRegressor

Justificativa:
- Baseline robusto
- Captura não linearidades
- Tolera features heterogêneas

Módulo principal:
- app/ml/train.py

---

## 4) Avaliação

Módulo:
- app/ml/evaluate.py

Métricas:
- MAE: erro médio em dias
- RMSE: penaliza grandes erros

Impacto jurídico:
- Erros em dias afetam decisões estratégicas (acordos, provisões, custo jurídico)

---

## 5) Registro de Modelo

Módulo:
- app/ml/model_registry.py

Estrutura:
- app/ml/models/{timestamp}/model.joblib
- app/ml/models/{timestamp}/metadata.json
- app/ml/models/active_model.json

Metadata contém:
- version
- trained_at
- total_records
- metrics
- feature_columns
- active

---

## 6) Predição em Produção (Feature de Negócio)

Endpoint:

```
POST /api/v1/jurimetria/previsao-tempo/{tribunal}/{numero_processo}
```

Fluxo:
1. Consulta o DataJud com tribunal + numero_processo
2. Extrai as mesmas features do treino
3. Carrega modelo ACTIVE
4. Prediz tempo_total_estimado_dias
5. Calcula tempo_decorrido_dias e tempo_estimado_restante_dias

Resposta:
- numero_processo
- tribunal
- tempo_total_estimado_dias
- tempo_decorrido_dias
- tempo_estimado_restante_dias
- fonte_dados = DataJud

---

## 7) Boas práticas para produção

- Treinar em horários de baixa carga
- Exportar dataset para uso offline (parquet/CSV) quando necessário
- Monitorar drift de dados e performance das métricas
- Versionar modelos e dados para reprodutibilidade

---

## 8) Próximos passos recomendados

- Adicionar pipeline de feature store
- Criar validação automática de dados
- Implementar A/B testing de versões de modelo
- Monitoramento contínuo de métricas e drift
