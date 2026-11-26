# Nomos API

API do escritório. Cobre autenticação, organizações, convites, perfis, clientes, processos, atividades, notificações, dashboard, planos, DataJud, jurimetria e acompanhamento pela Juri+.

O contrato de cada rota está em `/docs`.

## Stack

Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Alembic e JWT.

## Setup

```bash
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha o banco, o `SECRET_KEY` e as chaves de DataJud e Juri+.

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

`python init_db.py` só confere se a migration foi aplicada. O schema é do Alembic.
