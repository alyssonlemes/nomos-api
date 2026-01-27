# 🚀 Como Inicializar a Nomos API

Este guia fornece instruções completas para configurar e executar a API Nomos do zero.

## 📋 Pré-requisitos

### Software Necessário

1. **Python 3.9+**
   - Download: https://www.python.org/downloads/
   - Verifique: `python --version`

2. **PostgreSQL 12+**
   - Download: https://www.postgresql.org/download/
   - Verifique: `psql --version`

3. **Git** (para clonar o repositório)
   - Download: https://git-scm.com/downloads
   - Verifique: `git --version`

4. **pip** (gerenciador de pacotes Python)
   - Normalmente já vem com Python
   - Verifique: `pip --version`

## 🔧 Setup do Ambiente

### 1. Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd nomos-api
```

### 2. Criar Ambiente Virtual

É altamente recomendado usar um ambiente virtual para isolar as dependências:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Você verá `(venv)` no início da linha do terminal quando o ambiente estiver ativado.

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

Isso instalará:
- FastAPI (framework web)
- Uvicorn (servidor ASGI)
- SQLAlchemy (ORM)
- Pydantic (validação de dados)
- Python-JOSE (JWT)
- PassLib (hashing de senhas)
- PostgreSQL driver
- Outras dependências necessárias

## 🗄️ Configurar Banco de Dados

### 1. Iniciar PostgreSQL

**Windows (se instalado como serviço):**
```bash
# Verificar se está rodando
pg_isready

# Se não estiver, iniciar serviço
net start postgresql-x64-14
```

**Linux:**
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

**Mac:**
```bash
brew services start postgresql
```

### 2. Criar Banco de Dados

Acesse o PostgreSQL:
```bash
psql -U postgres
```

Execute os comandos SQL:
```sql
-- Criar banco de dados
CREATE DATABASE nomos;

-- Criar usuário (opcional)
CREATE USER nomos_user WITH PASSWORD 'sua_senha';

-- Dar permissões
GRANT ALL PRIVILEGES ON DATABASE nomos TO nomos_user;

-- Sair
\q
```

### 3. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
# .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nomos
SECRET_KEY=sua-chave-secreta-super-segura-mude-isso-em-producao
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**⚠️ IMPORTANTE:** 
- Altere `SECRET_KEY` para uma chave segura em produção
- Ajuste as credenciais do `DATABASE_URL` conforme seu setup
- Nunca commite o arquivo `.env` para o Git (já está no .gitignore)

### Gerar SECRET_KEY Segura

Use Python para gerar uma chave segura:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🏃 Executar a API

### 1. Criar Tabelas do Banco

As tabelas serão criadas automaticamente quando você iniciar a API pela primeira vez.

### 2. Iniciar o Servidor

**Modo Desenvolvimento (com hot-reload):**
```bash
uvicorn app.main:app --reload
```

**Modo Desenvolvimento com Host/Porta personalizados:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Modo Produção:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Verificar se está Funcionando

Acesse no navegador:
- **API Root**: http://localhost:8000
- **Documentação Swagger**: http://localhost:8000/docs
- **Documentação ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

Você deve ver uma resposta JSON na raiz:
```json
{
  "message": "Bem-vindo à Nomos API",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc",
  "api_v1": "/api"
}
```

## 🧪 Testar a API

### Usando Swagger UI (Navegador)

1. Acesse http://localhost:8000/docs
2. Explore e teste todos os endpoints diretamente no navegador
3. Clique em "Try it out" em qualquer endpoint
4. Preencha os parâmetros e clique em "Execute"

### Usando Insomnia (Recomendado)

1. Execute o script para gerar a coleção:
   ```bash
   python generate_insomnia_collection.py
   ```

2. Siga o guia [INSOMNIA_SETUP.md](INSOMNIA_SETUP.md)

### Criar Primeiro Usuário

**Via Swagger UI:**
1. Vá para http://localhost:8000/docs
2. Encontre `POST /api/users/register`
3. Clique em "Try it out"
4. Preencha os dados:
   ```json
   {
     "email": "admin@example.com",
     "username": "admin",
     "password": "admin123",
     "full_name": "Administrador"
   }
   ```
5. Clique em "Execute"

**Via curl:**
```bash
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "admin123",
    "full_name": "Administrador"
  }'
```

### Fazer Login e Obter Token

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

Resposta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Usar Token em Requisições Autenticadas

```bash
curl -X GET "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

## 📁 Estrutura do Projeto

