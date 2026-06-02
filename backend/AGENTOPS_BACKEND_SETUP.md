# DevBareun Backend AgentOps

Run inside the backend repo:

```bash
python -m agents.devbareun_ops_engine.run_all_agents --root . --frontend-root . --backend-root . --out agent_reports
```

Primary checks in backend repo:

- Python syntax
- parser accuracy readiness
- security/secrets
- deployment readiness
- backend health check
- Chief Supervisor report
