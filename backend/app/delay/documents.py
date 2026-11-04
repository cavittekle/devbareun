"""Project documents next to the schedule: contract and F2 certificates.

* The **schedule** goes through the existing readers (Excel/CSV, XER, MS
  Project XML). A PDF print or an ``.mpp`` file is kept as a reference.
* An **F2** certificate (görülmüş işlərin aktı) is read from Excel/CSV or
  Word ``.docx``: the reporting period, the certificate number and the period
  total (before and with VAT), plus the value since the start of the works when
  the form has that column. A register sheet with one row per period also works.
* The **contract** is kept with the analysis and listed in the report; its
  dates and value come from the project sheet of the template.

Nothing is estimated: a value the document does not state stays ``None``.
"""
from __future__ import annotations

import calendar
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..document_types import CONTRACT, F2, READABLE_FORMATS, SCHEDULE, infer_document_type
from .costs import extract_costs
from .model import CostLine, DelayInput, PaymentCertificate, SupportingDocument
from .reader import _norm, csv_tables, parse_date, parse_number, read_path, workbook_tables, xls_tables

Table = Tuple[str, List[Sequence[Any]]]

MAX_DOCX_XML_BYTES = 20 * 1024 * 1024
HEADER_SCAN_ROWS = 80

AMOUNT_WORDS = ("mebleg", "deyer", "summa", "amount", "value", "cost", "сумма", "стоимость", "tutar", "bedel")
UNIT_WORDS = ("vahid", "unit", "единиц", "birim")
NAME_WORDS = ("isinadi", "islerinadi", "isinnovu", "adi", "name", "description", "наименование", "isler", "work", "isinmezmunu")
CUMULATIVE_WORDS = ("evvelinden", "baslanmasindan", "baslangicdan", "kumulyativ", "cumulative", "todate", "сначала", "нарастающ", "toplam")
PERIOD_WORDS = ("hesabatdovr", "caridovr", "cariay", "budovr", "thisperiod", "dovrerzinde", "hesabatay", "отчетн", "period", "dovr")
CONTRACT_WORDS = ("muqavile", "smeta", "contract", "budget", "договор", "смет", "sozlesme")
DATE_WORDS = ("dovr", "period", "month", "ay", "tarix", "date", "период", "месяц", "donem")
TOTAL_WORDS = ("cemi", "yekun", "total", "grand", "overall", "итого", "всего", "umumi", "toplam", "hamisi")
VAT_WORDS = ("edv", "vat", "ндс", "kdv")
WITH_WORDS = ("ile", "daxil", "includ", "incl", "сучетом", "свключ", "dahil")

MONTHS = {
    1: ("yanvar", "january", "январ", "ocak"),
    2: ("fevral", "february", "феврал", "subat"),
    3: ("mart", "march", "март"),
    4: ("aprel", "april", "апрел", "nisan"),
    5: ("may", "мая", "май", "mayis"),
    6: ("iyun", "june", "июн", "haziran"),
    7: ("iyul", "july", "июл", "temmuz"),
    8: ("avqust", "august", "август", "agustos"),
    9: ("sentyabr", "september", "сентябр", "eylul"),
    10: ("oktyabr", "october", "октябр", "ekim"),
    11: ("noyabr", "november", "ноябр", "kasim"),
    12: ("dekabr", "december", "декабр", "aralik"),
}

