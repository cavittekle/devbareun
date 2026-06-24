-- Promote the first real DevBareun owner after creating the user in Supabase Auth.
-- Run this in the live Supabase SQL editor after the main deploy SQL files.

update public.users_profile
set
  role = 'owner',
  status = 'active',
  updated_at = now()
where lower(email) = lower('info@devbareun.com');

select email, role, status
from public.users_profile
where lower(email) = lower('info@devbareun.com');
