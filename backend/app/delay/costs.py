"""Estimate (smeta) lines with accepted F-2 values, Forma-3 and contract terms.

* **Cost lines** come from the cumulative F-2 sheet ("Nakopitel", "Q.C",
  "smeta nakopitel") or any sheet whose header has a work name, a unit of
  measure and estimate / cumulative / reporting-month columns. Only lines with
  a unit of measure are work lines: section headers set the section (and the
  building when they name one) and "Cəmi" subtotals are never added.
* **Forma-3** is read from label rows (work done, advance received / withheld /
  remaining, payable) with cumulative and reporting-month columns.
* **Contract terms** come from a key/value sheet (the template's "Müqavilə"
  sheet or a contract's "Xüsusi şərtlər" table) and, as a best effort, from the
  text of a Word or text-based PDF contract. Values read from free text are
  marked so the report can say they need checking.
"""
from __future__ import annotations

import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .categories import building_of, categorize
from .model import ContractTerms, CostLine, DelayInput, F3Summary
from .reader import _norm, parse_date, parse_number

Table = Tuple[str, List[Sequence[Any]]]

HEADER_SCAN_ROWS = 60
MAX_TEXT_CHARS = 400_000

NAME_WORDS = ("isinadi", "islerinadi", "isinnovu", "isadi", "adi", "naimenovanie", "наименование", "name", "description",
              "workitem", "isinmezmunu", "mezmun", "isler")
UNIT_WORDS = ("olcuvahid", "vahid", "unit", "едизм", "единиц", "birim", "olcu")
PRICE_WORDS = ("qiymet", "price", "rate", "цена", "fiyat", "расценк")
AMOUNT_WORDS = ("mebleg", "deyer", "summa", "amount", "value", "cost", "сумма", "стоимость", "tutar", "bedel", "manat", "azn")
QTY_WORDS = ("miqdar", "hecm", "quantity", "qty", "количество", "объем", "kol", "miktar")
ESTIMATE_WORDS = ("smeta", "muqavile", "layihe", "estimate", "contract", "budget", "boq", "смет", "договор", "проект", "sozlesme")
CUMULATIVE_WORDS = ("kumulyativ", "cumulative", "evvelinden", "baslanmasindan", "baslangicdan", "nakopitel", "todate",
                    "сначала", "нарастающ", "cemiicra", "toplam")
PERIOD_WORDS = ("hesabatay", "hesabatdovr", "caridovr", "cariay", "budovr", "thisperiod", "thismonth", "dovrerzinde",
                "отчетн", "period", "month", "dovr", "ay")
BUILDING_WORDS = ("bina", "building", "blok", "korpus", "корпус", "obyekt")
SECTION_WORDS = ("bolme", "section", "раздел", "bolum", "grup", "group")
TOTAL_PREFIXES = ("cemi", "yekun", "total", "grand", "overall", "итого", "всего", "umumi", "toplam", "hamisi", "cem")
RESERVE_WORDS = ("ehtiyat", "gozlenilmez", "nezerdetutulmayan", "непредвид", "reserve", "contingenc", "резерв")
CUMULATIVE_SHEET_HINTS = ("nakopitel", "накопит", "qc", "kumulyativ", "cumulative", "smetanakopitel")


def _has(text: str, words: Sequence[str]) -> bool:
    return any(word in text for word in words)


def _cell(row: Sequence[Any], index: Optional[int]) -> Any:
    if index is None or index >= len(row):
        return None
    return row[index]


def _str(value: Any) -> str:
    return "" if value is None else str(value).strip()


# -------------------------------------------------------------- cost lines
def _labels(rows: List[Sequence[Any]], index: int) -> List[str]:
    """Header labels with a grouped header above and a sub-header below."""
    width = max(len(r) for r in rows[max(0, index - 1):index + 3])

    def filled(row: Sequence[Any]) -> List[str]:
        out, last = [], ""
        for i in range(width):
            value = _norm(row[i]) if i < len(row) else ""
            if value:
                last = value
            out.append(value or last)
        return out

    # The row above is a grouped header only when it has several cells; a
    # single title cell ("Bina-3") is not a column label.
    above_row = rows[index - 1] if index > 0 else ()
    above = filled(above_row) if sum(1 for c in above_row if _norm(c)) >= 2 else [""] * width
    own = filled(rows[index])
    own_raw = [_norm(rows[index][i]) if i < len(rows[index]) else "" for i in range(width)]
    below_row = rows[index + 1] if index + 1 < len(rows) else ()
    below = [_norm(below_row[i]) if i < len(below_row) else "" for i in range(width)]
    labels = []
    for i in range(width):
        parts = [above[i], own_raw[i] or own[i]]
        if below[i] and parse_number(below_row[i]) is None:
            parts.append(below[i])
        labels.append(" ".join(p for p in parts if p))
    return labels