NOTES = {
    "contract": (
        "Kept as a reference: no text could be read (scanned PDF or image). Enter the key terms (value, dates, advance, penalty) in the template's Contract sheet.",
        "İstinad kimi saxlanıldı: mətn oxunmadı (skan PDF və ya şəkil). Əsas şərtləri (məbləğ, tarixlər, avans, cərimə) şablonun Müqavilə vərəqinə daxil edin.",
    ),
    "contract_read": (
        "Contract terms were read from the terms table.",
        "Müqavilə şərtləri şərtlər cədvəlindən oxundu.",
    ),
    "contract_text": (
        "Contract terms were found in the text automatically; check them in the report.",
        "Müqavilə şərtləri mətndən avtomatik tapıldı; hesabatda yoxlayın.",
    ),
    "schedule_pdf": (
        "PDF schedules are kept as a reference; dates cannot be read from a PDF. Upload the Excel, XER or MS Project XML export for the calculation.",
        "PDF qrafik istinad kimi saxlanıldı; PDF-dən tarixlər oxunmur. Hesablama üçün Excel, XER və ya MS Project XML ixracını yükləyin.",
    ),
    "schedule_mpp": (
        "MS Project .mpp files are kept as a reference. In MS Project use File > Save As > XML and upload the XML for the calculation.",
        "MS Project .mpp faylı istinad kimi saxlanıldı. Hesablama üçün MS Project-də Fayl > Fərqli saxla > XML seçin və XML faylını yükləyin.",
    ),
    "schedule_empty": (
        "No activities, events or project data were found in this file.",
        "Bu faylda iş, hadisə və ya layihə məlumatı tapılmadı.",
    ),
    "f2_doc": (
        "Old Word .doc files cannot be read; save the F2 as .docx or Excel to include its amounts.",
        "Köhnə Word .doc faylı oxunmur; məbləğlərin hesaba alınması üçün F2-ni .docx və ya Excel kimi saxlayın.",
    ),
    "f2_empty": (
        "No F2 total amount was found in this file.",
        "Bu faylda F2 yekun məbləği tapılmadı.",
    ),
    "unreadable": (
        "The file could not be read.",
        "Fayl oxunmadı.",
    ),
}


def _document(path: Path, document_type: str, status: str, note: Optional[str] = None, *, extra_en: str = "", extra_az: str = "") -> SupportingDocument:
    en, az = NOTES[note] if note else (None, None)
    if extra_en:
        en = f"{extra_en} {en or ''}".strip()
        az = f"{extra_az} {az or ''}".strip()
    return SupportingDocument(name=path.name, document_type=document_type, file_format=path.suffix.lower().lstrip("."),
                              status=status, note_en=en, note_az=az)


# ------------------------------------------------------------- dispatching
def read_document(path: Path, document_type: Optional[str] = None) -> DelayInput:
    """Read one uploaded file according to its document type."""
    document_type = document_type or infer_document_type(path.name)
    suffix = path.suffix.lower()
    if document_type == CONTRACT:
        return _read_contract(path)
    if document_type == F2:
        return _read_f2_document(path)
    if suffix not in READABLE_FORMATS[SCHEDULE]:
        note = "schedule_mpp" if suffix == ".mpp" else "schedule_pdf"
        return DelayInput(documents=[_document(path, SCHEDULE, "reference", note)])
    result = read_path(path)
    if suffix in {".xlsx", ".xlsm"}:
        tables = workbook_tables(path)
        # The template's optional F2 register: one row per certificate.
        f2_sheets = [table for table in tables if _has(_norm(table[0].rsplit(":", 1)[-1]), ("f2", "odenis", "payment"))
                     and not _has(_norm(table[0].rsplit(":", 1)[-1]), ("smeta", "nakopitel"))]
        if f2_sheets:
            result.payments.extend(f2_from_tables(f2_sheets, path.name))
        # The template's estimate / Forma-3 / contract sheets.
        result.merge(extract_costs(tables, path.name))
    found = bool(result.activities or result.events or result.monthly or result.sources or result.payments or result.cost_lines)
    result.documents.append(_document(path, SCHEDULE, "read" if found else "no_data", None if found else "schedule_empty"))
    return result


def read_documents(paths: Sequence[Path], document_types: Optional[Mapping[str, str]] = None) -> DelayInput:
    from .reader import _merge_duplicate_activities

    types = dict(document_types or {})
    combined = DelayInput()
    for raw in paths:
        path = Path(raw)
        document_type = types.get(str(path)) or types.get(path.name) or infer_document_type(path.name)
        try:
            combined.merge(read_document(path, document_type))
        except Exception as exc:  # one unreadable file must not block the rest
            combined.warnings.append(f"{path.name}: file could not be read ({type(exc).__name__}).")
            combined.documents.append(_document(path, document_type, "unreadable", "unreadable"))
    _merge_duplicate_activities(combined)
    return combined


