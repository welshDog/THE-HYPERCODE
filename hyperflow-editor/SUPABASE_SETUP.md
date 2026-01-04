# ⚡ Supabase Cloud Sync Setup

Enable real-time cloud persistence for your HyperFlow Editor.

## 1. Create a Supabase Project
1. Go to [database.new](https://database.new) and create a new project.
2. Wait for the database to provision.

## 2. Get API Keys
1. Go to **Project Settings** -> **API**.
2. Copy the **Project URL** and **anon public** key.
3. Rename `.env.example` to `.env` in the `hyperflow-editor` root.
4. Paste your keys:
   ```env
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

## 3. Run SQL Setup
Go to the **SQL Editor** in your Supabase dashboard and run this script to create the table and disable Row Level Security (RLS) for testing:

```sql
-- Create the flows table
create table flows (
  id text primary key,
  name text,
  description text,
  nodes jsonb default '[]'::jsonb,
  edges jsonb default '[]'::jsonb,
  viewport jsonb default '{}'::jsonb,
  tags text[] default array[]::text[],
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ⚠️ DISABLE RLS FOR DEV (Allows anyone with the URL to read/write)
-- For production, you must enable RLS and set up Auth policies.
alter table flows enable row level security;

create policy "Enable read access for all users"
on flows for select
using (true);

create policy "Enable insert access for all users"
on flows for insert
with check (true);

create policy "Enable update access for all users"
on flows for update
using (true);
```

## 4. Verify
Restart your development server:
```bash
npm run dev
```
Check the browser console. You should see: `Using Supabase Cloud Storage`.
