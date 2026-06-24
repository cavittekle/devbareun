# v1.4.11 Frontend Asset Restoration

This release restores the public brand/static asset bundle that is required by
landing pages, Open Graph metadata, the web manifest and the React workspace.

## Required source assets

The source package must include `frontend/assets/` with at least:

- `favicon.ico`
- `favicon.png`
- `apple-touch-icon.png`
- `devbareun-app-icon-512.png`
- `devbareun-logo-horizontal-white.svg`
- `devbareun-logo-horizontal-black.svg`
- `devbareun-logo-horizontal-cyan.svg`
- `devbareun-logo-compact-white.svg`
- `devbareun-logo-compact-black.svg`
- `devbareun-symbol-white.svg`
- `devbareun-symbol-black.svg`
- `devbareun-symbol-cyan.svg`
- `devbareun-wordmark-white.svg`
- `devbareun-wordmark-black.svg`
- `abstract-building-outline-bg.webp`
- `og-image.png`

These files are source/public assets, not generated dependencies. They must not
be removed by release-package cleanup.

## New asset gate

`tools/check_frontend_assets.py` scans frontend HTML/CSS/JS/JSX/manifest files
for `/assets/*` references and fails if the referenced file is missing under
`frontend/assets/`.

Run it locally:

```bash
python tools/check_frontend_assets.py --root .
```

The release gate and CI now require this checker so future packages cannot omit
favicons, logos or public Open Graph assets silently.
## Deployment configuration templates

`deploy/env/` contains safe placeholder templates, not a Python virtual environment. Release/package filters must retain this directory.