# --------------------------------------------------------------------- F2
def _read_f2_document(path: Path) -> DelayInput:
    suffix = path.suffix.lower()
    if suffix not in READABLE_FORMATS[F2]:
        return DelayInput(documents=[_document(path, F2, "reference", "f2_doc")])
    if suffix in {".xlsx", ".xlsm"}:
        tables = workbook_tables(path)
    elif suffix == ".xls":
        tables = xls_tables(path)
    elif suffix == ".csv":
        tables = csv_tables(path)
    else:
        tables = docx_tables(path)
    costs = extract_costs(tables, path.name)
    if costs.cost_lines:
        certificates = [_certificate_from_lines(costs.cost_lines, tables, path.name)]
    else:
        certificates = f2_from_tables(tables, path.name)
    if not certificates and not costs.f3:
        return DelayInput(documents=[_document(path, F2, "no_data", "f2_empty")])
    missing_period = [c for c in certificates if c.period is None]
    note_en = note_az = ""
    if missing_period:
        note_en = "The reporting period was not found; add it to the form or the file name (e.g. F2_2024-05)."
        note_az = "Hesabat dövrü tapılmadı; onu formaya və ya fayl adına əlavə edin (məs. F2_2024-05)."
    if costs.cost_lines:
        buildings = len({line.building for line in costs.cost_lines if line.building})
        note_en = f"{len(costs.cost_lines)} estimate lines read ({buildings} buildings). {note_en}".strip()
        note_az = f"{len(costs.cost_lines)} smeta sətri oxundu ({buildings} bina). {note_az}".strip()
    for summary in costs.f3:
        if summary.period is None and certificates and certificates[0].period:
            summary.period = certificates[0].period
    if costs.f3:
        note_en = f"{note_en} Forma-3 read.".strip()
        note_az = f"{note_az} Forma-3 oxundu.".strip()
    return DelayInput(payments=certificates, cost_lines=costs.cost_lines, f3=costs.f3, contract=costs.contract,
                      sources=[path.name],
                      documents=[_document(path, F2, "read", None, extra_en=note_en, extra_az=note_az)])


def _certificate_from_lines(lines: Sequence[CostLine], tables: Sequence[Table], filename: str) -> PaymentCertificate:
    """The reporting-month F-2 total of a cumulative estimate workbook."""
    period_values = [line.period_value for line in lines if line.period_value is not None]
    cum_values = [line.cum_value for line in lines if line.cum_value is not None]
    head_rows = [row for _, rows in tables for row in list(rows)[:12]]
    return PaymentCertificate(
        source=filename,
        period=_period_from_rows(head_rows) or period_from_text(Path(filename).stem),
        number=_number_from_rows(head_rows),
        amount=round(sum(period_values), 2) if period_values else None,
        cumulative=round(sum(cum_values), 2) if cum_values else None,
        line_count=len(lines),
    )


def _read_contract(path: Path) -> DelayInput:
    from .costs import read_contract_document

    try:
        terms, status = read_contract_document(path)
    except Exception:  # a damaged contract file is still kept as a reference
        terms, status = None, "reference"
    if terms is None or status == "reference":
        return DelayInput(documents=[_document(path, CONTRACT, "reference", "contract")])
    note = "contract_text" if status == "text" else "contract_read"
    return DelayInput(contract=terms, documents=[_document(path, CONTRACT, "read", note)])


def f2_from_tables(tables: Sequence[Table], filename: str) -> List[PaymentCertificate]:
    certificates: List[PaymentCertificate] = []
    for source, rows in tables:
        rows = [tuple(r) for r in rows if r is not None]
        if not rows:
            continue
        register = _register_rows(rows, source)
        if register:
            certificates.extend(register)
            continue
        certificate = _certificate_from_rows(rows, source)
        if certificate:
            certificates.append(certificate)
    fallback_period = period_from_text(Path(filename).stem)
    for certificate in certificates:
        if certificate.period is None and fallback_period and len(certificates) == 1:
            certificate.period = fallback_period
    return certificates


def _has(text: str, words: Sequence[str]) -> bool:
    return any(word in text for word in words)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _filled(row: Sequence[Any], width: int) -> List[str]:
    """Row labels with merged-cell gaps filled from the left."""
    out: List[str] = []
    last = ""
    for index in range(width):
        value = _norm(row[index]) if index < len(row) else ""
        if value:
            last = value
        out.append(value or last)
    return out


