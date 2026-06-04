# DevBareun Database Documentation

## Purpose

This document defines the planned database structure, ownership model, and security rules for DevBareun.

Database direction:

- Supabase PostgreSQL
- Supabase Auth
- Supabase Storage
- Row Level Security where applicable

## Main Ownership Model

Most user-owned records should include:

```text
user_id
company_id
project_id
created_at
updated_at
```

Users should not access other users' data.

Admin access must be explicit.

## Recommended Tables

## 1. `profiles`

Purpose: Stores user profile data linked to auth user.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key, linked to auth user |
| email | text | User email |
| full_name | text | User name |
| role | text | user/admin |
| company_id | uuid | Optional company link |
| created_at | timestamptz | Created date |
| updated_at | timestamptz | Updated date |

Security:

- User can read/update own profile.
- Admin can read all profiles.

## 2. `companies`

Purpose: Stores customer company records.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| name | text | Company name |
| owner_user_id | uuid | Company owner |
| billing_email | text | Optional |
| created_at | timestamptz | Created date |
| updated_at | timestamptz | Updated date |

Security:

- Company owner can access company.
- Company members can access if membership table exists.
- Admin can access all.

## 3. `projects`

Purpose: Stores construction projects.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Owner |
| company_id | uuid | Optional company |
| name | text | Project name |
| location | text | Optional |
| contractor | text | Optional |
| status | text | active/archived |
| created_at | timestamptz | Created date |
| updated_at | timestamptz | Updated date |

Indexes:

- `user_id`
- `company_id`
- `status`
- `created_at`

Security:

- User can access own projects.
- Admin can access all.

## 4. `project_files`

Purpose: Stores uploaded file metadata.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Owner |
| project_id | uuid | Related project |
| filename | text | Original filename |
| file_type | text | xlsx/csv/pdf/xml/xer |
| storage_bucket | text | Storage bucket |
| storage_path | text | Private file path |
| file_size | bigint | File size |
| status | text | uploaded/parsed/failed/deleted |
| created_at | timestamptz | Created date |
| updated_at | timestamptz | Updated date |

Indexes:

- `user_id`
- `project_id`
- `status`

Security:

- Files must be private.
- User can access own project files.
- Admin can access all.

## 5. `analysis_jobs`

Purpose: Tracks analysis processing status.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Owner |
| project_id | uuid | Related project |
| analysis_type | text | selected analysis type |
| status | text | uploaded/queued/parsing/analyzing/completed/failed |
| progress | integer | 0-100 |
| error_message | text | safe error only |
| created_at | timestamptz | Created date |
| updated_at | timestamptz | Updated date |
| completed_at | timestamptz | Completion date |

Indexes:

- `user_id`
- `project_id`
- `status`
- `created_at`

Security:

- User can read own jobs.
- Admin can inspect all jobs.

## 6. `analysis_results`

Purpose: Stores normalized analysis result JSON.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Owner |
| project_id | uuid | Related project |
| job_id | uuid | Related job |
| result_json | jsonb | Result payload |
| confidence_score | numeric | 0-1 |
| missing_fields | jsonb | Missing fields list |
| warnings | jsonb | Parser/analysis warnings |
| language | text | en/az |
| created_at | timestamptz | Created date |

Indexes:

- `user_id`
- `project_id`
- `job_id`
- `created_at`

Security:

- User can read own results.
- Admin can read all results.

## 7. `reports`

Purpose: Stores generated report metadata.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Owner |
| project_id | uuid | Related project |
| result_id | uuid | Related analysis result |
| format | text | pdf/excel |
| language | text | en/az |
| paper_size | text | A4/A3 |
| storage_bucket | text | Storage bucket |
| storage_path | text | Private report path |
| expires_at | timestamptz | Optional expiry |
| created_at | timestamptz | Created date |

Indexes:

- `user_id`
- `project_id`
- `result_id`
- `created_at`

Security:

- Reports should be private.
- Use signed URLs for downloads.

## 8. `subscriptions`

Purpose: Stores user subscription state.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Owner |
| plan_code | text | guest/plus/pro |
| status | text | active/cancelled/past_due/trial |
| provider | text | lemonsqueezy/other |
| provider_customer_id | text | Payment provider customer |
| provider_subscription_id | text | Payment provider subscription |
| current_period_start | timestamptz | Period start |
| current_period_end | timestamptz | Period end |
| created_at | timestamptz | Created date |
| updated_at | timestamptz | Updated date |

Indexes:

- `user_id`
- `plan_code`
- `status`
- `provider_customer_id`

Security:

- User can read own subscription.
- Backend updates via verified webhook.
- Admin can read all.

## 9. `payments`

Purpose: Stores payment events and invoices.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Owner |
| provider | text | lemonsqueezy/other |
| provider_payment_id | text | Provider payment id |
| amount | numeric | Amount |
| currency | text | Currency |
| status | text | paid/failed/refunded |
| raw_event | jsonb | Optional sanitized event |
| created_at | timestamptz | Created date |

Indexes:

- `user_id`
- `provider`
- `status`
- `created_at`

Security:

- User can read own payment history.
- Backend writes after webhook verification.
- Admin can read all.

## 10. `plan_limits`

Purpose: Defines project analysis limits.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| plan_code | text | guest/plus/pro |
| monthly_project_limit | integer | Number of analyses |
| active | boolean | Plan active |
| created_at | timestamptz | Created date |
| updated_at | timestamptz | Updated date |

Seed direction:

```text
guest: 1 one-time project analysis
plus: 5 projects/month
pro: 20 projects/month
```

## 11. `usage_counters`

Purpose: Tracks monthly analysis usage.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Owner |
| plan_code | text | Current plan |
| period_start | date | Usage period start |
| period_end | date | Usage period end |
| used_count | integer | Used analyses |
| created_at | timestamptz | Created date |
| updated_at | timestamptz | Updated date |

Indexes:

- `user_id`
- `period_start`
- `period_end`

Security:

- User can read own usage.
- Backend updates usage.
- Admin can read all.

## 12. `activity_logs`

Purpose: Stores important user/admin system activity.

Suggested columns:

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| user_id | uuid | Optional |
| action | text | Action type |
| entity_type | text | project/file/report/payment/etc |
| entity_id | uuid | Optional entity |
| metadata | jsonb | Extra data |
| created_at | timestamptz | Created date |

Security:

- Users may read limited own logs if needed.
- Admin can read all.
- Do not store secrets in metadata.

## Storage Buckets

Recommended buckets:

```text
project-files
reports
public-assets
```

Access:

| Bucket | Access | Notes |
|---|---|---|
| project-files | private | Uploaded user files |
| reports | private | Generated PDF/Excel reports |
| public-assets | public | Logos, public images, public assets |

## RLS Policy Direction

Apply Row Level Security for user-owned tables.

Policy examples:

- Users can select rows where `user_id = auth.uid()`.
- Users can insert rows linked to their own `user_id`.
- Users can update their own rows where allowed.
- Admin role can access all records.
- Private storage paths should include user/project ownership.

## Database Rules

- Do not duplicate tables.
- Check existing schema before adding a table.
- Use migrations.
- Add indexes for lookup fields.
- Do not weaken existing security policies.
- Do not store raw secrets in normal tables.
- Do not expose private data through public views.
