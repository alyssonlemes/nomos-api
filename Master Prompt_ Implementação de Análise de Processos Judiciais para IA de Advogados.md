
# Master Prompt: Implementação de Análise de Processos Judiciais para IA de Advogados

## Objetivo da Feature

Implementar uma funcionalidade que permita a um modelo de IA (a ser treinado ou alimentado com RAG) interagir com advogados, fornecendo informações sobre processos judiciais, especificamente:

1.  **Filtragem de Processos**: Capacidade de buscar processos por áreas jurídicas específicas (e.g., Criminal, Família, Cível, Militar) utilizando a API Pública do DataJud.
2.  **Análise de Tempo Médio**: Cálculo do tempo médio de duração de processos dentro das áreas filtradas, para oferecer insights preditivos aos advogados.

## 1. Integração com a API Pública do DataJud

### 1.1. Autenticação

A API requer autenticação via chave pública. A chave deve ser obtida e configurada como uma variável de ambiente ou em um arquivo de configuração seguro. A documentação oficial detalha o processo de obtenção da chave [1].

### 1.2. Endpoint e Requisições

*   **Base URL**: `https://datajud.cnj.jus.br/api_publica`
*   **Endpoint de Busca**: `/processo/search`
*   **Método**: `POST`
*   **Headers**: `Content-Type: application/json`, `X-Auth-Token: <SUA_CHAVE_AQUI>`

### 1.3. Estrutura da Query DSL

As requisições devem seguir o padrão Query DSL (Domain Specific Language) do Elasticsearch. Para coletar um grande volume de processos, é crucial utilizar a paginação via `search_after` para evitar limites de `size` e garantir a recuperação de todos os dados relevantes [2].

**Exemplo de Query DSL base para São Paulo (TJSP) com `search_after`:**

```json
{
  "size": 10000, // Máximo permitido por requisição
  "query": {
    "bool": {
      "must": [
        {"match": {"tribunal": "TJSP"}}
      ]
    }
  },
  "sort": [
    { "@timestamp": { "order": "asc" } }
  ],
  "search_after": [] // Preenchido com o valor do último processo da requisição anterior
}
```

## 2. Filtragem de Processos por Área Jurídica

Os processos são classificados por `classe` e `assuntos`, ambos padronizados pela Tabela Processual Unificada (TPU) do CNJ. A filtragem deve ser feita utilizando os códigos numéricos dessas classificações para maior precisão [3].

### 2.1. Campos para Filtragem

*   **`classe.codigo`**: Código numérico da classe processual principal (ex: 268 para PROCESSO CRIMINAL).
*   **`assuntos.codigo`**: Array de códigos numéricos dos assuntos relacionados ao processo (ex: 5626 para Família, sob DIREITO CIVIL).

### 2.2. Consulta à Tabela Processual Unificada (TPU)

Para obter os códigos e nomes das classes e assuntos:

