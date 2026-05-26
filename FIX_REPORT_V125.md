# DevBareun v1.2.5 — Flexible Upload + Adaptive Dashboard + Print + Landing Animation

## Fixed / Added

1. Upload file manager
   - Selected files are listed by real filename.
   - Each file has an individual remove button.
   - Clear/Generate state follows the currently selected files.

2. Adaptive dashboard profile
   - Backend now returns `advanced_sections.adaptive_dashboard`.
   - Dashboard blocks activate based on available uploaded evidence.
   - Missing blocks are shown as data requirements, not invented values.

3. Print button
   - Result dashboard now includes a Print button.
   - The button calls `window.print()` and uses existing print CSS.

4. Landing page animated background
   - Non-repeating animated construction skyline/grid background added across the full landing page.
   - Reduced-motion and print safeguards included.

## Version

`1.2.5-flexible-upload-adaptive-dashboard`
