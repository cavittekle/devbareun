from __future__ import annotations

import argparse
import json
import logging
import time
from typing import Any, Dict

from .services.analysis_job_service import DEFAULT_WORKER_STALE_AFTER_MINUTES, analysis_job_mode, record_analysis_worker_heartbeat, run_worker_once
from .telemetry import capture_exception, configure_telemetry, log_event


LOGGER = logging.getLogger("devbareun.analysis_worker")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run queued DevBareun analysis jobs from the analysis_jobs table.")
    parser.add_argument("--loop", action="store_true", help="Continuously poll for queued jobs.")
    parser.add_argument("--once", action="store_true", help="Run one polling pass and exit. This is the default when --loop is not set.")
    parser.add_argument("--interval", type=float, default=10.0, help="Polling interval in seconds for --loop mode. Default: 10.")
    parser.add_argument("--batch-size", type=int, default=1, help="Maximum jobs to claim per pass. Default: 1.")
    parser.add_argument("--worker-id", default=None, help="Optional stable worker identifier for logs and job locks.")
    parser.add_argument("--stale-after-minutes", type=int, default=DEFAULT_WORKER_STALE_AFTER_MINUTES, help="Requeue running jobs older than this many minutes. Default: 45.")
    parser.add_argument("--max-loops", type=int, default=0, help="Optional safety cap for loop mode. 0 means unlimited.")
    return parser


def _emit(result: Dict[str, Any]) -> None:
    log_event("analysis_worker_result", service="analysis-worker", worker_id=result.get("worker_id"), result=result)


def main() -> int:
    configure_telemetry(service_name="analysis-worker")
    args = _build_parser().parse_args()
    worker_id = args.worker_id or None
    log_event("analysis_worker_started", service="analysis-worker", mode=analysis_job_mode(), loop=bool(args.loop), batch_size=args.batch_size)

    loops = 0
    exit_code = 0
    try:
        while True:
            try:
                result = run_worker_once(
                    batch_size=args.batch_size,
                    worker_id=worker_id,
                    stale_after_minutes=args.stale_after_minutes,
                )
                worker_id = str(result.get("worker_id") or worker_id or "analysis-worker")
                _emit(result)
            except Exception as exc:
                exit_code = 1
                worker_id = worker_id or "analysis-worker"
                record_analysis_worker_heartbeat(worker_id=worker_id, status="degraded", error_type=exc.__class__.__name__)
                capture_exception(exc, event="analysis_worker_poll_failed", service="analysis-worker", worker_id=worker_id)
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
            record_analysis_worker_heartbeat(worker_id=worker_id, status="stopped")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
