# DevBareun Frontend + Universal Backend MVP Package

This package contains the DevBareun public frontend and a working backend MVP for construction project file processing.

## Main fixes included

- Added a real `backend/` folder with FastAPI endpoints.
- Added sheet-level construction file classification:
  - cost / smeta / BOQ
  - schedule / baseline / Primavera-style exports
  - progress / Forma-2 / plan-fact tables
  - workforce / manpower tables
  - procurement / material delivery data
  - report/supporting documents
- Added automatic project name detection from Excel/CSV sheet content, sheet names and file names.
- Added currency detection:
  - AZN / manat / ₼ → AZN
  - USD / $ → USD
  - EUR / € → EUR
  - Azerbaijani/Turkish files default to AZN only when no explicit currency is found.
- Removed misleading static result values from `result-dashboard.html`.
- Result dashboard now shows placeholders until backend JSON is loaded.
- Result dashboard now updates KPI cards, risk score, risk register, recommended actions, forecast, cost and workforce panels from backend data.
- PDF export now uses wrapped paragraphs/tables so the executive summary is not cut.
- Excel export now includes KPI, risk register, actions and sheet classification profiles.
- Frontend upload flow now supports drag-and-drop files correctly when sending files to backend.
- API base is configurable and defaults to `http://localhost:8000` for local testing.

## Folder structure

```text
devbareun_generate_fix/
  index.html
  result-dashboard.html
  css/
  js/
  assets/
  backend/
    app/
      main.py
      parser.py
      analyzer.py
      reports.py
      models.py
    requirements.txt
    README.md
```

## Local test

### 1. Start backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```text
http://localhost:8000/api/health
```

### 2. Open frontend

Open `index.html` in browser, upload an Excel/CSV/PDF file and click **Generate Preview**.

For best local testing, use a local static server:

```bash
python -m http.server 5500
```

Then open:

```text
http://localhost:5500
```

## Deployment note

- Frontend can be deployed on Vercel.
- Backend can be deployed on Railway/Render/Fly.io.
- Update API base in `js/api-client.js` or set `window.DEVBAREUN_API_BASE` before loading the API client.


## v0.5.0 Analysis-specific dashboards

Each selected analysis type now produces a matching dashboard view and the PDF/Excel exports are generated from the same selected dashboard payload. Supported views: Cost, Schedule/Delay, Workforce, Progress/F-2 and Executive Dashboard.


## v0.9.3 — Professional Upload Template Fix

The optional upload template has been replaced with a professional multi-sheet construction workbook for cost, F-2, schedule, workforce and equipment data.
