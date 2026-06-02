# DevBareun v1.2.11 — Result Upload Print Background Polish

## Fixes

1. Replaced the scaled landing background with a non-repeating full-page abstract construction line composition.
2. Scoped the animated background to landing pages; result/print pages are not affected.
3. Every generated analysis result now receives a fresh `result_id` / `report_id`.
4. Excel output includes Result ID and Project ID metadata, and export filenames use the unique report ID.
5. Print button receives a stable `window.print()` binding.
6. Upload file list remains visible after selecting multiple files; each file has its own remove button before analysis.

## QA focus

- Upload 3 files and remove only one file.
- Generate Full Project Control and other packages.
- Confirm result dashboard has unique Report ID.
- Export Excel and verify Result ID appears in workbook.
- Click Print on result dashboard.
- Scroll landing page and verify building background is continuous, non-repeating and not stretched.
