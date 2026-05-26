# DevBareun v0.7.0 — WebP Background + Offset Path Dots

## Changes
- Replaced `assets/abstract-building-outline-bg.png` with optimized `assets/abstract-building-outline-bg.webp`.
- Background size reduced from approximately 1.12 MB to a small WebP asset.
- Updated `css/styles.css` to reference the WebP background.
- Added `offset-path` motion for 4 line dots so the light points move along abstract building/grid contours instead of simple horizontal movement.
- Kept `prefers-reduced-motion` behavior.
- Added `netlify.toml` with `www.devbareun.com` to `devbareun.com` redirect and asset cache headers.

## Deploy
Upload this frontend package to Netlify, then verify:
- `devbareun.com` shows the v0.7.0 background.
- `www.devbareun.com` redirects to `devbareun.com`.
- Lighthouse/network shows the WebP background loaded instead of PNG.
