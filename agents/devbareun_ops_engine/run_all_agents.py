from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from agents.devbareun_ops_engine.agent_base import load_config
from agents.devbareun_ops_engine.backend_parser_accuracy_agent import BackendParserAccuracyAgent
from agents.devbareun_ops_engine.backend_syntax_agent import BackendSyntaxAgent
from agents.devbareun_ops_engine.browser_qa_agent import BrowserQaAgent
from agents.devbareun_ops_engine.chief_supervisor_agent import ChiefSupervisorAgent
from agents.devbareun_ops_engine.construction_marketing_research_agent import ConstructionMarketingResearchAgent
from agents.devbareun_ops_engine.deployment_readiness_agent import DeploymentReadinessAgent
from agents.devbareun_ops_engine.frontend_readability_agent import FrontendReadabilityAgent
from agents.devbareun_ops_engine.github_sync_agent import GitHubSyncAgent
from agents.devbareun_ops_engine.language_audit_agent import LanguageAuditAgent
from agents.devbareun_ops_engine.release_manager_agent import ReleaseManagerAgent
from agents.devbareun_ops_engine.security_secrets_agent import SecuritySecretsAgent
from agents.devbareun_ops_engine.seo_audit_agent import SeoAuditAgent
from agents.devbareun_ops_engine.site_manager_agent import SiteManagerAgent


AGENTS = [
    BackendSyntaxAgent,
    BackendParserAccuracyAgent,
    FrontendReadabilityAgent,
    LanguageAuditAgent,
    SeoAuditAgent,
    SecuritySecretsAgent,
    DeploymentReadinessAgent,
    GitHubSyncAgent,
    SiteManagerAgent,
    BrowserQaAgent,
    ConstructionMarketingResearchAgent,
    ReleaseManagerAgent,
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DevBareun Ops Engine agents.")
    parser.add_argument("--root", default=".", help="Package/repository root.")
    parser.add_argument("--frontend-root", default=None)
    parser.add_argument("--backend-root", default=None)
    parser.add_argument("--out", default="agent_reports")
    parser.add_argument("--config", default=None)
    parser.add_argument("--strict", action="store_true", help="Return non-zero on warnings as well as failures.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    frontend = Path(args.frontend_root).resolve() if args.frontend_root else root / "frontend"
    backend = Path(args.backend_root).resolve() if args.backend_root else root / "backend"
    out_dir = Path(args.out).resolve()
    config = load_config(root, args.config)

    results = []
    for cls in AGENTS:
        agent = cls(root=root, frontend_root=frontend, backend_root=backend, out_dir=out_dir, config=config)
        result = agent.run()
        results.append(result)
        print(f"[{result.status.upper():4}] {result.agent:34} score={result.score:3} {result.summary}")

    supervisor = ChiefSupervisorAgent(root=root, out_dir=out_dir)
    report_paths = supervisor.write_reports(results)
    grade = supervisor.grade(results)

    print("")
    print(f"Supervisor decision: {grade['decision']}")
    print(f"Markdown report: {report_paths['markdown']}")
    print(f"JSON report: {report_paths['json']}")

    if grade["fail_count"] > 0:
        return 2
    if args.strict and grade["warn_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
