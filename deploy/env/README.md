# Provider environment templates

These templates are safe, placeholder-only references for the four production configuration surfaces plus a separate backup operator reference:

- `railway-web.env.template`: Railway FastAPI web service.
- `railway-worker.env.template`: Railway analysis worker service.
- `vercel.env.template`: Vercel public browser values.
- `backup-operator.env.template`: secured, non-provider backup/recovery operator reference.

Never fill values in these tracked templates. Copy values into the provider dashboards, or create ignored local files outside the repository for validation.

Before deployment, validate actual exported provider values without printing secrets:

```bash
python tools/check_provider_config.py \
  --railway-web-env /secure/path/railway-web.env \
  --railway-worker-env /secure/path/railway-worker.env \
  --vercel-env /secure/path/vercel.env
```

Template-only CI validation uses `--allow-placeholders`.


All Railway templates also include the v1.4.29 telemetry and backup-policy values. Use one real backend-only `DEVBAREUN_SENTRY_DSN` across web and worker services; do not place it in Vercel.
