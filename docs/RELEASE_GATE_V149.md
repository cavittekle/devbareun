# DevBareun v1.4.9 Release Gate and Package Hygiene

v1.4.9 adds a cross-platform release gate and package builder so the repository can be checked and packaged consistently on Linux, macOS, Windows, GitHub Actions and local developer machines.

## Release gate

Run from the repository root:

```bash
python tools/release_gate.py --root .
```

The gate is dependency-free and checks:

- required project, backend, frontend, database, docs and tool files are present;
- generated/cache directories such as `.git`, `.venv`, `node_modules`, `dist`, `__pycache__` and `.pytest_cache` are not part of the release tree;
- real runtime `.env` files are not committed;
- obvious secret patterns are not present in text files;
- `APP_VERSION` is represented in `docs/CHANGELOG.md`;
- Supabase deploy-order SQL references exist and include the canonical production migration chain;
- frontend package metadata includes a reproducible lockfile and build script;
- CI mentions the release gate, env validator, backend tests and `npm ci`.

For stricter package-tree and migration audits:

```bash
python tools/release_gate.py --root . --strict-package-tree
python tools/release_gate.py --root . --require-all-migrations
```

Use `--strict-package-tree` on an already-clean release extraction. Use the migration strict flag only when every historical migration in `database/20*.sql` must be listed in `database/SUPABASE_DEPLOY_ORDER.md`. The default mode validates the production deploy path without forcing superseded historical files into a clean install order.

## Clean package builder

Run from the repository root:

```bash
python tools/package_release.py --root .
```

Default output:

```text
artifacts/devbareun_refactored_v1.4.9.zip
artifacts/devbareun_refactored_v1.4.9.manifest.json
```

The package excludes:

```text
.git
.venv
node_modules
dist
build
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
artifacts
devbareun_full_v1.4.0_latest
runtime .env files
logs/temp files
```

The manifest records:

```text
version
file_count
size_bytes
sha256
created_at_utc
excluded_dirs
```

## Recommended pre-release command sequence

```bash
python tools/release_gate.py --root .
python tools/validate_production_env.py --backend-env backend/.env.example --frontend-env frontend/.env.example --allow-placeholders
python -m compileall -q backend/app agents/devbareun_ops_engine tools
cd backend && pytest -q
cd ../frontend/member-dashboard-app && npm ci && npm run build
cd ../..
python tools/package_release.py --root .
```

For a deployed environment, run the HTTP smoke test after Vercel/Railway are updated:

```bash
python tools/smoke_deploy.py \
  --frontend-url https://devbareun.com \
  --backend-url https://devbareun-production.up.railway.app \
  --strict \
  --retries 3
```

## CI update

`.github/workflows/ci.yml` now runs the release gate and env-example validator before build/test steps. This catches common release mistakes earlier than deployment.