def _amount_header(rows: List[Sequence[Any]]) -> Optional[Tuple[int, List[str]]]:
    for index, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        cells = [_norm(c) for c in row]
        below_cells = [_norm(c) for c in rows[index + 1]] if index + 1 < len(rows) else []
        if sum(1 for c in cells if c) < 2:
            continue  # a title line, not a column header
        name_cols = {i for i, c in enumerate(cells) if c and _has(c, NAME_WORDS)}
        amount_cols = {i for i, c in enumerate(cells) if c and _has(c, AMOUNT_WORDS) and not _has(c, UNIT_WORDS)}
        amount_cols |= {i for i, c in enumerate(below_cells) if c and _has(c, AMOUNT_WORDS) and not _has(c, UNIT_WORDS)}
        if not name_cols or not (amount_cols - name_cols):
            continue
        width = max(len(r) for r in rows[max(0, index - 1):index + 2])
        above = _filled(rows[index - 1], width) if index > 0 else [""] * width
        below_row = rows[index + 1] if index + 1 < len(rows) else ()
        below = [_norm(below_row[i]) if i < len(below_row) else "" for i in range(width)]
        own = [_norm(row[i]) if i < len(row) else "" for i in range(width)]
        own_filled = _filled(row, width)
        labels = []
        for i in range(width):
            # A grouped header ("Hesabat dövründə") sits above or in this row;
            # the sub-header ("Məbləğ") sits in this row or below it.
            labels.append(" ".join(part for part in (above[i], own[i] or own_filled[i], below[i]) if part))
        return index, labels
    return None


def _classify_columns(labels: List[str]) -> Dict[str, Optional[int]]:
    amount_cols = [i for i, label in enumerate(labels) if _has(label, AMOUNT_WORDS) and not _has(label, UNIT_WORDS)]
    period = cumulative = None
    plain: List[int] = []
    for i in amount_cols:
        label = labels[i]
        if _has(label, CUMULATIVE_WORDS):
            cumulative = i if cumulative is None else cumulative
        elif _has(label, PERIOD_WORDS):
            period = i if period is None else period
        elif not _has(label, CONTRACT_WORDS):
            plain.append(i)
    if period is None and plain:
        # Prefer the total before VAT when the form has both.
        before_vat = [i for i in plain if not (_has(labels[i], VAT_WORDS) and _has(labels[i], WITH_WORDS))]
        period = (before_vat or plain)[-1]
    return {"period": period, "cumulative": cumulative}


def _row_text(row: Sequence[Any]) -> str:
    return " ".join(_norm(c) for c in row if isinstance(c, str) and _norm(c))


def _is_column_number_row(row: Sequence[Any]) -> bool:
    numbers = [parse_number(c) for c in row if c not in (None, "")]
    return len(numbers) >= 4 and all(n is not None and float(n).is_integer() and 0 < n <= 40 for n in numbers)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(1.0, abs(b) * 0.01)


def _overall_total(totals: List[tuple], line_sum: Optional[float]) -> tuple:
    """Pick the certificate total when a works table has section subtotals.

    The overall total is normally the last total row: it equals the sum of the
    work lines or of the subtotals above it. When every total row is a section
    subtotal (they add up to the work lines), their sum is the certificate.
    """
    if not totals:
        return (round(line_sum, 2) if line_sum is not None else None), None
    if len(totals) == 1:
        return totals[0]
    last_value, last_cumulative = totals[-1]
    earlier = sum(value for value, _ in totals[:-1])
    if _close(last_value, earlier) or (line_sum is not None and _close(last_value, line_sum)):
        return last_value, last_cumulative
    everything = sum(value for value, _ in totals)
    if line_sum is not None and _close(everything, line_sum):
        cumulatives = [c for _, c in totals]
        return round(everything, 2), (round(sum(cumulatives), 2) if all(c is not None for c in cumulatives) else None)
    return last_value, last_cumulative


