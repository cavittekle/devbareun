from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.delay import analyze, read_path, read_paths  # noqa: E402
from app.delay.model import Activity, DelayEvent, DelayInput, ProjectInfo  # noqa: E402
from app.delay.report import build_delay_excel, build_delay_pdf  # noqa: E402
from app.delay.sample import build_template_bytes, sample_input  # noqa: E402

D = date


def _input(activities, events=(), data_date=D(2024, 1, 31), **project):
    return DelayInput(project=ProjectInfo(data_date=data_date, **project), activities=list(activities), events=list(events))


class ProgressAndSpiTests(unittest.TestCase):
    def test_planned_and_actual_progress_are_weighted(self) -> None:
        # A: 10 days, fully planned by the data date, 100% done.
        # B: 20 days, half planned by the data date, 25% done.
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 1), D(2024, 1, 10), weight=1, actual_start=D(2024, 1, 1), actual_finish=D(2024, 1, 10), progress=100),
            Activity("B", "B", D(2024, 1, 11), D(2024, 1, 30), weight=1, actual_start=D(2024, 1, 11), progress=25),
        ], data_date=D(2024, 1, 20)))
        k = result["kpis"]
        self.assertTrue(result["ok"])
        self.assertEqual(k["planned_progress_pct"], 75.0)
        self.assertEqual(k["actual_progress_pct"], 62.5)
        self.assertEqual(k["spi"], 0.83)

    def test_duration_is_default_weight(self) -> None:
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 1), D(2024, 1, 10), progress=100, actual_finish=D(2024, 1, 10)),
            Activity("B", "B", D(2024, 1, 11), D(2024, 2, 9), progress=0),
        ], data_date=D(2024, 1, 10)))
        # A = 10 days of 40 total -> 25% planned and earned.
        self.assertEqual(result["kpis"]["planned_progress_pct"], 25.0)
        self.assertEqual(result["kpis"]["actual_progress_pct"], 25.0)
        self.assertEqual(result["method"]["weights"], "planned_duration")

    def test_earned_schedule_delay_in_days(self) -> None:
        # One 100-day activity, 40% done at day 60 -> plan reached 40% on day 40.
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 1), D(2024, 4, 9), actual_start=D(2024, 1, 1), progress=40),
        ], data_date=D(2024, 2, 29)))
        self.assertEqual(result["kpis"]["earned_schedule_date"], "2024-02-09")
        self.assertEqual(result["kpis"]["schedule_delay_days"], 20)


class ForecastTests(unittest.TestCase):
    def test_production_rate_forecast(self) -> None:
        # 50% in 10 days -> 10 more days.
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 1), D(2024, 1, 15), actual_start=D(2024, 1, 1), progress=50),
        ], data_date=D(2024, 1, 10)))
        row = result["activities"][0]
        self.assertEqual(row["forecast_basis"], "production_rate")
        self.assertEqual(row["forecast_finish"], "2024-01-20")
        self.assertEqual(row["finish_variance_days"], 5)

    def test_low_progress_uses_planned_rate(self) -> None:
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 1), D(2024, 1, 20), actual_start=D(2024, 1, 1), progress=10),
        ], data_date=D(2024, 1, 10)))
        row = result["activities"][0]
        self.assertEqual(row["forecast_basis"], "planned_rate")
        self.assertEqual(row["forecast_finish"], "2024-01-28")  # 90% of 20 days = 18 days

    def test_reported_forecast_is_respected(self) -> None:
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 1), D(2024, 1, 20), actual_start=D(2024, 1, 1), progress=60, forecast_finish=D(2024, 1, 25)),
        ], data_date=D(2024, 1, 10)))
        self.assertEqual(result["activities"][0]["forecast_finish"], "2024-01-25")

    def test_late_start_shifts_to_data_date(self) -> None:
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 1), D(2024, 1, 10), progress=0),
        ], data_date=D(2024, 1, 5)))
        row = result["activities"][0]
        self.assertEqual(row["forecast_start"], "2024-01-06")
        self.assertEqual(row["forecast_finish"], "2024-01-15")
        self.assertEqual(row["start_variance_days"], 5)


