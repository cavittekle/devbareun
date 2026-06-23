#!/usr/bin/env python3
"""Validate the static frontend deploy surface.

The public frontend is deployed from frontend/ as a static site. The React
workspace source lives under frontend/member-dashboard-app/, but the deployed
SPA entry must exist under frontend/workspace/ after running `npm run build`
from frontend/. This check catches release packages that include the React
source but forget the built /workspace surface used by vercel.json rewrites.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

SCRIPT_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
CSS_RE = re.compile(r'<link[^>]+href=["\']([^"\']+\.css)["\']', re.I)
MIN_JS_SIZE = 20_000
MIN_CSS_SIZE = 1_000


def resolve_workspace_asset(workspace: Path, ref: str) -> Path:
    ref = ref.split('?', 1)[0].split('#', 1)[0]
    if ref.startswith('/workspace/'):
        ref = ref[len('/workspace/'):]
    elif ref.startswith('workspace/'):
        ref = ref[len('workspace/'):]
    elif ref.startswith('/'):
        ref = ref.lstrip('/')
    return workspace / ref


def check(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    frontend = root / 'frontend'
    workspace = frontend / 'workspace'
    vercel = frontend / 'vercel.json'
    index = workspace / 'index.html'

    if not vercel.exists():
        errors.append('frontend/vercel.json is missing')
    elif '/workspace/index.html' not in vercel.read_text(encoding='utf-8', errors='replace'):
        errors.append('frontend/vercel.json does not rewrite workspace routes to /workspace/index.html')

    if not workspace.exists():
        errors.append('frontend/workspace/ is missing; run `cd frontend && npm run build` before packaging')
        return errors, warnings
    if not index.exists():
        errors.append('frontend/workspace/index.html is missing')
        return errors, warnings

    html = index.read_text(encoding='utf-8', errors='replace')
    scripts = SCRIPT_RE.findall(html)
    styles = CSS_RE.findall(html)
    if not scripts:
        errors.append('frontend/workspace/index.html has no script asset reference')
    if not styles:
        errors.append('frontend/workspace/index.html has no CSS asset reference')

    for ref in scripts:
        path = resolve_workspace_asset(workspace, ref)
        if not path.exists():
            errors.append(f'missing workspace script asset: frontend/workspace/{ref.lstrip("/")}')
        elif path.stat().st_size < MIN_JS_SIZE:
            errors.append(f'workspace JS asset is suspiciously small: {path.relative_to(root).as_posix()}')
    for ref in styles:
        path = resolve_workspace_asset(workspace, ref)
        if not path.exists():
            errors.append(f'missing workspace CSS asset: frontend/workspace/{ref.lstrip("/")}')
        elif path.stat().st_size < MIN_CSS_SIZE:
            errors.append(f'workspace CSS asset is suspiciously small: {path.relative_to(root).as_posix()}')

    for required in ('favicon.ico', 'favicon.png', 'devbareun-logo-horizontal-white.svg'):
        if not (workspace / 'assets' / required).exists():
            warnings.append(f'workspace brand asset missing: frontend/workspace/assets/{required}')

    return errors, warnings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Check DevBareun static workspace deploy surface.')
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Repository root.')
    parser.add_argument('--strict', action='store_true', help='Treat warnings as failures.')
    args = parser.parse_args(argv)

    errors, warnings = check(args.root.resolve())
    for warning in warnings:
        print(f'[WARN] {warning}')
    if errors:
        print('Frontend deploy surface check failed:', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1
    if args.strict and warnings:
        print('Frontend deploy surface check failed because --strict was used.', file=sys.stderr)
        return 1
    print(f'Frontend deploy surface check passed. Warnings: {len(warnings)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
