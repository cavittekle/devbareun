# v1.3.9.9 — AZ / Theme Exact Alignment Hotfix

## Fix
The AZ/theme capsule has been rebuilt with a definitive layout override:

- Capsule uses two equal 50% halves.
- Divider is absolute-centered.
- AZ is centered in the left half.
- Theme/sun icon is absolute-centered in the right half.
- Theme button text is hidden so JS text updates cannot shift the icon.
- The icon is rendered via CSS mask and cannot drift with font metrics.

## Updated file
- `frontend/css/landing-saas-v139.css`
