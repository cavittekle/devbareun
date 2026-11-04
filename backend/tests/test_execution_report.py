"""Execution report v2: estimate-weighted plan, earned schedule, F-2/F-3 and
contract readers, and the two-page A3 PDF."""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date as D
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.delay import analyze  # noqa: E402
from app.delay import categories as cat  # noqa: E402
from app.delay.costs import contract_from_text, cost_lines_from_rows, f3_from_rows  # noqa: E402
from app.delay.documents import read_document  # noqa: E402
from app.delay.executive import build_executive  # noqa: E402
from app.delay.model import Activity, CostLine, DelayInput, ProjectInfo  # noqa: E402
from app.delay.report import build_delay_excel, build_delay_pdf  # noqa: E402
from app.delay.report_a3 import report_filename  # noqa: E402
from app.delay.sample import sample_input  # noqa: E402
from app.delay.sample_estate import estate_sample_input  # noqa: E402


class CategoryTests(unittest.TestCase):
    def test_strong_words_win(self) -> None:
        self.assertEqual(cat.categorize("Döşəmə plitəsinin betonlanması"), cat.FRAME)
        self.assertEqual(cat.categorize("Divarlar", "Əhəng daşından hörgü"), cat.MASONRY)
        self.assertEqual(cat.categorize("Lift quraşdırılması"), cat.MEP)
        self.assertEqual(cat.categorize("Ərazi abadlığı"), cat.SITE)
        self.assertIsNone(cat.categorize("Müxtəlif"))

    def test_building_names(self) -> None:
        self.assertEqual(cat.building_of("BINA №20"), "Bina-20")
        self.assertEqual(cat.building_of("3 saylı bina"), "Bina-3")
        self.assertEqual(cat.building_of("Korpus 4A"), "Bina-4A")


class CostReaderTests(unittest.TestCase):
    def test_cumulative_sheet_skips_totals_and_header_rows(self) -> None:
        rows = [
            ("Bina-3",),
            ("№", "İşin adı", "Ölçü vahidi", "Smeta üzrə", None, "Əvvəldən kumulyativ", None, "Hesabat ayı", None),
            (None, None, None, "həcm", "məbləğ", "həcm", "məbləğ", "həcm", "məbləğ"),
            (None, "Dəmir-beton karkas", None, None, None, None, None, None, None),
            (1, "Beton B25", "m3", 100, 10_000, 40, 4_000, 10, 1_000),
            (2, "Armatur", "t", 10, 8_000, 10, 8_000, 0, 0),
            (None, "Cəmi bölmə üzrə", None, None, 18_000, None, 12_000, None, 1_000),
            (None, "Gözlənilməz xərclər 2%", "%", None, 360, None, 0, None, 0),
        ]
        lines = cost_lines_from_rows(rows, "f2.xlsx:Nakopitel")
        self.assertEqual([l.name for l in lines], ["Beton B25", "Armatur"])
        self.assertEqual(lines[0].building, "Bina-3")
        self.assertEqual(lines[0].category, cat.FRAME)
        self.assertEqual((lines[0].estimate_value, lines[0].cum_value, lines[0].period_value), (10_000, 4_000, 1_000))
        self.assertEqual(lines[1].cum_qty, 10)

    def test_forma3_labels(self) -> None:
        rows = [
            ("Forma № 3, hesabat dövrü 01.10.2026 - 31.10.2026",),
            ("Göstərici", "Əvvəldən kumulyativ", "Hesabat ayı"),
            ("Görülmüş işlərin dəyəri ƏDV ilə", 1_180_000, 118_000),
            ("Alınmış avans", 3_000_000, None),
            ("Avansdan tutulmuş", 354_000, 35_400),
            ("Ödəniləcək məbləğ", None, 82_600),
        ]
        f3 = f3_from_rows(rows, "akt.xlsx:F3")
        self.assertIsNotNone(f3)
        self.assertEqual(f3.works_cum, 1_180_000)
        self.assertEqual(f3.advance_withheld_period, 35_400)
        self.assertEqual(f3.advance_remaining, 2_646_000)
        self.assertEqual(f3.payable_period, 82_600)
        self.assertEqual(f3.period, D(2026, 10, 31))

    def test_contract_text_terms(self) -> None:
        text = ("Müqavilə № 54-N, 15.09.2025. Müqavilənin ümumi məbləği ƏDV daxil 34 591 000,00 manat təşkil edir. "
                "Podratçıya müqavilə qiymətinin 30% həcmində avans ödənilir. Avans ödənişi bank təminatı ilə, 10 (on) ay müddətinə. "
                "İşlərin gecikdirilməsinə görə hər gün üçün müqavilə qiymətinin 0,1% həcmində cərimə, lakin maksimum 10% ödənilir. "
                "Aktlar 15 iş günü ərzində ödənilir.")
        terms = contract_from_text(text, "muqavile.docx")
        self.assertEqual(terms.number, "54-n")
        self.assertEqual(terms.signed, D(2025, 9, 15))
        self.assertEqual(terms.value_with_vat, 34_591_000)
        self.assertEqual(terms.advance_pct, 30)
        self.assertEqual(terms.advance_guarantee_months, 10)
        self.assertEqual(terms.penalty_pct_per_day, 0.1)
        self.assertEqual(terms.penalty_cap_pct, 10)
        self.assertEqual(terms.payment_days, 15)


class ExecutiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = analyze(estate_sample_input())
        self.r = self.result["executive"]

    def test_headline_numbers(self) -> None:
        t = self.r["totals"]
        self.assertTrue(self.r["ok"])
        self.assertEqual(self.r["method"], "estimate_value")
        self.assertEqual((t["plan_pct"], t["fact_pct"], t["delay_days"]), (91.7, 21.8, 202))
        self.assertEqual(t["earned_schedule_date"], "2026-04-12")
        self.assertEqual(self.r["forecast"]["earliest_finish"], "2027-07-22")
        self.assertTrue(self.r["forecast"]["current_pace_unacceptable"])
        self.assertIsNone(self.r["forecast"]["current_pace_finish"])

    def test_penalty_finance_and_physical_checks(self) -> None:
        penalty = self.r["penalty"]
        self.assertEqual((penalty["cap_days"], penalty["cap_date"]), (100, "2027-04-25"))
        finance = self.r["finance"]
        self.assertTrue(finance["advance_exceeds_works"])
        self.assertTrue(finance["advance_guarantee_risk"])
        mismatch = self.r["physical"]["mismatches"]
        self.assertEqual([m["building"] for m in mismatch], ["Bina-3"])

    def test_missing_f2_months_and_cards(self) -> None:
        self.assertEqual(self.r["f2_missing_months"], ["2025-11-30", "2026-01-31", "2026-02-28"])
        for lang in ("az", "en"):
            texts = self.r["texts"][lang]
            self.assertTrue(3 <= len(texts["delay_cards"]) <= 5)
            self.assertEqual(len(texts["director_decisions"]), 5)
            self.assertEqual(len(texts["contractor_actions"]), 5)

    def test_plan_is_spread_over_the_mapped_activity(self) -> None:
        inp = DelayInput(
            project=ProjectInfo(name="T", data_date=D(2026, 1, 31)),
            activities=[Activity("F", "Bina-1 karkas", D(2026, 1, 1), D(2026, 3, 2), progress=10),
                        Activity("M", "Bina-1 hörgü", D(2026, 3, 3), D(2026, 5, 1), progress=0)],
            cost_lines=[CostLine("Beton", 600, unit="m3", building="Bina-1", category=cat.FRAME, cum_value=60),
                        CostLine("Hörgü", 400, unit="m2", building="Bina-1", category=cat.MASONRY, cum_value=0)])
        r = build_executive(inp, D(2026, 1, 31))
        self.assertAlmostEqual(r["totals"]["plan_pct"], 30.0, delta=1.0)
        self.assertEqual(r["totals"]["fact_pct"], 6.0)
        self.assertEqual(r["totals"]["earned_schedule_date"], "2026-01-07")

    def test_schedule_only_input_uses_schedule_fact_and_percent_pace(self) -> None:
        r = analyze(sample_input())["executive"]
        self.assertEqual(r["method"], "activity_weights")
        self.assertEqual(r["forecast"]["pace_unit"], "pct")
        self.assertTrue(all(p["plan_value"] is None for p in r["monthly"]))
        facts = [p["fact_pct"] for p in r["monthly"] if p.get("fact_pct") is not None]
        self.assertEqual(facts[-1], 35.3)
        self.assertGreater(r["finance"]["works_cum_with_vat"], 1_000_000)


class ReportTests(unittest.TestCase):
    def test_a3_pdf_has_two_landscape_pages(self) -> None:
        result = analyze(estate_sample_input())
        for lang in ("az", "en"):
            pdf = build_delay_pdf(result, lang)
            self.assertTrue(pdf.startswith(b"%PDF"))
            self.assertEqual(pdf.count(b"/Type /Page\n") or pdf.count(b"/Type /Page "), 2)
            self.assertIn(b"1190.55", pdf)  # A3 landscape width in points

    def test_excel_has_executive_sheets(self) -> None:
        from io import BytesIO

        from openpyxl import load_workbook

        content = build_delay_excel(analyze(estate_sample_input()), "az")
        names = load_workbook(BytesIO(content)).sheetnames
        for name in ("İş növləri", "Binalar", "Aylıq plan vs F-2", "Maliyyə və proqnoz"):
            self.assertIn(name, names)

    def test_report_filename(self) -> None:
        result = analyze(estate_sample_input())
        self.assertEqual(report_filename(result, "az"), "Nümunə yaşayış massivi, 1-ci mərhələ (6 bina) icra hesabatı -10.2026.pdf")

    def test_f2_workbook_upload_feeds_the_report(self) -> None:
        wb = Workbook()
        ws = wb.active
        ws.title = "Smeta nakopitel"
        for row in [
            ["Forma F-2, hesabat dövrü 01.10.2026 - 31.10.2026"],
            ["Bina", "İşin adı", "Ölçü vahidi", "Smeta dəyəri", "Kumulyativ dəyər", "Hesabat ayı dəyəri"],
            ["Bina-1", "Beton B25", "m3", 1_000_000, 400_000, 50_000],
            ["Bina-1", "Fasad üzlüyü", "m2", 500_000, 0, 0],
            [None, "Cəmi", None, 1_500_000, 400_000, 50_000],
        ]:
            ws.append(row)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "akt10.xlsx"
            wb.save(path)
            inp = read_document(path, "f2")
        self.assertEqual(len(inp.cost_lines), 2)
        self.assertEqual(inp.payments[0].period, D(2026, 10, 31))
        self.assertEqual(inp.payments[0].cumulative, 400_000)


if __name__ == "__main__":
    unittest.main()