def _cost_columns(labels: List[str]) -> Optional[Dict[str, Optional[int]]]:
    cols: Dict[str, Optional[int]] = {k: None for k in (
        "name", "unit", "building", "section", "estimate_qty", "estimate_value", "cum_qty", "cum_value", "period_qty", "period_value")}
    for i, label in enumerate(labels):
        if not label:
            continue
        if cols["unit"] is None and _has(label, UNIT_WORDS) and not _has(label, PRICE_WORDS) and not _has(label, AMOUNT_WORDS):
            cols["unit"] = i
            continue
        if _has(label, PRICE_WORDS) and not _has(label, ("mebleg", "summa", "amount", "сумма")):
            continue  # unit price
        is_amount = _has(label, AMOUNT_WORDS)
        is_qty = _has(label, QTY_WORDS) and not is_amount
        if is_amount or is_qty:
            kind = "value" if is_amount else "qty"
            if _has(label, CUMULATIVE_WORDS):
                group = "cum"
            elif _has(label, ESTIMATE_WORDS):
                group = "estimate"
            elif _has(label, PERIOD_WORDS):
                group = "period"
            else:
                continue
            key = f"{group}_{kind}"
            if cols[key] is None:
                cols[key] = i
            continue
        if cols["building"] is None and _has(label, BUILDING_WORDS) and not _has(label, NAME_WORDS):
            cols["building"] = i
        elif cols["section"] is None and _has(label, SECTION_WORDS) and not _has(label, NAME_WORDS):
            cols["section"] = i
        elif cols["name"] is None and _has(label, NAME_WORDS):
            cols["name"] = i
    if cols["name"] is None or cols["unit"] is None or cols["estimate_value"] is None:
        return None
    if cols["cum_value"] is None and cols["period_value"] is None:
        return None
    return cols


def _cost_header(rows: List[Sequence[Any]]) -> Optional[Tuple[int, Dict[str, Optional[int]]]]:
    for index, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        if sum(1 for c in row if _norm(c)) < 3:
            continue
        cols = _cost_columns(_labels(rows, index))
        if cols:
            return index, cols
    return None


def _is_number_row(row: Sequence[Any]) -> bool:
    numbers = [parse_number(c) for c in row if c not in (None, "")]
    return len(numbers) >= 4 and all(n is not None and float(n).is_integer() and 0 < n <= 40 for n in numbers)


def _starts_total(text: str) -> bool:
    return _norm(text).startswith(TOTAL_PREFIXES)


def cost_lines_from_rows(rows: List[Sequence[Any]], source: str) -> List[CostLine]:
    rows = [tuple(r) for r in rows if r is not None]
    header = _cost_header(rows)
    if not header:
        return []
    index, cols = header
    sheet = source.rsplit(":", 1)[-1]
    title = " ".join(_str(c) for r in rows[:index] for c in r if isinstance(c, str))
    building = building_of(sheet) or building_of(title)
    section: Optional[str] = None
    lines: List[CostLine] = []
    for row in rows[index + 1:]:
        if _is_number_row(row):
            continue
        name = _str(_cell(row, cols["name"]))
        unit = _str(_cell(row, cols["unit"]))
        row_building = _str(_cell(row, cols["building"])) if cols["building"] is not None else ""
        row_section = _str(_cell(row, cols["section"])) if cols["section"] is not None else ""
        if not name:
            continue
        if not unit:
            # A section header, a building header or a subtotal.
            if _starts_total(name) or _has(_norm(name), RESERVE_WORDS):
                continue
            named = building_of(name)
            if named:
                building = named
                rest = re.sub(r"(?i)\b(bina|blok|korpus|building|block)\s*[-№#:.]?\s*\d+[a-zа-я]?\b[\s.:,-]*", "", name).strip()
                if rest and categorize(rest):
                    section = rest
            else:
                section = name
            continue
        if _starts_total(name) or _has(_norm(name), RESERVE_WORDS):
            continue
        estimate_value = parse_number(_cell(row, cols["estimate_value"]))
        cum_value = parse_number(_cell(row, cols["cum_value"]))
        period_value = parse_number(_cell(row, cols["period_value"]))
        if not estimate_value and not cum_value and not period_value:
            continue
        line_building = building_of(row_building) or (row_building or None) if row_building else building
        line_section = row_section or section
        lines.append(CostLine(
            name=name,
            unit=unit,
            building=line_building,
            section=line_section,
            category=categorize(line_section, name),
            estimate_value=float(estimate_value or 0.0),
            estimate_qty=parse_number(_cell(row, cols["estimate_qty"])),
            cum_qty=parse_number(_cell(row, cols["cum_qty"])),
            cum_value=cum_value,
            period_qty=parse_number(_cell(row, cols["period_qty"])),
            period_value=period_value,
            source=source,
        ))
    return lines


