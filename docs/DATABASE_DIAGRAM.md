# Diagrama de Banco de Dados - Nomos API

## 🌐 Como usar:

1. Acesse: **https://dbdiagram.io/**
2. Cole o código abaixo
3. O diagrama será gerado automaticamente
4. Exporte como PNG, PDF ou SQL

---

## 📋 Código DBML:

```dbml
// Nomos API - Database Schema

Table users {
  id integer [primary key, increment]
  email varchar [unique, not null]
  hashed_password varchar [not null]
  full_name varchar
  is_active boolean [default: true]
  is_superuser boolean [default: false]
  organization_id integer
  created_at timestamp [default: `now()`]
  updated_at timestamp
  
  indexes {
    email
    organization_id
  }
}

Table organizations {
  id integer [primary key, increment]
  name varchar [not null]
  document varchar [unique]
  owner_id integer [not null]
  is_active boolean [default: true]
  created_at timestamp [default: `now()`]
  updated_at timestamp
  
  indexes {
    name
    document
  }
}

Table invitations {
  id integer [primary key, increment]
  email varchar [not null]
  organization_id integer [not null]
  invited_by_id integer [not null]
  status varchar [default: 'pending', note: 'pending, accepted, rejected']
  created_at timestamp [default: `now()`]
  updated_at timestamp
  
  indexes {
    email
    status
  }
}

Table clients {
  id integer [primary key, increment]
  name varchar [not null]
  email varchar
  phone varchar
  document varchar [not null]
  client_type varchar [default: 'individual', note: 'individual, business']
  status varchar [default: 'prospect', note: 'active, inactive, prospect, archived']
  address varchar
  city varchar
  state varchar
  zip_code varchar
  company_name varchar
  organization_id integer [not null]
  user_id integer
  created_at timestamp [default: `now()`]
  updated_at timestamp
  
  indexes {
    name
    document
  }
}

Table legal_actions {
  id integer [primary key, increment]
  number varchar [unique, not null]
  title varchar [not null]
  description text
  client_id integer [not null]
  user_id integer
  organization_id integer [not null]
  action_type varchar [not null, note: 'labor, civil, criminal, admin, tax, commercial, family, real_estate, other']
  legal_status varchar [default: 'pre_trial', note: 'pre_trial, filing, litigation, execution, appeal, finalized, archived']
  court_name varchar
  filing_date date
  closing_date date
  is_active boolean [default: true]
  created_at timestamp [default: `now()`]
  updated_at timestamp
  
  indexes {
    number
    title
  }
}

// Relacionamentos
Ref: users.organization_id > organizations.id
Ref: organizations.owner_id > users.id
Ref: invitations.organization_id > organizations.id
Ref: invitations.invited_by_id > users.id
Ref: clients.organization_id > organizations.id
Ref: clients.user_id > users.id
Ref: legal_actions.client_id > clients.id
Ref: legal_actions.user_id > users.id
Ref: legal_actions.organization_id > organizations.id
```

---

## 📖 Legenda:

- **PK**: Primary Key
- **FK**: Foreign Key  
- **UK**: Unique Key
- **Ref**: Relacionamento entre tabelas
- **>**: Indica direção do relacionamento (many to one)
