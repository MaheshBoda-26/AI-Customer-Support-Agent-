# Database Migrations

This directory contains SQL migration files for the Supabase database schema.

## Migration Files

1. `001_initial_schema.sql` - Core tables (customers, conversations, messages, tickets, handoffs)
2. `002_rls_policies.sql` - Row Level Security policies

## Running Migrations

### Option 1: Supabase Dashboard (Recommended)
1. Go to Supabase Dashboard > SQL Editor
2. Copy and paste each migration file content
3. Run in order: 001 then 002

### Option 2: psql Command Line
```bash
psql "postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres" -f backend/migrations/001_initial_schema.sql
psql "postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres" -f backend/migrations/002_rls_policies.sql
```

### Option 3: Supabase CLI
```bash
supabase db push --file backend/migrations/001_initial_schema.sql
supabase db push --file backend/migrations/002_rls_policies.sql
```