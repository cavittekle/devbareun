# DevBareun Backend v0.8.0 — Assisted Column Mapping

Adds optional OpenAI-assisted sheet and column mapping as a fallback layer.

## Safety model
- Rule-based parser remains primary.
- OpenAI is called only when preflight confidence is below the configured threshold.
- Only sheet names, headers and a few sample rows are sent; full workbooks are not sent.
- OpenAI maps structure only; Python performs all commercial calculations.
- User confirmation remains required for unclear mappings.

## Environment variables
```bash
OPENAI_MAPPING_ENABLED=true
OPENAI_API_KEY=sk-...
OPENAI_MAPPING_MODEL=gpt-4.1-mini
OPENAI_MAPPING_CONFIDENCE_THRESHOLD=85
```

If the variables are missing, the backend works normally using the deterministic parser.
