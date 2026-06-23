#!/usr/bin/env python3
"""Verify that DevBareun frontend brand/static assets are present.

This catches accidental release packages that include HTML/CSS/JS references to
/assets/* but omit frontend/assets/* files such as favicon, logos and OG image.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

ASSET_REF_RE = re.compile(r"(?:^|[\"'(\s])/?(?:\.\./)?assets/([^\"')?#\s]+)")
TEXT_SUFFIXES = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".webmanifest"}

REQUIRED_ASSETS = [
    "favicon.ico",
    "favicon.png",
    "apple-touch-icon.png",
    "devbareun-app-icon-512.png",
    "devbareun-logo-horizontal-white.svg",
    "devbareun-logo-horizontal-black.svg",
    "devbareun-logo-horizontal-cyan.svg",
    "devbareun-logo-compact-white.svg",
    "devbareun-logo-compact-black.svg",
    "devbareun-symbol-white.svg",
    "devbareun-symbol-black.svg",
    "devbareun-symbol-cyan.svg",
    "devbareun-wordmark-white.svg",
    "devbareun-wordmark-black.svg",
    "abstract-building-outline-bg.webp",
    "og-image.png",
]


def iter_text_files(frontend: Path) -> Iterable[Path]:
    excluded = {"node_modules", "dist", "build", ".git", "__pycache__"}
    for path in frontend.rglob("*"):
        if not path.is_file():
            continue
        if any(part in excluded for part in path.relative_to(frontend).parts[:-1]):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name == "site.webmanifest":
            yield path


def collect_references(frontend: Path) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for path in iter_text_files(frontend):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in ASSET_REF_RE.finditer(text):
            ref = match.group(1).strip().lstrip("/")
            if not ref or ref.startswith("data:") or "*" in ref or "(" in ref or ")" in ref:
                continue
            refs.setdefault(ref, set()).add(path.relative_to(frontend).as_posix())
    return refs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun frontend brand/static assets.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    frontend = root / "frontend"
    assets = frontend / "assets"
    errors: list[str] = []

    if not frontend.exists():
        errors.append("frontend/ directory is missing")
    if not assets.exists():
        errors.append("frontend/assets/ directory is missing")
    else:
        for name in REQUIRED_ASSETS:
            path = assets / name
            if not path.exists():
                errors.append(f"missing required brand asset: frontend/assets/{name}")
            elif path.stat().st_size <= 0:
                errors.append(f"empty brand asset: frontend/assets/{name}")

    refs = collect_references(frontend) if frontend.exists() else {}
    for ref, sources in sorted(refs.items()):
        if not (assets / ref).exists():
            errors.append(
                "missing referenced asset: "
                f"frontend/assets/{ref} referenced by {', '.join(sorted(sources)[:4])}"
            )

    if errors:
        print("Frontend asset check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Frontend asset check passed. Required assets: {len(REQUIRED_ASSETS)}; references: {len(refs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
