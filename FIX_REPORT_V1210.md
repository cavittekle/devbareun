# DevBareun v1.2.10 — Global Landing Background Fix

## Fixed

- The abstract animated construction/building background was previously scoped to the hero section.
- On the landing page, especially around the upload wizard, the skyline looked cut off / half visible.

## Implementation

- Added a fixed full-page background layer through `body::before`.
- Added subtle animated grid/light motion through `body::after`.
- Disabled `.construction-abstract-bg` so the old hero-only background does not duplicate or appear half-cut.
- Background uses `no-repeat` and `cover`, with controlled opacity for dark/light modes.
- Motion is disabled for `prefers-reduced-motion`.
- Print output hides the decorative background.

## Changed files

- `frontend/css/styles.css`
- `backend/app/version.py`
- `AGENTOPS_RELEASE_MANIFEST.json`
