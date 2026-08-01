-- Phase 1: Core Tables for AI Customer Support Agent
-- Run this in Supabase SQL Editor or via migration runner

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ============================================
-- CUSTOMERS TABLE
-- ============================================
create table if not exists customers (
    id uuid primary key default gen_random_uuid(),
    email text unique not null,
    name text,
    created_at timestamptz default now()
);

create index if not exists idx_customers_email on customers(email);

-- ============================================
-- CONVERSATIONS TABLE
-- ============================================
create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid references customers(id) on delete set null,
    status text default 'active' check (status in ('active', 'escalated', 'closed')),
    language text default 'en',
    summary text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_conversations_customer_id on conversations(customer_id);
create index if not exists idx_conversations_status on conversations(status);
create index if not exists idx_conversations_created_at on conversations(created_at desc);

-- ============================================
-- MESSAGES TABLE
-- ============================================
create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    created_at timestamptz default now()
);

create index if not exists idx_messages_conversation_id on messages(conversation_id, created_at);

-- ============================================
-- TICKETS TABLE
-- ============================================
create table if not exists tickets (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid references conversations(id) on delete cascade,
    subject text not null,
    description text not null,
    category text not null check (category in ('billing', 'bug', 'account', 'other')),
    status text default 'open' check (status in ('open', 'in_progress', 'resolved')),
    priority text default 'normal' check (priority in ('low', 'normal', 'high', 'urgent')),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_tickets_conversation_id on tickets(conversation_id);
create index if not exists idx_tickets_status on tickets(status);
create index if not exists idx_tickets_priority on tickets(priority);
create index if not exists idx_tickets_created_at on tickets(created_at desc);

-- ============================================
-- HANDOFFS TABLE
-- ============================================
create table if not exists handoffs (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid references conversations(id) on delete cascade,
    reason text not null,
    assigned_to text,
    created_at timestamptz default now()
);

create index if not exists idx_handoffs_conversation_id on handoffs(conversation_id);
create index if not exists idx_handoffs_created_at on handoffs(created_at desc);

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================
create or replace function update_updated_at_column()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists update_conversations_updated_at on conversations;
create trigger update_conversations_updated_at
    before update on conversations
    for each row execute function update_updated_at_column();

drop trigger if exists update_tickets_updated_at on tickets;
create trigger update_tickets_updated_at
    before update on tickets
    for each row execute function update_updated_at_column();