def _certificate_from_rows(rows: List[Sequence[Any]], source: str) -> Optional[PaymentCertificate]:
    header = _amount_header(rows)
    if not header:
        return None
    header_index, labels = header
    columns = _classify_columns(labels)
    period_col = columns["period"]
    if period_col is None:
        return None
    cumulative_col = columns["cumulative"]
    with_vat = None
    totals: List[tuple] = []  # (value, cumulative) of each total row, in order
    line_sum = 0.0
    lines = 0
    for row in rows[header_index + 1:]:
        if _is_column_number_row(row):
            continue
        text = _row_text(row)
        value = parse_number(row[period_col]) if period_col < len(row) else None
        starts_total = any(_norm(c).startswith(TOTAL_WORDS) for c in row if isinstance(c, str))
        if starts_total or (_has(text, VAT_WORDS) and value is not None):
            if value is None:
                continue
            if _has(text, VAT_WORDS):
                if _has(text, WITH_WORDS):
                    with_vat = value  # the last VAT-inclusive line is the overall one
                continue  # a VAT-only line is not the works total
            cumulative = None
            if cumulative_col is not None and cumulative_col < len(row):
                cumulative = parse_number(row[cumulative_col])
            totals.append((value, cumulative))
            continue
        if value is not None and text:
            line_sum += value
            lines += 1
    amount, cumulative = _overall_total(totals, line_sum if lines else None)
    if amount is None or amount <= 0:
        return None
    head_rows = rows[:header_index]
    return PaymentCertificate(
        source=source,
        period=_period_from_rows(head_rows),
        number=_number_from_rows(head_rows),
        amount=amount,
        amount_with_vat=with_vat,
        cumulative=cumulative,
        line_count=lines,
    )


def _register_rows(rows: List[Sequence[Any]], source: str) -> List[PaymentCertificate]:
    """A summary sheet: one row per F2 with its period and amount."""
    for index, row in enumerate(rows[:20]):
        cells = [_norm(c) for c in row]
        date_col = next((i for i, c in enumerate(cells) if c and _has(c, DATE_WORDS) and not _has(c, AMOUNT_WORDS)), None)
        if date_col is None:
            continue
        if any(c and _has(c, NAME_WORDS) and not _has(c, ("akt", "f2", "forma")) for c in cells):
            return []  # a works list, not a register
        columns = _classify_columns(cells)
        period_col = columns["period"]
        if period_col is None or period_col == date_col:
            continue
        number_col = next((i for i, c in enumerate(cells) if c and not _has(c, AMOUNT_WORDS) and (c in {"no", "nomre", "number"} or c.startswith(("akt", "f2", "certificate")))), None)
        vat_col = next((i for i, c in enumerate(cells) if c and _has(c, AMOUNT_WORDS) and _has(c, VAT_WORDS) and _has(c, WITH_WORDS)), None)
        if vat_col == period_col:
            vat_col = None
        out: List[PaymentCertificate] = []
        for data in rows[index + 1:]:
            period = parse_date(data[date_col]) if date_col < len(data) else None
            if period is None and date_col < len(data):
                period = period_from_text(_text(data[date_col]))
            value = parse_number(data[period_col]) if period_col < len(data) else None
            if period is None or value is None or value <= 0:
                continue
            cumulative = None
            if columns["cumulative"] is not None and columns["cumulative"] < len(data):
                cumulative = parse_number(data[columns["cumulative"]])
            number = _text(data[number_col]).strip() if number_col is not None and number_col < len(data) else None
            with_vat = parse_number(data[vat_col]) if vat_col is not None and vat_col < len(data) else None
            out.append(PaymentCertificate(source=source, period=_month_end(period), number=number or None,
                                          amount=value, amount_with_vat=with_vat, cumulative=cumulative))
        if out:
            return out
    return []


# ------------------------------------------------------------ periods etc.
def _month_end(value: date) -> date:
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


_DATE_IN_TEXT = re.compile(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})")
_ISO_IN_TEXT = re.compile(r"(20\d\d)-(\d{1,2})-(\d{1,2})")
_YEAR_MONTH = re.compile(r"(20\d\d)[._\- ](0?[1-9]|1[0-2])(?!\d)")
_MONTH_YEAR = re.compile(r"(?<!\d)(0?[1-9]|1[0-2])[._\-](20\d\d)")


def _month_from_name(text: str) -> Optional[int]:
    for number, names in MONTHS.items():
        for name in names:
            if re.search(rf"(?<![a-zа-я]){name}", text):
                return number
    return None


