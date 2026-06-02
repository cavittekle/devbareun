#!/usr/bin/env python3
"""DevBareun GitHub Auto Upload

Uploads the current DevBareun frontend/ and backend/ folders into separate GitHub
repositories. It uses the GitHub Git Data API to create one commit per repository
instead of committing file-by-file.

Required environment variable:
  GITHUB_TOKEN or GH_TOKEN

Default repositories:
  frontend -> cavittekle/devbareun-frontend
  backend  -> cavittekle/devbareun-backend

Safe default:
  Creates/updates agentops-auto-sync branch and opens pull requests.

Examples:
  python tools/github_auto_upload.py --root .
  python tools/github_auto_upload.py --root . --direct-main
  python tools/github_auto_upload.py --root . --dry-run
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

API = "https://api.github.com"

DEFAULT_IGNORES = {
    ".git", ".github/workflows/.cache", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "agent_reports", "dist", "build", ".DS_Store", "Thumbs.db",
}

# Backend runtime data should not be uploaded to GitHub.
BACKEND_IGNORES = {"storage", "data"}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".pdf", ".xlsx", ".xls", ".xlsm",
    ".zip", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3"
}


@dataclass
class UploadPlan:
    source_dir: Path
    repo: str
    branch: str
    base_branch: str
    commit_message: str
    pull_request_title: str
    direct_main: bool = False
    clean: bool = False


class GitHubApi:
    def __init__(self, token: str):
        self.token = token

    def request(self, method: str, path: str, data: Optional[dict] = None, *, ok: Tuple[int, ...] = (200, 201, 204)) -> dict:
        url = path if path.startswith("https://") else API + path
        body = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DevBareun-AgentOps-AutoUploader",
        }
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            if e.code in ok:
                return json.loads(raw) if raw else {}
            raise RuntimeError(f"GitHub API {method} {path} failed: HTTP {e.code}: {raw}") from e

    def get_ref(self, repo: str, branch: str) -> dict:
        return self.request("GET", f"/repos/{repo}/git/ref/heads/{urllib.parse.quote(branch, safe='')}")

    def create_ref(self, repo: str, branch: str, sha: str) -> dict:
        return self.request("POST", f"/repos/{repo}/git/refs", {
            "ref": f"refs/heads/{branch}",
            "sha": sha,
        })

    def update_ref(self, repo: str, branch: str, sha: str, force: bool = True) -> dict:
        return self.request("PATCH", f"/repos/{repo}/git/refs/heads/{urllib.parse.quote(branch, safe='')}", {
            "sha": sha,
            "force": force,
        })

    def get_commit(self, repo: str, sha: str) -> dict:
        return self.request("GET", f"/repos/{repo}/git/commits/{sha}")

    def get_tree(self, repo: str, tree_sha: str, recursive: bool = True) -> dict:
        suffix = "?recursive=1" if recursive else ""
        return self.request("GET", f"/repos/{repo}/git/trees/{tree_sha}{suffix}")

    def create_blob(self, repo: str, content: bytes) -> str:
        payload = {
            "content": base64.b64encode(content).decode("ascii"),
            "encoding": "base64",
        }
        return self.request("POST", f"/repos/{repo}/git/blobs", payload)["sha"]

    def create_tree(self, repo: str, base_tree_sha: str, tree: List[dict]) -> str:
        return self.request("POST", f"/repos/{repo}/git/trees", {
            "base_tree": base_tree_sha,
            "tree": tree,
        })["sha"]

    def create_commit(self, repo: str, message: str, tree_sha: str, parent_sha: str) -> str:
        return self.request("POST", f"/repos/{repo}/git/commits", {
            "message": message,
            "tree": tree_sha,
            "parents": [parent_sha],
        })["sha"]

    def create_pr_if_missing(self, repo: str, title: str, head: str, base: str, body: str) -> dict:
        # Search existing open PRs from this head branch.
        existing = self.request("GET", f"/repos/{repo}/pulls?state=open&head={urllib.parse.quote(repo.split('/')[0] + ':' + head)}&base={urllib.parse.quote(base)}")
        if isinstance(existing, list) and existing:
            return existing[0]
        return self.request("POST", f"/repos/{repo}/pulls", {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "maintainer_can_modify": True,
            "draft": False,
        })


def should_ignore(path: Path, source_root: Path, *, is_backend: bool) -> bool:
    rel = path.relative_to(source_root)
    parts = set(rel.parts)
    if any(part in DEFAULT_IGNORES for part in rel.parts):
        return True
    if is_backend and rel.parts and rel.parts[0] in BACKEND_IGNORES:
        return True
    if path.name.endswith((".pyc", ".pyo", ".log", ".tmp")):
        return True
    return False


def collect_files(source_dir: Path, *, is_backend: bool) -> List[Path]:
    files = []
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        if should_ignore(path, source_dir, is_backend=is_backend):
            continue
        files.append(path)
    return sorted(files)


def upload_plan(api: GitHubApi, plan: UploadPlan, *, dry_run: bool = False) -> Dict[str, object]:
    if not plan.source_dir.exists():
        raise FileNotFoundError(f"Source folder not found: {plan.source_dir}")
    is_backend = plan.source_dir.name == "backend"
    files = collect_files(plan.source_dir, is_backend=is_backend)
    target_branch = plan.base_branch if plan.direct_main else plan.branch

    result: Dict[str, object] = {
        "repo": plan.repo,
        "source": str(plan.source_dir),
        "target_branch": target_branch,
        "file_count": len(files),
        "dry_run": dry_run,
        "clean": plan.clean,
        "commit_sha": None,
        "pull_request": None,
    }

    print(f"\n[{plan.repo}] {len(files)} files -> {target_branch}" + (" [clean sync]" if plan.clean else ""))
    for file in files[:12]:
        print("  +", file.relative_to(plan.source_dir).as_posix())
    if len(files) > 12:
        print(f"  ... +{len(files)-12} more files")

    if dry_run:
        return result

    base_ref = api.get_ref(plan.repo, plan.base_branch)
    base_sha = base_ref["object"]["sha"]
    base_commit = api.get_commit(plan.repo, base_sha)
    base_tree_sha = base_commit["tree"]["sha"]

    if not plan.direct_main:
        try:
            api.get_ref(plan.repo, target_branch)
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                api.create_ref(plan.repo, target_branch, base_sha)
            else:
                raise

    tree_entries = []
    local_paths = {file.relative_to(plan.source_dir).as_posix() for file in files}
    if plan.clean:
        current_tree = api.get_tree(plan.repo, base_tree_sha, recursive=True)
        for item in current_tree.get("tree", []):
            if item.get("type") != "blob":
                continue
            remote_path = item.get("path")
            if not remote_path or remote_path in local_paths:
                continue
            tree_entries.append({
                "path": remote_path,
                "mode": "100644",
                "type": "blob",
                "sha": None,
            })

    for file in files:
        rel_path = file.relative_to(plan.source_dir).as_posix()
        blob_sha = api.create_blob(plan.repo, file.read_bytes())
        tree_entries.append({
            "path": rel_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        })

    tree_sha = api.create_tree(plan.repo, base_tree_sha, tree_entries)
    commit_sha = api.create_commit(plan.repo, plan.commit_message, tree_sha, base_sha)
    api.update_ref(plan.repo, target_branch, commit_sha, force=True)
    result["commit_sha"] = commit_sha

    if not plan.direct_main:
        pr = api.create_pr_if_missing(
            plan.repo,
            plan.pull_request_title,
            target_branch,
            plan.base_branch,
            body=(
                "Automated DevBareun AgentOps sync.\n\n"
                f"Source folder: `{plan.source_dir.name}/`\n"
                f"Files uploaded: `{len(files)}`\n"
                f"Clean sync: `{plan.clean}`\n"
                "\nReview this PR before merging to production."
            ),
        )
        result["pull_request"] = {"number": pr.get("number"), "url": pr.get("html_url")}
        print(f"  PR: {pr.get('html_url')}")
    else:
        print(f"  Commit: https://github.com/{plan.repo}/commit/{commit_sha}")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload DevBareun frontend/backend to GitHub automatically.")
    parser.add_argument("--root", default=".", help="DevBareun package root containing frontend/ and backend/.")
    parser.add_argument("--frontend-repo", default="cavittekle/devbareun-frontend")
    parser.add_argument("--backend-repo", default="cavittekle/devbareun-backend")
    parser.add_argument("--base-branch", default="main")
    parser.add_argument("--branch", default="agentops-auto-sync")
    parser.add_argument("--direct-main", action="store_true", help="Push directly to main instead of creating PR branches.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true", help="Delete files from the target repo branch when they no longer exist in the source folder.")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-backend", action="store_true")
    parser.add_argument("--out", default="agent_reports/github_auto_upload_report.json")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token and not args.dry_run:
        print("ERROR: Set GITHUB_TOKEN or GH_TOKEN first.", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    api = GitHubApi(token or "dry-run-token")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")

    plans: List[UploadPlan] = []
    if not args.skip_frontend:
        plans.append(UploadPlan(
            source_dir=root / "frontend",
            repo=args.frontend_repo,
            branch=args.branch,
            base_branch=args.base_branch,
            commit_message=f"DevBareun AgentOps frontend auto-sync ({stamp})",
            pull_request_title="DevBareun frontend AgentOps auto-sync",
            direct_main=args.direct_main,
            clean=args.clean,
        ))
    if not args.skip_backend:
        plans.append(UploadPlan(
            source_dir=root / "backend",
            repo=args.backend_repo,
            branch=args.branch,
            base_branch=args.base_branch,
            commit_message=f"DevBareun AgentOps backend auto-sync ({stamp})",
            pull_request_title="DevBareun backend AgentOps auto-sync",
            direct_main=args.direct_main,
            clean=args.clean,
        ))

    results = []
    for plan in plans:
        results.append(upload_plan(api, plan, dry_run=args.dry_run))

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
