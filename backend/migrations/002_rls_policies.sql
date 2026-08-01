-- Phase 1b: Row Level Security (RLS) Policies
-- Run AFTER 001_initial_schema.sql
-- These policies implement a permissive model for development
-- Tighten for production when adding real authentication

-- ============================================
-- ENABLE RLS ON ALL TABLES
-- ============================================
alter table customers enable row level security;
alter table conversations enable row level security;
alter table messages enable row level security;
alter table tickets enable row level security;
alter table handoffs enable row level security;

-- ============================================
-- CUSTOMERS POLICIES
-- ============================================
-- Service role has full access (for backend)
create policy "Service role full access customers" on customers
    for all using (auth.role() = 'service_role');

-- Allow reading own customer record (for future auth integration)
create policy "Users can view own customer" on customers
    for select using (auth.uid() = id);

-- ============================================
-- CONVERSATIONS POLICIES
-- ============================================
create policy "Service role full access conversations" on conversations
    for all using (auth.role() = 'service_role');

-- Users can view their own conversations
create policy "Users can view own conversations" on conversations
    for select using (auth.uid() = customer_id);

-- Users can insert their own conversations
create policy "Users can create own conversations" on conversations
    for insert with check (auth.uid() = customer_id);

-- Users can update their own conversations (status, summary)
create policy "Users can update own conversations" on conversations
    for update using (auth.uid() = customer_id);

-- ============================================
-- MESSAGES POLICIES
-- ============================================
create policy "Service role full access messages" on messages
    for all using (auth.role() = 'service_role');

-- Users can view messages in their conversations
create policy "Users can view own messages" on messages
    for select using (
        exists (
            select 1 from conversations
            where conversations.id = messages.conversation_id
            and conversations.customer_id = auth.uid()
        )
    );

-- Users can insert messages in their conversations
create policy "Users can insert own messages" on messages
    for insert with check (
        exists (
            select 1 from conversations
            where conversations.id = messages.conversation_id
            and conversations.customer_id = auth.uid()
        )
    );

-- ============================================
-- TICKETS POLICIES
-- ============================================
create policy "Service role full access tickets" on tickets
    for all using (auth.role() = 'service_role');

-- Users can view tickets for their conversations
create policy "Users can view own tickets" on tickets
    for select using (
        exists (
            select 1 from conversations
            where conversations.id = tickets.conversation_id
            and conversations.customer_id = auth.uid()
        )
    );

-- ============================================
-- HANDOFFS POLICIES
-- ============================================
create policy "Service role full access handoffs" on handoffs
    for all using (auth.role() = 'service_role');

-- Users can view handoffs for their conversations
create policy "Users can view own handoffs" on handoffs
    for select using (
        exists (
            select 1 from conversations
            where conversations.id = handoffs.conversation_id
            and conversations.customer_id = auth.uid()
        )
    );

-- ============================================
-- DEVELOPMENT OVERRIDE: Allow anon read for dashboard
-- Remove or restrict in production!
-- ============================================
-- This allows the admin dashboard to read data via anon key
-- In production, use service role or proper admin authentication

-- Allow anon to read conversations (for dashboard realtime)
create policy "Anon can read conversations" on conversations
    for select using (true);

-- Allow anon to read messages (for dashboard realtime)
create policy "Anon can read messages" on messages
    for select using (true);

-- Allow anon to read tickets (for dashboard)
create policy "Anon can read tickets" on tickets
    for select using (true);

-- Allow anon to read handoffs (for dashboard realtime)
create policy "Anon can read handoffs" on handoffs
    for select using (true);

-- Allow anon to read customers (for dashboard)
create policy "Anon can read customers" on customers
    for select using (true);

-- Note: No anon INSERT/UPDATE/DELETE policies - only SELECT