```
nomos-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicação FastAPI principal
│   ├── database.py          # Configuração do banco
│   ├── api/                 # Camada de API
│   │   ├── api_router.py    # Router principal
│   │   ├── deps.py          # Dependências (autenticação)
│   │   └── endpoints/       # Endpoints da API
│   ├── core/                # Configurações e segurança
│   ├── models/              # Modelos SQLAlchemy
│   ├── schemas/             # Schemas Pydantic
│   └── services/            # Lógica de negócio
├── docs/                    # Documentação
├── generate_insomnia_collection.py  # Script gerador
├── requirements.txt         # Dependências Python
├── .env                     # Variáveis de ambiente (criar)
└── README.md
```

## 🔧 Comandos Úteis

### Parar o Servidor
- `Ctrl + C` no terminal

### Desativar Ambiente Virtual
```bash
deactivate
```

### Recriar Banco de Dados
```sql
DROP DATABASE nomos;
CREATE DATABASE nomos;
```

### Ver Logs Detalhados
```bash
uvicorn app.main:app --reload --log-level debug
```

### Verificar Dependências Instaladas
```bash
pip list
```

### Atualizar Dependências
```bash
pip install --upgrade -r requirements.txt
```

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError"
**Solução:** Certifique-se de que o ambiente virtual está ativado e as dependências foram instaladas:
```bash
pip install -r requirements.txt
```

### Erro: "Could not connect to database"
**Solução:** 
1. Verifique se o PostgreSQL está rodando
2. Verifique as credenciais no `.env`
3. Teste a conexão: `psql -U postgres -d nomos`

### Erro: "Address already in use"
**Solução:** Outra aplicação está usando a porta 8000. Use outra porta:
```bash
uvicorn app.main:app --reload --port 8001
```

### Erro: "SECRET_KEY not found"
**Solução:** Crie o arquivo `.env` com as variáveis necessárias.

### Erro 401 Unauthorized
**Solução:** 
1. Verifique se o token está correto
2. Token pode ter expirado - faça login novamente
3. Certifique-se de incluir "Bearer " antes do token

### Tabelas não criadas
**Solução:** 
1. Verifique se o banco de dados existe
2. Reinicie a aplicação
3. Se necessário, crie as tabelas manualmente ou use migrations

## 🚀 Próximos Passos

Após inicializar a API:

1. ✅ Configure o Insomnia: [INSOMNIA_SETUP.md](INSOMNIA_SETUP.md)
2. ✅ Teste todos os endpoints
3. ✅ Crie dados de teste (usuários, clientes, ações)
4. ✅ Explore a documentação interativa em `/docs`

## 📚 Documentação da API

### Endpoints Principais

**Autenticação:**
- `POST /api/auth/login` - Login

**Usuários:**
- `POST /api/users/register` - Criar usuário
- `GET /api/users/me` - Usuário atual
- `GET /api/users` - Listar usuários
- `GET /api/users/{id}` - Buscar usuário
- `PUT /api/users/{id}` - Atualizar usuário
- `DELETE /api/users/{id}` - Deletar usuário

**Clientes:**
- `POST /api/clients` - Criar cliente
- `GET /api/clients` - Listar clientes
- `GET /api/clients/statistics` - Estatísticas
- `GET /api/clients/{id}` - Buscar cliente
- `PUT /api/clients/{id}` - Atualizar cliente
- `DELETE /api/clients/{id}` - Deletar cliente

**Ações Jurídicas:**
- `POST /api/legal-actions` - Criar ação
- `GET /api/legal-actions` - Listar ações
- `GET /api/legal-actions/{id}` - Buscar ação
- `PUT /api/legal-actions/{id}` - Atualizar ação
- `DELETE /api/legal-actions/{id}` - Deletar ação

## 💡 Dicas de Desenvolvimento

1. **Use o hot-reload**: Com `--reload`, o servidor reinicia automaticamente ao salvar arquivos

2. **Explore o Swagger**: A interface em `/docs` é excelente para testar e entender a API

3. **Use o Insomnia**: Para testes mais complexos e automatizados

4. **Verifique logs**: O terminal mostra todas as requisições e erros

5. **Banco de testes**: Considere criar um banco separado para testes

## 🤝 Contribuindo

Se você encontrar problemas ou tiver sugestões, por favor:
1. Verifique se o problema já foi reportado
2. Crie uma issue descrevendo o problema
3. Se possível, sugira uma solução

---

**Happy Coding! 🎉**
