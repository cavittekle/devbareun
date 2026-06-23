from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
TOOLS_ROOT = ROOT / "tools"
for item in (BACKEND_ROOT, TOOLS_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))


class CompanyTeamFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = importlib.import_module("app.services.company_team_service")
        cls.CurrentUser = importlib.import_module("app.auth_dependencies").CurrentUser

    def user(self, *, email: str = "owner@example.test", company_id: str | None = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"):
        return self.CurrentUser(
            id="11111111-1111-1111-1111-111111111111",
            auth_user_id="11111111-1111-1111-1111-111111111111",
            email=email,
            company_id=company_id,
            role="customer",
        )

    def test_invitation_hash_never_equals_raw_token(self) -> None:
        token = "manual-token-that-is-long-enough-to-be-safe"
        digest = self.service.invitation_hash(token)
        self.assertEqual(len(digest), 64)
        self.assertNotEqual(digest, token)
        self.assertEqual(digest, self.service.invitation_hash(token))

    def test_create_invitation_returns_raw_url_but_persists_only_hash(self) -> None:
        owner = self.user()
        company = {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "name": "Example"}
        membership = {"id": "m-owner", "company_role": "owner", "status": "active"}
        captured = {}

        def insert(_table, payload):
            captured.update(payload)
            return {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", **payload}

        with patch.object(self.service, "require_active_membership", return_value=(company, membership)), \
             patch.object(self.service, "_find_membership", return_value=None), \
             patch.object(self.service, "select_rows", return_value=[]), \
             patch.object(self.service, "insert_row", side_effect=insert):
            response = self.service.create_invitation(owner, "invitee@example.test", "viewer", 24)

        self.assertIn("invite=", response["invite_url"])
        self.assertIn("token_hash", captured)
        self.assertNotIn("token", captured)
        self.assertNotIn(response["invite_url"].split("invite=", 1)[1], str(captured))
        self.assertEqual(captured["company_role"], "viewer")

    def test_accept_rejects_invited_email_mismatch(self) -> None:
        invitation = {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "company_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "invitee_email": "invited@example.test",
            "company_role": "viewer",
            "status": "pending",
            "expires_at": "2030-01-01T00:00:00Z",
        }
        with patch.object(self.service, "select_one", return_value=invitation):
            with self.assertRaises(PermissionError):
                self.service.accept_invitation(self.user(email="other@example.test", company_id=None), "x" * 32)

    def test_owner_or_manager_can_manage_but_editor_cannot(self) -> None:
        self.assertTrue(self.service.can_manage_team({"company_role": "owner", "status": "active"}))
        self.assertTrue(self.service.can_manage_team({"company_role": "manager", "status": "active"}))
        self.assertFalse(self.service.can_manage_team({"company_role": "editor", "status": "active"}))
        self.assertFalse(self.service.can_manage_team({"company_role": "manager", "status": "suspended"}))

    def test_company_membership_does_not_change_existing_project_ownership_policy(self) -> None:
        auth = importlib.import_module("app.auth_dependencies")
        project = {
            "owner_email": "owner@example.test",
            "user_id": "owner-id",
            "company_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        }
        teammate = self.CurrentUser(
            id="22222222-2222-2222-2222-222222222222",
            auth_user_id="22222222-2222-2222-2222-222222222222",
            email="teammate@example.test",
            company_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            role="customer",
        )
        self.assertFalse(auth._project_belongs_to_user(project, teammate, section="projects"))

    def test_company_team_contract_checker_passes(self) -> None:
        checker = importlib.import_module("check_company_team_foundation")
        result = checker.check(ROOT)
        self.assertEqual(result.errors, [])

    def test_company_team_routes_are_in_openapi(self) -> None:
        app = importlib.import_module("app.main").app
        route_keys = {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())}
        for path, method in (
            ("/api/company/workspace", "GET"),
            ("/api/company/workspace", "POST"),
            ("/api/company/invitations", "POST"),
            ("/api/company/invitations/accept", "POST"),
            ("/api/company/invitations/{invitation_id}/revoke", "POST"),
            ("/api/company/members/{membership_id}", "PATCH"),
        ):
            self.assertIn((path, method), route_keys)


if __name__ == "__main__":
    unittest.main()