class CriticalPathTests(unittest.TestCase):
    def _network(self):
        return [
            Activity("A", "A", D(2024, 1, 1), D(2024, 1, 10), actual_start=D(2024, 1, 1), actual_finish=D(2024, 1, 15), progress=100),
            Activity("B", "B", D(2024, 1, 11), D(2024, 1, 20), predecessors=["A"], progress=0),
            Activity("C", "C", D(2024, 1, 11), D(2024, 1, 15), predecessors=["A"], progress=0),
            Activity("D", "D", D(2024, 1, 21), D(2024, 1, 30), predecessors=["B", "C"], progress=0),
        ]

    def test_late_predecessor_pushes_successors(self) -> None:
        result = analyze(_input(self._network(), data_date=D(2024, 1, 15)))
        rows = {r["id"]: r for r in result["activities"]}
        self.assertEqual(result["critical_path"]["method"], "cpm")
        self.assertEqual(rows["B"]["forecast_finish"], "2024-01-25")
        self.assertEqual(rows["D"]["forecast_finish"], "2024-02-04")
        self.assertEqual(result["kpis"]["forecast_delay_days"], 5)
        self.assertTrue(rows["B"]["critical"])
        self.assertTrue(rows["D"]["critical"])
        self.assertFalse(rows["C"]["critical"])
        self.assertEqual(rows["C"]["total_float_days"], 5)
        self.assertEqual(rows["D"]["status"], "critical_delay")

    def test_logic_loop_falls_back(self) -> None:
        acts = self._network()
        acts[1].predecessors = ["A", "D"]
        result = analyze(_input(acts, data_date=D(2024, 1, 15)))
        self.assertEqual(result["critical_path"]["method"], "approximate")
        self.assertIn("logic_loop", {q["code"] for q in result["data_quality"]})

    def test_without_logic_uses_latest_finishing_work(self) -> None:
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 1), D(2024, 1, 10), progress=0),
            Activity("B", "B", D(2024, 1, 1), D(2024, 3, 1), progress=0),
        ], data_date=D(2023, 12, 31)))
        rows = {r["id"]: r for r in result["activities"]}
        self.assertEqual(result["critical_path"]["method"], "approximate")
        self.assertTrue(rows["B"]["critical"])
        self.assertFalse(rows["A"]["critical"])
        self.assertIn("add_logic", {a["code"] for a in result["actions"]})


class DelayEventTests(unittest.TestCase):
    def test_concurrent_days_are_counted_once(self) -> None:
        acts = [Activity("A", "A", D(2024, 1, 1), D(2024, 1, 31), actual_start=D(2024, 1, 1), progress=50)]
        events = [
            DelayEvent("E1", "Late drawings", D(2024, 1, 1), D(2024, 1, 10), ["A"], "Design", "employer"),
            DelayEvent("E2", "Crew shortage", D(2024, 1, 6), D(2024, 1, 15), ["A"], "Labour", "contractor"),
            DelayEvent("E3", "Storm", D(2024, 1, 20), D(2024, 1, 21), ["A"], "Weather", "neutral"),
        ]
        result = analyze(_input(acts, events, data_date=D(2024, 1, 31)))
        days = result["events"]["by_party_days"]
        self.assertEqual(days["employer"], 5)
        self.assertEqual(days["concurrent"], 5)
        self.assertEqual(days["contractor"], 5)
        self.assertEqual(days["neutral"], 2)
        self.assertEqual(days["total"], 17)
        self.assertEqual(days["excusable"], 12)
        self.assertEqual(days["compensable"], 5)

    def test_ongoing_event_runs_to_data_date_and_unassigned_is_reported(self) -> None:
        acts = [Activity("A", "A", D(2024, 1, 1), D(2024, 1, 31), progress=0)]
        events = [DelayEvent("E1", "Permit", D(2024, 1, 25), None, ["A"], "Permit", None)]
        result = analyze(_input(acts, events, data_date=D(2024, 1, 31)))
        self.assertEqual(result["events"]["events"][0]["days"], 7)
        self.assertTrue(result["events"]["events"][0]["ongoing"])
        self.assertEqual(result["events"]["unassigned_days"], 7)

    def test_no_events_recommends_recording_them_when_late(self) -> None:
        result = analyze(_input([Activity("A", "A", D(2024, 1, 1), D(2024, 1, 10), progress=0)], data_date=D(2024, 1, 20)))
        self.assertFalse(result["events"]["available"])
        self.assertIn("record_events", {a["code"] for a in result["actions"]})


