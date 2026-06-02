# Generate + Universal Parser Fix

This version fixes the previous Generate Preview flow and adds the backend MVP needed for real construction-file processing.

## Fixed

- Choose Files click reliability
- Drag-and-drop file upload compatibility with backend submission
- Generate Preview click not responding
- Old frontend-only preview overriding backend flow
- Visible backend progress status
- Static dashboard sample values shown when backend data is missing
- Project name not being detected from uploaded content
- AZN currency handling for Azerbaijani/Turkish construction files
- PDF report text being cut due to missing wrapping

## New backend logic

```text
Upload
→ File type detection
→ Sheet-level classification
→ Header detection
→ Column mapping
→ Data normalization
→ Validation / confidence score
→ Dashboard JSON
→ PDF / Excel export
```

Supported construction data categories:

```text
cost, schedule, progress, workforce, procurement, report/supporting document
```
