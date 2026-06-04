from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dateutil import parser as date_parser


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    repl = {"ə":"e","ı":"i","ğ":"g","ü":"u","ö":"o","ş":"s","ç":"c","Ə":"e","İ":"i","Ğ":"g","Ü":"u","Ö":"o","Ş":"s","Ç":"c"}
    for a,b in repl.items():
        text = text.replace(a,b)
    text = re.sub(r"[^a-z0-9%+./\- ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _num(value: Any) -> Optional[float]:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    cleaned = re.sub(r"[^0-9,\.\-+]", "", text)
    if not cleaned or cleaned in {"-","+", ".", ","}:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        cleaned = cleaned.replace(",", ".") if len(parts[-1]) in {1,2} else cleaned.replace(",", "")
    try:
        return float(cleaned)
    except Exception:
        return None


def _dt(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    text = str(value)
    if not re.search(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}", text):
        return None
    try:
        return date_parser.parse(text, dayfirst=True, fuzzy=True).date()
    except Exception:
        return None


ACTIVITY_LIBRARY: Dict[str, Dict[str, Any]] = {
    "plaster": {
        "az": "Alçı işi", "en": "Plaster works", "unit": "m²",
        "keywords": ["alci", "alci is", "plaster", "gypsum plaster", "alcı", "alçı"],
        "labor": ["Alçı ustası", "Fəhlə"], "equipment": ["hand tools", "scaffold"],
        "productivity": {"low": 20, "typical": 25, "high": 35}, "productivity_unit": "m²/worker/day"
    },
    "paint": {
        "az": "Boya işi", "en": "Painting works", "unit": "m²",
        "keywords": ["boya", "malyar", "paint", "painting", "astar"],
        "labor": ["Malyar"], "equipment": ["roller", "spray", "scaffold"],
        "productivity": {"low": 40, "typical": 60, "high": 80}, "productivity_unit": "m²/worker/day"
    },
    "tile": {
        "az": "Kafel / metlax işi", "en": "Tile works", "unit": "m²",
        "keywords": ["kafel", "metlax", "tile", "ceramic", "keramik"],
        "labor": ["Kafel ustası", "Fəhlə"], "equipment": ["tile cutter", "hand tools"],
        "productivity": {"low": 8, "typical": 12, "high": 15}, "productivity_unit": "m²/worker/day"
    },
    "masonry": {
        "az": "Hörgü işi", "en": "Masonry works", "unit": "m²",
        "keywords": ["horgu", "horgu is", "kərpic", "kerpic", "blok", "misar das", "masonry", "brick", "block"],
        "labor": ["Hörgü ustası", "Fəhlə"], "equipment": ["hand tools", "scaffold"],
        "productivity": {"low": 8, "typical": 12, "high": 15}, "productivity_unit": "m²/worker/day"
    },
    "screed": {
        "az": "Şap işi", "en": "Screed works", "unit": "m²",
        "keywords": ["sap", "şap", "screed", "floor screed"],
        "labor": ["Şap ustası", "Fəhlə"], "equipment": ["mixer", "laser level"],
        "productivity": {"low": 35, "typical": 50, "high": 70}, "productivity_unit": "m²/worker/day"
    },
    "formwork": {
        "az": "Qəlib işi", "en": "Formwork", "unit": "m²",
        "keywords": ["qelib", "kalip", "formwork", "shuttering"],
        "labor": ["Qəlibçi", "Fəhlə"], "equipment": ["formwork system", "crane", "hand tools"],
        "productivity": {"low": 8, "typical": 12, "high": 18}, "productivity_unit": "m²/worker/day"
    },
    "rebar": {
        "az": "Armatur işi", "en": "Rebar fixing", "unit": "ton",
        "keywords": ["armatur", "demir", "dəmir", "rebar", "reinforcement"],
        "labor": ["Dəmirçi", "Fəhlə"], "equipment": ["rebar cutter", "rebar bender", "crane"],
        "productivity": {"low": 0.25, "typical": 0.45, "high": 0.70}, "productivity_unit": "ton/worker/day"
    },
    "concrete": {
        "az": "Beton işi", "en": "Concrete pouring", "unit": "m³",
        "keywords": ["beton", "concrete", "pouring", "tokulme", "tökülmə"],
        "labor": ["Betonçu", "Fəhlə"], "equipment": ["concrete pump", "mixer truck", "vibrator"],
        "productivity": {"low": 8, "typical": 12, "high": 18}, "productivity_unit": "m³/worker/day"
    },
    "facade": {
        "az": "Fasad işi", "en": "Facade works", "unit": "m²",
        "keywords": ["fasad", "facade", "kompozit", "vitrage", "vitray", "cladding"],
        "labor": ["Fasad ustası", "Fəhlə"], "equipment": ["scaffold", "manlift", "hand tools"],
        "productivity": {"low": 5, "typical": 9, "high": 14}, "productivity_unit": "m²/worker/day"
    },
    "stone_floor": {
        "az": "Daş/granit döşəmə", "en": "Stone/granite flooring", "unit": "m²",
        "keywords": ["granit", "mermer", "mərmər", "susa das", "şuşa daşı", "stone", "granite", "marble"],
        "labor": ["Daş ustası", "Fəhlə"], "equipment": ["stone cutter", "vibroplate", "forklift"],
        "productivity": {"low": 8, "typical": 14, "high": 20}, "productivity_unit": "m²/worker/day"
    },
    "electrical_cable": {
        "az": "Elektrik kabel işi", "en": "Electrical cable works", "unit": "m",
        "keywords": ["kabel", "elektrik", "cable", "conduit", "lotok"],
        "labor": ["Elektrik", "Fəhlə"], "equipment": ["cable tools", "lift"],
        "productivity": {"low": 40, "typical": 80, "high": 130}, "productivity_unit": "m/worker/day"
    },
    "plumbing_pipe": {
        "az": "Santexnika boru işi", "en": "Plumbing pipe works", "unit": "m",
        "keywords": ["santex", "boru", "su xetti", "kanalizasiya", "pipe", "plumbing"],
        "labor": ["Santexnik", "Fəhlə"], "equipment": ["press/welding tools", "hand tools"],
        "productivity": {"low": 20, "typical": 40, "high": 70}, "productivity_unit": "m/worker/day"
    },
    "excavation": {
        "az": "Qazıntı işi", "en": "Excavation", "unit": "m³",
        "keywords": ["qazinti", "qazıntı", "torpaq", "excavation", "earthwork", "trench"],
        "labor": ["Operator", "Fəhlə"], "equipment": ["excavator", "dump truck"],
        "productivity": {"low": 20, "typical": 45, "high": 80}, "productivity_unit": "m³/crew/day"
    },
}


def classify_activity(name: Any) -> Optional[Dict[str, Any]]:
    norm = _norm(name)
    if not norm:
        return None
    best_key: Optional[str] = None
    best_score = 0
    for key, item in ACTIVITY_LIBRARY.items():
        score = sum(1 for kw in item["keywords"] if _norm(kw) in norm)
        if score > best_score:
            best_key = key
            best_score = score
    if not best_key:
        return None
    item = dict(ACTIVITY_LIBRARY[best_key])
    item["activity_code"] = best_key
    item["confidence"] = min(95, 60 + best_score * 15)
    return item


COLUMN_HINTS = {
    "activity": ("activity", "iş", "is", "iş növü", "is novu", "work", "description", "təsvir", "tesvir", "ad"),
    "unit": ("unit", "vahid", "ölçü", "olcu"),
    "quantity": ("quantity", "qty", "miqdar", "həcm", "hecm", "həcmi", "volume"),
    "planned_start": ("planned start", "plan start", "start", "başlama", "baslama"),
    "planned_finish": ("planned finish", "plan finish", "finish", "bitmə", "bitme", "son"),
    "duration": ("duration", "müddət", "muddet", "gün", "gun", "days"),
    "actual_workers": ("actual workers", "current workers", "işçi sayı", "isci sayi", "mövcud", "movcud", "cari işçi", "manpower", "worker"),
    "required_workers": ("required workers", "tələb olunan", "teleb olunan", "required manpower"),
}


def _map_header(row: Sequence[Any]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for idx, val in enumerate(row):
        n = _norm(val)
        if not n:
            continue
        for field, hints in COLUMN_HINTS.items():
            if any(_norm(h) in n for h in hints):
                mapping.setdefault(field, idx)
    return mapping


def _best_header(rows: Sequence[Sequence[Any]]) -> Tuple[Optional[int], Dict[str, int]]:
    best_i: Optional[int] = None
    best_map: Dict[str, int] = {}
    best_score = 0
    for i, row in enumerate(rows[:60]):
        m = _map_header(row)
        score = len(m) * 10
        if "activity" in m and "quantity" in m:
            score += 20
        if "duration" in m or ("planned_start" in m and "planned_finish" in m):
            score += 10
        if score > best_score:
            best_i, best_map, best_score = i, m, score
    return best_i, best_map


def _planned_days(row: Sequence[Any], mapping: Dict[str, int]) -> Optional[float]:
    if "duration" in mapping and mapping["duration"] < len(row):
        d = _num(row[mapping["duration"]])
        if d and 0 < d < 1000:
            return float(d)
    start = _dt(row[mapping["planned_start"]]) if "planned_start" in mapping and mapping["planned_start"] < len(row) else None
    finish = _dt(row[mapping["planned_finish"]]) if "planned_finish" in mapping and mapping["planned_finish"] < len(row) else None
    if start and finish:
        days = (finish - start).days + 1
        if days > 0:
            return float(days)
    return None


def analyze_workforce_productivity(rows: Sequence[Sequence[Any]], max_rows: int = 300) -> Dict[str, Any]:
    """Extract activity quantity/workforce rows and calculate manpower/duration risk.

    This module is intentionally deterministic: it classifies activity type and uses a
    reference productivity library. If quantity, unit, duration or worker count is
    missing, the row is returned as needs_confirmation instead of inventing values.
    """
    header_i, mapping = _best_header(rows)
    if header_i is None or not mapping or "activity" not in mapping:
        return {"enabled": True, "activities": [], "summary": {}, "warnings": ["No workforce productivity activity table was confidently detected."]}

    activities: List[Dict[str, Any]] = []
    warnings: List[str] = []
    data_rows = rows[header_i + 1: header_i + 1 + max_rows]
    for row in data_rows:
        if not any(v not in (None, "") for v in row):
            continue
        act_idx = mapping.get("activity")
        if act_idx is None or act_idx >= len(row):
            continue
        activity_name = str(row[act_idx] or "").strip()
        if len(activity_name) < 3:
            continue
        lib = classify_activity(activity_name)
        qty = _num(row[mapping["quantity"]]) if "quantity" in mapping and mapping["quantity"] < len(row) else None
        unit = str(row[mapping["unit"]]).strip() if "unit" in mapping and mapping["unit"] < len(row) and row[mapping["unit"]] not in (None, "") else (lib.get("unit") if lib else None)
        days = _planned_days(row, mapping)
        actual_workers = _num(row[mapping["actual_workers"]]) if "actual_workers" in mapping and mapping["actual_workers"] < len(row) else None
        required_from_file = _num(row[mapping["required_workers"]]) if "required_workers" in mapping and mapping["required_workers"] < len(row) else None

        if lib is None and qty is None and actual_workers is None:
            continue

        status = "needs_confirmation"
        required_workers = None
        realistic_days = None
        delay_days = None
        gap = None
        productivity = None
        risk = "Needs confirmation"
        notes: List[str] = []
        if lib:
            productivity = float(lib["productivity"]["typical"])
        else:
            notes.append("Activity type not matched to productivity library.")
        if qty is None or qty <= 0:
            notes.append("Quantity is missing or invalid.")
        if days is None or days <= 0:
            notes.append("Planned duration/dates are missing.")
        if actual_workers is None and required_from_file is None:
            notes.append("Actual/current worker count is missing.")
        if lib and qty and days and productivity and productivity > 0:
            required_workers = max(1, int(math.ceil(float(qty) / (productivity * float(days)))))
            status = "calculated"
        if required_from_file and not required_workers:
            required_workers = int(math.ceil(required_from_file))
        if actual_workers and productivity and qty:
            realistic_days = round(float(qty) / (float(actual_workers) * productivity), 1) if actual_workers > 0 else None
            if realistic_days and days:
                delay_days = round(max(0.0, realistic_days - float(days)), 1)
        if actual_workers and required_workers:
            gap = int(round(float(actual_workers))) - int(required_workers)
            if gap < 0:
                risk = "High" if abs(gap) >= max(2, required_workers * 0.25) else "Medium"
            else:
                risk = "Low"
        elif status == "calculated":
            risk = "Needs actual workforce"

        if lib and unit and _norm(unit) and _norm(lib["unit"]) not in _norm(unit):
            notes.append(f"Unit may not match productivity library unit ({lib['unit']}).")
            if status == "calculated":
                status = "needs_confirmation"

        activities.append({
            "activity_name": activity_name,
            "activity_code": lib.get("activity_code") if lib else None,
            "activity_label_az": lib.get("az") if lib else None,
            "activity_label_en": lib.get("en") if lib else None,
            "unit": unit,
            "quantity": qty,
            "planned_days": days,
            "actual_workers": int(actual_workers) if actual_workers is not None else None,
            "required_workers": required_workers,
            "workforce_gap": gap,
            "productivity_typical": productivity,
            "productivity_unit": lib.get("productivity_unit") if lib else None,
            "realistic_days": realistic_days,
            "delay_risk_days": delay_days,
            "risk_level": risk,
            "status": status,
            "labor": lib.get("labor") if lib else [],
            "equipment": lib.get("equipment") if lib else [],
            "notes": notes,
        })

    calculated = [a for a in activities if a.get("status") == "calculated"]
    shortages = [a for a in activities if isinstance(a.get("workforce_gap"), int) and a["workforce_gap"] < 0]
    needs = [a for a in activities if a.get("status") != "calculated" or a.get("risk_level") == "Needs actual workforce"]
    total_required = sum(a.get("required_workers") or 0 for a in calculated)
    total_actual = sum(a.get("actual_workers") or 0 for a in calculated if a.get("actual_workers") is not None)
    max_delay = max([a.get("delay_risk_days") or 0 for a in calculated], default=0)
    if not activities:
        warnings.append("No activity rows with quantity/workforce evidence were found.")
    if needs:
        warnings.append("Some activities require productivity, quantity, duration or actual workforce confirmation.")
    return {
        "enabled": True,
        "header_row_index": header_i + 1,
        "mapped_columns": {k: v + 1 for k, v in mapping.items()},
        "activities": activities[:100],
        "summary": {
            "activities_checked": len(activities),
            "calculated_activities": len(calculated),
            "activities_with_shortage": len(shortages),
            "needs_confirmation": len(needs),
            "total_required_workers": int(total_required) if total_required else None,
            "total_actual_workers": int(total_actual) if total_actual else None,
            "workforce_gap": int(total_actual - total_required) if total_required or total_actual else None,
            "max_delay_risk_days": max_delay,
        },
        "warnings": warnings,
        "library_version": "0.9.0-productivity-reference",
    }
