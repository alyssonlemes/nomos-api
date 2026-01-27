# 📦 Setup do Insomnia para Nomos API

Este guia explica como configurar e usar o Insomnia para testar a API Nomos automaticamente.

## 🎯 Objetivo

Este script Python gera automaticamente uma coleção completa do Insomnia com todas as rotas da API, permitindo que você teste a API de forma rápida e organizada.

## 📋 Pré-requisitos

1. **Insomnia** instalado ([Download aqui](https://insomnia.rest/download))
2. **Python 3.7+** instalado
3. **API rodando** (veja [INICIALIZAR_API.md](INICIALIZAR_API.md))

## 🚀 Como Usar

### Passo 1: Gerar a Coleção

Execute o script Python na raiz do projeto:

```bash
python generate_insomnia_collection.py
```

Isso criará um arquivo `insomnia_collection.json` com todas as rotas configuradas.

### Passo 2: Importar no Insomnia

1. Abra o **Insomnia**
2. Clique em **Application** > **Preferences** > **Data** > **Import Data**
   - Ou use o atalho: `Ctrl+Shift+I` (Windows/Linux) ou `Cmd+Shift+I` (Mac)
3. Selecione **From File**
4. Escolha o arquivo `insomnia_collection.json` gerado
5. Clique em **Import**

### Passo 3: Configurar Variáveis de Ambiente

A coleção já vem com um ambiente configurado, mas você pode ajustar:

1. No Insomnia, clique no dropdown de **Environments** (canto superior esquerdo)
2. Selecione **Base Environment**
3. Verifique as variáveis:
   ```json
   {
     "base_url": "http://localhost:8000",
     "api_prefix": "/api",
     "token": ""
   }
   ```
4. Clique em **Done**

### Passo 4: Autenticar e Obter Token

1. Na pasta **🔐 Autenticação**, execute a requisição **Login**
   - Usuário padrão: `admin`
   - Senha padrão: `admin123`
   
2. Copie o `access_token` retornado na resposta

3. Volte ao **Environment** e cole o token no campo `token`:
   ```json
   {
     "base_url": "http://localhost:8000",
     "api_prefix": "/api",
     "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   }
   ```

4. Salve o environment

## 📚 Estrutura da Coleção

A coleção está organizada em 4 pastas principais:

### 🔐 Autenticação
- **Login**: Autentica usuário e retorna JWT token

### 👥 Usuários
- **Registrar Usuário**: Cria novo usuário
- **Obter Usuário Atual (Me)**: Retorna dados do usuário autenticado
- **Listar Usuários**: Lista todos os usuários (com paginação)
- **Buscar Usuário por ID**: Busca usuário específico
- **Atualizar Usuário**: Atualiza dados do usuário
- **Deletar Usuário**: Remove usuário do sistema

### 👤 Clientes
- **Criar Cliente**: Adiciona novo cliente
- **Listar Clientes**: Lista todos os clientes (com paginação e filtros)
- **Listar Clientes com Filtro**: Lista com filtros de status e busca
- **Estatísticas de Clientes**: Retorna estatísticas gerais
- **Buscar Cliente por ID**: Busca cliente específico
- **Atualizar Cliente**: Atualiza dados do cliente
- **Deletar Cliente**: Remove cliente

### ⚖️ Ações Jurídicas
- **Criar Ação Jurídica**: Adiciona novo processo/ação
- **Listar Ações Jurídicas**: Lista todas as ações
- **Listar Ações com Filtros**: Lista com filtros de status e cliente
- **Buscar Ação por ID**: Busca ação específica com detalhes
- **Atualizar Ação Jurídica**: Atualiza dados da ação
- **Deletar Ação Jurídica**: Remove ação

## 🔄 Workflow de Teste Recomendado

1. **Registrar novo usuário** (ou usar credenciais existentes)
2. **Fazer login** e obter token
3. **Configurar token** no environment
4. **Criar clientes** de teste
5. **Criar ações jurídicas** vinculadas aos clientes
6. **Testar endpoints de listagem** com filtros
7. **Testar atualizações** e deleções

## 💡 Dicas

### Autenticação Automática
Todas as requisições (exceto Login e Registro) já estão configuradas para usar o token automaticamente através da variável `{{ _.token }}`.

### Personalizando URLs
Se sua API estiver rodando em outra porta ou host, ajuste no environment:
```json
{
  "base_url": "http://localhost:3000",
  "api_prefix": "/api/v1"
}
```

### Testando Paginação
Use os parâmetros `skip` e `limit` nas requisições de listagem:
```
/clients?skip=0&limit=10
```

### Testando Filtros
Combine múltiplos filtros nas URLs:
```
/clients?status=active&search=silva
/legal-actions?legal_status=in_progress&client_id=1
```

## 🐛 Troubleshooting

### Token expirado
- **Sintoma**: Erro 401 Unauthorized
- **Solução**: Faça login novamente e atualize o token no environment

### Erro de conexão
- **Sintoma**: Connection refused
- **Solução**: Verifique se a API está rodando (`uvicorn app.main:app --reload`)

### Database error
- **Sintoma**: Erro 500 com mensagem de banco de dados
- **Solução**: Verifique se o PostgreSQL está rodando e as credenciais estão corretas

### ID não encontrado
- **Sintoma**: Erro 404 Not Found
- **Solução**: Verifique se o recurso existe ou crie um novo antes de buscar

## 🔄 Regenerando a Coleção

Se você adicionar novas rotas à API, basta executar o script novamente:

```bash
python generate_insomnia_collection.py
```

E reimportar o arquivo no Insomnia.

## 📖 Recursos Adicionais

- **Documentação da API**: http://localhost:8000/docs (Swagger UI)
- **Documentação alternativa**: http://localhost:8000/redoc (ReDoc)
- **Health check**: http://localhost:8000/health

## 🤝 Contribuindo

Se você adicionar novos endpoints, lembre-se de:
1. Atualizar o script `generate_insomnia_collection.py`
2. Regenerar a coleção
3. Testar no Insomnia
4. Atualizar esta documentação se necessário

---

**Happy Testing! 🚀**