def cost_lines_from_tables(tables: Sequence[Table]) -> List[CostLine]:
    """Cost lines of a workbook. A cumulative sheet ("Nakopitel") wins over
    the monthly F-2 sheets so the same works are not counted twice."""
    found: List[Tuple[str, List[CostLine]]] = []
    for source, rows in tables:
        lines = cost_lines_from_rows(list(rows), source)
        if lines:
            found.append((source, lines))
    if not found:
        return []
    cumulative = [(s, l) for s, l in found if _has(_norm(s.rsplit(":", 1)[-1]), CUMULATIVE_SHEET_HINTS)]
    if cumulative:
        found = cumulative
    else:
        with_cum = [(s, l) for s, l in found if any(x.cum_value is not None for x in l)]
        if with_cum:
            found = with_cum
    return [line for _, lines in found for line in lines]


# ------------------------------------------------------------------ Forma-3
F3_LABELS: Sequence[Tuple[str, Sequence[str]]] = (
    ("advance_remaining", ("qaliqavans", "avansqaliq", "avansinqaligi", "qaliq", "outstandingadvance", "remainingadvance", "остатокаванс")),
    ("advance_withheld", ("tutulmusavans", "avansintutul", "avansdantutul", "tutulanavans", "advancerecover", "advancewithheld",
                          "advancededuct", "удержаниеаванс", "зачетаванс")),
    ("advance_received", ("alinmisavans", "verilmisavans", "odenilmisavans", "avansodenisi", "avansalinib", "advancepaid",
                          "advancereceived", "полученныйаванс", "выплаченныйаванс")),
    ("payable", ("odenilecek", "odenmeli", "odenisemebleg", "payable", "amountdue", "коплате")),
    ("works", ("gorulmusis", "yerineyetirilmisis", "icraolunmusis", "worksdone", "workdone", "completedwork", "valueofwork",
               "выполненныхработ", "стоимостьработ")),
)


def _f3_columns(rows: List[Sequence[Any]]) -> Tuple[Optional[int], Optional[int], int]:
    for index, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        labels = [_norm(c) for c in row]
        cum = next((i for i, c in enumerate(labels) if c and _has(c, CUMULATIVE_WORDS)), None)
        period = next((i for i, c in enumerate(labels) if c and _has(c, ("hesabatay", "hesabatdovr", "cariay", "caridovr",
                                                                             "thisperiod", "thismonth", "отчетн")) and i != cum), None)
        if cum is not None or period is not None:
            return cum, period, index
    return None, None, -1


