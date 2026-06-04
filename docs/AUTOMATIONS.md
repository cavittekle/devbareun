# DevBareun Codex Automations

## Purpose

This file stores reusable Codex automation prompts.

Use these prompts inside Codex Automations.

Recommended automations:

1. Weekly project audit
2. Daily build/test check
3. Pull request review
4. Security scan
5. Deployment readiness check

## General Automation Rule

Every automation should begin with:

```text
Read AGENTS.md and docs/PROJECT_STATE.md first.

Do not recreate the project.
Do not duplicate existing files, pages, components, APIs, routes, styles, database tables, migrations, or configuration files.
Find the existing implementation and improve only the required part.
```

## 1. Weekly Project Audit

Schedule:

```text
Every Monday at 09:00
```

Prompt:

```text
Read AGENTS.md and docs/PROJECT_STATE.md first.

Inspect the repository and check for:

- duplicated files
- duplicated pages
- duplicated components
- duplicated CSS or JS logic
- broken links
- broken routes
- build errors
- mobile layout problems
- dark-only public UI readability issues
- missing EN/AZ translations
- public copy using restricted wording
- exposed secrets or .env files
- deployment risks for Vercel, Railway, and Supabase
- empty dashboard sections
- fake dashboard data
- report/export risks

Rules:
- Do not recreate the project.
- Do not rewrite the whole codebase.
- Do not create a second version of existing pages or components.
- If something already exists, reuse and improve it.
- Only apply small safe fixes.
- If a change is risky, report it instead of applying it.

After checking, report:
1. Files checked
2. Problems found
3. Fixes applied
4. Problems that need approval
5. How to test
6. Recommended next task
```

## 2. Daily Build/Test Check

Schedule:

```text
Every day at 10:00
```

Prompt:

```text
Read AGENTS.md first.

Run a daily project health check.

Check:
- frontend build
- frontend lint if available
- backend syntax check
- backend tests if available
- missing environment variables
- obvious deployment risks
- committed .env files
- basic route/build problems

Rules:
- Do not change design.
- Do not refactor unrelated files.
- Fix only clear build-breaking issues.
- Report risky issues instead of changing them.

Return:
1. Commands run
2. Errors found
3. Files changed
4. Remaining issues
5. How to test
```

## 3. Pull Request Review

Use for PR review:

```text
Read AGENTS.md and docs/PROJECT_STATE.md first.

Review this pull request for:
- duplicated code
- broken build risks
- security risks
- exposed secrets
- frontend regressions
- backend regressions
- database risks
- localization regressions
- dashboard rendering problems
- missing tests
- deployment risks

Do not rewrite the project.
Do not suggest unrelated refactors.
Focus only on serious issues and practical fixes.

Return:
1. Critical issues
2. Medium risks
3. Safe suggestions
4. Files affected
5. Required tests
```

## 4. Security Scan

Schedule:

```text
Every Friday at 16:00
```

Prompt:

```text
Read AGENTS.md first.

Inspect the repository for security risks:
- committed secrets
- exposed API keys
- unsafe CORS
- unprotected private routes
- weak admin route protection
- unsafe file uploads
- missing payment webhook verification
- database access risks
- public storage risks
- service role key leakage
- JWT secret leakage

Do not make risky changes automatically.
Fix only obvious safe issues.
Report anything that needs approval.

Return:
1. Security risks found
2. Safe fixes applied
3. Issues requiring approval
4. Files checked
5. Recommended next steps
```

## 5. Deployment Readiness Check

Schedule:

```text
Every Wednesday at 11:00
```

Prompt:

```text
Read AGENTS.md and docs/DEPLOYMENT_GUIDE.md first.

Check deployment readiness for:
- Vercel frontend
- Railway backend
- Supabase database/auth/storage
- GitHub repository structure
- CI workflow
- environment variable documentation
- health check endpoint
- frontend API base URL
- CORS
- production build
- protected secrets

Rules:
- Do not modify unrelated project files.
- Fix only small clear deployment configuration issues.
- Report risky issues before changing them.

Return:
1. Deployment status
2. Missing environment variables
3. Build/test status
4. Safe fixes applied
5. Risks requiring approval
6. Next deployment steps
```

## 6. Localization Check

Schedule:

```text
Every Thursday at 12:00
```

Prompt:

```text
Read AGENTS.md and docs/PROJECT_STATE.md first.

Check EN/AZ localization quality:
- missing English strings
- missing Azerbaijani strings
- mixed-language UI
- hardcoded visible text
- dashboard labels not translated
- export/report labels not translated
- public copy using restricted wording

Rules:
- Preserve existing UI.
- Do not rewrite the whole localization system unless required.
- Add missing translation keys only where needed.
- Do not introduce restricted public wording.

Return:
1. Missing translations
2. Files changed
3. Public copy issues
4. How to test language switching
```

## 7. Dashboard Quality Check

Schedule:

```text
Every Tuesday at 15:00
```

Prompt:

```text
Read AGENTS.md and docs/PROJECT_STATE.md first.

Inspect dashboard rendering logic:
- empty cards
- placeholder charts
- fake KPIs
- duplicated sections
- Ref errors
- missing warnings for missing data
- mobile overflow
- dark-only readability
- export button issues

Rules:
- Do not create a new dashboard.
- Improve the existing dashboard only.
- Show sections only when relevant data exists.
- Do not add fake data.

Return:
1. Dashboard issues found
2. Safe fixes applied
3. Files changed
4. How to test with sample results
5. Remaining risks
```
