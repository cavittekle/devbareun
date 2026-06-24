#!/usr/bin/env python3
"""Validate DevBareun downloadable Excel templates and backend template manifest.

This deliberately avoids spreadsheet runtime dependencies. It reads .xlsx files
as ZIP packages and inspects xl/workbook.xml for sheet names, then compares the
result with backend/app/template_manifest.py and static frontend download links.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Sequence

TEMPLATE_LINK_RE = re.compile(r"(?:href|src)=[\"'](?:\./)?templates/([^\"'#?]+)")
TEXT_SUFFIXES = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".webmanifest"}
MIN_TEMPLATE_SIZE_BYTES = 1024


def iter_text_files(frontend: Path) -> Iterable[Path]:
    excluded = {"node_modules", "dist", "build", ".git", "__pycache__"}
    for path in frontend.rglob("*"):
        if not path.is_file():
            continue
        if any(part in excluded for part in path.relative_to(frontend).parts[:-1]):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name == "site.webmanifest":
            yield path


def load_template_manifest(root: Path) -> dict[str, dict[str, object]]:
    backend = root / "backend"
    module_path = backend / "app" / "template_manifest.py"
    if not module_path.exists():
        raise FileNotFoundError("backend/app/template_manifest.py is missing")
    # template_manifest imports app.analysis_types; make backend importable without importing app.main.
    sys.path.insert(0, str(backend))
    spec = importlib.util.spec_from_file_location("app.template_manifest", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load backend/app/template_manifest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = getattr(module, "TEMPLATE_MANIFEST", None)
    if not isinstance(manifest, dict):
        raise RuntimeError("TEMPLATE_MANIFEST must be a dictionary")
    return manifest


def workbook_sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        workbook_xml = archive.read("xl/workbook.xml")
    root = ET.fromstring(workbook_xml)
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [sheet.attrib.get("name", "") for sheet in root.findall("main:sheets/main:sheet", ns)]


def frontend_template_links(frontend: Path) -> dict[str, set[str]]:
    links: dict[str, set[str]] = {}
    for path in iter_text_files(frontend):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in TEMPLATE_LINK_RE.finditer(text):
            filename = match.group(1).strip()
            if filename:
                links.setdefault(filename, set()).add(path.relative_to(frontend).as_posix())
    return links


def check(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    frontend = root / "frontend"
    templates_dir = frontend / "templates"

    if not templates_dir.exists():
        return (["frontend/templates/ directory is missing"], warnings)

    try:
        manifest = load_template_manifest(root)
    except Exception as exc:  # pragma: no cover - surfaced to CLI/tests as error text.
        return ([f"could not load template manifest: {exc}"], warnings)

    manifest_files: dict[str, set[str]] = {}
    for key, item in manifest.items():
        if not isinstance(item, dict):
            errors.append(f"manifest entry {key!r} must be an object")
            continue
        filename = item.get("file")
        if not isinstance(filename, str) or not filename.endswith(".xlsx"):
            errors.append(f"manifest entry {key!r} has invalid file value: {filename!r}")
            continue
        manifest_files.setdefault(filename, set()).add(str(key))
        template_path = templates_dir / filename
        if not template_path.exists():
            errors.append(f"manifest template file is missing: frontend/templates/{filename}")
            continue
        if template_path.stat().st_size < MIN_TEMPLATE_SIZE_BYTES:
            errors.append(f"template file is suspiciously small: frontend/templates/{filename}")
            continue
        try:
            sheets = workbook_sheet_names(template_path)
        except Exception as exc:
            errors.append(f"template is not a valid xlsx package: frontend/templates/{filename}: {exc}")
            continue
        required = item.get("required_sheets", [])
        if not isinstance(required, list) or not all(isinstance(sheet, str) for sheet in required):
            errors.append(f"manifest entry {key!r} required_sheets must be a list[str]")
            continue
        missing_sheets = [sheet for sheet in required if sheet not in sheets]
        if missing_sheets:
            errors.append(
                f"manifest entry {key!r} requires sheets missing from {filename}: "
                + ", ".join(missing_sheets)
            )

    links = frontend_template_links(frontend)
    for filename, sources in sorted(links.items()):
        if not (templates_dir / filename).exists():
            errors.append(f"missing linked template: frontend/templates/{filename} referenced by {', '.join(sorted(sources))}")

    linked_or_manifest = set(links) | set(manifest_files)
    for path in sorted(templates_dir.glob("*.xlsx")):
        if path.name not in linked_or_manifest:
            warnings.append(f"template is packaged but not linked/manifested: frontend/templates/{path.name}")

    return errors, warnings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun Excel template downloads and manifest.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args(argv)

    errors, warnings = check(args.root.resolve())
    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        print("Template manifest check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if args.strict and warnings:
        print("Template manifest check failed because --strict was used.", file=sys.stderr)
        return 1
    print(f"Template manifest check passed. Warnings: {len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