def f3_from_rows(rows: List[Sequence[Any]], source: str) -> Optional[F3Summary]:
    rows = [tuple(r) for r in rows if r is not None]
    sheet = _norm(source.rsplit(":", 1)[-1])
    text = " ".join(_norm(c) for r in rows[:HEADER_SCAN_ROWS] for c in r if isinstance(c, str))
    if not (_has(sheet, ("f3", "forma3", "форма3", "ks3", "кс3", "avans", "advance")) or "forma3" in text or "f3" in text
            or ("avans" in text and _has(text, ("odenilecek", "payable", "коплате")))):
        return None
    cum_col, period_col, header_index = _f3_columns(rows)
    out = F3Summary(source=source)
    hits = 0
    for row in rows[header_index + 1:]:
        label_cells = [c for c in row if isinstance(c, str) and _norm(c) and parse_number(c) is None]
        if not label_cells:
            continue
        label = _norm(" ".join(label_cells))
        key = next((k for k, words in F3_LABELS if _has(label, words)), None)
        if key is None:
            continue
        numbers = [(i, parse_number(c)) for i, c in enumerate(row) if not isinstance(c, str) or parse_number(c) is not None]
        numbers = [(i, n) for i, n in numbers if n is not None]
        if not numbers:
            continue
        cum = parse_number(_cell(row, cum_col)) if cum_col is not None else None
        period = parse_number(_cell(row, period_col)) if period_col is not None else None
        if cum is None and period is None:
            cum = numbers[0][1]
            period = numbers[1][1] if len(numbers) > 1 else None
        if key == "works":
            if _has(label, ("edvsiz", "withoutvat", "безндс")):
                continue  # Forma-3 values are compared with VAT
            out.works_cum = out.works_cum if out.works_cum is not None else cum
            out.works_period = out.works_period if out.works_period is not None else period
        elif key == "advance_received":
            out.advance_received = out.advance_received if out.advance_received is not None else (cum if cum is not None else period)
        elif key == "advance_withheld":
            out.advance_withheld_cum = out.advance_withheld_cum if out.advance_withheld_cum is not None else cum
            out.advance_withheld_period = out.advance_withheld_period if out.advance_withheld_period is not None else period
        elif key == "advance_remaining":
            out.advance_remaining = out.advance_remaining if out.advance_remaining is not None else (cum if cum is not None else period)
        elif key == "payable":
            out.payable_period = out.payable_period if out.payable_period is not None else (period if period is not None else cum)
        hits += 1
    if hits < 2:
        return None
    if out.advance_remaining is None and out.advance_received is not None and out.advance_withheld_cum is not None:
        out.advance_remaining = round(out.advance_received - out.advance_withheld_cum, 2)
    from .documents import _number_from_rows, _period_from_rows

    out.period = _period_from_rows(rows[:max(header_index, 0) + 1] or rows[:10])
    out.number = _number_from_rows(rows[:max(header_index, 0) + 1] or rows[:10])
    return out


def f3_from_tables(tables: Sequence[Table], filename: str) -> List[F3Summary]:
    from .documents import period_from_text

    found = [f for f in (f3_from_rows(list(rows), source) for source, rows in tables) if f]
    fallback = period_from_text(Path(filename).stem)
    for item in found:
        if item.period is None:
            item.period = fallback
    return found


# --------------------------------------------------------- contract terms
CONTRACT_ALIASES: Dict[str, Sequence[str]] = {
    "number": ("muqavilenomresi", "muqavileno", "muqavile№", "contractno", "contractnumber", "номердоговора", "sozlesmeno"),
    "signed": ("muqaviletarixi", "imzalanmatarixi", "contractdate", "signed", "датадоговора", "sozlesmetarihi"),
    "client": ("sifarisci", "client", "employer", "заказчик", "isveren"),
    "contractor": ("podratci", "contractor", "подрядчик", "yuklenici"),
    "partners": ("birlik", "consortium", "jointventure", "jv", "pay", "shares", "консорциум"),
    "subject": ("obyekt", "subject", "object", "predmet", "предмет", "layihe", "project"),
    "value_with_vat": ("muqavilemeblegi", "muqaviledeyeri", "contractvalue", "contractamount", "contractprice", "суммадоговора",
                       "стоимостьдоговора", "sozlesmebedeli"),
    "vat_rate_pct": ("edvderecesi", "edv%", "vatrate", "vat%", "ставкандс"),
    "start": ("baslamatarixi", "muqavilebaslangici", "startdate", "contractstart", "началоработ", "baslangictarihi"),
    "finish": ("bitmetarixi", "muqavilebitisi", "muqavilebitmetarixi", "completiondate", "contractfinish", "finishdate",
               "окончаниеработ", "bitistarihi"),
    "duration_months": ("muddet", "muddetay", "icramuddeti", "duration", "durationmonths", "срок", "sure"),
    "performance_guarantee_pct": ("icrateminati", "performanceguarantee", "performancebond", "обеспечениеисполнения", "71"),
    "advance_pct": ("avans%", "avansfaizi", "avans", "advance%", "advance", "аванс"),
    "advance_guarantee_months": ("avansteminati", "avansteminatinimuddeti", "advanceguarantee", "advancebond", "обеспечениеаванса", "131"),
    "payment_days": ("odenismuddeti", "paymentdays", "paymentterm", "срокоплаты"),
    "penalty_pct_per_day": ("cerime%gun", "gundelikcerime", "gecikmecerimesi", "cerime", "penaltyperday", "liquidateddamages",
                            "delaypenalty", "неустойка", "пеня", "281"),
    "penalty_cap_pct": ("cerimelimiti", "cerimehedd", "maksimumcerime", "penaltycap", "ldcap", "maximumpenalty", "лимитнеустойки"),
    "employer_obligations": ("sifariscininohdelikleri", "employerobligations", "обязанностизаказчика", "122"),
    "warranty_months": ("zemanet", "zemanetmuddeti", "warranty", "defectsliability", "гарантия"),
}
_DATE_FIELDS = {"signed", "start", "finish"}
_NUMBER_FIELDS = {"value_with_vat", "vat_rate_pct", "duration_months", "performance_guarantee_pct", "advance_pct",
                  "advance_guarantee_months", "payment_days", "penalty_pct_per_day", "penalty_cap_pct", "warranty_months"}


