from __future__ import annotations

import unittest
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.analyzer import apply_baseline_actual_guardrails
from app.models import ParsedProjectData, SheetProfile


class BaselineActualGuardrailTests(unittest.TestCase):
    def test_cost_guardrail_clears_unconfirmed_actuals(self) -> None:
        parsed = ParsedProjectData(
            total_cost=100000.0,
            actual_cost=90000.0,
            actual_execution=45.0,
            cost_variance_percent=10.0,
            sheets=[SheetProfile(file_name="smeta.xlsx", sheet_name="Sheet1", detected_type="cost", confidence=80)],
            evidence={},
            warnings=[],
        )
        apply_baseline_actual_guardrails(parsed, "cost")

        self.assertIsNone(parsed.actual_cost)
        self.assertIsNone(parsed.actual_execution)
        self.assertIsNone(parsed.cost_variance_percent)
        self.assertTrue(parsed.evidence.get("cost_actual_data_missing"))
        self.assertTrue(any("Actual cost / progress payment data was not found" in w for w in parsed.warnings))

    def test_cost_guardrail_keeps_confirmed_actuals(self) -> None:
        parsed = ParsedProjectData(
            total_cost=100000.0,
            actual_cost=90000.0,
            actual_execution=45.0,
            cost_variance_percent=10.0,
            sheets=[
                SheetProfile(file_name="smeta.xlsx", sheet_name="Sheet1", detected_type="cost", confidence=80),
                SheetProfile(file_name="f2.xlsx", sheet_name="F2", detected_type="progress", confidence=90),
            ],
            evidence={"f2_completed_amount": 45000.0},
            warnings=[],
        )
        apply_baseline_actual_guardrails(parsed, "cost")

        self.assertEqual(parsed.actual_cost, 90000.0)
        self.assertEqual(parsed.actual_execution, 45.0)
        self.assertEqual(parsed.cost_variance_percent, 10.0)
        self.assertIsNone(parsed.evidence.get("cost_actual_data_missing"))

    def test_schedule_guardrail_clears_delay_without_actual_source(self) -> None:
        parsed = ParsedProjectData(
            planned_execution=60.0,
            baseline_finish="2026-12-31",
            delay_days=14,
            sheets=[SheetProfile(file_name="schedule.xer", sheet_name="TASKS", detected_type="schedule", confidence=85)],
            evidence={},
            warnings=[],
        )
        apply_baseline_actual_guardrails(parsed, "schedule")

        self.assertIsNone(parsed.delay_days)
        self.assertTrue(parsed.evidence.get("schedule_actual_data_missing"))
        self.assertTrue(any("Actual progress data was not found" in w for w in parsed.warnings))

    def test_workforce_guardrail_isolates_workforce_kpis(self) -> None:
        parsed = ParsedProjectData(
            total_cost=100000.0,
            actual_cost=90000.0,
            planned_execution=60.0,
            actual_execution=45.0,
            delay_days=14,
            workforce_current=20,
            workforce_required=25,
            sheets=[SheetProfile(file_name="workforce.xlsx", sheet_name="Sheet1", detected_type="workforce", confidence=80)],
            evidence={"workforce_productivity": {"summary": {"total_actual_workers": 22, "total_required_workers": 28}}},
            warnings=[],
        )
        apply_baseline_actual_guardrails(parsed, "workforce")

        self.assertEqual(parsed.workforce_current, 22)
        self.assertEqual(parsed.workforce_required, 28)
        self.assertIsNone(parsed.total_cost)
        self.assertIsNone(parsed.actual_cost)
        self.assertIsNone(parsed.planned_execution)
        self.assertIsNone(parsed.actual_execution)
        self.assertIsNone(parsed.delay_days)


if __name__ == "__main__":
    unittest.main()
