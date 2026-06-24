# Parser regression fixture policy

The parser regression tests generate small synthetic workbooks at runtime instead of storing binary `.xlsx` files in Git. This keeps the repository small while still exercising the real `openpyxl` parser path.

Covered scenarios in `backend/tests/test_parser_regression.py`:

- smeta-only baseline: confirms the dashboard does not invent actual cost, actual execution, or cost variance.
- smeta + F-2: confirms validated progress-payment evidence produces actual cost and execution percentage.
- baseline schedule without actual progress: confirms delay/progress-gap KPIs are withheld.
- workforce-only dashboard: confirms commercial and schedule KPIs are cleared for pure workforce analysis.

When adding real client examples, keep them anonymized and small. Do not commit confidential commercial totals, owner names, contractor names, signatures, stamps, or personal data.