def _contract_key(text: str) -> Optional[str]:
    key = _norm(text)
    if not key:
        return None
    best: Optional[Tuple[int, str]] = None
    for field, aliases in CONTRACT_ALIASES.items():
        for alias in aliases:
            if key == alias or (len(alias) >= 4 and key.startswith(alias)) or (len(alias) >= 6 and alias in key):
                score = len(alias) + (100 if key == alias else 0)
                if best is None or score > best[0]:
                    best = (score, field)
    return best[1] if best else None


def contract_from_rows(rows: List[Sequence[Any]], source: str) -> ContractTerms:
    terms = ContractTerms()
    hits = 0
    for row in rows[:120]:
        cells = [c for c in row if c not in (None, "")]
        if len(cells) < 2:
            continue
        key = _contract_key(_str(cells[0]))
        if not key or getattr(terms, key) not in (None, ""):
            continue
        value = cells[1]
        if key in _DATE_FIELDS:
            parsed = parse_date(value)
            if parsed:
                setattr(terms, key, parsed)
                hits += 1
        elif key in _NUMBER_FIELDS:
            number = parse_number(value)
            if number is not None:
                if key.endswith("_pct") and 0 < number < 1 and key != "penalty_pct_per_day":
                    number *= 100  # 0.3 written as a fraction
                setattr(terms, key, number)
                hits += 1
        else:
            setattr(terms, key, _str(value))
            hits += 1
    if hits:
        terms.source = source
    return terms if hits >= 2 else ContractTerms()


def contract_from_tables(tables: Sequence[Table]) -> ContractTerms:
    terms = ContractTerms()
    for source, rows in tables:
        sheet = _norm(source.rsplit(":", 1)[-1])
        found = contract_from_rows(list(rows), source)
        if found.source and (_has(sheet, ("muqavile", "contract", "договор", "sozlesme", "xususisert", "specialcond")) or
                             sum(1 for v in vars(found).values() if v not in (None, "")) >= 4):
            terms.update(found)
    return terms


# A number written with spaces or dots as thousand separators and a comma or
# dot as the decimal mark.
_NUM = r"(\d{1,3}(?:[ . ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"


def _num(text: str) -> Optional[float]:
    return parse_number(text.replace(" ", " "))