def period_from_text(text: str) -> Optional[date]:
    """Period end from free text such as '01.05.2024-31.05.2024', 'may 2024' or 'F2_2024-05'."""
    raw = str(text or "").lower().translate({ord("ə"): "e", ord("ı"): "i", ord("ş"): "s", ord("ç"): "c", ord("ğ"): "g", ord("ö"): "o", ord("ü"): "u"})
    dates: List[date] = []
    for d, m, y in _DATE_IN_TEXT.findall(raw):
        try:
            dates.append(date(int(y), int(m), int(d)))
        except ValueError:
            continue
    for y, m, d in _ISO_IN_TEXT.findall(raw):
        try:
            dates.append(date(int(y), int(m), int(d)))
        except ValueError:
            continue
    if dates:
        return max(dates)
    year = re.search(r"20\d\d", raw)
    month = _month_from_name(raw)
    if year and month:
        return _month_end(date(int(year.group(0)), month, 1))
    match = _YEAR_MONTH.search(raw)
    if match:
        return _month_end(date(int(match.group(1)), int(match.group(2)), 1))
    match = _MONTH_YEAR.search(raw)
    if match:
        return _month_end(date(int(match.group(2)), int(match.group(1)), 1))
    return None


def _period_from_rows(rows: Sequence[Sequence[Any]]) -> Optional[date]:
    keyed: List[date] = []
    other: List[date] = []
    for row in rows:
        row_text = " ".join(_text(c) for c in row)
        is_period = _has(_norm(row_text), ("dovr", "period", "период", "donem", "hesabatay"))
        for cell in row:
            found = parse_date(cell) if isinstance(cell, (datetime, date)) else period_from_text(_text(cell))
            if found:
                (keyed if is_period else other).append(found)
        if is_period and not any(isinstance(c, (datetime, date)) for c in row):
            found = period_from_text(row_text)
            if found:
                keyed.append(found)
    if keyed:
        return max(keyed)
    return max(other) if other else None


_NUMBER = re.compile(r"(?:№|\bno\.?|\bnomre(?:si)?)\s*[:\-]?\s*([0-9][0-9A-Za-z/\-]*)", re.IGNORECASE)


def _number_from_rows(rows: Sequence[Sequence[Any]]) -> Optional[str]:
    for row in rows:
        for cell in row:
            text = _text(cell)
            norm = _norm(text)
            if not _has(norm, ("akt", "f2", "forma", "arayis", "акт", "справк", "certificate")):
                continue
            match = _NUMBER.search(text.replace("ö", "o"))
            if match:
                return match.group(1)
    return None


# -------------------------------------------------------------------- docx
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _cell_text(element: ET.Element) -> str:
    parts: List[str] = []
    for paragraph in element.iter(f"{_W}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_W}t"))
        if text.strip():
            parts.append(text.strip())
    return " ".join(parts)


def docx_tables(path: Path) -> List[Table]:
    """Word body as one table: paragraphs become one-cell rows, tables keep
    their columns (``gridSpan`` cells are padded so columns stay aligned)."""
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo("word/document.xml")
        if info.file_size > MAX_DOCX_XML_BYTES:
            raise ValueError("Word document is too large to read.")
        data = archive.read(info)
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError("Word documents with DOCTYPE/ENTITY declarations are not accepted.")
    root = ET.fromstring(data)
    body = root.find(f"{_W}body")
    rows: List[Sequence[Any]] = []
    if body is None:
        return [(path.name, rows)]
    for block in body:
        if block.tag == f"{_W}p":
            text = _cell_text(block)
            if text:
                rows.append((text,))
        elif block.tag == f"{_W}tbl":
            for tr in block.iter(f"{_W}tr"):
                cells: List[Any] = []
                for tc in tr.findall(f"{_W}tc"):
                    cells.append(_cell_text(tc))
                    span = tc.find(f"{_W}tcPr/{_W}gridSpan")
                    extra = int(span.get(f"{_W}val", "1")) - 1 if span is not None else 0
                    cells.extend([""] * max(0, min(extra, 50)))
                rows.append(tuple(cells))
    return [(path.name, rows)]
