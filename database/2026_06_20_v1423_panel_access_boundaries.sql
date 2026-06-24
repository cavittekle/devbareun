-- DevBareun v1.4.23: canonical panel roles and least-privilege boundaries.
-- Additive/idempotent migration. Run after v1.4.22.

DO $$
BEGIN
    IF to_regclass('public.users_profile') IS NULL THEN
        RAISE EXCEPTION 'public.users_profile is required before applying v1.4.23';
    END IF;
END $$;

-- Normalize legacy profile labels before enforcing the canonical role set.
UPDATE public.users_profile
SET role = CASE lower(coalesce(role, ''))
    WHEN 'admin' THEN 'owner'
    WHEN 'owner' THEN 'owner'
    WHEN 'support' THEN 'support'
    WHEN 'analyst' THEN 'analyst'
    WHEN 'finance' THEN 'finance'
    WHEN 'operator' THEN 'operator'
    WHEN 'user' THEN 'customer'
    WHEN 'customer' THEN 'customer'
    ELSE 'customer'
END,
updated_at = now()
WHERE lower(coalesce(role, '')) NOT IN ('owner', 'support', 'analyst', 'finance', 'operator', 'customer')
   OR role IS NULL
   OR role <> lower(role)
   OR lower(role) IN ('admin', 'user');

ALTER TABLE public.users_profile
    ALTER COLUMN role SET DEFAULT 'customer';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'users_profile_canonical_role_check'
          AND conrelid = 'public.users_profile'::regclass
    ) THEN
        ALTER TABLE public.users_profile
            ADD CONSTRAINT users_profile_canonical_role_check
            CHECK (role IN ('customer', 'owner', 'support', 'analyst', 'finance', 'operator'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_users_profile_active_role
    ON public.users_profile (role, status)
    WHERE status = 'active';