def contract_from_text(text: str, source: str) -> ContractTerms:
    """Best-effort reading of key terms from contract text."""
    text = re.sub(r"\s+", " ", text or "")[:MAX_TEXT_CHARS]
    low = text.lower()
    terms = ContractTerms()

    match = re.search(r"müqavilə\s*(?:№|n[o°]\.?)\s*([0-9][0-9A-Za-z/\-]*)", low) or re.search(r"(?:contract|договор)\s*(?:№|no\.?)\s*([0-9][0-9A-Za-z/\-]*)", low)
    if match:
        terms.number = match.group(1)
    match = re.search(r"(\d{1,2}[./]\d{1,2}[./]20\d\d)", text)
    if match:
        terms.signed = parse_date(match.group(1))
    match = re.search(r"(?:ümumi\s+)?(?:müqavilə\s+)?(?:məbləğ|dəyər|qiymət)[^.;]{0,80}?" + _NUM + r"\s*(?:manat|azn)", low)
    if match:
        value = _num(match.group(1))
        if value and value > 1000:
            terms.value_with_vat = value
    match = re.search(r"(?:hər\s+gün|gününə|günü\s+üçün|gün\s+üçün|per\s+day|за\s+каждый\s+день)[^.;]{0,120}?" + _NUM + r"\s*%", low) \
        or re.search(_NUM + r"\s*%[^.;]{0,80}?(?:hər\s+gün|günü\s+üçün|gün\s+üçün|per\s+day|за\s+каждый\s+день)", low)
    if match:
        value = _num(match.group(1))
        if value is not None and 0 < value <= 1:
            terms.penalty_pct_per_day = value
    match = re.search(r"(?:cərimə|penalt|неустойк)[^.;]{0,200}?(?:maksimum|ən\s+çox|çox\s+olmamaqla|artıq\s+olmamaqla|həddi|cap|maximum|не\s+более)[^.;]{0,60}?" + _NUM + r"\s*%", low)
    if match:
        value = _num(match.group(1))
        if value is not None and 1 <= value <= 30:
            terms.penalty_cap_pct = value
    match = re.search(_NUM + r"\s*%[^.;]{0,40}?(?:həcmində\s+)?avans", low) or re.search(r"avans[^.;]{0,80}?" + _NUM + r"\s*%", low)
    if match:
        value = _num(match.group(1))
        if value is not None and 0 < value <= 50:
            terms.advance_pct = value
    match = re.search(r"avans[^.]{0,200}?təminat[^.]{0,160}?(\d{1,2})\s*(?:\(\w+\)\s*)?ay", low)
    if match:
        terms.advance_guarantee_months = float(match.group(1))
    match = re.search(r"(\d{1,3})\s*(?:\(\w+\)\s*)?iş\s+günü[^.;]{0,100}?ödən", low)
    if match:
        terms.payment_days = float(match.group(1))
    match = re.search(r"icra\s+təminat[^.;]{0,120}?" + _NUM + r"\s*%", low)
    if match:
        value = _num(match.group(1))
        if value is not None and 0 < value <= 30:
            terms.performance_guarantee_pct = value
    if any(v not in (None, "") for v in vars(terms).values()):
        terms.source = f"{source} (text)"
    return terms


def docx_text(path: Path) -> str:
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo("word/document.xml")
        if info.file_size > 20 * 1024 * 1024:
            raise ValueError("document.xml is too large")
        data = archive.read(info)
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError("DTDs are not allowed in .docx files")
    root = ET.fromstring(data)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    return "\n".join("".join(t.text or "" for t in p.iter(f"{ns}t")) for p in root.iter(f"{ns}p"))


def pdf_text(path: Path, max_pages: int = 40) -> str:
    """Text of a text-based PDF; scanned PDFs give an empty string."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return ""
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages[:max_pages]:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # a broken page must not stop the rest
            continue
    return "\n".join(parts)


def read_contract_document(path: Path) -> Tuple[ContractTerms, str]:
    """Contract terms from a Word / PDF contract and how they were found:
    ``read`` (from a terms table), ``text`` (free text, to be checked) or
    ``reference`` (nothing readable, e.g. a scanned PDF or an image)."""
    suffix = path.suffix.lower()
    if suffix == ".docx":
        from .documents import docx_tables

        terms = contract_from_tables(docx_tables(path))
        status = "read" if terms.source else "reference"
        text_terms = contract_from_text(docx_text(path), path.name)
        if text_terms.source:
            terms.update(text_terms)
            status = "read" if status == "read" else "text"
        return terms, status
    if suffix == ".pdf":
        text = pdf_text(path)
        if len(text.strip()) < 200:
            return ContractTerms(), "reference"
        terms = contract_from_text(text, path.name)
        return terms, ("text" if terms.source else "reference")
    return ContractTerms(), "reference"


def extract_costs(tables: Sequence[Table], filename: str) -> DelayInput:
    """Cost lines, Forma-3 and contract terms found in a workbook."""
    result = DelayInput()
    result.cost_lines = cost_lines_from_tables(tables)
    result.f3 = f3_from_tables(tables, filename)
    result.contract = contract_from_tables(tables)
    return result
