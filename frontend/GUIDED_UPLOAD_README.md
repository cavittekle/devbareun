# DevBareun guided upload flow v0.4.0

This package adds the product flow requested for MVP:

1. Analysis type selection before upload: Cost, Schedule, Workforce, Progress Report, Full Dashboard.
2. Optional templates for each analysis type.
3. Parser focus passed to the backend as `analysis_type`.
4. Preflight/mapping preview after upload.
5. Missing fields panel for manual inputs when required data is not detected.

Frontend repo: upload all files except `/backend` if backend is deployed separately.
Backend repo: upload the contents of `/backend` to `devbareun-backend`.

Railway start command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```


## v0.5.0 Analysis-specific dashboards

Each selected analysis type now produces a matching dashboard view and the PDF/Excel exports are generated from the same selected dashboard payload. Supported views: Cost, Schedule/Delay, Workforce, Progress/F-2 and Executive Dashboard.
