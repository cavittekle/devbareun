# DevBareun Backend v0.6.5 — Runtime + Report Export Fix

Fixes:
- Replaced backend/app/reports.py with the corrected report exporter.
- Fixed nested f-string risk in workforce formatting for Python compatibility.
- Added backend/runtime.txt with python-3.12.3 for Railway/Nixpacks.
- Expanded Azerbaijani Excel header styling labels: Dəyər, Qeyd, Vərəq, Növ, Tövsiyə olunan tədbirlər, Risk reyestri and related report headings.

Railway start command:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health check expected version:
```json
{"version":"0.7.1-commercial-accuracy-guardrails"}
```
