"""PDF and Excel execution report (icra hesabatı) for a delay analysis result."""
from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any, Dict, List, Optional, Sequence
from xml.sax.saxutils import escape as _esc

NAVY = "#0B1730"
GOLD = "#D4A24C"
GREY = "#8A94A6"
RED = "#C0392B"
GREEN = "#2E8B57"

LABELS: Dict[str, Dict[str, str]] = {
    "title": {"en": "Construction Execution and Delay Analysis Report", "az": "Tikinti Layihəsinin İcra və Gecikmə Analizi Hesabatı"},
    "project": {"en": "Project", "az": "Layihə"},
    "client": {"en": "Client", "az": "Sifarişçi"},
    "contractor": {"en": "Contractor", "az": "Podratçı"},
    "location": {"en": "Location", "az": "Ünvan"},
    "data_date": {"en": "Data date", "az": "Hesabat tarixi"},
    "contract": {"en": "Contract period", "az": "Müqavilə müddəti"},
    "summary": {"en": "1. Execution summary", "az": "1. İcra xülasəsi"},
    "planned_progress": {"en": "Planned progress", "az": "Plan icra"},
    "actual_progress": {"en": "Actual progress", "az": "Faktiki icra"},
    "spi": {"en": "SPI", "az": "SPI"},
    "schedule_delay": {"en": "Schedule delay (earned schedule)", "az": "Qrafikdən geri qalma (earned schedule)"},
    "planned_finish": {"en": "Planned completion", "az": "Plan bitmə tarixi"},
    "forecast_finish": {"en": "Forecast completion", "az": "Proqnoz bitmə tarixi"},
    "forecast_delay": {"en": "Forecast delay", "az": "Proqnoz gecikmə"},
    "forecast_spi": {"en": "Forecast by SPI(t)", "az": "SPI(t) üzrə proqnoz"},
    "status": {"en": "Overall status", "az": "Ümumi vəziyyət"},
    "days": {"en": "days", "az": "gün"},
    "scurve": {"en": "2. Planned vs actual progress (S-curve)", "az": "2. Plan və faktiki icra (S-əyrisi)"},
    "wbs": {"en": "3. Execution by section", "az": "3. Bölmələr üzrə icra"},
    "section": {"en": "Section", "az": "Bölmə"},
    "share": {"en": "Share %", "az": "Pay %"},
    "plan_pct": {"en": "Plan %", "az": "Plan %"},
    "actual_pct": {"en": "Actual %", "az": "Faktiki %"},
    "variance": {"en": "Finish var. (d)", "az": "Bitmə fərqi (gün)"},
    "delayed": {"en": "Delayed", "az": "Gecikən"},
    "top": {"en": "4. Most delayed activities and critical path", "az": "4. Ən çox gecikən işlər və kritik yol"},
    "id": {"en": "ID", "az": "Kod"},
    "activity": {"en": "Activity", "az": "İş"},
    "pfinish": {"en": "Plan finish", "az": "Plan bitmə"},
    "ffinish": {"en": "Forecast", "az": "Proqnoz"},
    "float": {"en": "Float", "az": "Ehtiyat"},
    "state": {"en": "Status", "az": "Status"},
    "critical_method_cpm": {"en": "Critical path from predecessor logic (CPM, total float ≤ 0).", "az": "Kritik yol işlər arası əlaqələrə görə hesablanıb (CPM, ümumi ehtiyat ≤ 0)."},
    "critical_method_approximate": {"en": "No predecessor logic: critical activities are those finishing within 7 days of the forecast completion.", "az": "İşlər arası əlaqə yoxdur: kritik işlər proqnoz bitmə tarixindən 7 gün ərzində bitən işlərdir."},
    "events": {"en": "5. Delay events and responsibility", "az": "5. Gecikmə hadisələri və məsuliyyət"},
    "no_events": {"en": "No delay events were supplied.", "az": "Gecikmə hadisələri təqdim olunmayıb."},
    "event": {"en": "Event", "az": "Hadisə"},
    "period": {"en": "Period", "az": "Dövr"},
    "cause": {"en": "Cause", "az": "Səbəb"},
    "responsible": {"en": "Responsible", "az": "Məsul"},
    "employer": {"en": "Employer", "az": "Sifarişçi"},
    "contractor_party": {"en": "Contractor", "az": "Podratçı"},
    "neutral": {"en": "Neutral", "az": "Neytral"},
    "concurrent": {"en": "Concurrent", "az": "Eyni vaxtda"},
    "unassigned": {"en": "Unassigned", "az": "Təyin edilməyib"},
    "excusable": {"en": "Excusable (EOT)", "az": "Üzrlü (EOT)"},
    "compensable": {"en": "Compensable", "az": "Kompensasiyalı"},
    "non_excusable": {"en": "Non-excusable", "az": "Üzrsüz"},
    "all_events": {"en": "All events", "az": "Bütün hadisələr"},
    "critical_events": {"en": "On critical path", "az": "Kritik yolda"},
    "monthly": {"en": "6. Monthly delay development", "az": "6. Aylar üzrə gecikmənin inkişafı"},
    "month": {"en": "Month", "az": "Ay"},
    "delay_days": {"en": "Delay (d)", "az": "Gecikmə (gün)"},
    "change": {"en": "Change (d)", "az": "Dəyişmə (gün)"},
    "payments": {"en": "7. F2 certified work and payments", "az": "7. F2 aktları üzrə görülmüş işlər və ödənişlər"},
    "f2_no": {"en": "F2 No", "az": "F2 №"},
    "amount": {"en": "Amount excl. VAT", "az": "Məbləğ (ƏDV-siz)"},
    "amount_vat": {"en": "Incl. VAT", "az": "ƏDV ilə"},
    "cumulative": {"en": "Cumulative", "az": "Kumulyativ"},
    "of_contract": {"en": "% of contract", "az": "Müqavilədən %"},
    "contract_value": {"en": "Contract value", "az": "Müqavilə dəyəri"},
    "total_certified": {"en": "Total certified (F2)", "az": "Cəmi aktlaşdırılıb (F2)"},
    "financial_progress": {"en": "Financial progress", "az": "Maliyyə icrası"},
    "physical_progress": {"en": "Physical progress", "az": "Fiziki icra"},
    "fin_gap": {"en": "Financial − physical", "az": "Maliyyə − fiziki"},
    "source": {"en": "Source", "az": "Mənbə"},
    "conclusions": {"en": "8. Conclusions and recommendations", "az": "8. Nəticə və tövsiyələr"},
    "documents": {"en": "9. Documents reviewed", "az": "9. Baxılan sənədlər"},
    "document": {"en": "Document", "az": "Sənəd"},
    "doc_type": {"en": "Type", "az": "Növ"},
    "doc_status": {"en": "Use in analysis", "az": "Analizdə istifadə"},
    "note": {"en": "Note", "az": "Qeyd"},
    "type_contract": {"en": "Contract", "az": "Müqavilə"},
    "type_schedule": {"en": "Schedule", "az": "Planlama"},
    "type_f2": {"en": "F2 certificate", "az": "F2 aktı"},
    "doc_read": {"en": "Read", "az": "Oxundu"},
    "doc_reference": {"en": "Reference", "az": "İstinad"},
    "doc_no_data": {"en": "No data found", "az": "Məlumat tapılmadı"},
    "doc_unreadable": {"en": "Not readable", "az": "Oxunmadı"},
    "findings": {"en": "Findings", "az": "Nəticələr"},
    "actions": {"en": "Recommended actions", "az": "Tövsiyə olunan tədbirlər"},
    "quality": {"en": "10. Data quality notes", "az": "10. Məlumat keyfiyyəti qeydləri"},
    "no_quality": {"en": "No data quality issues were found.", "az": "Məlumat keyfiyyəti problemi aşkar edilmədi."},
    "method": {"en": "Method: calendar days; weights from the weight column or planned duration; schedule delay by earned schedule; forecast from actuals, production rate and predecessor logic.",
               "az": "Metod: təqvim günləri; çəki sütunu və ya plan müddəti üzrə çəkilər; geri qalma earned schedule ilə; proqnoz faktiki tarixlər, icra sürəti və işlər arası əlaqələrlə."},
    "status_on_track": {"en": "On track", "az": "Qrafik üzrə"},
    "status_at_risk": {"en": "At risk", "az": "Risk altında"},
    "status_critical": {"en": "Critical delay", "az": "Kritik gecikmə"},
    "st_completed": {"en": "Completed", "az": "Bitib"},
    "st_completed_late": {"en": "Completed late", "az": "Gec bitib"},
    "st_on_track": {"en": "On track", "az": "Qrafik üzrə"},
    "st_not_started": {"en": "Not started", "az": "Başlanmayıb"},
    "st_late_start": {"en": "Late start", "az": "Gec başlanğıc"},
    "st_delayed": {"en": "Delayed", "az": "Gecikir"},
    "st_major_delay": {"en": "Major delay", "az": "Böyük gecikmə"},
    "st_critical_delay": {"en": "Critical delay", "az": "Kritik gecikmə"},
    "actual_reconstructed": {"en": "Monthly actual progress reconstructed from activity actual dates.", "az": "Aylıq faktiki icra işlərin faktiki tarixlərindən bərpa olunub."},
    "generated": {"en": "Generated by DevBareun", "az": "DevBareun tərəfindən hazırlanıb"},
    "activities_sheet": {"en": "Activities", "az": "İşlər"},
}