class DataQualityTests(unittest.TestCase):
    def test_no_planned_dates_returns_error(self) -> None:
        result = analyze(_input([Activity("A", "A")]))
        self.assertFalse(result["ok"])
        self.assertIn("az", result["error"])

    def test_reversed_and_missing_dates_are_reported(self) -> None:
        result = analyze(_input([
            Activity("A", "A", D(2024, 1, 10), D(2024, 1, 1), progress=100),
            Activity("B", "B"),
        ]))
        codes = {q["code"] for q in result["data_quality"]}
        self.assertIn("reversed_dates", codes)
        self.assertIn("missing_plan_dates", codes)
        self.assertIn("complete_without_finish", codes)
        self.assertEqual(result["activities"][0]["planned_start"], "2024-01-01")

    def test_data_date_inferred_from_actuals(self) -> None:
        inp = DelayInput(activities=[Activity("A", "A", D(2024, 1, 1), D(2024, 1, 10), actual_start=D(2024, 1, 3), progress=30)])
        result = analyze(inp, today=D(2030, 1, 1))
        self.assertEqual(result["kpis"]["data_date"], "2024-01-03")
        self.assertEqual(result["kpis"]["data_date_source"], "latest_actual")

    def test_every_message_is_bilingual(self) -> None:
        result = analyze(sample_input())
        for item in result["findings"] + result["actions"] + result["data_quality"]:
            self.assertTrue(item["en"])
            self.assertTrue(item["az"])


class SampleTests(unittest.TestCase):
    def test_sample_project_results(self) -> None:
        result = analyze(sample_input())
        k = result["kpis"]
        self.assertEqual(k["planned_progress_pct"], 57.1)
        self.assertEqual(k["actual_progress_pct"], 35.3)
        self.assertEqual(k["spi"], 0.62)
        self.assertEqual(k["schedule_delay_days"], 67)
        self.assertEqual(k["forecast_delay_days"], 98)
        self.assertEqual(k["status"], "critical")
        self.assertEqual(result["critical_path"]["method"], "cpm")
        self.assertEqual(result["events"]["by_party_days"]["concurrent"], 12)
        months = [m for m in result["monthly"] if m["actual_cumulative_pct"] is not None]
        self.assertEqual(months[-1]["month"], "2024-05")
        self.assertEqual(months[-1]["schedule_delay_days"], 67)


def _write_xlsx(sheets: dict) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row)
    handle = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    handle.close()
    wb.save(handle.name)
    return Path(handle.name)


