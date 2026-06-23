#!/usr/bin/env python3
"""Static Supabase database contract checker for DevBareun.

This is intentionally dependency-free. It does not connect to Supabase; it
parses the migration files listed in `database/SUPABASE_DEPLOY_ORDER.md` and
verifies that the deployable schema still contains the tables/columns, RLS
coverage and storage-bucket policy surface expected by the backend.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

DEPLOY_ORDER_RE = re.compile(r"`([^`]+\.sql)`")
CREATE_TABLE_RE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?([a-zA-Z_][\w]*)\s*\(", re.I)
ALTER_ADD_COLUMN_RE = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?(?:public\.)?([a-zA-Z_][\w]*)\s+add\s+column\s+(?:if\s+not\s+exists\s+)?([a-zA-Z_][\w]*)",
    re.I,
)
ALTER_TABLE_BLOCK_RE = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?(?:public\.)?([a-zA-Z_][\w]*)\s+(.*?);",
    re.I | re.S,
)
ALTER_BLOCK_ADD_COLUMN_RE = re.compile(r"add\s+column\s+(?:if\s+not\s+exists\s+)?([a-zA-Z_][\w]*)", re.I)
RLS_RE = re.compile(r"alter\s+table\s+(?:if\s+exists\s+)?(?:public\.)?([a-zA-Z_][\w]*)\s+enable\s+row\s+level\s+security", re.I)
POLICY_RE = re.compile(r"create\s+policy\s+(?:if\s+not\s+exists\s+)?[\"a-zA-Z0-9_\- ]+\s+on\s+(?:public\.)?([a-zA-Z_][\w]*)", re.I)
STORAGE_POLICY_RE = re.compile(r"create\s+policy\s+(?:if\s+not\s+exists\s+)?[\"a-zA-Z0-9_\- ]+\s+on\s+storage\.objects", re.I)
BUCKET_INSERT_RE = re.compile(r"insert\s+into\s+storage\.buckets.*?values\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(true|false)", re.I | re.S)

EXPECTED_TABLE_COLUMNS: Dict[str, Set[str]] = {
    "users_profile": {
        "id", "auth_user_id", "email", "full_name", "role", "status", "company_id", "plan",
        "user_id", "auth_provider", "created_at", "updated_at",
    },
    "companies": {
        "id", "owner_user_id", "name", "plan", "company_id", "company_name", "contact_person",
        "email", "phone", "country", "subscription_plan", "owner_email", "created_at", "updated_at",
    },
    "projects": {
        "id", "project_id", "user_id", "owner_email", "owner_user_id", "project_name", "name",
        "contractor_name", "contractor", "client_name", "client", "planned_finish_date", "end_date",
        "current_status", "project_status", "analysis_type", "company_id", "deleted_at", "purge_after_at", "retention_status", "created_at", "updated_at",
    },
    "uploaded_files": {
        "id", "file_id", "user_id", "project_id", "bucket", "storage_bucket", "storage_path",
        "original_filename", "original_name", "file_ext", "extension", "mime_type", "content_type",
        "size_bytes", "file_size_bytes", "upload_status", "parser_status", "status", "checksum",
        "owner_email", "uploaded_by_user_id", "deleted_at", "purge_after_at", "retention_status", "storage_delete_status", "created_at", "updated_at",
        "security_scan_status", "security_scan_engine", "security_scan_started_at", "security_scan_completed_at",
        "security_scan_error", "security_scan_findings", "quarantine_status", "quarantine_reason", "quarantined_at",
    },
    "analysis_jobs": {
        "id", "job_id", "user_id", "project_id", "owner_email", "analysis_type", "status", "progress",
        "error_message", "started_at", "completed_at", "created_at", "updated_at", "worker_id",
        "locked_at", "last_heartbeat_at", "attempts", "max_attempts", "user_payload", "requeue_count",
        "retry_requested_at", "retry_requested_by", "terminal_reason", "idempotency_key",
        "request_fingerprint", "billing_status", "billing_consumed_at", "input_manifest",
        "input_manifest_sha256", "input_file_count", "provenance_schema_version",
    },
    "analysis_results": {
        "id", "analysis_id", "user_id", "project_id", "job_id", "owner_email", "normalized_data",
        "dashboard_data", "risk_data", "confidence_score", "uploaded_file_ids", "result_json", "dashboard",
        "kpis", "report_payload", "risk_level", "analysis_type", "status", "completed_at", "created_at",
        "input_manifest", "input_manifest_sha256", "input_file_count", "provenance_schema_version", "deleted_at", "purge_after_at", "retention_status",
    },
    "risks": {
        "id", "user_id", "project_id", "analysis_result_id", "risk_title", "category", "severity",
        "probability", "impact", "explanation", "recommended_action", "status", "created_at", "updated_at",
    },
    "reports": {
        "id", "report_id", "user_id", "project_id", "analysis_result_id", "analysis_id", "project_name",
        "analysis_type", "report_name", "report_type", "format", "media_type", "storage_path", "storage_bucket",
        "report_payload", "payload_sha256", "content_sha256", "snapshot_version", "generated_at", "last_downloaded_at", "owner_email", "download_count", "unlocked_at", "status", "deleted_at", "purge_after_at", "retention_status", "created_at", "updated_at",
    },
    "subscriptions": {
        "id", "subscription_id", "user_id", "owner_email", "plan_code", "plan_name", "status", "monthly_credits",
        "monthly_project_limit", "used_project_count", "created_at", "updated_at",
    },
    "analysis_credits": {
        "id", "credit_id", "user_id", "owner_email", "plan_code", "project_id", "amount", "remaining",
        "total_credits", "used_credits", "remaining_credits", "status", "period_start", "period_end", "checkout_id", "provider_order_id", "source_event_id", "created_at", "updated_at",
    },
    "payments": {
        "id", "payment_id", "user_id", "owner_email", "checkout_id", "provider_session_id", "plan_code",
        "payment_provider", "status", "amount", "currency", "paid_at", "unlock_status", "provider_order_id", "last_provider_event_id", "failure_reason_code", "refunded_at", "created_at", "updated_at",
    },
    "payment_events": {"id", "provider", "event_id", "provider_event_id", "event_type", "payload", "payload_sha256", "checkout_id", "processing_status", "attempts", "max_attempts", "received_at", "last_attempt_at", "completed_at", "last_error_code", "outcome", "updated_at"},
    "activity_logs": {"id", "user_id", "owner_email", "action", "entity_type", "entity_id", "metadata", "created_at"},
    "support_tickets": {"id", "ticket_id", "owner_email", "subject", "message", "status", "priority", "created_at", "updated_at"},
    "admin_notes": {"id", "note_id", "target_type", "target_id", "owner_email", "note", "created_by", "created_at"},
    "audit_logs": {"id", "audit_id", "actor_email", "action", "target_type", "target_id", "metadata", "created_at", "request_id", "event_hash", "previous_event_hash", "metadata_sha256", "integrity_version"},
    "credit_transactions": {"id", "transaction_id", "owner_email", "amount", "reason", "created_by", "created_at"},
    "checkout_sessions": {"id", "checkout_id", "plan_code", "project_id", "guest_order_id", "user_id", "owner_email", "customer_email", "provider_checkout_session_id", "checkout_url", "status", "provider_order_id", "last_event_id", "paid_at", "failure_code", "expires_at", "created_at", "updated_at"},
    "guest_orders": {"id", "guest_order_id", "email", "project_id", "checkout_id", "status", "created_at", "updated_at"},
    "subscription_usage": {"id", "subscription_id", "owner_email", "period_start", "period_end", "used_credits", "created_at", "updated_at"},
    "analysis_worker_heartbeats": {"worker_id", "status", "started_at", "last_seen_at", "last_result_at", "processed_jobs", "claimed_jobs", "metadata", "updated_at"},
    "analysis_usage_ledger": {"id", "job_id", "user_id", "owner_email", "project_id", "usage_mode", "subscription_id", "credit_id", "created_at"},
    "audit_archive_outbox": {"id", "archive_id", "audit_id", "integrity_version", "previous_event_hash", "event_hash", "payload", "payload_sha256", "status", "attempts", "max_attempts", "next_attempt_at", "lease_token", "delivered_at", "last_error", "created_at", "updated_at"},
    "audit_archive_worker_heartbeats": {"worker_id", "status", "started_at", "last_seen_at", "last_result_at", "processed_events", "claimed_events", "metadata", "updated_at"},
    "data_lifecycle_requests": {"id", "lifecycle_request_id", "requester_user_id", "requester_email", "request_type", "scope", "project_id", "reason", "status", "requested_at", "request_expires_at", "grace_expires_at", "scheduled_purge_at", "reviewed_at", "reviewed_by", "review_note", "completed_at", "cancelled_at", "cancel_reason", "request_id", "metadata", "created_at", "updated_at"},
    "company_memberships": {"id", "company_id", "user_id", "member_email", "company_role", "status", "invited_by_user_id", "joined_at", "created_at", "updated_at"},
    "company_invitations": {"id", "company_id", "invitee_email", "company_role", "token_hash", "status", "invited_by_user_id", "accepted_by_user_id", "expires_at", "accepted_at", "created_at", "updated_at"},
    "project_access_grants": {"id", "project_id", "company_id", "membership_id", "user_id", "member_email", "project_role", "status", "granted_by_user_id", "granted_at", "created_at", "updated_at"},
}

REQUIRED_DEPLOY_ORDER = [
    "2026_05_29_v140_production_saas_core.sql",
    "2026_05_29_v140_part2_jobs_billing_reports.sql",
    "2026_06_08_v141_super_admin_workspace.sql",
    "2026_06_18_v142_canonical_api_bridge.sql",
    "2026_06_18_v145_analysis_worker.sql",
    "2026_06_19_v1416_analysis_worker_observability.sql",
    "2026_06_19_v1417_analysis_job_recovery.sql",
    "2026_06_19_v1418_analysis_idempotency.sql",
    "2026_06_19_v1419_report_snapshot_integrity.sql", "2026_06_19_v1420_upload_checksum_integrity.sql",
    "2026_06_19_v1421_upload_security_screening.sql",
    "2026_06_19_v1422_analysis_input_provenance.sql",
    "2026_06_20_v1423_panel_access_boundaries.sql",
    "2026_06_20_v1424_audit_integrity.sql",
    "2026_06_20_v1425_audit_archive_outbox.sql",
    "2026_06_21_v1430_data_lifecycle_requests.sql",
    "2026_06_21_v1431_billing_lifecycle_integrity.sql",
    "2026_06_21_v1432_company_team_foundation.sql",
    "2026_06_21_v1433_project_sharing.sql",
]

RLS_REQUIRED_TABLES = set(EXPECTED_TABLE_COLUMNS)
POLICY_REQUIRED_TABLES = set(EXPECTED_TABLE_COLUMNS) - {"payment_events"}
REQUIRED_BUCKETS = {"project-files"}
MANUAL_BUCKETS_IN_DEPLOY_NOTES = {"project-files", "reports"}

SQL_COLUMN_SKIP = {
    "primary", "foreign", "unique", "constraint", "check", "exclude", "like", "partition", "created", "updated"
}


@dataclass
class DatabaseContract:
    tables: Dict[str, Set[str]] = field(default_factory=dict)
    rls_enabled: Set[str] = field(default_factory=set)
    policy_tables: Set[str] = field(default_factory=set)
    storage_policy_count: int = 0
    storage_buckets: Dict[str, bool] = field(default_factory=dict)
    deploy_order: List[str] = field(default_factory=list)


@dataclass
class ContractResult:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    contract: DatabaseContract = field(default_factory=DatabaseContract)

    @property
    def ok(self) -> bool:
        return not self.errors


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def deploy_order_files(root: Path) -> List[Path]:
    order = root / "database" / "SUPABASE_DEPLOY_ORDER.md"
    if not order.exists():
        return []
    listed = DEPLOY_ORDER_RE.findall(read_text(order))
    return [root / "database" / item for item in listed if item.endswith(".sql")]


def _find_matching_paren(text: str, start_index: int) -> int:
    depth = 0
    for index in range(start_index, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _split_columns(body: str) -> Iterable[str]:
    depth = 0
    in_single = False
    chunk: List[str] = []
    previous = ""
    for char in body:
        if char == "'" and previous != "\\":
            in_single = not in_single
        if not in_single:
            if char == "(":
                depth += 1
            elif char == ")" and depth > 0:
                depth -= 1
            elif char == "," and depth == 0:
                yield "".join(chunk).strip()
                chunk = []
                previous = char
                continue
        chunk.append(char)
        previous = char
    if chunk:
        yield "".join(chunk).strip()


def _column_name_from_definition(definition: str) -> str | None:
    definition = definition.strip()
    if not definition or definition.startswith("--"):
        return None
    first = definition.split(None, 1)[0].strip('"').lower()
    if first in SQL_COLUMN_SKIP:
        return None
    return first


def parse_sql_files(paths: Iterable[Path]) -> DatabaseContract:
    contract = DatabaseContract()
    for path in paths:
        if not path.exists():
            continue
        text = read_text(path)
        contract.deploy_order.append(path.name)
        for match in CREATE_TABLE_RE.finditer(text):
            table = match.group(1).lower()
            contract.tables.setdefault(table, set())
            open_paren = text.find("(", match.end() - 1)
            close_paren = _find_matching_paren(text, open_paren)
            if open_paren == -1 or close_paren == -1:
                continue
            body = text[open_paren + 1:close_paren]
            for definition in _split_columns(body):
                column = _column_name_from_definition(definition)
                if column:
                    contract.tables[table].add(column)
        for table, column in ALTER_ADD_COLUMN_RE.findall(text):
            contract.tables.setdefault(table.lower(), set()).add(column.lower())
        # PostgreSQL allows a single ALTER TABLE statement to add several
        # columns. Parse the full statement so schema contracts do not miss
        # every column after the first comma-separated ADD COLUMN clause.
        for match in ALTER_TABLE_BLOCK_RE.finditer(text):
            table = match.group(1).lower()
            for column in ALTER_BLOCK_ADD_COLUMN_RE.findall(match.group(2)):
                contract.tables.setdefault(table, set()).add(column.lower())
        for table in RLS_RE.findall(text):
            contract.rls_enabled.add(table.lower())
        for table in POLICY_RE.findall(text):
            contract.policy_tables.add(table.lower())
        contract.storage_policy_count += len(STORAGE_POLICY_RE.findall(text))
        for bucket_id, _name, public_flag in BUCKET_INSERT_RE.findall(text):
            contract.storage_buckets[bucket_id] = (public_flag.lower() == "true")
    return contract


def check_contract(root: Path) -> ContractResult:
    root = root.resolve()
    result = ContractResult()
    database = root / "database"
    order_path = database / "SUPABASE_DEPLOY_ORDER.md"
    if not order_path.exists():
        result.errors.append("database/SUPABASE_DEPLOY_ORDER.md is missing")
        return result
    order_text = read_text(order_path)
    deploy_files = deploy_order_files(root)
    listed_names = [path.name for path in deploy_files]
    for required in REQUIRED_DEPLOY_ORDER:
        if required not in listed_names:
            result.errors.append(f"deploy order missing required production migration: {required}")
    for path in deploy_files:
        if not path.exists() and path.name not in {"seed_plans.sql", "promote_owner_info_devbareun.sql", "production_rls_audit.sql"}:
            result.errors.append(f"deploy-order SQL file does not exist: {path.name}")
    result.contract = parse_sql_files(path for path in deploy_files if path.exists())

    for table, expected_columns in sorted(EXPECTED_TABLE_COLUMNS.items()):
        actual = result.contract.tables.get(table)
        if actual is None:
            result.errors.append(f"required table is not created or altered by deploy-order SQL: {table}")
            continue
        missing = sorted(expected_columns - actual)
        if missing:
            result.errors.append(f"table {table} missing required column(s): {', '.join(missing)}")

    for table in sorted(RLS_REQUIRED_TABLES):
        if table not in result.contract.rls_enabled:
            result.errors.append(f"table {table} is missing `enable row level security` in deploy-order SQL")
    for table in sorted(POLICY_REQUIRED_TABLES):
        if table not in result.contract.policy_tables:
            result.errors.append(f"table {table} has no create policy statement in deploy-order SQL")
    if result.contract.storage_policy_count < 3:
        result.errors.append("storage.objects must have insert/read/delete policies for project-files")
    for bucket in REQUIRED_BUCKETS:
        if bucket not in result.contract.storage_buckets:
            result.errors.append(f"required private storage bucket insert is missing: {bucket}")
        elif result.contract.storage_buckets[bucket]:
            result.errors.append(f"storage bucket must be private: {bucket}")
    for bucket in MANUAL_BUCKETS_IN_DEPLOY_NOTES:
        if bucket not in order_text:
            result.warnings.append(f"deploy notes do not mention storage bucket: {bucket}")
    if "production_rls_audit.sql" not in listed_names:
        result.warnings.append("deploy order should end with production_rls_audit.sql as a read-only verification step")
    return result


def to_json(result: ContractResult) -> Dict[str, object]:
    return {
        "ok": result.ok,
        "errors": result.errors,
        "warnings": result.warnings,
        "deploy_order": result.contract.deploy_order,
        "tables": {table: sorted(cols) for table, cols in sorted(result.contract.tables.items())},
        "rls_enabled": sorted(result.contract.rls_enabled),
        "policy_tables": sorted(result.contract.policy_tables),
        "storage_policy_count": result.contract.storage_policy_count,
        "storage_buckets": result.contract.storage_buckets,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DevBareun Supabase migration/table/RLS contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)

    result = check_contract(args.root)
    if args.json:
        print(json.dumps(to_json(result), indent=2, sort_keys=True))
    else:
        for warning in result.warnings:
            print(f"[WARN] {warning}")
        for error in result.errors:
            print(f"[FAIL] {error}")
        print(f"Database contract {'passed' if result.ok else 'failed'}: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
