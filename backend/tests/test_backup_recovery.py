from __future__ import annotations

import hashlib
import importlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


class BackupRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = importlib.import_module("backup_recovery")

    def test_database_url_is_sanitized_and_mapped_without_secret_output(self) -> None:
        url = "postgresql://backup_user:super-secret@db.example.com:6543/project_control?sslmode=require"
        safe = self.module.sanitize_database_url(url)
        env = self.module.database_env_from_url(url)
        self.assertEqual(safe, "postgresql://db.example.com:6543/project_control")
        self.assertNotIn("super-secret", safe)
        self.assertEqual(env["PGHOST"], "db.example.com")
        self.assertEqual(env["PGPORT"], "6543")
        self.assertEqual(env["PGUSER"], "backup_user")
        self.assertEqual(env["PGDATABASE"], "project_control")
        self.assertEqual(env["PGPASSWORD"], "super-secret")

    def test_policy_validation_requires_valid_ranges(self) -> None:
        good = {
            "DEVBAREUN_BACKUP_REQUIRED": "true",
            "DEVBAREUN_BACKUP_RPO_HOURS": "24",
            "DEVBAREUN_BACKUP_RTO_HOURS": "8",
            "DEVBAREUN_BACKUP_DRILL_MAX_AGE_DAYS": "90",
            "DEVBAREUN_BACKUP_STORAGE_MANIFEST_REQUIRED": "true",
        }
        policy = self.module.policy_from_env(good)
        self.assertEqual(policy.rpo_hours, 24)
        bad = dict(good, DEVBAREUN_BACKUP_RPO_HOURS="0")
        with self.assertRaises(ValueError):
            self.module.policy_from_env(bad)

    def test_checksum_verification_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dump = Path(temp) / "backup.dump"
            dump.write_bytes(b"safe-backup")
            digest = hashlib.sha256(b"safe-backup").hexdigest()
            dump.with_suffix(".dump.sha256").write_text(f"{digest}  {dump.name}\n", encoding="utf-8")
            ok, message = self.module.verify_checksum(dump)
            self.assertTrue(ok)
            self.assertEqual(message, "checksum verified")
            dump.write_bytes(b"changed")
            ok, message = self.module.verify_checksum(dump)
            self.assertFalse(ok)
            self.assertEqual(message, "checksum mismatch")

    def test_restore_preflight_confirmation_is_mandatory(self) -> None:
        with self.assertRaises(ValueError):
            self.module.require_confirmation(None, "RUN_RESTORE_PREFLIGHT", "restore preflight")


    def test_frontend_validator_rejects_backup_credentials(self) -> None:
        validator = importlib.import_module("validate_production_env")
        errors, _warnings = validator.validate_frontend({
            "VITE_PUBLIC_SITE_URL": "https://devbareun.example",
            "VITE_API_BASE_URL": "https://api.devbareun.example",
            "VITE_SUPABASE_URL": "https://project.supabase.co",
            "VITE_SUPABASE_ANON_KEY": "public-anon-key",
            "DEVBAREUN_BACKUP_DATABASE_URL": "postgresql://should-not-be-here",
        }, allow_placeholders=False)
        self.assertTrue(any("DEVBAREUN_BACKUP_DATABASE_URL" in error for error in errors))

    def test_backup_recovery_static_contract_and_assets(self) -> None:
        checker = importlib.import_module("check_backup_recovery")
        result = checker.check(ROOT)
        self.assertEqual(result.errors, [])
        self.assertIn("v1.4.29", (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "deploy" / "env" / "backup-operator.env.template").exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
