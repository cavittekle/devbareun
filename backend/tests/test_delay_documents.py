"""Contract / schedule / F2 documents for the delay analysis."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from app.delay import run_delay_analysis
from app.delay.documents import f2_from_tables, period_from_text, read_document, read_documents
from app.document_types import infer_document_type, normalize_document_type, validate_document_format
from app.file_validation import validate_magic_signature, validate_upload_metadata

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "frontend" / "templates" / "devbareun-delay-analysis-template.xlsx"


def _f2_simple(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "F2"
    for row in [
        ["Forma F2"],
        ["Görülmüş işlərin təhvil-təslim aktı № 7"],
        ["Hesabat dövrü: 01.03.2024 - 31.03.2024"],
        ["Sifarişçi: Nümunə MMC"],
        ["№", "İşlərin adı", "Ölçü vahidi", "Miqdar", "Vahid qiymət", "Məbləğ, AZN"],
        [1, 2, 3, 4, 5, 6],
        [1, "Beton işləri", "m3", 120, 150, 18000],
        [2, "Armatur işləri", "t", 10, 1200, 12000],
        [None, "Cəmi", None, None, None, 30000],
        [None, "ƏDV 18%", None, None, None, 5400],
        [None, "Cəmi ƏDV ilə", None, None, None, 35400],
    ]:
        ws.append(row)
    wb.save(path)
    return path


def _f2_grouped(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    for row in [
        ["Görülmüş işlərin dəyəri haqqında arayış (F2) № 12", None, None, None, None, None, None, None],
        ["Hesabat dövrü", "may 2024", None, None, None, None, None, None],
        ["№", "İşin adı", "Müqavilə üzrə", None, "Hesabat dövründə", None, "İşlərin əvvəlindən", None],
        [None, None, "Miqdar", "Məbləğ", "Miqdar", "Məbləğ", "Miqdar", "Məbləğ"],
        [1, "Fasad işləri", 1000, 500000, 100, 50000, 300, 150000],
        [2, "Hörgü işləri", 2000, 300000, 200, 30000, 1000, 150000],
        [None, "Cəmi", None, 800000, None, 80000, None, 300000],
    ]:
        ws.append(row)
    wb.save(path)
    return path


def _docx(path: Path, rows: list[list[str]], paragraphs: list[str]) -> Path:
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    def p(text: str) -> str:
        return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
    body = "".join(p(text) for text in paragraphs)
    body += "<w:tbl>" + "".join(
        "<w:tr>" + "".join(f"<w:tc>{p(cell)}</w:tc>" for cell in row) + "</w:tr>" for row in rows
    ) + "</w:tbl>"
    xml = f'<?xml version="1.0" encoding="UTF-8"?><w:document {w}><w:body>{body}</w:body></w:document>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", xml)
    return path


class DocumentTypeTests(unittest.TestCase):
    def test_formats_per_document_type(self):
        validate_document_format("contract", "muqavile.pdf")
        validate_document_format("contract", "muqavile.docx")
        validate_document_format("contract", "scan.jpg")
        validate_document_format("schedule", "plan.pdf")
        validate_document_format("schedule", "plan.mpp")
        validate_document_format("schedule", "plan.xer")
        validate_document_format("f2", "f2.xlsx")
        validate_document_format("f2", "f2.doc")
        with self.assertRaises(ValueError):
            validate_document_format("f2", "f2.pdf")
        with self.assertRaises(ValueError):
            validate_document_format("schedule", "plan.jpg")

    def test_upload_metadata_accepts_document_formats(self):
        for name in ("muqavile.pdf", "muqavile.docx", "akt.doc", "plan.mpp", "scan.png"):
            self.assertTrue(validate_upload_metadata(name, None, 10, 1000)["file_ext"])
        with self.assertRaises(ValueError):
            validate_upload_metadata("run.exe", None, 10, 1000)

    def test_signatures(self):
        self.assertTrue(validate_magic_signature(b"PK\x03\x04rest", "a.docx"))
        self.assertTrue(validate_magic_signature(bytes.fromhex("D0CF11E0A1B11AE1") + b"x", "a.doc"))
        self.assertTrue(validate_magic_signature(bytes.fromhex("D0CF11E0A1B11AE1") + b"x", "a.mpp"))
        self.assertFalse(validate_magic_signature(b"%PDF-1.7", "a.docx"))

    def test_type_names_and_inference(self):
        self.assertEqual(normalize_document_type("Müqavilə"), "contract")
        self.assertEqual(normalize_document_type("F2"), "f2")
        self.assertEqual(normalize_document_type("planning"), "schedule")
        self.assertIsNone(normalize_document_type("photo"))
        self.assertEqual(infer_document_type("F2_2024_05.xlsx"), "f2")
        self.assertEqual(infer_document_type("Muqavile_123.pdf"), "contract")
        self.assertEqual(infer_document_type("baseline.xer"), "schedule")


class F2ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_simple_f2_excel(self):
        result = read_document(_f2_simple(self.dir / "akt7.xlsx"), "f2")
        self.assertEqual(len(result.payments), 1)
        cert = result.payments[0]
        self.assertEqual(cert.amount, 30000)
        self.assertEqual(cert.amount_with_vat, 35400)
        self.assertEqual(cert.period, date(2024, 3, 31))
        self.assertEqual(cert.number, "7")
        self.assertEqual(result.documents[0].status, "read")

    def test_grouped_header_uses_period_and_cumulative_columns(self):
        cert = read_document(_f2_grouped(self.dir / "f2.xlsx"), "f2").payments[0]
        self.assertEqual(cert.amount, 80000)
        self.assertEqual(cert.cumulative, 300000)
        self.assertEqual(cert.period, date(2024, 5, 31))
        self.assertEqual(cert.number, "12")

    def test_f2_word_docx(self):
        path = _docx(self.dir / "f2_aprel.docx", [
            ["№", "İşlərin adı", "Ölçü vahidi", "Miqdar", "Məbləğ"],
            ["1", "Torpaq işləri", "m3", "500", "12 500,00"],
            ["2", "Beton işləri", "m3", "40", "7 500,00"],
            ["", "Cəmi", "", "", "20 000,00"],
        ], ["Təhvil-təslim aktı № 4", "Hesabat dövrü: aprel 2024"])
        cert = read_document(path, "f2").payments[0]
        self.assertEqual(cert.amount, 20000)
        self.assertEqual(cert.period, date(2024, 4, 30))
        self.assertEqual(cert.number, "4")

    def test_without_total_row_sums_lines(self):
        certs = f2_from_tables([("s", [
            ("İşin adı", "Məbləğ"),
            ("Qazıntı", 1000),
            ("Beton", 2500),
        ])], "F2_2024-02.xlsx")
        self.assertEqual(certs[0].amount, 3500)
        self.assertEqual(certs[0].period, date(2024, 2, 29))

    def test_old_doc_and_contract_are_references(self):
        doc = self.dir / "f2.doc"
        doc.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1"))
        self.assertEqual(read_document(doc, "f2").documents[0].status, "reference")
        pdf = self.dir / "muqavile.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        contract = read_document(pdf, "contract").documents[0]
        self.assertEqual((contract.document_type, contract.status), ("contract", "reference"))
        mpp = self.dir / "plan.mpp"
        mpp.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1"))
        self.assertIn("XML", read_document(mpp, "schedule").documents[0].note_en)

    def test_period_from_text(self):
        self.assertEqual(period_from_text("01.05.2024 - 31.05.2024"), date(2024, 5, 31))
        self.assertEqual(period_from_text("Mart ayı 2024"), date(2024, 3, 31))
        self.assertEqual(period_from_text("F2_2023-11"), date(2023, 11, 30))
        self.assertIsNone(period_from_text("Forma F2"))


class PaymentAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_template_f2_sheet_feeds_payments(self):
        result = run_delay_analysis([TEMPLATE])
        payments = result["payments"]
        self.assertTrue(payments["available"])
        self.assertEqual(payments["certificate_count"], 9)
        self.assertEqual(payments["contract_value"], 18500000.0)
        self.assertAlmostEqual(payments["financial_progress_pct"], 37.7)
        may = next(row for row in result["monthly"] if row["month"] == "2024-05")
        self.assertEqual(may["certified_amount"], 800000.0)

    def test_documents_are_listed_and_f2_files_add_up(self):
        f2 = _f2_simple(self.dir / "akt7.xlsx")
        contract = self.dir / "muqavile.pdf"
        contract.write_bytes(b"%PDF-1.4")
        result = run_delay_analysis([TEMPLATE, f2, contract], document_types={
            str(TEMPLATE): "schedule", str(f2): "f2", str(contract): "contract",
        })
        types = {d["name"]: (d["document_type"], d["status"]) for d in result["documents"]}
        self.assertEqual(types["muqavile.pdf"], ("contract", "reference"))
        self.assertEqual(types["akt7.xlsx"], ("f2", "read"))
        # 9 template rows + the uploaded F2 for March 2024 (duplicate month).
        self.assertEqual(result["payments"]["certificate_count"], 10)
        self.assertIn("f2_duplicate_period", {q["code"] for q in result["data_quality"]})

    def test_gap_between_certified_value_and_progress_is_flagged(self):
        result = run_delay_analysis([TEMPLATE])
        self.assertNotIn("f2_ahead_of_progress", {f["code"] for f in result["findings"]})
        from app.delay.documents import read_documents as rd
        from app.delay import analyze

        data = rd([TEMPLATE])
        data.project.contract_value = 10_000_000.0  # 69.8% certified vs 35.3% physical
        codes = {f["code"] for f in analyze(data)["findings"]}
        self.assertIn("f2_ahead_of_progress", codes)

    def test_only_pdf_schedule_fails_with_documents_listed(self):
        pdf = self.dir / "plan.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        result = run_delay_analysis([pdf], document_types={"plan.pdf": "schedule"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["documents"][0]["status"], "reference")


if __name__ == "__main__":
    unittest.main()


class UploadRouteDocumentTypeTests(unittest.TestCase):
    def test_document_type_from_request_or_file_name(self):
        from app.upload_routes import CreateUploadUrlRequest, _document_type

        def req(name, document_type=None):
            return CreateUploadUrlRequest(project_id="p1", filename=name, document_type=document_type)

        self.assertEqual(_document_type(req("x.pdf", "contract"), "x.pdf"), "contract")
        self.assertEqual(_document_type(req("akt.docx", "F2"), "akt.docx"), "f2")
        self.assertEqual(_document_type(req("F2_may.xlsx"), "F2_may.xlsx"), "f2")
        with self.assertRaises(ValueError):
            _document_type(req("plan.jpg", "schedule"), "plan.jpg")
        with self.assertRaises(ValueError):
            _document_type(req("x.pdf", "invoice"), "x.pdf")

    def test_insert_falls_back_when_column_is_missing(self):
        from unittest import mock

        from app import upload_routes
        from app.production_store import ProductionStoreError

        calls = []

        def fake_insert(table, record):
            calls.append(dict(record))
            if "document_type" in record:
                raise ProductionStoreError("Supabase REST error 400: Could not find the 'document_type' column")
            return dict(record)

        with mock.patch.object(upload_routes, "insert_row", side_effect=fake_insert):
            row = upload_routes._insert_upload_row({"id": "1", "document_type": "f2"})
        self.assertEqual(len(calls), 2)
        self.assertNotIn("document_type", calls[1])
        self.assertEqual(row["document_type"], "f2")
