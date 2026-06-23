#!/usr/bin/env python3
"""Create a clean DevBareun release zip.

The packager is dependency-free and intentionally excludes generated folders,
local environments, repository metadata and runtime secrets. It writes a small
JSON manifest with file count, package size and SHA-256 checksum for audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

VERSION_RE = re.compile(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']')

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".turbo",
    "artifacts",
    "devbareun_full_v1.4.0_latest",
}

EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
}

ENV_ALLOWED = {".env.example", ".env.sample", ".env.template"}


def read_version(root: Path) -> str:
    version_file = root / "backend" / "app" / "version.py"
    if not version_file.exists():
        return "unknown"
    match = VERSION_RE.search(version_file.read_text(encoding="utf-8", errors="replace"))
    return match.group(1) if match else "unknown"


def is_env_file(path: Path) -> bool:
    name = path.name
    return name == ".env" or name.startswith(".env.")


def should_include(path: Path, root: Path, output_path: Path | None = None) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(part in EXCLUDED_DIRS for part in rel_parts[:-1]):
        return False
    if path.is_dir():
        return False
    if output_path and path.resolve() == output_path.resolve():
        return False
    if path.name in EXCLUDED_FILE_NAMES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if is_env_file(path) and path.name not in ENV_ALLOWED:
        return False
    return True


def iter_release_files(root: Path, output_path: Path | None = None) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if should_include(path, root, output_path):
            yield path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_zip(root: Path, output: Path, prefix: str) -> Dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    files = list(iter_release_files(root, output))
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            arcname = f"{prefix}/{path.relative_to(root).as_posix()}"
            zf.write(path, arcname)
    return {
        "file_count": len(files),
        "size_bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a clean DevBareun release zip.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to package.")
    parser.add_argument("--output", type=Path, help="Output .zip path. Defaults to artifacts/devbareun_refactored_v<version>.zip")
    parser.add_argument("--manifest", type=Path, help="Output manifest JSON path. Defaults next to the zip.")
    parser.add_argument("--prefix", help="Top-level directory name inside zip. Defaults to devbareun_refactored_v<version>.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.exists():
        print(f"Root does not exist: {root}", file=sys.stderr)
        return 2
    version = read_version(root)
    prefix = args.prefix or f"devbareun_refactored_v{version}"
    output = (args.output or (root / "artifacts" / f"{prefix}.zip")).resolve()
    manifest_path = (args.manifest or output.with_suffix(".manifest.json")).resolve()

    metadata = write_zip(root, output, prefix)
    manifest = {
        "package": output.name,
        "prefix": prefix,
        "version": version,
        **metadata,
        "excluded_dirs": sorted(EXCLUDED_DIRS),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created {output}")
    print(f"Manifest {manifest_path}")
    print(f"Files: {manifest['file_count']}  Size: {manifest['size_bytes']} bytes  SHA256: {manifest['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
