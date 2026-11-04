"""Readers that turn uploaded schedule/progress files into ``DelayInput``.

Supported inputs:

* DevBareun delay-analysis Excel template (and most plan/actual workbooks:
  sheets are detected by their column headers, not only by their names)
* CSV with one plan/actual table
* Primavera P6 XER export (TASK + TASKPRED + PROJECT tables)
* MS Project XML export (baseline, actual and predecessor links)

Column headers are matched in English, Azerbaijani, Turkish and Russian.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .model import Activity, DelayEvent, DelayInput, MonthlyProgress, ProjectInfo

MAX_ROWS_PER_SHEET = 20000

_TRANSLIT = str.maketrans({"ə": "e", "ı": "i", "ş": "s", "ç": "c", "ğ": "g", "ö": "o", "ü": "u", "İ": "i", "Ə": "e"})


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower().translate(_TRANSLIT)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9а-яё%]+", "", text)


# Field -> header aliases (normalised with _norm before comparison).
ACTIVITY_ALIASES: Dict[str, Sequence[str]] = {
    "id": ("activityid", "id", "taskid", "code", "activitycode", "isid", "iskodu", "iskod", "kod", "№", "no", "sira", "faaliyetid", "kodработы", "кодработы"),
    "name": ("activityname", "activity", "taskname", "task", "name", "description", "isinadi", "isadi", "is", "isler", "faaliyet", "faaliyetadi", "naimenovanie", "наименование", "работа"),
    "wbs": ("wbs", "section", "workpackage", "bolme", "blok", "block", "building", "zone", "obyekt", "obyekt", "bolum", "раздел"),
    "planned_start": ("plannedstart", "baselinestart", "planstart", "start", "planlananbaslangic", "planbaslangic", "planbaslangici", "planbaslama", "baslangicplan", "началоплан", "плановоеначало"),
    "planned_finish": ("plannedfinish", "baselinefinish", "planfinish", "finish", "plannedend", "planbitis", "planlananbitis", "planbitme", "bitisplan", "окончаниеплан", "плановоеокончание"),
    "weight": ("weight", "weight%", "ceki", "ceki%", "agirlik", "agirlik%", "plannedcost", "budget", "contractvalue", "value", "amount", "deyer", "mebleg", "вес", "стоимость"),
    "predecessors": ("predecessors", "predecessor", "predecessorids", "oncul", "onculler", "onculisler", "evvelkiisler", "предшественники"),
    "actual_start": ("actualstart", "faktikibaslangic", "faktikibaslama", "fiilibaslangic", "gercekbaslangic", "фактическоеначало", "началофакт"),
    "actual_finish": ("actualfinish", "faktikibitis", "faktikibitme", "fiilibitis", "gercekbitis", "фактическоеокончание", "окончаниефакт"),
    "forecast_finish": ("forecastfinish", "expectedfinish", "actualfinishforecastfinish", "proqnozbitis", "proqnozlasdirilanbitis", "tahminibitis", "прогнозокончания"),
    "progress": ("actualprogress%", "actualprogress", "actual%", "%complete", "percentcomplete", "complete%", "progress", "progress%", "icra%", "icra", "faktikiicra%", "faktikiicra", "faktiki%", "tamamlanma%", "gerceklesme%", "fiili%", "выполнение%", "факт%"),
    "planned_progress": ("plannedprogress%", "planned%", "plan%", "planicra%", "planlanan%", "план%"),
    "status_date": ("statusdate", "datadate", "hesabattarixi", "statustarixi", "durumtarihi"),
    "delay_days": ("delaydays", "gecikmegun", "gecikme", "gecikmegunu", "gecikmesi", "задержкадней"),
}

EVENT_ALIASES: Dict[str, Sequence[str]] = {
    "id": ("eventid", "delayid", "id", "no", "hadiseid", "olayid", "№"),
    "description": ("event", "delayevent", "description", "hadise", "gecikmehadisesi", "olay", "aciklama", "tesvir", "событие"),
    "start": ("start", "eventstart", "from", "baslangic", "basladi", "начало"),
    "finish": ("finish", "end", "eventfinish", "to", "bitis", "bitdi", "окончание"),
    "activity_ids": ("affectedactivities", "activityids", "activities", "activityid", "tesiretdiyiisler", "etkilenenisler", "isler", "работы"),
    "cause": ("cause", "causecategory", "category", "reason", "sebeb", "sebebkateqoriyasi", "sebep", "kateqoriya", "причина"),
    "responsible": ("responsible", "responsibleparty", "party", "liability", "mesuliyyet", "mesultaraf", "mesul", "sorumlu", "ответственный"),
    "notes": ("notes", "qeyd", "qeydler", "not", "notlar", "примечание"),
}

MONTHLY_ALIASES: Dict[str, Sequence[str]] = {
    "period": ("period", "month", "date", "ay", "dovr", "tarix", "donem", "месяц", "период"),
    "planned": ("plannedcumulative%", "plannedcumulative", "planned%", "plan%", "planned", "plan", "plankumulyativ%", "planicra%", "план%"),
    "actual": ("actualcumulative%", "actualcumulative", "actual%", "fakt%", "actual", "faktiki", "faktiki%", "faktikikumulyativ%", "icra%", "факт%"),
}

PROJECT_FIELD_ALIASES: Dict[str, Sequence[str]] = {
    "name": ("projectname", "project", "name", "layihe", "layiheninadi", "layiheadi", "proje", "projeadi", "объект", "проект"),
    "client": ("client", "employer", "owner", "sifarisci", "isveren", "заказчик"),
    "contractor": ("contractor", "podratci", "yuklenici", "подрядчик"),
    "location": ("location", "unvan", "yer", "konum", "место"),
    "contract_start": ("contractstart", "startdate", "projectstart", "muqavilebaslangici", "muqavilebaslangic", "baslangictarixi", "sozlesmebaslangic", "началодоговора"),
    "contract_finish": ("contractfinish", "completiondate", "contractcompletion", "finishdate", "muqavilebitisi", "muqavilebitis", "bitistarixi", "sozlesmebitis", "окончаниедоговора"),
    "data_date": ("datadate", "statusdate", "reportdate", "cutoffdate", "hesabattarixi", "statustarixi", "raportarihi", "отчетнаядата"),
    "currency": ("currency", "valyuta", "parabirimi", "валюта"),
}

PARTY_ALIASES = {
    "employer": ("employer", "client", "owner", "sifarisci", "isveren", "заказчик", "e"),
    "contractor": ("contractor", "podratci", "yuklenici", "подрядчик", "c"),
    "neutral": ("neutral", "neytral", "forcemajeure", "fors", "forsmajor", "weather", "hava", "notr", "нейтральный", "n", "third", "thirdparty", "ucunc", "ucunctereftaraf"),
}


# ---------------------------------------------------------------- primitives
def parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if 20000 < number < 80000:  # Excel serial day
            return date(1899, 12, 30) + timedelta(days=int(number))
        return None
    text = str(value).strip()
    if not text or text.lower() in {"-", "n/a", "na", "none", "null", "yoxdur"}:
        return None
    text = text.split("T")[0] if re.match(r"^\d{4}-\d{2}-\d{2}T", text) else text
    text = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?$", "", text)
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%y", "%d/%m/%y", "%d-%b-%y", "%d-%b-%Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace(" ", "")
    if not text:
        return None
    percent = text.endswith("%")
    text = text.rstrip("%")
    if text.count(",") and text.count("."):
        text = text.replace(",", "") if text.rfind(".") > text.rfind(",") else text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+", text):
        text = text.replace(",", "")  # 1,500 / 2,450,000 = thousands separators
    elif text.count(",") == 1:
        text = text.replace(",", ".")  # 12,5 = decimal comma
    try:
        number = float(text)
    except ValueError:
        return None
    return number if not percent else number


def _split_ids(value: Any) -> List[str]:
    """Split a predecessor / activity list cell into raw ID tokens.

    Relationship types and lags (``A100FS+2d``) are resolved later against
    the real activity IDs (see ``resolve_id``), because IDs such as ``B-20``
    or ``STAFF`` would otherwise be cut by a suffix rule.
    """
    if value is None or value == "":
        return []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [_clean_id(value)]
    tokens = re.split(r"[;,\s]+", str(value).strip())
    return [_clean_id(token) for token in tokens if token.strip()]


_RELATION_SUFFIX = re.compile(r"^(.+?)(?:FS|SS|FF|SF)?(?:[+-]\d+(?:\.\d+)?[dwhgDWHG]?)?$")
_RELATION_ONLY = re.compile(r"^(.+?)(FS|SS|FF|SF)$", re.IGNORECASE)


def resolve_id(token: str, known: Iterable[str]) -> Optional[str]:
    """Return the activity ID a predecessor token refers to, if any."""
    known_set = known if isinstance(known, (set, frozenset, dict)) else set(known)
    if token in known_set:
        return token
    for pattern in (_RELATION_ONLY, _RELATION_SUFFIX):
        match = pattern.match(token)
        if match and match.group(1) in known_set:
            return match.group(1)
    return None


def _clean_id(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0+", text):  # numeric cells read as floats (xlrd/CSV)
        text = text.split(".")[0]
    return text


def _party(value: Any) -> Optional[str]:
    key = _norm(value)
    if not key:
        return None
    for party, aliases in PARTY_ALIASES.items():
        if key in aliases or any(alias in key for alias in aliases if len(alias) > 3):
            return party
    return None


# ----------------------------------------------------------- table detection
def _match_columns(headers: Sequence[Any], aliases: Dict[str, Sequence[str]]) -> Dict[str, int]:
    """Map fields to column indexes.

    Exact header matches win first. Remaining columns are matched by the
    longest alias contained in the header, across all fields at once, so
    "Faktiki başlanğıc / Actual Start" goes to actual_start ("actualstart")
    and never to planned_start ("start").
    """
    normalised = [_norm(h) for h in headers]
    mapping: Dict[str, int] = {}
    used: set[int] = set()
    for field_name, names in aliases.items():
        for index, header in enumerate(normalised):
            if index not in used and header and header in names:
                mapping[field_name] = index
                used.add(index)
                break
    candidates: List[Tuple[int, str, int]] = []
    for field_name, names in aliases.items():
        if field_name in mapping:
            continue
        for index, header in enumerate(normalised):
            if index in used or not header:
                continue
            for alias in names:
                if len(alias) >= 5 and alias in header:
                    candidates.append((len(alias), field_name, index))
    for _, field_name, index in sorted(candidates, key=lambda c: (-c[0], c[2])):
        if field_name not in mapping and index not in used:
            mapping[field_name] = index
            used.add(index)
    return mapping


def _match_key(key: str, aliases: Dict[str, Sequence[str]]) -> Optional[str]:
    for field_name, names in aliases.items():
        if key in names:
            return field_name
    best: Tuple[int, Optional[str]] = (0, None)
    for field_name, names in aliases.items():
        for alias in names:
            if len(alias) >= 5 and alias in key and len(alias) > best[0]:
                best = (len(alias), field_name)
    return best[1]


def _find_header(rows: List[Sequence[Any]], aliases: Dict[str, Sequence[str]], required: Iterable[str]) -> Tuple[int, Dict[str, int]] | None:
    required = list(required)
    for index, row in enumerate(rows[:15]):
        mapping = _match_columns(row, aliases)
        if all(name in mapping for name in required):
            return index, mapping
    return None


def _cell(row: Sequence[Any], mapping: Dict[str, int], key: str) -> Any:
    index = mapping.get(key)
    if index is None or index >= len(row):
        return None
    return row[index]


def _scale_percent(values: List[Optional[float]]) -> List[Optional[float]]:
    present = [v for v in values if v is not None]
    if present and max(present) <= 1.0 and any(0 < v < 1 for v in present):
        return [None if v is None else v * 100 for v in values]
    return values


def _clamp_pct(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return max(0.0, min(100.0, value))


# -------------------------------------------------------------- table parsers
def _activities_from_table(rows: List[Sequence[Any]], source: str, result: DelayInput) -> bool:
    found = _find_header(rows, ACTIVITY_ALIASES, ("id",))
    if not found:
        found = _find_header(rows, ACTIVITY_ALIASES, ("name",))
    if not found:
        return False
    header_index, mapping = found
    has_plan = "planned_start" in mapping and "planned_finish" in mapping
    has_actual = any(k in mapping for k in ("actual_start", "actual_finish", "progress", "forecast_finish"))
    if not has_plan and not has_actual:
        return False
    data_rows = [r for r in rows[header_index + 1:header_index + 1 + MAX_ROWS_PER_SHEET] if any(c not in (None, "") for c in r)]
    progress_values = _scale_percent([parse_number(_cell(r, mapping, "progress")) for r in data_rows])
    weight_values = [parse_number(_cell(r, mapping, "weight")) for r in data_rows]
    added = 0
    for position, row in enumerate(data_rows):
        raw_id = _cell(row, mapping, "id")
        name = _cell(row, mapping, "name")
        if raw_id in (None, "") and name in (None, ""):
            continue
        activity_id = _clean_id(raw_id) if raw_id not in (None, "") else f"ROW-{position + 1}"
        if _norm(activity_id) in {"total", "cemi", "toplam", "итого"}:
            continue
        activity = Activity(
            id=activity_id,
            name=str(name).strip() if name not in (None, "") else activity_id,
            wbs=(str(_cell(row, mapping, "wbs")).strip() or None) if _cell(row, mapping, "wbs") not in (None, "") else None,
            planned_start=parse_date(_cell(row, mapping, "planned_start")),
            planned_finish=parse_date(_cell(row, mapping, "planned_finish")),
            weight=weight_values[position] if weight_values[position] and weight_values[position] > 0 else None,
            predecessors=_split_ids(_cell(row, mapping, "predecessors")),
            actual_start=parse_date(_cell(row, mapping, "actual_start")),
            actual_finish=parse_date(_cell(row, mapping, "actual_finish")),
            forecast_finish=parse_date(_cell(row, mapping, "forecast_finish")),
            progress=_clamp_pct(progress_values[position]),
            source=source,
        )
        # Some workbooks use one "Actual Finish / Forecast Finish" column. A
        # finished activity's forecast is its actual finish; an unfinished
        # activity can only have a forecast.
        if activity.progress is not None and activity.progress >= 100 and not activity.actual_finish and activity.forecast_finish:
            activity.actual_finish = activity.forecast_finish
        if activity.actual_finish and activity.progress is not None and activity.progress < 100:
            activity.forecast_finish = activity.forecast_finish or activity.actual_finish
            activity.actual_finish = None
        result.activities.append(activity)
        added += 1
    status_dates = [d for d in (parse_date(_cell(r, mapping, "status_date")) for r in data_rows) if d]
    if status_dates and not result.project.data_date:
        result.project.data_date = max(status_dates)
    if added:
        result.sources.append(source)
    return added > 0


def _events_from_table(rows: List[Sequence[Any]], source: str, result: DelayInput) -> bool:
    found = _find_header(rows, EVENT_ALIASES, ("description", "responsible"))
    if not found:
        found = _find_header(rows, EVENT_ALIASES, ("description", "cause", "start"))
    if not found:
        return False
    header_index, mapping = found
    added = 0
    for position, row in enumerate(rows[header_index + 1:header_index + 1 + MAX_ROWS_PER_SHEET]):
        description = _cell(row, mapping, "description")
        if description in (None, ""):
            continue
        raw_party = _cell(row, mapping, "responsible")
        party = _party(raw_party)
        if raw_party not in (None, "") and party is None:
            result.warnings.append(f"{source}: responsible party '{raw_party}' was not recognised; use Employer, Contractor or Neutral.")
        result.events.append(
            DelayEvent(
                id=_clean_id(_cell(row, mapping, "id") or f"E{position + 1}"),
                description=str(description).strip(),
                start=parse_date(_cell(row, mapping, "start")),
                finish=parse_date(_cell(row, mapping, "finish")),
                activity_ids=_split_ids(_cell(row, mapping, "activity_ids")),
                cause=(str(_cell(row, mapping, "cause")).strip() or None) if _cell(row, mapping, "cause") not in (None, "") else None,
                responsible=party,
                notes=(str(_cell(row, mapping, "notes")).strip() or None) if _cell(row, mapping, "notes") not in (None, "") else None,
            )
        )
        added += 1
    if added:
        result.sources.append(source)
    return added > 0


def _monthly_from_table(rows: List[Sequence[Any]], source: str, result: DelayInput) -> bool:
    found = _find_header(rows, MONTHLY_ALIASES, ("period", "planned", "actual"))
    if not found:
        return False
    header_index, mapping = found
    if _find_header(rows[header_index:header_index + 1], ACTIVITY_ALIASES, ("id",)):
        return False
    data_rows = rows[header_index + 1:header_index + 1 + MAX_ROWS_PER_SHEET]
    planned = _scale_percent([parse_number(_cell(r, mapping, "planned")) for r in data_rows])
    actual = _scale_percent([parse_number(_cell(r, mapping, "actual")) for r in data_rows])
    added = 0
    for position, row in enumerate(data_rows):
        period = parse_date(_cell(row, mapping, "period"))
        if not period:
            continue
        result.monthly.append(MonthlyProgress(period=period, planned=_clamp_pct(planned[position]), actual=_clamp_pct(actual[position])))
        added += 1
    if added:
        result.sources.append(source)
    return added > 0


def _project_from_table(rows: List[Sequence[Any]], source: str, result: DelayInput) -> bool:
    """Key/value sheet: first column = field name, second = value."""
    hits = 0
    info = result.project
    for row in rows[:60]:
        if len(row) < 2:
            continue
        key = _norm(row[0])
        value = row[1]
        if not key or value in (None, ""):
            continue
        field_name = _match_key(key, PROJECT_FIELD_ALIASES)
        if not field_name:
            continue
        if field_name in {"contract_start", "contract_finish", "data_date"}:
            parsed = parse_date(value)
            if parsed:
                setattr(info, field_name, parsed)
                hits += 1
        else:
            setattr(info, field_name, str(value).strip())
            hits += 1
    if hits:
        result.sources.append(source)
    return hits >= 2


_EVENT_SHEET_HINTS = ("gecikme", "hadise", "event", "delay", "olay", "claim", "событ")


def _looks_like_events(source: str, rows: List[Sequence[Any]]) -> bool:
    """An events table has a description + responsible/cause column and no
    progress or actual-date columns; a sheet named like an event log wins."""
    sheet = _norm(source.rsplit(":", 1)[-1])
    if any(hint in sheet for hint in _EVENT_SHEET_HINTS):
        return True
    for row in rows[:15]:
        events = _match_columns(row, EVENT_ALIASES)
        if "description" in events and ("responsible" in events or "cause" in events):
            activity = _match_columns(row, ACTIVITY_ALIASES)
            return not any(key in activity for key in ("progress", "actual_start", "actual_finish", "forecast_finish", "planned_progress"))
    return False


def parse_tables(tables: List[Tuple[str, List[Sequence[Any]]]]) -> DelayInput:
    result = DelayInput()
    for source, rows in tables:
        if not rows:
            continue
        if _looks_like_events(source, rows) and _events_from_table(rows, source, result):
            continue
        if _activities_from_table(rows, source, result):
            continue
        if _monthly_from_table(rows, source, result):
            continue
        _project_from_table(rows, source, result)
    _merge_duplicate_activities(result)
    return result


def _merge_duplicate_activities(result: DelayInput) -> None:
    """Baseline and actual sheets list the same IDs; merge them into one row."""
    merged: Dict[str, Activity] = {}
    order: List[str] = []
    for activity in result.activities:
        existing = merged.get(activity.id)
        if existing is None:
            merged[activity.id] = activity
            order.append(activity.id)
            continue
        for attr in vars(activity):
            value = getattr(activity, attr)
            current = getattr(existing, attr)
            if value not in (None, "", []) and (current in (None, "", []) or (attr == "name" and current == existing.id)):
                setattr(existing, attr, value)
    result.activities = [merged[key] for key in order]


# ------------------------------------------------------------- file readers
def read_workbook(path: Path) -> DelayInput:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        tables: List[Tuple[str, List[Sequence[Any]]]] = []
        for sheet in workbook.worksheets:
            if _norm(sheet.title) in {"readme", "lists", "instructions", "telimat", "melumat"}:
                continue
            rows = [tuple(r) for r in sheet.iter_rows(max_row=MAX_ROWS_PER_SHEET + 20, values_only=True)]
            tables.append((f"{path.name}:{sheet.title}", rows))
    finally:
        workbook.close()
    return parse_tables(tables)


def read_xls(path: Path) -> DelayInput:
    import xlrd  # type: ignore

    book = xlrd.open_workbook(str(path))
    tables = []
    for sheet in book.sheets():
        rows = []
        for r in range(min(sheet.nrows, MAX_ROWS_PER_SHEET + 20)):
            row = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    row.append(xlrd.xldate.xldate_as_datetime(cell.value, book.datemode))
                else:
                    row.append(cell.value)
            rows.append(tuple(row))
        tables.append((f"{path.name}:{sheet.name}", rows))
    return parse_tables(tables)


def read_csv(path: Path) -> DelayInput:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1254", "cp1251", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = [tuple(r) for r in csv.reader(io.StringIO(text), dialect)]
    return parse_tables([(path.name, rows)])


def read_xer(path: Path) -> DelayInput:
    """Primavera P6 XER: tab-separated %T (table), %F (fields), %R (rows)."""
    text = path.read_bytes().decode("cp1252", errors="replace")
    tables: Dict[str, List[Dict[str, str]]] = {}
    current: Optional[str] = None
    fields: List[str] = []
    for line in text.splitlines():
        parts = line.split("\t")
        tag = parts[0]
        if tag == "%T":
            current = parts[1].strip() if len(parts) > 1 else None
            tables.setdefault(current or "", [])
        elif tag == "%F":
            fields = [p.strip() for p in parts[1:]]
        elif tag == "%R" and current:
            tables[current].append(dict(zip(fields, parts[1:])))
    result = DelayInput(sources=[path.name])
    project_rows = tables.get("PROJECT") or []
    if project_rows:
        project = project_rows[0]
        result.project.name = project.get("proj_short_name") or result.project.name
        result.project.contract_start = parse_date(project.get("plan_start_date"))
        result.project.contract_finish = parse_date(project.get("scd_end_date") or project.get("plan_end_date"))
        result.project.data_date = parse_date(project.get("last_recalc_date") or project.get("next_data_date"))
    wbs_names = {row.get("wbs_id"): row.get("wbs_name") for row in tables.get("PROJWBS") or []}
    task_code_by_id: Dict[str, str] = {}
    for task in tables.get("TASK") or []:
        if task.get("task_type") in {"TT_LOE", "TT_WBS"}:
            continue
        code = task.get("task_code") or task.get("task_id") or ""
        task_code_by_id[task.get("task_id") or code] = code
        progress = parse_number(task.get("phys_complete_pct"))
        if task.get("status_code") == "TK_Complete":
            progress = 100.0
        result.activities.append(
            Activity(
                id=code,
                name=task.get("task_name") or code,
                wbs=wbs_names.get(task.get("wbs_id")),
                planned_start=parse_date(task.get("target_start_date")),
                planned_finish=parse_date(task.get("target_end_date")),
                weight=parse_number(task.get("target_drtn_hr_cnt")),
                actual_start=parse_date(task.get("act_start_date")),
                actual_finish=parse_date(task.get("act_end_date")),
                forecast_finish=parse_date(task.get("reend_date") or task.get("early_end_date")),
                progress=_clamp_pct(progress),
                source=path.name,
            )
        )
    by_code = {a.id: a for a in result.activities}
    for pred in tables.get("TASKPRED") or []:
        succ = by_code.get(task_code_by_id.get(pred.get("task_id"), ""))
        pred_code = task_code_by_id.get(pred.get("pred_task_id"))
        if succ and pred_code:
            succ.predecessors.append(pred_code)
    if not result.activities:
        result.warnings.append(f"{path.name}: no TASK table found in the XER file.")
    return result


def read_msproject_xml(path: Path) -> DelayInput:
    raw = path.read_bytes()
    if b"<!DOCTYPE" in raw[:4096].upper() or b"<!ENTITY" in raw.upper():
        # MS Project exports never need a DTD; refusing them blocks entity-expansion payloads.
        return DelayInput(warnings=[f"{path.name}: XML files with DOCTYPE/ENTITY declarations are not accepted."])
    root = ET.fromstring(raw)  # noqa: S314 - DTDs rejected above
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    def find(node: ET.Element, tag: str) -> Optional[str]:
        child = node.find(f"{ns}{tag}")
        return child.text if child is not None else None

    result = DelayInput(sources=[path.name])
    result.project.name = find(root, "Title") or find(root, "Name") or result.project.name
    result.project.contract_start = parse_date(find(root, "StartDate"))
    result.project.contract_finish = parse_date(find(root, "FinishDate"))
    result.project.data_date = parse_date(find(root, "StatusDate") or find(root, "CurrentDate"))
    uid_to_id: Dict[str, str] = {}
    pending_links: List[Tuple[Activity, List[str]]] = []
    tasks = root.find(f"{ns}Tasks")
    for task in list(tasks) if tasks is not None else []:
        if find(task, "Summary") == "1" or find(task, "IsNull") == "1":
            continue
        uid = find(task, "UID") or ""
        if uid == "0":
            continue
        code = find(task, "WBS") or find(task, "ID") or uid
        uid_to_id[uid] = code
        baseline_start = baseline_finish = None
        for baseline in task.findall(f"{ns}Baseline"):
            if (find(baseline, "Number") or "0") == "0":
                baseline_start = parse_date(find(baseline, "Start"))
                baseline_finish = parse_date(find(baseline, "Finish"))
        activity = Activity(
            id=code,
            name=find(task, "Name") or code,
            wbs=(find(task, "OutlineNumber") or "").rsplit(".", 1)[0] or None,
            planned_start=baseline_start or parse_date(find(task, "Start")),
            planned_finish=baseline_finish or parse_date(find(task, "Finish")),
            actual_start=parse_date(find(task, "ActualStart")),
            actual_finish=parse_date(find(task, "ActualFinish")),
            forecast_finish=parse_date(find(task, "Finish")) if baseline_finish else None,
            progress=_clamp_pct(parse_number(find(task, "PercentComplete"))),
            source=path.name,
        )
        links = [find(link, "PredecessorUID") or "" for link in task.findall(f"{ns}PredecessorLink")]
        pending_links.append((activity, links))
        result.activities.append(activity)
    for activity, links in pending_links:
        activity.predecessors = [uid_to_id[uid] for uid in links if uid in uid_to_id]
    return result


def read_path(path: Path) -> DelayInput:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return read_workbook(path)
    if suffix == ".xls":
        return read_xls(path)
    if suffix == ".csv":
        return read_csv(path)
    if suffix == ".xer":
        return read_xer(path)
    if suffix == ".xml":
        return read_msproject_xml(path)
    return DelayInput(warnings=[f"{path.name}: this file type is kept as a supporting document and is not read for the delay analysis."])


def read_paths(paths: Sequence[Path]) -> DelayInput:
    combined = DelayInput()
    for path in paths:
        try:
            combined.merge(read_path(Path(path)))
        except Exception as exc:  # one unreadable file must not block the rest
            combined.warnings.append(f"{Path(path).name}: file could not be read ({type(exc).__name__}).")
    _merge_duplicate_activities(combined)
    return combined