class ReaderTests(unittest.TestCase):
    def test_template_round_trip_matches_sample(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "template.xlsx"
            path.write_bytes(build_template_bytes())
            parsed = read_path(path)
        self.assertEqual(parsed.project.data_date, D(2024, 5, 31))
        self.assertEqual(parsed.project.contract_finish, D(2024, 12, 15))
        self.assertEqual(len(parsed.activities), 16)
        self.assertEqual(len(parsed.events), 5)
        self.assertEqual(analyze(parsed)["kpis"], analyze(sample_input())["kpis"])

    def test_turkish_headers_fraction_percent_and_combined_finish_column(self) -> None:
        path = _write_xlsx({
            "Program": [
                ["İş Kodu", "İşin adı", "Plan Başlangıç", "Plan Bitiş", "Gerçekleşme %", "Actual Finish / Forecast Finish", "Status Date"],
                ["1", "Kazı", "01.01.2024", "10.01.2024", 1.0, "12.01.2024", "15.01.2024"],
                ["2", "Beton", "11.01.2024", "20.01.2024", 0.25, "25.01.2024", "15.01.2024"],
            ]
        })
        try:
            parsed = read_path(path)
        finally:
            path.unlink()
        a, b = parsed.activities
        self.assertEqual((a.progress, a.actual_finish), (100.0, D(2024, 1, 12)))
        self.assertEqual((b.progress, b.actual_finish, b.forecast_finish), (25.0, None, D(2024, 1, 25)))
        self.assertEqual(parsed.project.data_date, D(2024, 1, 15))

    def test_separate_baseline_and_actual_sheets_merge_by_id(self) -> None:
        path = _write_xlsx({
            "Baseline_Schedule": [["Activity ID", "Activity Name", "Planned Start", "Planned Finish"], ["A1", "Piling", D(2024, 1, 1), D(2024, 1, 31)]],
            "Actual_Progress": [["Activity ID", "Actual Start", "Actual Progress %"], ["A1", D(2024, 1, 5), 40]],
        })
        try:
            parsed = read_path(path)
        finally:
            path.unlink()
        self.assertEqual(len(parsed.activities), 1)
        activity = parsed.activities[0]
        self.assertEqual((activity.name, activity.actual_start, activity.progress), ("Piling", D(2024, 1, 5), 40.0))

    def test_csv_with_semicolons(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "plan.csv"
            path.write_text("Activity ID;Activity Name;Planned Start;Planned Finish;Actual %\nA;Walls;2024-01-01;2024-01-10;50\n", encoding="utf-8")
            parsed = read_path(path)
        self.assertEqual(parsed.activities[0].progress, 50.0)
        self.assertEqual(parsed.activities[0].planned_finish, D(2024, 1, 10))

    def test_primavera_xer(self) -> None:
        xer = "\n".join([
            "ERMHDR\t19.12",
            "%T\tPROJECT", "%F\tproj_id\tproj_short_name\tplan_start_date\tscd_end_date\tlast_recalc_date",
            "%R\t1\tTOWER\t2024-01-01 08:00\t2024-03-01 17:00\t2024-01-20 08:00",
            "%T\tTASK", "%F\ttask_id\ttask_code\ttask_name\ttask_type\tstatus_code\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date\tphys_complete_pct",
            "%R\t10\tA100\tExcavation\tTT_Task\tTK_Complete\t2024-01-01 08:00\t2024-01-10 17:00\t2024-01-01 08:00\t2024-01-12 17:00\t100",
            "%R\t11\tA200\tFoundation\tTT_Task\tTK_Active\t2024-01-11 08:00\t2024-01-31 17:00\t2024-01-13 08:00\t\t30",
            "%T\tTASKPRED", "%F\ttask_pred_id\ttask_id\tpred_task_id",
            "%R\t1\t11\t10",
            "%E",
        ])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "schedule.xer"
            path.write_text(xer, encoding="cp1252")
            parsed = read_path(path)
        self.assertEqual(parsed.project.name, "TOWER")
        self.assertEqual(parsed.project.data_date, D(2024, 1, 20))
        self.assertEqual([a.id for a in parsed.activities], ["A100", "A200"])
        self.assertEqual(parsed.activities[1].predecessors, ["A100"])
        self.assertEqual(parsed.activities[0].actual_finish, D(2024, 1, 12))

    def test_ms_project_xml_and_doctype_rejection(self) -> None:
        xml = """<?xml version="1.0"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Title>Villa</Title><StatusDate>2024-01-15T08:00:00</StatusDate>
  <Tasks>
    <Task><UID>0</UID><ID>0</ID><Name>Villa</Name><Summary>1</Summary></Task>
    <Task><UID>1</UID><ID>1</ID><WBS>1.1</WBS><Name>Slab</Name><Start>2024-01-03T08:00:00</Start><Finish>2024-01-12T17:00:00</Finish>
      <ActualStart>2024-01-03T08:00:00</ActualStart><PercentComplete>60</PercentComplete>
      <Baseline><Number>0</Number><Start>2024-01-01T08:00:00</Start><Finish>2024-01-10T17:00:00</Finish></Baseline></Task>
    <Task><UID>2</UID><ID>2</ID><WBS>1.2</WBS><Name>Walls</Name><Start>2024-01-13T08:00:00</Start><Finish>2024-01-20T17:00:00</Finish>
      <PredecessorLink><PredecessorUID>1</PredecessorUID></PredecessorLink></Task>
  </Tasks>
</Project>"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "plan.xml"
            path.write_text(xml, encoding="utf-8")
            parsed = read_path(path)
            evil = Path(temp) / "evil.xml"
            evil.write_text('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><Project>&a;</Project>', encoding="utf-8")
            rejected = read_path(evil)
        self.assertEqual(parsed.project.name, "Villa")
        slab, walls = parsed.activities
        self.assertEqual((slab.planned_start, slab.planned_finish, slab.forecast_finish), (D(2024, 1, 1), D(2024, 1, 10), D(2024, 1, 12)))
        self.assertEqual(walls.predecessors, ["1.1"])
        self.assertFalse(rejected.activities)
        self.assertTrue(rejected.warnings)

    def test_unreadable_file_is_a_warning_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "broken.xlsx"
            bad.write_bytes(b"PK\x03\x04 not really a workbook")
            parsed = read_paths([bad])
        self.assertTrue(parsed.warnings)
        self.assertFalse(parsed.activities)


class ReportTests(unittest.TestCase):
    def test_pdf_and_excel_in_both_languages(self) -> None:
        result = analyze(sample_input())
        for lang in ("az", "en"):
            pdf = build_delay_pdf(result, lang)
            self.assertTrue(pdf.startswith(b"%PDF"))
            self.assertGreater(len(pdf), 5000)
            xlsx = build_delay_excel(result, lang)
            self.assertTrue(xlsx.startswith(b"PK"))
            from openpyxl import load_workbook

            wb = load_workbook(io.BytesIO(xlsx))
            self.assertGreaterEqual(len(wb.sheetnames), 5)


try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover
    TestClient = None


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed.")
class DelayApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT"] = "true"
        os.environ["DEVBAREUN_PRODUCTION_SECURITY"] = "false"
        from app.main import app

        cls.app = app
        cls.client = TestClient(app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_public_sample_template_and_report(self) -> None:
        sample = self.client.get("/api/delay-analysis/sample")
        self.assertEqual(sample.status_code, 200)
        self.assertTrue(sample.json()["is_example"])
        template = self.client.get("/api/delay-analysis/template")
        self.assertEqual(template.status_code, 200)
        self.assertTrue(template.content.startswith(b"PK"))
        pdf = self.client.get("/api/delay-analysis/sample/report?format=pdf&lang=az")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        xlsx = self.client.get("/api/delay-analysis/sample/report?format=xlsx&lang=en")
        self.assertIn("spreadsheetml", xlsx.headers["content-type"])

    def test_template_download_route_serves_delay_template(self) -> None:
        response = self.client.get("/api/templates/delay/download")
        self.assertEqual(response.status_code, 200)
        self.assertIn("delay-analysis-template", response.headers.get("content-disposition", ""))

    def test_preview_requires_login(self) -> None:
        response = self.client.post("/api/delay-analysis/preview", files={"files": ("plan.xlsx", build_template_bytes(), "application/octet-stream")})
        self.assertIn(response.status_code, {401, 403})

    def test_preview_analyses_upload_and_rejects_bad_files(self) -> None:
        from app.auth_dependencies import CurrentUser, get_current_user

        self.app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="u1", auth_user_id="u1", email="test@example.com")
        ok = self.client.post("/api/delay-analysis/preview", files={"files": ("plan.xlsx", build_template_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["kpis"]["forecast_delay_days"], 98)
        fake = self.client.post("/api/delay-analysis/preview", files={"files": ("plan.xlsx", b"not a zip", "application/octet-stream")})
        self.assertEqual(fake.status_code, 400)
        script = self.client.post("/api/delay-analysis/preview", files={"files": ("run.py", b"print(1)", "text/plain")})
        self.assertEqual(script.status_code, 400)


if __name__ == "__main__":
    unittest.main()