*   **Classes**: [https://www.cnj.jus.br/sgt/consulta_publica_classes.php](https://www.cnj.jus.br/sgt/consulta_publica_classes.php)
*   **Assuntos**: [https://www.cnj.jus.br/sgt/consulta_publica_assuntos.php](https://www.cnj.jus.br/sgt/consulta_publica_assuntos.php)

É recomendável criar um mapeamento interno ou uma função de busca para traduzir termos de área (e.g., "Criminal") para os códigos da TPU correspondentes.

### 2.3. Exemplo de Query DSL com Filtragem por Área (Criminal)

```json
{
  "size": 10000,
  "query": {
    "bool": {
      "must": [
        {"match": {"tribunal": "TJSP"}},
        {"match": {"classe.codigo": 268}} // Exemplo: PROCESSO CRIMINAL
        // Para múltiplos assuntos ou classes, usar "should" dentro de um "bool" aninhado
      ]
    }
  },
  "sort": [
    { "@timestamp": { "order": "asc" } }
  ],
  "search_after": []
}
```

## 3. Cálculo do Tempo Médio do Processo

Para calcular o tempo de duração de um processo, precisamos da data de início e da data de fim.

### 3.1. Data de Início

*   **`dataAjuizamento`**: Este campo, presente na raiz do objeto `processo`, representa a data de início do processo [1].

### 3.2. Data de Fim

A API não possui um campo `dataFim` direto. A data de encerramento deve ser inferida a partir do array `movimentos` [4].

**Lógica para identificar a data de fim:**

1.  Iterar sobre o array `movimentos` de cada processo.
2.  Procurar por movimentos cujo `nome` contenha termos que indiquem o encerramento definitivo do processo. Exemplos de termos:
    *   "Baixa Definitiva"
    *   "Arquivamento"
    *   "Trânsito em Julgado"
    *   "Extinção do Processo"
    *   "Julgado Extinto"
3.  A `dataHora` do movimento mais recente que corresponda a um desses termos será considerada a data de fim do processo.
4.  Se nenhum movimento de encerramento for encontrado, o processo é considerado em andamento e não deve ser incluído no cálculo do tempo médio de processos *finalizados*.

### 3.3. Cálculo da Duração

Uma vez que `dataAjuizamento` e a data de fim (inferida) são obtidas, a duração pode ser calculada como a diferença entre as duas datas (em dias, meses ou anos, conforme a granularidade desejada).

## 4. Preparação dos Dados para o Modelo de IA

Os dados coletados e processados devem ser estruturados de forma a serem facilmente consumidos pelo modelo de IA, seja para fine-tuning ou para uso em um sistema RAG (Retrieval Augmented Generation) [5].

### 4.1. Estrutura de Dados Sugerida (JSON)

Para cada processo, após a coleta e processamento, a estrutura de dados pode ser similar a:

```json
{
  "numeroProcesso": "0001234-56.2023.8.26.0000",
  "tribunal": "TJSP",
  "areaJuridicaPrincipal": "Criminal", // Inferido da classe ou assunto principal
  "classePrincipal": {
    "codigo": 268,
    "nome": "PROCESSO CRIMINAL"
  },
  "assuntosRelacionados": [
    {"codigo": 287, "nome": "DIREITO PENAL"},
    {"codigo": 123, "nome": "Homicídio Qualificado"}
  ],
  "dataAjuizamento": "2023-01-01T10:00:00.000Z",
  "dataFim": "2023-04-20T16:00:00.000Z", // Inferido dos movimentos
  "duracaoDias": 109, // Calculado
  "movimentosPrincipais": [
    // Lista simplificada dos movimentos mais relevantes, se necessário
  ],
  "textoProcesso": "..." // Conteúdo textual relevante do processo, se disponível e necessário para RAG
}
```

### 4.2. Agregação para Tempo Médio

Para o cálculo do tempo médio por área, os dados devem ser agregados. Por exemplo:

```json
{
  "area": "Criminal",
  "tempoMedioDias": 150,
  "desvioPadraoDias": 30,
  "totalProcessosFinalizados": 5000,
  "percentil25Dias": 90,
  "percentil50Dias": 140,
  "percentil75Dias": 180
}
```

## 5. Requisitos Técnicos e Considerações

*   **Linguagem**: Python (preferencialmente, devido à vasta gama de bibliotecas para processamento de dados e IA).
*   **Bibliotecas**: `requests` para chamadas HTTP, `pandas` para manipulação de dados, `datetime` para cálculo de datas.
*   **Tratamento de Erros**: Implementar robusto tratamento de erros para falhas na API, dados inconsistentes e movimentos ausentes.
*   **Persistência**: Os dados coletados e processados devem ser armazenados em um banco de dados (SQL, NoSQL) ou em arquivos (JSON, CSV) para uso posterior pelo modelo de IA.
*   **Escalabilidade**: A coleta de "muitos e muitos processos" exige um pipeline escalável, com controle de taxa de requisições (rate limiting) para não sobrecarregar a API e respeitar seus limites.
*   **Atualização Contínua**: Considerar um mecanismo para atualizar periodicamente os dados dos processos, especialmente para aqueles em andamento.

## 6. Passos para o Copilot (ou IA de Desenvolvimento)

Com base nas informações acima, o Copilot deve realizar as seguintes tarefas:

1.  **Configuração**: Criar um projeto Python e configurar as dependências necessárias.
2.  **Cliente API**: Desenvolver um cliente Python para a API DataJud, encapsulando a autenticação e as chamadas `POST` com Query DSL.
3.  **Coleta de Dados**: Implementar um script para coletar processos do TJSP, utilizando `search_after` para paginação. O script deve ser capaz de filtrar por `classe.codigo` ou `assuntos.codigo` conforme parâmetros de entrada.
4.  **Processamento de Dados**: Para cada processo coletado:
    *   Extrair `dataAjuizamento`.
    *   Implementar a lógica para inferir `dataFim` a partir do array `movimentos`, buscando por termos de encerramento (conforme Seção 3.2).
    *   Calcular `duracaoDias` para processos finalizados.
    *   Classificar o processo em uma `areaJuridicaPrincipal` (e.g., "Criminal", "Família") com base em `classe.codigo` e `assuntos.codigo`.
5.  **Armazenamento**: Salvar os dados processados em um formato adequado (e.g., JSON Lines, CSV) ou em um banco de dados.
6.  **Análise de Tempo Médio**: Desenvolver uma função que, dado uma `areaJuridicaPrincipal`, calcule o tempo médio, desvio padrão e percentis de duração para os processos finalizados nessa área.
7.  **Estrutura de Saída**: Garantir que os dados de saída (processos individuais e estatísticas de tempo médio) estejam no formato sugerido na Seção 4 para fácil consumo pelo modelo de IA.
8.  **Documentação Interna**: Adicionar comentários claros no código e documentação para facilitar a manutenção e futuras extensões.

Este guia fornece todas as informações necessárias para que a IA possa desenvolver a funcionalidade de forma autônoma e eficiente.

## Referências

[1] [API Pública | Datajud-Wiki - Acesso](https://datajud-wiki.cnj.jus.br/api-publica/acesso)
[2] [API Pública | Datajud-Wiki - Exemplos (search_after)](https://datajud-wiki.cnj.jus.br/api-publica/exemplos#exemplo-3---paginacao-search_after)
[3] [Glossário de Dados | Datajud-Wiki](https://datajud-wiki.cnj.jus.br/api-publica/glossario)
[4] [Identificando a Data Final de um Processo na API Pública do DataJud](/home/ubuntu/identificando_fim_processo_datajud.md)
[5] [Guia de Preparação de Dados para Ollama (Fine-tuning vs RAG)](/home/ubuntu/guia_preparacao_dados_ollama.md)
