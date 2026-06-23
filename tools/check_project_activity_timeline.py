#!/usr/bin/env python3
"""Static release contract for the v1.4.34 project activity timeline."""
from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    @property
    def ok(self) -> bool: return not self.errors

def check(root: Path) -> Result:
    root=root.resolve(); r=Result()
    files={
      "migration": root/"database/2026_06_21_v1434_project_activity_timeline.sql",
      "service": root/"backend/app/services/project_activity_service.py",
      "routes": root/"backend/app/project_activity_routes.py",
      "doc": root/"docs/PROJECT_ACTIVITY_TIMELINE_V1434.md",
      "page": root/"frontend/member-dashboard-app/src/pages/ProjectActivity.jsx",
      "client": root/"frontend/member-dashboard-app/src/api/client.js",
    }
    for label,path in files.items():
      if not path.exists(): r.errors.append(f"missing project activity {label}: {path.relative_to(root)}")
    if r.errors: return r
    migration=files["migration"].read_text(encoding="utf-8",errors="replace").lower()
    for item in ("create table if not exists public.project_activity_events", "project_activity_events_immutable_v1434", "enable row level security", "project_activity_events_select_scoped_v1434", "same-company membership alone"):
      if item not in migration: r.errors.append(f"project activity migration missing: {item}")
    service=files["service"].read_text(encoding="utf-8",errors="replace")
    for item in ("record_project_activity", "list_project_activity", "sanitize_metadata", "storage_path", "signed_url"):
      if item not in service: r.errors.append(f"project activity service missing: {item}")
    routes=files["routes"].read_text(encoding="utf-8",errors="replace")
    if '@router.get("/{project_id}")' not in routes or 'section="project_activity"' not in routes:
      r.errors.append("project activity route does not enforce project scope")
    main=(root/"backend/app/main.py").read_text(encoding="utf-8",errors="replace")
    if "project_activity_router" not in main: r.errors.append("main application does not register project activity router")
    sharing=(root/"backend/app/services/project_sharing_service.py").read_text(encoding="utf-8",errors="replace")
    if '"project_activity"' not in sharing: r.errors.append("project activity scope missing from project role policy")
    client=files["client"].read_text(encoding="utf-8",errors="replace")
    if "projectActivity:" not in client or "/api/project-activity/" not in client: r.errors.append("frontend client lacks project activity endpoint")
    order=(root/"database/SUPABASE_DEPLOY_ORDER.md").read_text(encoding="utf-8",errors="replace")
    if "2026_06_21_v1434_project_activity_timeline.sql" not in order: r.errors.append("deploy order missing v1.4.34 project activity migration")
    ci=root/".github/workflows/ci.yml"
    if not ci.exists() or "tools/check_project_activity_timeline.py" not in ci.read_text(encoding="utf-8",errors="replace"):
      r.errors.append("CI does not run project activity checker")
    return r

def main(argv: Sequence[str] | None = None) -> int:
  p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());args=p.parse_args(argv);r=check(args.root)
  for error in r.errors: print("[FAIL]",error)
  print(f"Project activity timeline contract {'passed' if r.ok else 'failed'}: {len(r.errors)} error(s).")
  return 0 if r.ok else 1
if __name__ == "__main__": raise SystemExit(main())
