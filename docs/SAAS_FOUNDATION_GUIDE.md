
# DevBareun v1.3.0 SaaS Foundation

This release does **not** recreate the website. It preserves the current DevBareun landing page, upload section, dashboard, loading screen, cyan/blue branding, header/footer and responsive enterprise SaaS visual language.

The purpose is to add the first real SaaS foundation layer around the existing platform:

- user/company/project data model
- guest one-time analysis flow
- project/file/analysis/report IDs
- Supabase-ready database schema
- Stripe-ready checkout and webhook skeleton
- admin API skeleton
- credit and plan model
- secure guest result token model

## Business model

### Single Project
One-time construction project review. No monthly subscription required.

### Plus
Monthly subscription with 5 project analyses per month.

### Pro
Monthly subscription with 20 project analyses per month and advanced exports.

## Important terminology rule
Public website copy should avoid the words AI, Artificial Intelligence, intelligence, süni intellekt and intellekt. Use construction analytics, project control, management dashboard, risk analytics, schedule analytics, cost analytics, document control, reporting and project review.

## Current status

v1.3.0 is a foundation layer. It adds SaaS-ready routes, data schema and documentation. Production Supabase Auth, Supabase Storage and Stripe secrets must be configured before commercial launch.
