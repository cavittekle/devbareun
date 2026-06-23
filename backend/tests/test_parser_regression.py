from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import Workbook

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.analyzer import build_dashboard
from app.models import ParsedProjectData, SheetProfile
from app.parser import ConstructionFileParser


class ParserRegressionTests(unittest.TestCase):
    def _make_smeta_workbook(self, path: Path, *, include_f2: bool = False, f2_amount: float = 400_000) -> None:
        wb = Workbook()
        ws = wb.active
        ws.title = "Nokopitelni" if include_f2 else "Smeta"
        ws.append(["Project", "Demo Construction Project"])
        ws.append(["Item", "Quantity", "Unit price", "Amount"])
        ws.append(["Concrete", 10, 10_000, 100_000])
        ws.append(["Steel", 20, 15_000, 300_000])
        ws.append(["Smeta uzre yekun", "", "", 1_000_000])

        if include_f2:
            f2 = wb.create_sheet("F-2 January")
            f2.append(["Item", "Quantity", "Unit price", "Amount"])
            f2.append(["Concrete completed", 5, 10_000, 50_000])
            f2.append(["Steel completed", 20, 15_000, 300_000])
            f2.append(["Yekun cemi", "", "", f2_amount])

        wb.save(path)

    def test_smeta_only_does_not_create_actual_cost_or_progress(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "smeta_only.xlsx"
            self._make_smeta_workbook(path)

            parsed = ConstructionFileParser("cost").parse_files([path])
            dashboard = build_dashboard("project-1", parsed, "cost")["dashboard"]

        self.assertEqual(parsed.total_cost, 1_000_000)
        self.assertEqual(parsed.planned_cost, 1_000_000)
        self.assertIsNone(parsed.actual_cost)
        self.assertIsNone(parsed.actual_execution)
        self.assertIsNone(parsed.cost_variance_percent)
        self.assertTrue(parsed.evidence.get("cost_actual_data_missing"))
        self.assertIsNone(dashboard["kpis"]["actual_cost"])
        self.assertIsNone(dashboard["kpis"]["actual_execution"])
        self.assertIsNone(dashboard["kpis"]["cost_variance_percent"])
        self.assertTrue(any(row["risk"] == "Actual cost data missing" for row in dashboard["risk_register"]))

    def test_smeta_plus_f2_confirms_actual_progress_payment(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "smeta_f2.xlsx"
            self._make_smeta_workbook(path, include_f2=True, f2_amount=400_000)

            parsed = ConstructionFileParser("all").parse_files([path])
            dashboard = build_dashboard("project-2", parsed, "all")["dashboard"]

        self.assertEqual(parsed.total_cost, 1_000_000)
        self.assertEqual(parsed.actual_cost, 400_000)
        self.assertEqual(parsed.actual_execution, 40.0)
        self.assertEqual(parsed.evidence.get("f2_completed_amount"), 400_000)
        self.assertFalse(parsed.evidence.get("cost_actual_data_missing"))
        self.assertEqual(dashboard["kpis"]["actual_cost"], 400_000)
        self.assertEqual(dashboard["kpis"]["actual_execution"], 40.0)

    def test_schedule_baseline_without_actual_progress_clears_delay(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline_schedule.csv"
            path.write_text(
                "Project,Demo Schedule Project\n"
                "Activity,Planned Start,Planned Finish,Plan %,Delay days\n"
                "Foundation,2026-01-01,2026-02-01,70%,20\n",
                encoding="utf-8",
            )

            parsed = ConstructionFileParser("schedule").parse_files([path])
            dashboard = build_dashboard("project-3", parsed, "schedule")["dashboard"]

        self.assertEqual(parsed.planned_execution, 70.0)
        self.assertIsNone(parsed.actual_execution)
        self.assertIsNone(parsed.delay_days)
        self.assertTrue(parsed.evidence.get("schedule_actual_data_missing"))
        self.assertIsNone(dashboard["kpis"]["schedule_gap_percent"])
        self.assertIsNone(dashboard["kpis"]["delay_days"])
        self.assertTrue(any(row["risk"] == "Actual schedule data missing" for row in dashboard["risk_register"]))

    def test_workforce_analysis_clears_cost_and_schedule_pollution(self) -> None:
        parsed = ParsedProjectData(
            project_name="Workforce Control Project",
            total_cost=1_000_000,
            planned_cost=1_000_000,
            actual_cost=250_000,
            planned_execution=80,
            actual_execution=50,
            delay_days=15,
            workforce_current=12,
            workforce_required=20,
            sheets=[
                SheetProfile(
                    file_name="workforce.csv",
                    sheet_name="workforce",
                    detected_type="workforce",
                    confidence=90,
                    mapped_columns={"workforce_current": "B", "workforce_required": "C"},
                    row_count=4,
                )
            ],
        )

        dashboard = build_dashboard("project-4", parsed, "workforce")["dashboard"]

        self.assertIsNone(parsed.total_cost)
        self.assertIsNone(parsed.actual_cost)
        self.assertIsNone(parsed.planned_execution)
        self.assertIsNone(parsed.actual_execution)
        self.assertIsNone(parsed.delay_days)
        self.assertEqual(parsed.workforce_current, 12)
        self.assertEqual(parsed.workforce_required, 20)
        self.assertIsNone(dashboard["kpis"]["total_cost"])
        self.assertEqual(dashboard["kpis"]["workforce_current"], 12)
        self.assertEqual(dashboard["kpis"]["workforce_required"], 20)


if __name__ == "__main__":
    unittest.main()
