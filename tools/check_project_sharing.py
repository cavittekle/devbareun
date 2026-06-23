#!/usr/bin/env python3
"""Static contract checker for explicit project sharing v1.4.33."""
from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

@dataclass
class Result:
    errors: List[str] = field(default_factory=list)
    @property
    def ok(self) -> bool: return not self.errors

def check(root: Path) -> Result:
    root=root.resolve(); r=Result()
    files={
      'migration':root/'database/2026_06_21_v1433_project_sharing.sql',
      'service':root/'backend/app/services/project_sharing_service.py',
      'routes':root/'backend/app/project_sharing_routes.py',
      'doc':root/'docs/PROJECT_SHARING_V1433.md',
      'client':root/'frontend/member-dashboard-app/src/api/client.js',
      'page':root/'frontend/member-dashboard-app/src/pages/ProjectAccess.jsx',
    }
    for label,path in files.items():
      if not path.exists(): r.errors.append(f'missing project-sharing {label}: {path.relative_to(root)}')
    if r.errors:return r
    migration=files['migration'].read_text(encoding='utf-8',errors='replace').lower()
    for item in ('create table if not exists public.project_access_grants','project_role in (\'manager\', \'editor\', \'viewer\')','enable row level security','validate_project_access_grant_v1433','company membership'):
      if item not in migration:r.errors.append(f'project-sharing migration missing: {item}')
    service=files['service'].read_text(encoding='utf-8',errors='replace')
    for item in ('PROJECT_ROLES','RESOURCE_ROLES','project_access_role','can_access_project_resource','list_accessible_projects','grant_project_access'):
      if item not in service:r.errors.append(f'project-sharing service missing: {item}')
    routes=files['routes'].read_text(encoding='utf-8',errors='replace')
    for item in ('@router.get("/projects")','@router.get("/{project_id}/members")','@router.post("/{project_id}/members")','@router.patch("/{project_id}/members/{grant_id}")','@router.delete("/{project_id}/members/{grant_id}")'):
      if item not in routes:r.errors.append(f'project-sharing route missing: {item}')
    client=files['client'].read_text(encoding='utf-8',errors='replace')
    if 'projectAccessProjects' not in client or '/api/project-access/projects' not in client:r.errors.append('frontend client does not use explicit project-access list')
    order=(root/'database/SUPABASE_DEPLOY_ORDER.md').read_text(encoding='utf-8',errors='replace')
    if '2026_06_21_v1433_project_sharing.sql' not in order:r.errors.append('deploy order missing v1.4.33 project-sharing migration')
    ci=root/'.github/workflows/ci.yml'
    if not ci.exists() or 'tools/check_project_sharing.py' not in ci.read_text(encoding='utf-8',errors='replace'):r.errors.append('CI does not run project-sharing checker')
    return r

def main(argv:Sequence[str]|None=None)->int:
  p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());args=p.parse_args(argv);r=check(args.root)
  for e in r.errors:print('[FAIL]',e)
  print(f'Project sharing contract {"passed" if r.ok else "failed"}: {len(r.errors)} error(s).')
  return 0 if r.ok else 1
if __name__=='__main__':raise SystemExit(main())
