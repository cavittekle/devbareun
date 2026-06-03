# AGENTS.md

## Project Identity

This project is DevBareun, a construction analytics and project-control SaaS platform.

The project must be improved, not recreated.

Default public language: English.
Secondary language: Azerbaijani.

Public website copy must avoid these words:

- AI
- artificial intelligence
- suni intellekt
- intelligence
- intellekt

Use neutral construction SaaS wording instead:

- construction analytics
- project control
- management dashboard
- schedule analytics
- cost analytics
- risk analytics
- document control
- reporting
- project performance dashboard
- executive dashboard
- construction reporting platform

## Main Rule

Before making any change, inspect the existing codebase.

Do not recreate the project from scratch unless explicitly requested.

Do not duplicate existing pages, components, files, styles, APIs, routes, database tables, migrations, or configuration files.

If a similar implementation already exists, reuse it and improve it instead of creating a second version.

## Required Pre-Work Before Coding

Before editing files, always check:

1. What files and folders already exist.
2. Which files control the requested feature, bug, or design issue.
3. Whether the requested feature already exists.
4. Whether a similar page, component, function, API endpoint, database table, migration, route, or style already exists.
5. Whether the change affects frontend, backend, database, deployment, authentication, payment, storage, export, reports, or documentation.
6. Whether the change may break mobile layout, dark-only styling, localization, dashboard behavior, upload flow, print/export behavior, or existing user flows.
7. Whether the task can be completed with minimal changes.

Do not start coding before identifying the exact files that need to be changed.

## Do Not Repeat Or Rebuild

Do not:

- recreate the whole project
- create a new version of an existing page
- create a duplicate dashboard
- create duplicate components
- create duplicate CSS or styling systems
- create duplicate JavaScript logic
- create duplicate API endpoints
- create duplicate database tables
- create duplicate migrations
- create duplicate configuration files
- rename files unnecessarily
- change folder structure unnecessarily
- replace the approved design direction
- remove working features without explicit instruction
- add unrelated sections or features
- add fake data unless explicitly requested
- hardcode values that should come from config, database, or environment variables
- commit secrets, API keys, tokens, passwords, service role keys, or `.env` files

Always:

- edit existing files when possible
- keep changes small and focused
- preserve the existing architecture
- preserve the existing design style
- preserve existing user flows
- remove duplication only when safe
- explain what was changed
- explain how to test the result

## Design Preservation Rules

Preserve the approved DevBareun visual direction:

- clean cyan/blue branding
- professional construction SaaS interface
- dark-only public landing experience unless the user explicitly requests a theme change
- mobile-first layout
- compact footer
- EN/AZ language toggle
- upload section
- pricing section
- dashboard preview
- orbit-logo loading screen or equivalent polished loading state
- executive construction dashboard style
- customer dashboard after login
- public landing page without forced login
- PDF and Excel export direction
- Supabase + Vercel + Railway + GitHub deployment direction

Do not replace the UI with a completely different design unless explicitly requested.

## Logo Rules

Use the approved DevBareun logo direction consistently:

- DB monogram
- white geometric D+B mark
- blue analytics bars inside the D
- blue circular connector between D and B
- DevBareun wordmark where "Dev" is white and "Bareun" is blue

Apply the same logo style in:

- header
- loading screen
- footer
- dashboard header
- favicon
- deployment package

## Frontend Rules

Before creating a new component, check whether an existing component can be reused.

Before adding new CSS, check whether existing styles already solve the need.

Before creating a new page, check whether the page already exists.

Visible text must support localization if the project has EN/AZ language switching.

When changing frontend:

- keep responsive behavior
- check mobile widths around 360px, 390px, and 430px
- avoid horizontal overflow
- keep the dark interface readable
- keep EN/AZ switching working
- keep spacing and typography consistent
- preserve approved header, footer, loading screen, and dashboard direction
- do not add unnecessary visual noise
- do not show empty cards, empty sections, placeholder charts, or fake dashboard data in production UI

## Localization Rules

Default language is English.

Azerbaijani is the secondary language.

Do not leave mixed-language UI.

When adding new visible text:

- add both English and Azerbaijani versions
- keep construction terminology professional
- make sure buttons, menus, labels, tooltips, dashboard titles, form errors, and report/export labels are translated
- selected language should apply to the dashboard and reports/exports where applicable

