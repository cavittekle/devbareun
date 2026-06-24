-- DevBareun production RLS/Data API audit
-- Run after applying migrations in Supabase SQL editor.
-- This query does not change data.

with expected_tables(table_name) as (
  values
    ('users'),
    ('companies'),
    ('projects'),
    ('uploaded_files'),
    ('analysis_jobs'),
    ('analysis_results'),
    ('reports'),
    ('payments'),
    ('subscriptions'),
    ('analysis_credits'),
    ('payment_events'),
    ('activity_logs'),
    ('support_tickets'),
    ('staff_members'),
    ('admin_notes'),
    ('credit_adjustments')
),
rls_status as (
  select
    c.relname as table_name,
    c.relrowsecurity as rls_enabled,
    c.relforcerowsecurity as rls_forced
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public'
    and c.relkind = 'r'
),
policy_counts as (
  select
    schemaname,
    tablename as table_name,
    count(*) as policy_count
  from pg_policies
  where schemaname = 'public'
  group by schemaname, tablename
),
role_grants as (
  select
    table_name,
    bool_or(grantee = 'anon') as anon_granted,
    bool_or(grantee = 'authenticated') as authenticated_granted
  from information_schema.role_table_grants
  where table_schema = 'public'
  group by table_name
)
select
  e.table_name,
  coalesce(r.rls_enabled, false) as rls_enabled,
  coalesce(r.rls_forced, false) as rls_forced,
  coalesce(p.policy_count, 0) as policy_count,
  coalesce(g.anon_granted, false) as anon_granted,
  coalesce(g.authenticated_granted, false) as authenticated_granted,
  case
    when r.table_name is null then 'missing_table'
    when not r.rls_enabled then 'rls_disabled'
    when coalesce(p.policy_count, 0) = 0 then 'no_policies'
    else 'review'
  end as audit_status
from expected_tables e
left join rls_status r on r.table_name = e.table_name
left join policy_counts p on p.table_name = e.table_name
left join role_grants g on g.table_name = e.table_name
order by e.table_name;
