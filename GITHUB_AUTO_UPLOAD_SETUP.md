# DevBareun GitHub Auto Upload v1.1.3

This package can upload the DevBareun frontend and backend folders into separate GitHub repositories.

## What it does

- Uploads `frontend/` to `cavittekle/devbareun-frontend`.
- Uploads `backend/` to `cavittekle/devbareun-backend`.
- Safe default: creates/updates `agentops-auto-sync` branch and opens Pull Requests.
- Optional direct mode: pushes directly to `main`.
- Optional clean mode: deletes files from the target repo branch when they no longer exist in the source folder.
- Ignores runtime folders such as `backend/storage/`, `backend/data/`, `.venv/`, `__pycache__/`, and `agent_reports/`.

## Recommended safe command

```bash
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
python tools/github_auto_upload.py --root .
```

On Windows PowerShell:

```powershell
$env:GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
python tools/github_auto_upload.py --root .
```

## Dry run

```bash
python tools/github_auto_upload.py --root . --dry-run
```

## Clean sync

Use this when the old frontend/backend files are still visible in GitHub and you want the target repo to match this package exactly:

```bash
python tools/github_auto_upload.py --root . --clean
```

## Direct main push

Use only when you are sure:

```bash
python tools/github_auto_upload.py --root . --direct-main --clean
```

## GitHub Actions

The package includes:

```text
.github/workflows/devbareun-github-auto-upload.yml
```

Add this repository secret:

```text
GH_SYNC_TOKEN
```

Then run the workflow manually from GitHub Actions.

## AgentOps integration

The `GitHubSyncAgent` checks whether GitHub auto-upload is configured, whether the token is present, and whether clean-sync support is available.
