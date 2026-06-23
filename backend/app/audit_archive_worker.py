from __future__ import annotations

import argparse
import json
import logging
import time
from typing import Any, Dict

from .services.audit_archive_service import drain_audit_archive_once, record_audit_archive_worker_heartbeat
from .telemetry import capture_exception, configure_telemetry, log_event

LOGGER = logging.getLogger("devbareun.audit_archive_worker")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deliver DevBareun audit archive outbox events to the configured HTTPS webhook.")
    parser.add_argument("--loop", action="store_true", help="Continuously poll the audit archive outbox.")
    parser.add_argument("--once", action="store_true", help="Run one delivery pass and exit.")
    parser.add_argument("--interval", type=float, default=15.0, help="Polling interval in seconds. Default: 15.")
    parser.add_argument("--batch-size", type=int, default=25, help="Maximum audit events per pass. Default: 25.")
    parser.add_argument("--worker-id", default=None, help="Optional stable worker identifier.")
    parser.add_argument("--max-loops", type=int, default=0, help="Optional loop cap; 0 is unlimited.")
    return parser


def _emit(result: Dict[str, Any]) -> None:
    log_event("audit_archive_worker_result", service="audit-archive-worker", worker_id=result.get("worker_id"), result=result)


def main() -> int:
    configure_telemetry(service_name="audit-archive-worker")
    args = _parser().parse_args()
    worker_id = args.worker_id or None
    loops = 0
    exit_code = 0
    try:
        while True:
            try:
                result = drain_audit_archive_once(worker_id=worker_id, batch_size=args.batch_size)
                worker_id = str(result.get("worker_id") or worker_id or "audit-archive-worker")
                _emit(result)
            except Exception as exc:
                exit_code = 1
                worker_id = worker_id or "audit-archive-worker"
                record_audit_archive_worker_heartbeat(worker_id=worker_id, status="degraded", error_type=exc.__class__.__name__)
                capture_exception(exc, event="audit_archive_worker_poll_failed", service="audit-archive-worker", worker_id=worker_id)
                if not args.loop or args.once:
                    return exit_code
            loops += 1
            if not args.loop or args.once:
                return exit_code
            if args.max_loops and loops >= args.max_loops:
                return exit_code
            time.sleep(max(1.0, float(args.interval)))
    finally:
        if worker_id:
            record_audit_archive_worker_heartbeat(worker_id=worker_id, status="stopped")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