## Backend Rules

Before creating a new service, module, route, controller, or endpoint, check whether similar backend logic already exists.

Do not merge unrelated backend logic into one large file.

Keep business logic separated from route/controller logic when possible.

Validate inputs.

Return clear errors.

Do not expose internal stack traces or production errors to users.

Preferred backend separation:

- parser
- analytics
- risk engine
- report generator
- database
- auth
- API routes
- scheduler
- export logic
- payment logic

## Parser Rules

Parser must avoid aggressive guessing.

Parser should return:

- normalized JSON
- confidence score
- missing fields
- warnings
- detected project name
- detected contract value
- detected planned progress
- detected actual progress
- detected F-2 / progress payment data
- detected workforce data
- detected material stock data
- detected schedule data
- detected contractor name
- detected building/block names

Do not use section titles as project names if a better project header exists.

Do not inflate EAC when progress is too low.

If data is missing or uncertain, return warnings instead of fake values.

## Dashboard Rules

Dashboard must be dynamic.

Show sections only when relevant data exists.

Allowed dashboard sections:

- Executive Summary
- Schedule Status
- Delay Analysis
- Cost Control
- F-2 / Progress Payment Trend
- Workforce Productivity
- Material Continuity
- Risk Heatmap
- Critical Activities
- Recovery Actions
- Decision Register
- Export Buttons

Do not show:

- empty cards
- fake KPIs
- placeholder charts
- Ref errors
- duplicated dashboard sections
- unrelated analytics blocks

## SaaS Rules

DevBareun should support:

- guest one-time project analysis
- Plus plan with limited monthly project analyses
- Pro plan with higher monthly project limits
- user authentication
- protected customer dashboard
- report archive
- PDF export
- Excel export
- admin panel
- Supabase database
- payment provider abstraction

Do not hardcode only one payment provider into the core business logic.

Keep payment provider logic separated from subscription, plan, credit, and usage-limit logic.

## Database And Supabase Rules

Before creating a new table, check whether an existing table can be extended safely.

Do not duplicate database models or tables.

Use migrations when the project uses migrations.

Add indexes where needed.

Protect user-owned data.

Never expose:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- database password
- private storage keys
- production credentials

Frontend may only use public/anon keys.

Database should use:

- user ownership
- project ownership
- protected private files
- admin-only access where needed
- Row Level Security policies where applicable

## Authentication And Security Rules

Protect private routes.

Protect admin routes.

Validate file uploads.

Apply rate limiting if the project has public APIs.

Never commit:

- real `.env` files
- API keys
- service role keys
- database passwords
- JWT secrets
- private tokens
- payment secrets
- production credentials

Use `.env.example` only for variable names.

## Deployment Rules

Deployment targets:

- Frontend: Vercel
- Backend: Railway
- Database/Auth/Storage: Supabase
- Repository: GitHub

Keep deployment files clean.

Do not commit real secrets.

Use:

- `.env.example`
- README setup guide
- deployment guide
- health check endpoint
- clear environment variable documentation

## Testing Rules

After changes, run the available checks for the project.

Use whichever commands exist:

- `npm run build`
- `npm run lint`
- `npm test`
- `pnpm build`
- `pnpm test`
- `yarn build`
- `yarn test`
- `python -m pytest`
- `python -m compileall`
- backend health check

If tests cannot be run, explain why.

Do not claim tests passed if they were not run.

## Documentation Rules

Update documentation when the change affects:

- setup
- environment variables
- deployment
- API behavior
- database schema
- authentication
- payment
- upload flow
- dashboard behavior
- user flow
- important project structure

Keep documentation short and practical.

## Task Discipline

Every task must be small and focused.

If the user asks for one fix, only fix that issue.

Do not refactor unrelated files.

Do not improve unrelated areas unless they directly block the requested task.

Do not create a new version or package unless explicitly requested.

Do not rename the project.

Do not change branding without explicit instruction.

## Required Output After Every Task

At the end of every task, report:

1. Files changed
2. What changed
3. Why it changed
4. What was not changed
5. How to test
6. Risks or follow-up tasks

## Final Rule

Inspect first.

Reuse existing code.

Improve only what is needed.

Do not duplicate.

Do not rebuild.

Do not guess.

If something is unclear, explain the uncertainty before making risky changes.