def _l(key: str, lang: str) -> str:
    entry = LABELS.get(key) or {}
    return entry.get(lang) or entry.get("en") or key


def _lang(lang: Optional[str]) -> str:
    return "az" if (lang or "").lower().startswith("az") else "en"


def _d(value: Optional[str], lang: str = "en") -> str:
    if not value:
        return "—"
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%d.%m.%Y")


def _pct(value: Any) -> str:
    return "—" if value is None else f"{value:.1f}%"


def _money(value: Any) -> str:
    return "—" if value is None else f"{value:,.2f}".replace(",", " ")


def _party_label(party: str, lang: str) -> str:
    return _l({"contractor": "contractor_party"}.get(party, party), lang)


# ---------------------------------------------------------------------- PDF
def build_delay_pdf(result: Dict[str, Any], lang: str = "en") -> bytes:
    """The two-page A3 execution report; the older A4 layout only when the
    executive summary could not be built."""
    if (result.get("executive") or {}).get("ok"):
        from .report_a3 import build_executive_pdf

        return build_executive_pdf(result, lang)
    return _build_classic_pdf(result, lang)


def _build_classic_pdf(result: Dict[str, Any], lang: str = "en") -> bytes:
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing, Line, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from ..reports import _register_unicode_fonts
    from .. import reports as base_reports

    lang = _lang(lang)
    _register_unicode_fonts()
    regular, bold = base_reports._REGULAR_FONT, base_reports._BOLD_FONT
    navy, gold, grey = colors.HexColor(NAVY), colors.HexColor(GOLD), colors.HexColor(GREY)

    h1 = ParagraphStyle("h1", fontName=bold, fontSize=16, leading=20, textColor=navy, spaceAfter=4)
    h2 = ParagraphStyle("h2", fontName=bold, fontSize=12, leading=16, textColor=navy, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("body", fontName=regular, fontSize=9, leading=12.5)
    small = ParagraphStyle("small", fontName=regular, fontSize=7.5, leading=10, textColor=grey)
    cell = ParagraphStyle("cell", fontName=regular, fontSize=7.8, leading=9.6)

    def table(rows: List[List[Any]], widths: Sequence[float], header: bool = True, zebra: bool = True) -> Table:
        wrapped = [[Paragraph(_esc(v), cell) if isinstance(v, str) else v for v in row] for row in rows]
        if header:
            wrapped[0] = [Paragraph(f"<font color='#FFFFFF'><b>{_esc(str(v))}</b></font>", cell) for v in rows[0]]
        t = Table(wrapped, colWidths=list(widths), repeatRows=1 if header else 0)
        style = [
            ("FONTNAME", (0, 0), (-1, -1), regular),
            ("FONTSIZE", (0, 0), (-1, -1), 7.8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5DAE3")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), navy), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
        if zebra:
            for r in range(1 if header else 0, len(rows)):
                if r % 2 == 0:
                    style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F4F6FA")))
        t.setStyle(TableStyle(style))
        return t

    k = result.get("kpis") or {}
    project = result.get("project") or {}
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=_l("title", lang), author="DevBareun")
    width = A4[0] - 32 * mm
    story: List[Any] = []

    story.append(Paragraph(_l("title", lang), h1))
    story.append(Paragraph(f"<font color='{GOLD}'>■</font> {_esc(project.get('name') or '')}", ParagraphStyle("pn", parent=body, fontName=bold, fontSize=11)))
    story.append(Spacer(1, 6))
    info_rows = [
        [_l("client", lang), project.get("client") or "—", _l("contractor", lang), project.get("contractor") or "—"],
        [_l("contract", lang), f"{_d(project.get('contract_start'))} – {_d(project.get('contract_finish'))}", _l("data_date", lang), _d(k.get("data_date"))],
    ]
    if project.get("contract_value"):
        info_rows.append([_l("contract_value", lang), f"{_money(project['contract_value'])} {project.get('currency') or ''}".strip(), "", ""])
    story.append(table(info_rows, [width * 0.16, width * 0.34, width * 0.16, width * 0.34], header=False, zebra=False))

    # 1. Summary
    story.append(Paragraph(_l("summary", lang), h2))
    status_key = f"status_{k.get('status', 'at_risk')}"
    days = _l("days", lang)
    summary_rows = [
        [_l("planned_progress", lang), _pct(k.get("planned_progress_pct")), _l("planned_finish", lang), _d(k.get("planned_finish"))],
        [_l("actual_progress", lang), _pct(k.get("actual_progress_pct")), _l("forecast_finish", lang), _d(k.get("forecast_finish"))],
        [_l("spi", lang), str(k.get("spi") if k.get("spi") is not None else "—"), _l("forecast_delay", lang), f"{k.get('forecast_delay_days', 0)} {days}"],
        [_l("schedule_delay", lang), f"{k.get('schedule_delay_days', 0)} {days}", _l("forecast_spi", lang), _d(k.get("forecast_finish_spi"))],
        [_l("status", lang), _l(status_key, lang), "", ""],
    ]
    story.append(table(summary_rows, [width * 0.28, width * 0.22, width * 0.28, width * 0.22], header=False))

    # 2. S-curve
    monthly = result.get("monthly") or []
    if monthly:
        story.append(Paragraph(_l("scurve", lang), h2))
        drawing = Drawing(width, 190)
        plot = LinePlot()
        plot.x, plot.y, plot.width, plot.height = 34, 30, width - 50, 140
        planned = [(i, m["planned_cumulative_pct"] or 0) for i, m in enumerate(monthly)]
        actual = [(i, m["actual_cumulative_pct"]) for i, m in enumerate(monthly) if m["actual_cumulative_pct"] is not None]
        plot.data = [planned, actual or [(0, 0)]]
        plot.lines[0].strokeColor = grey
        plot.lines[0].strokeWidth = 1.6
        plot.lines[1].strokeColor = gold
        plot.lines[1].strokeWidth = 2.2
        plot.xValueAxis.valueMin = 0
        plot.xValueAxis.valueMax = max(1, len(monthly) - 1)
        step = max(1, len(monthly) // 8)
        plot.xValueAxis.valueSteps = list(range(0, len(monthly), step))
        plot.xValueAxis.labelTextFormat = lambda v: monthly[int(v)]["month"] if 0 <= int(v) < len(monthly) else ""
        plot.xValueAxis.labels.fontName = regular
        plot.xValueAxis.labels.fontSize = 6.5
        plot.yValueAxis.valueMin, plot.yValueAxis.valueMax, plot.yValueAxis.valueStep = 0, 100, 20
        plot.yValueAxis.labels.fontName = regular
        plot.yValueAxis.labels.fontSize = 7
        plot.yValueAxis.gridStrokeColor = colors.HexColor("#E3E7EE")
        plot.yValueAxis.visibleGrid = True
        drawing.add(plot)
        legend_y = 180
        drawing.add(Line(36, legend_y, 54, legend_y, strokeColor=grey, strokeWidth=1.6))
        drawing.add(String(58, legend_y - 3, _l("planned_progress", lang), fontName=regular, fontSize=7.5))
        drawing.add(Line(150, legend_y, 168, legend_y, strokeColor=gold, strokeWidth=2.2))
        drawing.add(String(172, legend_y - 3, _l("actual_progress", lang), fontName=regular, fontSize=7.5))
        story.append(drawing)
        if result.get("monthly_actual_source") == "reconstructed":
            story.append(Paragraph(_l("actual_reconstructed", lang), small))

    # 3. WBS
    wbs = result.get("wbs") or []
    if wbs:
        story.append(Paragraph(_l("wbs", lang), h2))
        rows = [[_l("section", lang), _l("share", lang), _l("plan_pct", lang), _l("actual_pct", lang), "SPI", _l("ffinish", lang), _l("variance", lang), _l("delayed", lang)]]
        for w in wbs:
            rows.append([w["wbs"], _pct(w["weight_share"]), _pct(w["planned_pct"]), _pct(w["actual_pct"]), str(w["spi"] if w["spi"] is not None else "—"),
                         _d(w["forecast_finish"]), str(w["finish_variance_days"]), f"{w['delayed_activities']}/{w['activities']}"])
        story.append(table(rows, [width * f for f in (0.28, 0.08, 0.09, 0.1, 0.07, 0.14, 0.13, 0.11)]))

    # 4. Top delays + critical path
    story.append(Paragraph(_l("top", lang), h2))
    critical_ids = {a["id"] for a in (result.get("critical_path") or {}).get("activities") or []}
    shown = list(result.get("top_delays") or [])
    for activity in (result.get("critical_path") or {}).get("activities") or []:
        if activity["id"] not in {a["id"] for a in shown} and activity["status"] not in {"completed"}:
            shown.append(activity)
    if shown:
        rows = [[_l("id", lang), _l("activity", lang), _l("actual_pct", lang), _l("pfinish", lang), _l("ffinish", lang), _l("variance", lang), _l("float", lang), _l("state", lang)]]
        for a in shown[:18]:
            name = ("★ " if a["id"] in critical_ids else "") + a["name"]
            rows.append([a["id"], name, _pct(a["actual_pct"]), _d(a["planned_finish"]), _d(a["forecast_finish"]), str(a["finish_variance_days"]),
                         "—" if a["total_float_days"] is None else str(a["total_float_days"]), _l(f"st_{a['status']}", lang)])
        story.append(table(rows, [width * f for f in (0.08, 0.31, 0.08, 0.12, 0.12, 0.1, 0.07, 0.12)]))
    method = (result.get("critical_path") or {}).get("method", "approximate")
    story.append(Spacer(1, 3))
    story.append(Paragraph("★ " + _l(f"critical_method_{method}", lang), small))

    # 5. Events
    story.append(Paragraph(_l("events", lang), h2))
    events = result.get("events") or {}
    if events.get("available"):
        allp, crit = events["by_party_days"], events["critical_by_party_days"]
        rows = [["", _l("employer", lang), _l("contractor_party", lang), _l("neutral", lang), _l("concurrent", lang), _l("excusable", lang), _l("compensable", lang), _l("non_excusable", lang)]]
        for label, data in ((_l("all_events", lang), allp), (_l("critical_events", lang), crit)):
            rows.append([label] + [str(data[key]) for key in ("employer", "contractor", "neutral", "concurrent", "excusable", "compensable", "non_excusable")])
        story.append(table(rows, [width * f for f in (0.18, 0.11, 0.11, 0.1, 0.12, 0.13, 0.13, 0.12)]))
        story.append(Spacer(1, 6))
        rows = [[_l("id", lang), _l("event", lang), _l("period", lang), _l("days", lang), _l("cause", lang), _l("responsible", lang)]]
        for e in events["events"][:25]:
            rows.append([e["id"], e["description"], f"{_d(e['start'])} – {_d(e['finish']) if e['finish'] else '…'}", str(e["days"]), e.get("cause") or "—",
                         _party_label(e["responsible"], lang)])
        story.append(table(rows, [width * f for f in (0.07, 0.35, 0.2, 0.07, 0.17, 0.14)]))
    else:
        story.append(Paragraph(_l("no_events", lang), body))

    # 6. Monthly
    past = [m for m in monthly if m["actual_cumulative_pct"] is not None]
    if past:
        story.append(Paragraph(_l("monthly", lang), h2))
        rows = [[_l("month", lang), _l("plan_pct", lang), _l("actual_pct", lang), _l("delay_days", lang), _l("change", lang)]]
        for m in past:
            rows.append([m["month"], _pct(m["planned_cumulative_pct"]), _pct(m["actual_cumulative_pct"]), str(m["schedule_delay_days"]),
                         ("+" if (m["delay_change_days"] or 0) > 0 else "") + str(m["delay_change_days"])])
        story.append(table(rows, [width * f for f in (0.2, 0.2, 0.2, 0.2, 0.2)]))

    # 7. F2 payments
    payments = result.get("payments") or {}
    if payments.get("available"):
        story.append(Paragraph(_l("payments", lang), h2))
        cur = payments.get("currency") or ""
        rows = [
            [_l("contract_value", lang), f"{_money(payments.get('contract_value'))} {cur}".strip(), _l("financial_progress", lang), _pct(payments.get("financial_progress_pct"))],
            [_l("total_certified", lang), f"{_money(payments.get('total_certified'))} {cur}".strip(), _l("physical_progress", lang), _pct(payments.get("physical_progress_pct"))],
            [_l("amount_vat", lang), _money(payments.get("total_certified_with_vat")), _l("fin_gap", lang),
             "—" if payments.get("financial_minus_physical_pct") is None else f"{payments['financial_minus_physical_pct']:+.1f}"],
        ]
        story.append(table(rows, [width * 0.26, width * 0.24, width * 0.26, width * 0.24], header=False))
        story.append(Spacer(1, 6))
        rows = [[_l("f2_no", lang), _l("period", lang), _l("amount", lang), _l("amount_vat", lang), _l("cumulative", lang), _l("of_contract", lang)]]
        for c in payments.get("certificates") or []:
            rows.append([c.get("number") or "—", c.get("period") or "—", _money(c.get("amount")), _money(c.get("amount_with_vat")),
                         _money(c.get("cumulative")), _pct(c.get("cumulative_pct_of_contract"))])
        story.append(table(rows, [width * f for f in (0.13, 0.13, 0.2, 0.2, 0.2, 0.14)]))

    # 8. Conclusions
    story.append(Paragraph(_l("conclusions", lang), h2))
    story.append(Paragraph(f"<b>{_l('findings', lang)}</b>", body))
    for item in result.get("findings") or []:
        story.append(Paragraph(f"• {_esc(item.get(lang) or item.get('en') or '')}", body))
    if result.get("actions"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>{_l('actions', lang)}</b>", body))
        for index, item in enumerate(result["actions"], start=1):
            story.append(Paragraph(f"{index}. {_esc(item.get(lang) or item.get('en') or '')}", body))

    # 9. Documents
    documents = result.get("documents") or []
    if documents:
        story.append(Paragraph(_l("documents", lang), h2))
        rows = [[_l("document", lang), _l("doc_type", lang), _l("doc_status", lang), _l("note", lang)]]
        for d in documents[:60]:
            rows.append([d["name"], _l(f"type_{d['document_type']}", lang), _l(f"doc_{d['status']}", lang),
                         (d.get(f"note_{lang}") or d.get("note_en") or "")])
        story.append(table(rows, [width * f for f in (0.3, 0.14, 0.14, 0.42)]))

    # 10. Data quality
    story.append(Paragraph(_l("quality", lang), h2))
    quality = result.get("data_quality") or []
    if quality:
        for item in quality[:30]:
            story.append(Paragraph(f"• {_esc(item.get(lang) or item.get('en') or '')}", small))
    else:
        story.append(Paragraph(_l("no_quality", lang), body))
    story.append(Spacer(1, 8))
    story.append(Paragraph(_l("method", lang), small))

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(gold)
        canvas.setLineWidth(1.2)
        canvas.line(16 * mm, A4[1] - 11 * mm, A4[0] - 16 * mm, A4[1] - 11 * mm)
        canvas.setFont(regular, 7)
        canvas.setFillColor(grey)
        canvas.drawString(16 * mm, 9 * mm, f"{_l('generated', lang)} · devbareun.com · {(project.get('name') or '')[:80]}")
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


# -------------------------------------------------------------------- Excel
def build_delay_excel(result: Dict[str, Any], lang: str = "en") -> bytes:
    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Alignment, Font, PatternFill

    lang = _lang(lang)
    wb = Workbook()
    head_fill = PatternFill("solid", fgColor=NAVY.strip("#"))
    head_font = Font(bold=True, color="FFFFFF")

    def sheet(title: str, headers: List[str], rows: List[List[Any]], widths: List[int]):
        ws = wb.create_sheet(title[:31])
        ws.append(headers)
        for row in rows:
            ws.append(row)
        for c in ws[1]:
            c.fill, c.font = head_fill, head_font
            c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.freeze_panes = "A2"
        for index, width in enumerate(widths, start=1):
            ws.column_dimensions[ws.cell(row=1, column=index).column_letter].width = width
        return ws

    k = result.get("kpis") or {}
    project = result.get("project") or {}
    summary = wb.active
    summary.title = _l("summary", lang).split(". ", 1)[-1][:31]
    summary.append([_l("title", lang)])
    summary["A1"].font = Font(bold=True, size=14, color=NAVY.strip("#"))
    rows = [
        (_l("project", lang), project.get("name")), (_l("client", lang), project.get("client")), (_l("contractor", lang), project.get("contractor")),
        (_l("contract_value", lang), project.get("contract_value")),
        (_l("data_date", lang), _d(k.get("data_date"))), (_l("planned_progress", lang), k.get("planned_progress_pct")),
        (_l("actual_progress", lang), k.get("actual_progress_pct")), ("SPI", k.get("spi")), (_l("schedule_delay", lang), k.get("schedule_delay_days")),
        (_l("planned_finish", lang), _d(k.get("planned_finish"))), (_l("forecast_finish", lang), _d(k.get("forecast_finish"))),
        (_l("forecast_delay", lang), k.get("forecast_delay_days")), (_l("forecast_spi", lang), _d(k.get("forecast_finish_spi"))),
        (_l("status", lang), _l(f"status_{k.get('status', 'at_risk')}", lang)),
    ]
    summary.append([])
    for label, value in rows:
        summary.append([label, value])
        summary.cell(row=summary.max_row, column=1).font = Font(bold=True)
    summary.append([])
    summary.append([_l("findings", lang)])
    summary.cell(row=summary.max_row, column=1).font = Font(bold=True, color=NAVY.strip("#"))
    for item in result.get("findings") or []:
        summary.append([item.get(lang) or item.get("en")])
    summary.append([_l("actions", lang)])
    summary.cell(row=summary.max_row, column=1).font = Font(bold=True, color=NAVY.strip("#"))
    for item in result.get("actions") or []:
        summary.append([item.get(lang) or item.get("en")])
    summary.column_dimensions["A"].width = 44
    summary.column_dimensions["B"].width = 30

    acts = result.get("activities") or []
    sheet(_l("activities_sheet", lang),
          [_l("id", lang), _l("section", lang), _l("activity", lang), "Plan start", _l("pfinish", lang), "Actual start", "Actual finish",
           _l("ffinish", lang), _l("plan_pct", lang), _l("actual_pct", lang), "Start var. (d)", _l("variance", lang), _l("float", lang), "Critical", _l("state", lang)],
          [[a["id"], a["wbs"], a["name"], a["planned_start"], a["planned_finish"], a["actual_start"], a["actual_finish"], a["forecast_finish"],
            a["planned_pct"], a["actual_pct"], a["start_variance_days"], a["finish_variance_days"], a["total_float_days"], "✓" if a["critical"] else "",
            _l(f"st_{a['status']}", lang)] for a in acts],
          [10, 22, 36, 12, 12, 12, 12, 12, 9, 9, 11, 12, 8, 8, 16])
    if result.get("wbs"):
        sheet(_l("wbs", lang).split(". ", 1)[-1],
              [_l("section", lang), _l("share", lang), _l("plan_pct", lang), _l("actual_pct", lang), "SPI", _l("pfinish", lang), _l("ffinish", lang), _l("variance", lang), _l("delayed", lang)],
              [[w["wbs"], w["weight_share"], w["planned_pct"], w["actual_pct"], w["spi"], w["planned_finish"], w["forecast_finish"], w["finish_variance_days"], w["delayed_activities"]]
               for w in result["wbs"]], [28, 9, 9, 9, 7, 12, 12, 12, 9])
    monthly = result.get("monthly") or []
    if monthly:
        ws = sheet(_l("monthly", lang).split(". ", 1)[-1],
                   [_l("month", lang), _l("plan_pct", lang), _l("actual_pct", lang), _l("delay_days", lang), _l("change", lang)],
                   [[m["month"], m["planned_cumulative_pct"], m["actual_cumulative_pct"], m["schedule_delay_days"], m["delay_change_days"]] for m in monthly],
                   [12, 12, 12, 14, 14])
        chart = LineChart()
        chart.title = _l("scurve", lang).split(". ", 1)[-1]
        chart.y_axis.scaling.min, chart.y_axis.scaling.max = 0, 100
        chart.add_data(Reference(ws, min_col=2, max_col=3, min_row=1, max_row=len(monthly) + 1), titles_from_data=True)
        chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=len(monthly) + 1))
        chart.height, chart.width = 8, 18
        ws.add_chart(chart, "G2")
    events = result.get("events") or {}
    if events.get("available"):
        sheet(_l("events", lang).split(". ", 1)[-1],
              [_l("id", lang), _l("event", lang), "Start", "Finish", _l("days", lang), _l("cause", lang), _l("responsible", lang), _l("activity", lang), _l("critical_events", lang)],
              [[e["id"], e["description"], e["start"], e["finish"], e["days"], e["cause"], _party_label(e["responsible"], lang), " ".join(e["activity_ids"]),
                {True: "✓", False: "", None: "?"}[e["affects_critical_path"]]] for e in events["events"]],
              [8, 44, 12, 12, 7, 20, 14, 18, 12])
    payments = result.get("payments") or {}
    if payments.get("available"):
        sheet(_l("payments", lang).split(". ", 1)[-1],
              [_l("f2_no", lang), _l("period", lang), _l("amount", lang), _l("amount_vat", lang), _l("cumulative", lang), _l("of_contract", lang), _l("source", lang)],
              [[c.get("number"), c.get("period"), c.get("amount"), c.get("amount_with_vat"), c.get("cumulative"), c.get("cumulative_pct_of_contract"), c.get("source")]
               for c in payments.get("certificates") or []]
              + [[], [_l("contract_value", lang), payments.get("contract_value")], [_l("total_certified", lang), payments.get("total_certified")],
                 [_l("financial_progress", lang), payments.get("financial_progress_pct")], [_l("physical_progress", lang), payments.get("physical_progress_pct")]],
              [14, 12, 18, 18, 18, 14, 40])
    documents = result.get("documents") or []
    if documents:
        sheet(_l("documents", lang).split(". ", 1)[-1], [_l("document", lang), _l("doc_type", lang), _l("doc_status", lang), _l("note", lang)],
              [[d["name"], _l(f"type_{d['document_type']}", lang), _l(f"doc_{d['status']}", lang), d.get(f"note_{lang}") or d.get("note_en")] for d in documents],
              [40, 16, 18, 90])
    quality = result.get("data_quality") or []
    if quality:
        sheet(_l("quality", lang).split(". ", 1)[-1], ["Severity", "Note"], [[q["severity"], q.get(lang) or q["en"]] for q in quality], [12, 120])
    _executive_sheets(wb, result, lang, sheet)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _executive_sheets(wb: Any, result: Dict[str, Any], lang: str, sheet: Any) -> None:
    """Work types, buildings, monthly plan vs F-2 and finance of the executive report."""
    from . import categories as cat

    ex = result.get("executive") or {}
    if not ex.get("ok"):
        return
    az = lang == "az"
    sheet("İş növləri" if az else "Work types",
          ["İş növü" if az else "Work type", "Smeta (ƏDV-siz)" if az else "Estimate (excl. VAT)", "Plan %", "Fakt %" if az else "Actual %",
           "Gerilik, f.b." if az else "Gap, pp", "Status"],
          [[cat.label(r["category"], lang) if r["category"] in cat.LABELS else r["category"], r["value"], r["plan_pct"], r["fact_pct"],
            r["gap_pp"], r["status"]] for r in ex.get("categories") or []], [30, 20, 10, 10, 14, 14])
    cats = [cat.FRAME, cat.MASONRY, cat.ENVELOPE, cat.FINISHING, cat.MEP]
    sheet("Binalar" if az else "Buildings",
          ["Bina" if az else "Building", "Plan bitmə" if az else "Plan finish", "Plan %", "Fakt %" if az else "Actual %", "Gerilik, f.b." if az else "Gap, pp"]
          + [cat.label(c, lang, short=True) + " %" for c in cats],
          [[b.get("building") or ("Ərazi abadlığı" if az else "Site works"), _d(b.get("plan_finish")), b["plan_pct"], b["fact_pct"], b["gap_pp"]]
           + [b["categories"].get(c) for c in cats] for b in ex.get("buildings") or []], [16, 14, 10, 10, 14] + [12] * 5)
    sheet("Aylıq plan vs F-2" if az else "Monthly plan vs F-2",
          ["Ay" if az else "Month", "Plan kumulyativ %" if az else "Plan cumulative %", "Fakt kumulyativ %" if az else "Actual cumulative %",
           "Plan dəyəri" if az else "Plan value", "F-2 dəyəri" if az else "F-2 value"],
          [[_d(m["month"]), m.get("plan_pct"), m.get("fact_pct"), m.get("plan_value"), m.get("f2_value")] for m in ex.get("monthly") or []],
          [14, 18, 18, 16, 16])
    fin = ex.get("finance") or {}
    fc = ex.get("forecast") or {}
    pen = ex.get("penalty") or {}
    rows = [
        ("Müqavilə məbləği (ƏDV ilə)" if az else "Contract value (incl. VAT)", fin.get("contract_value")),
        ("Görülmüş iş, F-2 kumulyativ (ƏDV ilə)" if az else "Work done, F-2 cumulative (incl. VAT)", fin.get("works_cum_with_vat")),
        ("Alınmış avans" if az else "Advance received", fin.get("advance_received")),
        ("Tutulmuş avans" if az else "Advance recovered", fin.get("advance_withheld")),
        ("Qalıq avans" if az else "Outstanding advance", fin.get("advance_remaining")),
        ("Hesabat ayı üzrə ödəniləcək" if az else "Payable for the month", fin.get("payable_period")),
        ("Proqnoz (ən tez)" if az else "Forecast (earliest)", _d(fc.get("earliest_finish"))),
        ("Son aylar tempi (ayda)" if az else "Recent pace (per month)", fc.get("recent_pace")),
        ("Müqavilə üçün lazım olan temp" if az else "Pace needed for the contract", fc.get("required_pace")),
        ("Cərimə, gündə %" if az else "Penalty, % per day", pen.get("pct_per_day")),
        ("Cərimə limiti %" if az else "Penalty cap %", pen.get("cap_pct")),
        ("Limitin dolma tarixi" if az else "Cap reached on", _d(pen.get("cap_date"))),
    ]
    sheet("Maliyyə və proqnoz" if az else "Finance and forecast", ["Göstərici" if az else "Item", "Dəyər" if az else "Value"],
          [[a, b] for a, b in rows], [44, 22])
