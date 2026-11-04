"""Two-page A3 landscape execution report (icra hesabatı) for the director.

Page 1 — overall status: key message, KPIs, plan–fact S-curve, monthly plan
vs F-2, work types and buildings. Page 2 — the most critical delays, forecast
and penalty, finance vs physical progress, contractor actions and director
decisions. Drawn with ReportLab on a fixed grid so both pages always fit.
"""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from . import categories as cat
from .executive import MONTHS_AZ, MONTHS_EN, STATUS_LABELS, dmy, mln, month_year, num, pace, pct

PAGE_W, PAGE_H = 1190.55, 841.89  # A3 landscape, points
M = 30  # page margin
GAP = 14

NAVY = "#14284B"
INK = "#1B2433"
MUTED = "#5B6475"
LINE = "#D9DDE3"
PANEL = "#FFFFFF"
SOFT = "#F5F5F2"
BLUE = "#2F6FD6"
ORANGE = "#EE6A2C"
RED = "#C62828"
AMBER = "#B7791F"
GREEN_BG = "#E3F2E1"
AMBER_BG = "#FFF3D6"
RED_BG = "#FCE9E9"
BLUE_BG = "#EAF1FC"

L: Dict[str, Dict[str, str]] = {
    "status_title": {"az": "tikintinin icra vəziyyəti", "en": "construction execution status"},
    "page2_title": {"az": "Gecikmələr, proqnoz və tələb olunan tədbirlər", "en": "Delays, forecast and required actions"},
    "contractor": {"az": "Podratçı", "en": "Contractor"},
    "contract": {"az": "Müqavilə", "en": "Contract"},
    "client": {"az": "Sifarişçi", "en": "Client"},
    "report_date": {"az": "Hesabat tarixi", "en": "Report date"},
    "prepared": {"az": "Hazırlanıb", "en": "Prepared"},
    "page": {"az": "Səhifə", "en": "Page"},
    "source_estimate": {"az": "Fakt % = kumulyativ F-2 / smeta (sahə ölçməsi deyil); plan % = bölmə dəyəri qrafik müddətinə bərabər paylanıb.",
                        "en": "Actual % = cumulative F-2 / estimate (not a site measurement); plan % = section value spread evenly over the scheduled duration."},
    "source_weights": {"az": "Smeta təqdim edilməyib: plan və fakt % qrafikdəki iş çəkiləri və icra faizləri ilə hesablanıb.",
                       "en": "No estimate provided: plan and actual % use the schedule's activity weights and progress."},
    "kpi_contract": {"az": "Müqavilə məbləği (ƏDV ilə)", "en": "Contract value (incl. VAT)"},
    "kpi_plan": {"az": "Qrafik üzrə plan icra", "en": "Planned progress"},
    "kpi_fact": {"az": "Faktiki icra (F-2 dəyəri ilə)", "en": "Actual progress (F-2 value)"},
    "kpi_fact_w": {"az": "Faktiki icra", "en": "Actual progress"},
    "kpi_gap": {"az": "İcra geriliyi", "en": "Progress gap"},
    "kpi_f2": {"az": "F-2 üzrə qəbul edilmiş işlər", "en": "Work accepted by F-2"},
    "kpi_paid": {"az": "Ödənilib (məlum hissə)", "en": "Paid (known part)"},
    "kpi_forecast": {"az": "Proqnoz tamamlanma (ən tez)", "en": "Forecast completion (earliest)"},
    "mln_azn": {"az": "mln AZN", "en": "m AZN"},
    "s_curve": {"az": "Plan–Fakt S-əyrisi", "en": "Plan–actual S-curve"},
    "s_curve_note": {"az": "(kumulyativ, smeta dəyəri ilə çəkilmiş; plan — podratçının iş qrafiki, fakt — aylıq F-2 aktları)",
                     "en": "(cumulative, weighted by estimate value; plan — contractor's programme, actual — monthly F-2 certificates)"},
    "s_curve_note_w": {"az": "(kumulyativ, qrafikdəki iş çəkiləri ilə)", "en": "(cumulative, weighted by schedule activities)"},
    "plan_line": {"az": "Plan (iş qrafiki)", "en": "Plan (programme)"},
    "fact_line": {"az": "Fakt (F-2)", "en": "Actual (F-2)"},
    "fact_line_schedule": {"az": "Fakt (iş qrafiki)", "en": "Actual (schedule)"},
    "contract_end": {"az": "Müqavilə sonu", "en": "Contract end"},
    "monthly": {"az": "Aylıq icra: plan vs F-2", "en": "Monthly work: plan vs F-2"},
    "monthly_unit": {"az": "(mln AZN, ƏDV-siz)", "en": "(m AZN, excl. VAT)"},
    "plan": {"az": "Plan", "en": "Plan"},
    "f2_act": {"az": "F-2 aktı", "en": "F-2 certificate"},
    "works_table": {"az": "Tikinti işləri üzrə Plan–Fakt", "en": "Plan vs actual by work type"},
    "works": {"az": "Tikinti işləri", "en": "Work type"},
    "estimate_mln": {"az": "Smeta, mln", "en": "Estimate, m"},
    "weight": {"az": "Çəki, %", "en": "Weight, %"},
    "fact": {"az": "Fakt", "en": "Actual"},
    "gap_pp": {"az": "Gerilik, f.b.", "en": "Gap, pp"},
    "status": {"az": "Status", "en": "Status"},
    "total_estimate": {"az": "Cəmi (ƏDV-siz smeta)", "en": "Total (estimate excl. VAT)"},
    "total": {"az": "Cəmi", "en": "Total"},
    "key_delays": {"az": "Əsas gecikmələr", "en": "Main delays"},
    "buildings_table": {"az": "Binalar üzrə gerilik", "en": "Delay by building"},
    "buildings_note": {"az": "(fakt %, iş növləri üzrə)", "en": "(actual %, by work type)"},
    "building": {"az": "Bina", "en": "Building"},
    "plan_finish": {"az": "Plan bitmə", "en": "Plan finish"},
    "gap": {"az": "Gerilik", "en": "Gap"},
    "site_row": {"az": "Ərazi abadlığı", "en": "Site works"},
    "general_row": {"az": "Ümumi işlər", "en": "General works"},
    "not_started": {"az": "Başlanmayıb", "en": "Not started"},
    "cards": {"az": "Ən kritik gecikmələr", "en": "Most critical delays"},
    "cause": {"az": "Səbəb", "en": "Cause"},
    "impact": {"az": "Təsir", "en": "Impact"},
    "who": {"az": "Kim / nə", "en": "Who / what"},
    "unconfirmed": {"az": "Təsdiqlənməmiş səbəblər — yoxlanılmalıdır:", "en": "Unconfirmed causes — to be checked:"},
    "forecast": {"az": "Tamamlanma proqnozu", "en": "Completion forecast"},
    "remaining": {"az": "qalan iş", "en": "remaining work"},
    "of_estimate": {"az": "smetanın", "en": "of the estimate"},
    "tile_schedule": {"az": "Qrafik tempi bərpa olunarsa", "en": "If the programme pace is restored"},
    "tile_required": {"az": "Müqavilə sonu üçün lazım olan temp", "en": "Pace needed for the contract date"},
    "tile_current": {"az": "Cari temp", "en": "Current pace"},
    "tile_current_tail": {"az": "davam etsə", "en": "continues"},
    "tile_delay": {"az": "Gecikmə", "en": "Delay"},
    "per_month": {"az": "mln/ay", "en": "m/month"},
    "years_plus": {"az": "3 ildən çox", "en": "over 3 years"},
    "passed": {"az": "müddət bitib", "en": "date passed"},
    "months_short": {"az": "ay", "en": "months"},
    "finance": {"az": "Maliyyə və fiziki icranın müqayisəsi", "en": "Finance vs physical progress"},
    "finance_unit": {"az": "(mln AZN, ƏDV ilə)", "en": "(m AZN, incl. VAT)"},
    "fin_contract": {"az": "Müqavilə məbləği", "en": "Contract value"},
    "fin_works": {"az": "Görülmüş iş (F-2, kumulyativ)", "en": "Work done (F-2, cumulative)"},
    "fin_advance": {"az": "Ödənilmiş avans", "en": "Advance paid"},
    "fin_withheld": {"az": "Aktlardan tutulmuş avans", "en": "Advance recovered from certificates"},
    "fin_remaining": {"az": "Qalıq (bağlanmamış) avans", "en": "Outstanding advance"},
    "fin_payable": {"az": "Hesabat ayı üzrə ödəniləcək", "en": "Payable for the month"},
    "fin_register": {"az": "Aktlar üzrə faktiki ödənişlər", "en": "Actual payments of certificates"},
    "not_provided": {"az": "məlumat təqdim edilməyib", "en": "not provided"},
    "of_f2": {"az": "F-2 dəyərinin", "en": "of the F-2 value"},
    "not_covered": {"az": "görülmüş işlə örtülməyib", "en": "not covered by work done"},
    "physical": {"az": "Fiziki həcmlər (akt / smeta)", "en": "Quantities (certified / estimate)"},
    "actions": {"az": "Podratçıdan tələb olunmalı tədbirlər", "en": "Actions to require from the contractor"},
    "decisions": {"az": "Direktorun qərar verməli olduğu məsələlər", "en": "Decisions for the director"},
    "concrete": {"az": "Beton", "en": "Concrete"},
    "rebar": {"az": "Armatur", "en": "Rebar"},
    "masonry": {"az": "Hörgü", "en": "Masonry"},
    "pp": {"az": "f.b.", "en": "pp"},
    "days": {"az": "gün", "en": "days"},
    "level_of": {"az": "qrafikin {date} səviyyəsi", "en": "programme level of {date}"},
    "share_contract": {"az": "müqavilənin {pct}-i", "en": "{pct} of the contract"},
    "advance_tile": {"az": "avans ({pct})", "en": "advance ({pct})"},
    "no_other_payments": {"az": "digər ödəniş məlumatı yoxdur", "en": "no other payment data"},
    "if_restored": {"az": "qrafik tempi bərpa olunarsa", "en": "if the programme pace is restored"},
    "delay_months": {"az": "≈{n} ay gecikmə", "en": "≈{n} months late"},
    "excl_vat": {"az": "ƏDV-siz", "en": "excl. VAT"},
    "incl_vat": {"az": "ƏDV ilə", "en": "incl. VAT"},
    "footnote2": {"az": "Faktiki ödənişlər, sahə hesabatları və gecikmə bildirişləri təqdim edilmədiyindən qiymətləndirilməyib. f.b. — faiz bəndi.",
                  "en": "Actual payments, site reports and delay notices were not provided and are not assessed. pp — percentage points."},
}


def _l(key: str, lang: str, **kw: Any) -> str:
    text = L[key]["az" if lang == "az" else "en"]
    return text.format(**kw) if kw else text


class _Pdf:
    def __init__(self, lang: str) -> None:
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfgen import canvas

        from .. import reports as base_reports

        base_reports._register_unicode_fonts()
        self.regular = base_reports._REGULAR_FONT
        self.bold = base_reports._BOLD_FONT
        self.colors = colors
        self.ParagraphStyle = ParagraphStyle
        self.lang = lang
        self.buffer = BytesIO()
        self.c = canvas.Canvas(self.buffer, pagesize=(PAGE_W, PAGE_H))

    # coordinates: y grows downward from the top edge for layout convenience
    def Y(self, y: float) -> float:
        return PAGE_H - y

    def color(self, value: str):
        return self.colors.HexColor(value)

    def rect(self, x: float, y: float, w: float, h: float, fill: Optional[str] = None, stroke: Optional[str] = LINE,
             radius: float = 4, width: float = 0.8) -> None:
        c = self.c
        if fill:
            c.setFillColor(self.color(fill))
        if stroke:
            c.setStrokeColor(self.color(stroke))
            c.setLineWidth(width)
        c.roundRect(x, self.Y(y + h), w, h, radius, stroke=1 if stroke else 0, fill=1 if fill else 0)

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = LINE, width: float = 0.8, dash: Optional[Sequence[float]] = None) -> None:
        c = self.c
        c.setStrokeColor(self.color(color))
        c.setLineWidth(width)
        c.setDash(list(dash) if dash else [])
        c.line(x1, self.Y(y1), x2, self.Y(y2))
        c.setDash([])

    def text(self, x: float, y: float, value: str, size: float = 10, bold: bool = False, color: str = INK, align: str = "left") -> float:
        c = self.c
        font = self.bold if bold else self.regular
        c.setFont(font, size)
        c.setFillColor(self.color(color))
        baseline = self.Y(y + size * 0.82)
        if align == "right":
            c.drawRightString(x, baseline, value)
        elif align == "center":
            c.drawCentredString(x, baseline, value)
        else:
            c.drawString(x, baseline, value)
        from reportlab.pdfbase.pdfmetrics import stringWidth

        return stringWidth(value, font, size)

    def width(self, value: str, size: float, bold: bool = False) -> float:
        from reportlab.pdfbase.pdfmetrics import stringWidth

        return stringWidth(value, self.bold if bold else self.regular, size)

    def para(self, x: float, y: float, w: float, markup: str, size: float = 10.5, color: str = INK, leading: Optional[float] = None,
             max_h: Optional[float] = None, min_size: float = 8.5, align: int = 0) -> float:
        """Draw wrapped text; shrinks the font to fit ``max_h``. Returns the height used."""
        from reportlab.platypus import Paragraph

        current = size
        while True:
            style = self.ParagraphStyle("p", fontName=self.regular, fontSize=current, leading=leading or current * 1.3,
                                        textColor=self.color(color), alignment=align)
            p = Paragraph(markup, style)
            _, h = p.wrap(w, 10_000)
            if max_h is None or h <= max_h or current <= min_size:
                p.drawOn(self.c, x, self.Y(y + h))
                return h
            current -= 0.25

    def para_block(self, x: float, y: float, w: float, items: Sequence[str], size: float = 10.5, max_h: float = 200,
                   gap: float = 4, min_size: float = 8.3, indent: float = 0, prefix: Optional[Callable[[int, float, float], None]] = None) -> float:
        """Draw several paragraphs with one font size, the largest that fits."""
        from reportlab.platypus import Paragraph

        current = size
        while True:
            style = self.ParagraphStyle("b", fontName=self.regular, fontSize=current, leading=current * 1.3, textColor=self.color(INK))
            paras = [Paragraph(item, style) for item in items]
            heights = [p.wrap(w - indent, 10_000)[1] for p in paras]
            total = sum(heights) + gap * max(0, len(items) - 1)
            if total <= max_h or current <= min_size:
                break
            current -= 0.25
        cy = y
        for i, (p, h) in enumerate(zip(paras, heights)):
            if prefix:
                prefix(i, cy, current)
            p.drawOn(self.c, x + indent, self.Y(cy + h))
            cy += h + gap
        return cy - y

    def bold_markup(self, text: str) -> str:
        return f"<font name='{self.bold}'>{escape(text)}</font>"

    def panel_title(self, x: float, y: float, title: str, note: str = "", size: float = 13) -> None:
        w = self.text(x, y, title, size=size, bold=True, color=INK)
        if note:
            self.text(x + w + 6, y + 2.5, note, size=9.5, color=MUTED)

    def table(self, x: float, y: float, widths: Sequence[float], rows: List[List[Any]], *, size: float = 10, row_h: float = 19,
              header_size: float = 9.5, aligns: Optional[Sequence[str]] = None, styles: Optional[Callable[[int, int, Any], Dict[str, Any]]] = None,
              bold_last: bool = False) -> float:
        aligns = aligns or ["left"] + ["right"] * (len(widths) - 1)
        cy = y
        for r, row in enumerate(rows):
            is_header = r == 0
            h = row_h if not is_header else row_h + 1
            cx = x
            for ci, value in enumerate(row):
                w = widths[ci]
                st = styles(r, ci, value) if styles else {}
                if st.get("fill"):
                    self.rect(cx + 1, cy + 2, w - 2, h - 4, fill=st["fill"], stroke=None, radius=2)
                align = aligns[ci]
                tx = cx + 5 if align == "left" else (cx + w - 5 if align == "right" else cx + w / 2)
                cell_size = header_size if is_header else size
                cell_text = str(value if value is not None else "")
                cell_bold = is_header or st.get("bold", False) or (bold_last and r == len(rows) - 1)
                while cell_size > 7.2 and self.width(cell_text, cell_size, cell_bold) > w - 8 and not st.get("overflow"):
                    cell_size -= 0.25
                self.text(tx, cy + (h - cell_size) / 2, cell_text,
                          size=cell_size,
                          bold=cell_bold,
                          color=st.get("color", MUTED if is_header else INK), align=align)
                cx += w
            cy += h
            if is_header:
                self.line(x, cy, x + sum(widths), cy, color=INK, width=0.9)
            elif bold_last and r == len(rows) - 2:
                self.line(x, cy, x + sum(widths), cy, color=INK, width=0.9)
            else:
                self.line(x, cy, x + sum(widths), cy, color=LINE, width=0.5)
        return cy - y

    def finish(self) -> bytes:
        self.c.save()
        return self.buffer.getvalue()


# ----------------------------------------------------------------- helpers
def _d(value: Optional[str]) -> Optional[date]:
    return date.fromisoformat(value) if value else None


def _short_date(value: Optional[str]) -> str:
    d = _d(value)
    return d.strftime("%d.%m.%y") if d else "—"


def _status_color(status: str) -> Tuple[str, str]:
    return {"critical": (RED, RED_BG), "serious": (AMBER, AMBER_BG), "minor": (AMBER, AMBER_BG)}.get(status, ("#2E7D32", GREEN_BG))


def _signed(value: Optional[float], lang: str, digits: int = 0) -> str:
    if value is None:
        return "—"
    text = num(abs(value), digits, lang)
    return f"−{text}" if value < 0 else f"+{text}" if value > 0 else text


def _month_label(d: date, lang: str, first: bool = False) -> str:
    names = MONTHS_AZ if lang == "az" else MONTHS_EN
    return f"{names[d.month - 1]} {str(d.year)[2:]}" if first or d.month == 1 else names[d.month - 1]


# ------------------------------------------------------------------ page 1
def _header(pdf: _Pdf, r: Dict[str, Any], project: Dict[str, Any], lang: str, page: int, title: str) -> float:
    contract = r["contract"]
    y = M - 4
    pdf.text(M, y, title, size=21, bold=True, color=NAVY)
    parts = []
    contractor = contract.get("contractor") or project.get("contractor")
    if contractor:
        parts.append(f"{_l('contractor', lang)}: {contractor}")
    if contract.get("number") or contract.get("signed"):
        parts.append(f"{_l('contract', lang)} №{contract.get('number') or '—'}" + (f", {dmy(_d(contract.get('signed')))}" if contract.get("signed") else ""))
    client = contract.get("client") or project.get("client")
    if client:
        parts.append(f"{_l('client', lang)}: {client}")
    sub = " · ".join(parts)
    report_date = _d(r["report_date"])
    right1 = f"{_l('report_date', lang)}: {dmy(report_date)}"
    if r["finance"].get("f3_number"):
        right1 += f" (F-2/F-3 №{r['finance']['f3_number']})"
    right2 = f"{_l('prepared', lang)}: {dmy(date.today())} · {_l('page', lang)} {page}/2"
    pdf.text(PAGE_W - M, y + 4, right1, size=11, bold=True, color=INK, align="right")
    pdf.text(PAGE_W - M, y + 20, right2, size=10, color=MUTED, align="right")
    y += 30
    if sub:
        pdf.text(M, y, sub, size=11, color=INK)
        y += 16
    return y


def _page1(pdf: _Pdf, r: Dict[str, Any], project: Dict[str, Any], lang: str) -> None:
    T, F, fin, texts = r["totals"], r["forecast"], r["finance"], r["texts"][lang]
    money = r["method"] == "estimate_value"
    name = project.get("name") or r["contract"].get("subject") or "Layihə"
    y = _header(pdf, r, project, lang, 1, f"{name} — {_l('status_title', lang)}")
    pdf.text(M, y, _l("source_estimate" if money else "source_weights", lang), size=9.5, color=MUTED)
    y += 16
    pdf.line(M, y, PAGE_W - M, y, color=NAVY, width=1.4)
    y += 8

    # Key message banner.
    banner_h = 44
    pdf.rect(M, y, PAGE_W - 2 * M, banner_h, fill=NAVY, stroke=None, radius=3)
    head = escape(texts["key_message_head"])
    tail = escape(texts["key_message_tail"])
    pdf.para(M + 14, y + 7, PAGE_W - 2 * M - 28, f"<font name='{pdf.bold}'>{head}</font> {tail}", size=12.5, color="#FFFFFF",
             max_h=banner_h - 10, min_size=10)
    y += banner_h + 10

    # KPI tiles.
    report_date = _d(r["report_date"])
    contract = r["contract"]
    finish = _d(contract.get("finish"))
    tiles: List[Tuple[str, str, str, str, str]] = []  # label, value, unit/caption, fill, value colour
    tiles.append((_l("kpi_contract", lang), mln(fin.get("contract_value"), lang),
                  f"{_l('mln_azn', lang)} · {'bitmə' if lang == 'az' else 'finish'}: {dmy(finish)}"
                  + (f" ({num(contract.get('duration_months'), 0, lang)} {_l('months_short', lang)})" if contract.get("duration_months") else ""),
                  SOFT, INK))
    tiles.append((_l("kpi_plan", lang), pct(T["plan_pct"], lang),
                  f"{dmy(report_date)}{'-ya' if lang == 'az' else ''} · {'qrafik sonu' if lang == 'az' else 'programme end'} {dmy(_d(r['baseline_finish']))}",
                  SOFT, INK))
    fact_caption = (f"{mln(T['cum_value'], lang)} / {mln(T['estimate_value'], lang)} mln ({_l('excl_vat', lang)})" if money else "")
    tiles.append((_l("kpi_fact" if money else "kpi_fact_w", lang), pct(T["fact_pct"], lang), fact_caption, AMBER_BG, INK))
    tiles.append((_l("kpi_gap", lang), f"{_signed(T['gap_pp'], lang, 1)} {_l('pp', lang)}",
                  f"≈{T['delay_days']} {_l('days', lang)} ({_l('level_of', lang, date=dmy(_d(T['earned_schedule_date'])))})", RED_BG, RED))
    if money:
        works = fin.get("works_cum_with_vat")
        share = fin.get("works_share_of_contract_pct")
        tiles.append((_l("kpi_f2", lang), mln(works, lang),
                      f"{_l('mln_azn', lang)} {_l('incl_vat', lang)}" + (f" · {_l('share_contract', lang, pct=pct(share, lang))}" if share else ""), SOFT, INK))
        if fin.get("advance_received"):
            adv_pct = fin.get("advance_pct")
            tiles.append((_l("kpi_paid", lang), mln(fin["advance_received"], lang),
                          f"{_l('mln_azn', lang)} {_l('advance_tile', lang, pct=pct(adv_pct, lang, 0) if adv_pct else '—')} · {_l('no_other_payments', lang)}",
                          SOFT, INK))
        else:
            tiles.append((_l("kpi_paid", lang), "—", _l("not_provided", lang), SOFT, INK))
    earliest = _d(F["earliest_finish"])
    delay_m = round((F["delay_vs_contract_days"] or 0) / 30.44)
    tiles.append((_l("kpi_forecast", lang), month_year(earliest, lang),
                  _l("if_restored", lang) + (f"; {_l('delay_months', lang, n=delay_m)}" if delay_m > 0 else ""), AMBER_BG, RED))
    tile_h = 90
    gap = 9
    tw = (PAGE_W - 2 * M - gap * (len(tiles) - 1)) / len(tiles)
    for i, (label, value, caption, fill, value_color) in enumerate(tiles):
        tx = M + i * (tw + gap)
        pdf.rect(tx, y, tw, tile_h, fill=fill, stroke=LINE)
        label_h = pdf.para(tx + 9, y + 7, tw - 18, escape(label), size=10, color=MUTED, max_h=26, min_size=8.5)
        size = 22 if pdf.width(value, 22, True) < tw - 18 else 17
        vy = y + 7 + label_h + 3
        pdf.text(tx + 9, vy, value, size=size, bold=True, color=value_color)
        pdf.para(tx + 9, vy + size + 4, tw - 18, escape(caption), size=9.5, color=MUTED, max_h=y + tile_h - (vy + size + 4) - 4, min_size=8)
    y += tile_h + GAP

    # Charts row.
    chart_h = 200
    left_w = (PAGE_W - 2 * M) * 0.60
    right_w = PAGE_W - 2 * M - left_w - GAP
    pdf.rect(M, y, left_w, chart_h, fill=PANEL)
    pdf.rect(M + left_w + GAP, y, right_w, chart_h, fill=PANEL)
    _s_curve(pdf, r, lang, M + 10, y + 8, left_w - 20, chart_h - 16)
    _monthly_chart(pdf, r, lang, M + left_w + GAP + 10, y + 8, right_w - 20, chart_h - 16)
    y += chart_h + GAP

    # Tables row.
    bottom = PAGE_H - M
    left_w = (PAGE_W - 2 * M) * 0.47
    right_w = PAGE_W - 2 * M - left_w - GAP
    h = bottom - y
    pdf.rect(M, y, left_w, h, fill=PANEL)
    pdf.rect(M + left_w + GAP, y, right_w, h, fill=PANEL)
    _works_table(pdf, r, lang, M + 10, y + 9, left_w - 20, h - 18)
    _buildings_table(pdf, r, lang, M + left_w + GAP + 10, y + 9, right_w - 20, h - 18)


def _s_curve(pdf: _Pdf, r: Dict[str, Any], lang: str, x: float, y: float, w: float, h: float) -> None:
    money = r["method"] == "estimate_value"
    pdf.panel_title(x, y, _l("s_curve", lang), _l("s_curve_note" if money else "s_curve_note_w", lang), size=12.5)
    # Legend.
    ly = y + 20
    lx = x
    for label, color, dash in ((_l("plan_line", lang), BLUE, (4, 3)), (_l("fact_line" if r["method"] == "estimate_value" else "fact_line_schedule", lang), ORANGE, None), (_l("contract_end", lang), RED, (2, 2))):
        pdf.line(lx, ly + 6, lx + 18, ly + 6, color=color, width=2, dash=dash)
        lx += 22 + pdf.text(lx + 22, ly, label, size=9.5, color=INK) + 14
    top, left = y + 40, x + 34
    plot_w, plot_h = w - 44, h - 62
    months = [_d(p["month"]) for p in r["monthly"]]
    start = _d(r["project_start"]).replace(day=1)
    end = months[-1]
    span = max(1, (end - start).days)

    def px(d: date) -> float:
        return left + (d - start).days / span * plot_w

    def py(v: float) -> float:
        return top + plot_h - v / 100 * plot_h

    for v in (0, 20, 40, 60, 80, 100):
        pdf.line(left, py(v), left + plot_w, py(v), color="#ECEEF1", width=0.6)
        pdf.text(left - 4, py(v) - 4.5, f"{v}%", size=8.5, color=MUTED, align="right")
    step = 1 if len(months) <= 18 else 2
    for i, m in enumerate(months):
        if i % step == 0:
            pdf.text(px(m.replace(day=15)), top + plot_h + 4, _month_label(m, lang, first=i == 0), size=8.5, color=MUTED, align="center")
    # Plan (dashed) and fact (solid).
    plan_pts = [(px(start), py(0))] + [(px(m), py(p["plan_pct"] or 0)) for m, p in zip(months, r["monthly"])]
    fact_pts = [(px(m), py(p["fact_pct"])) for m, p in zip(months, r["monthly"]) if p.get("fact_pct") is not None]
    c = pdf.c
    for pts, color, dash in ((plan_pts, BLUE, (5, 3)), (fact_pts, ORANGE, None)):
        if len(pts) < 2:
            continue
        c.setStrokeColor(pdf.color(color))
        c.setLineWidth(2)
        c.setDash(list(dash) if dash else [])
        path = c.beginPath()
        path.moveTo(pts[0][0], pdf.Y(pts[0][1]))
        for px_, py_ in pts[1:]:
            path.lineTo(px_, pdf.Y(py_))
        c.drawPath(path, stroke=1, fill=0)
        c.setDash([])
        if color == ORANGE:
            c.setFillColor(pdf.color(ORANGE))
            for px_, py_ in pts:
                c.circle(px_, pdf.Y(py_), 2.2, stroke=0, fill=1)
    T = r["totals"]
    report = _d(r["report_date"])
    rx = px(report)
    pdf.line(rx, top, rx, top + plot_h, color=MUTED, width=0.8, dash=(3, 3))
    pdf.text(rx - 4, top + plot_h * 0.42, f"{_l('report_date', lang)} {dmy(report)}", size=8.5, color=INK, align="right")
    finish = _d(r["contract"].get("finish"))
    if finish and start <= finish <= end:
        fx = px(finish)
        pdf.line(fx, top, fx, top + plot_h, color=RED, width=0.9, dash=(2, 2))
        pdf.text(fx + 4, top + 2, f"{_l('contract_end', lang)}", size=8.5, color=RED)
        pdf.text(fx + 4, top + 13, dmy(finish), size=8.5, color=RED)
    plan_y, fact_y = py(T["plan_pct"] or 0), py(T["fact_pct"] or 0)
    if T["gap_pp"] and T["gap_pp"] < -2:
        pdf.line(rx + 10, plan_y, rx + 10, fact_y, color=RED, width=1.6)
        pdf.text(rx + 16, (plan_y + fact_y) / 2 - 6, f"{_signed(T['gap_pp'], lang, 1)} {_l('pp', lang)}", size=11, bold=True, color=RED)
    pdf.text(rx - 4, plan_y - 15, f"{_l('plan', lang)} {pct(T['plan_pct'], lang)}", size=9.5, bold=True, color=INK, align="right")
    pdf.text(rx - 4, fact_y - 15, f"{_l('fact', lang)} {pct(T['fact_pct'], lang)}", size=9.5, bold=True, color=INK, align="right")
    es = _d(T["earned_schedule_date"])
    if T["delay_days"] > 0 and es:
        pdf.line(px(es), fact_y, rx, fact_y, color=MUTED, width=0.7, dash=(1, 2))
        note = (f"Faktiki həcm plana görə {dmy(es)}-də bitməli idi → ≈{T['delay_days']} gün gerilik" if lang == "az"
                else f"The work done was due by {dmy(es)} → ≈{T['delay_days']} days behind")
        pdf.text(px(es) + 4, fact_y + 4, note, size=8.5, color=MUTED)


def _monthly_chart(pdf: _Pdf, r: Dict[str, Any], lang: str, x: float, y: float, w: float, h: float) -> None:
    pdf.panel_title(x, y, _l("monthly", lang), _l("monthly_unit", lang), size=12.5)
    report = _d(r["report_date"])
    points = [p for p in r["monthly"] if _d(p["month"]) <= report.replace(day=28) + timedelta(days=4)]
    ly = y + 20
    lx = x
    has_plan = any(p.get("plan_value") for p in points)
    for label, color in (((_l("plan", lang), BLUE),) if has_plan else ()) + ((_l("f2_act", lang), ORANGE),):
        pdf.rect(lx, ly + 1, 10, 10, fill=color, stroke=None, radius=1)
        lx += 14 + pdf.text(lx + 14, ly, label, size=9.5) + 14
    note = r["texts"][lang].get("monthly_note") or ""
    note_h = 40 if note else 0
    top, left = y + 38, x + 26
    plot_w, plot_h = w - 30, h - 62 - note_h
    if not points or not any(p.get("plan_value") or p.get("f2_value") for p in points):
        pdf.text(x, top + 20, "—", size=11, color=MUTED)
        return
    values = [max(p.get("plan_value") or 0, p.get("f2_value") or 0) for p in points]
    peak = max(values + [1]) / 1_000_000
    step = 1 if peak <= 6 else 2 if peak <= 12 else 5
    ymax = max(step, ((int(peak) // step) + 1) * step)

    def py(v: float) -> float:
        return top + plot_h - (v / 1_000_000) / ymax * plot_h

    for v in range(0, int(ymax) + 1, step):
        pdf.line(left, py(v * 1_000_000), left + plot_w, py(v * 1_000_000), color="#ECEEF1", width=0.6)
        pdf.text(left - 4, py(v * 1_000_000) - 4.5, str(v), size=8.5, color=MUTED, align="right")
    slot = plot_w / len(points)
    bar = max(2.0, min(12.0, slot * 0.34))
    for i, p in enumerate(points):
        cx = left + slot * i + slot / 2
        pv = p.get("plan_value") or 0
        fv = p.get("f2_value")
        pdf.rect(cx - bar - 1, py(pv), bar, top + plot_h - py(pv), fill=BLUE, stroke=None, radius=0.8) if pv > 0 else None
        if fv:
            pdf.rect(cx + 1, py(fv), bar, top + plot_h - py(fv), fill=ORANGE, stroke=None, radius=0.8)
        elif fv == 0:
            pdf.text(cx + 1 + bar / 2, top + plot_h - 11, "0", size=8, color=MUTED, align="center")
        if len(points) <= 16 or i % 2 == 0:
            pdf.text(cx, top + plot_h + 4, _month_label(_d(p["month"]), lang), size=8, color=MUTED, align="center")
    if note:
        pdf.para(x, top + plot_h + 18, w, escape(note), size=9.5, color=INK, max_h=note_h, min_size=8.5)


def _works_table(pdf: _Pdf, r: Dict[str, Any], lang: str, x: float, y: float, w: float, h: float) -> None:
    money = r["method"] == "estimate_value"
    pdf.panel_title(x, y, _l("works_table", lang), f"({dmy(_d(r['report_date']))})", size=12.5)
    rows: List[List[Any]] = [[_l("works", lang), _l("estimate_mln" if money else "weight", lang), _l("plan", lang), _l("fact", lang),
                              _l("gap_pp", lang), _l("status", lang)]]
    status_of: Dict[int, str] = {}
    for row in r["categories"]:
        name = cat.label(row["category"], lang) if row["category"] in cat.LABELS else ("Digər işlər" if lang == "az" else "Other")
        size = mln(row["value"], lang) if money else pct(row["share_pct"], lang)
        rows.append([name, size, pct(row["plan_pct"], lang, 0), pct(row["fact_pct"], lang), _signed(row["gap_pp"], lang), ""])
        status_of[len(rows) - 1] = row["status"]
    T = r["totals"]
    rows.append([_l("total_estimate" if money else "total", lang), mln(T["estimate_value"], lang) if money else "100%",
                 pct(T["plan_pct"], lang, 0), pct(T["fact_pct"], lang), _signed(T["gap_pp"], lang), ""])
    status_of[len(rows) - 1] = T["status"]
    widths = [w * 0.34, w * 0.13, w * 0.10, w * 0.11, w * 0.13, w * 0.19]

    def style(ri: int, ci: int, value: Any) -> Dict[str, Any]:
        if ri and ci == 4:
            color, _ = _status_color(status_of.get(ri, "on_track"))
            return {"color": color, "bold": True}
        return {}

    row_h = 22
    used = pdf.table(x, y + 24, widths, rows, size=10.5, row_h=row_h, styles=style, bold_last=True,
                     aligns=["left", "right", "right", "right", "right", "left"])
    # Status badges.
    cy = y + 24 + row_h + 1
    for ri in range(1, len(rows)):
        status = status_of.get(ri, "on_track")
        color, fill = _status_color(status)
        label = ("▲ " if status == "critical" else "■ ") + STATUS_LABELS[status]["az" if lang == "az" else "en"]
        bx = x + sum(widths[:5]) + 4
        bw = pdf.width(label, 9.5, True) + 10
        pdf.rect(bx, cy + (row_h - 15) / 2, bw, 15, fill=fill, stroke=None, radius=2)
        pdf.text(bx + 5, cy + (row_h - 9.5) / 2, label, size=9.5, bold=True, color=color)
        cy += row_h
    # Key delays box.
    by = y + 24 + used + 8
    bh = y + h - by
    if bh < 40:
        return
    pdf.rect(x, by, w, bh, fill=SOFT, stroke=None, radius=3)
    pdf.text(x + 10, by + 8, _l("key_delays", lang), size=12, bold=True, color=NAVY)
    items = r["texts"][lang]["key_delays"]
    markups = [f"• <font name='{pdf.bold}' color='{RED}'>{escape(i['title'])}</font> {escape(i['text'])}" for i in items]
    pdf.para_block(x + 12, by + 27, w - 24, markups, size=10.5, max_h=bh - 31, gap=4)


def _buildings_table(pdf: _Pdf, r: Dict[str, Any], lang: str, x: float, y: float, w: float, h: float) -> None:
    pdf.panel_title(x, y, _l("buildings_table", lang), _l("buildings_note", lang), size=12.5)
    cats = [cat.FRAME, cat.MASONRY, cat.ENVELOPE, cat.FINISHING, cat.MEP]
    header = [_l("building", lang), _l("plan_finish", lang), _l("plan", lang), _l("fact", lang), _l("gap", lang)] + [cat.label(c, lang, short=True) for c in cats]
    rows: List[List[Any]] = [header]
    meta: List[Dict[str, Any]] = [{}]
    for b in r["buildings"]:
        if b.get("building"):
            label = b["building"] if lang == "az" else b["building"].replace("Bina-", "Bldg ")
            cells = [num(b["categories"].get(c), 0, lang) if b["categories"].get(c) is not None else "—" for c in cats]
        else:
            label = _l("site_row" if b.get("row") == "site" else "general_row", lang)
            cells = ["", "", "", "", ""]
        rows.append([label, _short_date(b.get("plan_finish")), pct(b["plan_pct"], lang, 0), pct(b["fact_pct"], lang), _signed(b["gap_pp"], lang)] + cells)
        meta.append(b)
    widths = [w * 0.14, w * 0.12, w * 0.08, w * 0.09, w * 0.09] + [w * 0.096] * 5
    n = len(rows)
    row_h = max(15.0, min(26.0, (h - 80) / max(1, n)))
    size = 10.5 if row_h >= 19 else 9.5 if row_h >= 16.5 else 8.8

    def style(ri: int, ci: int, value: Any) -> Dict[str, Any]:
        if ri == 0:
            return {}
        b = meta[ri]
        if ci == 4:
            return {"color": RED if (b.get("gap_pp") or 0) < -15 else INK, "bold": True}
        if ci >= 5 and b.get("building"):
            v = b["categories"].get(cats[ci - 5])
            if v is None:
                return {}
            return {"fill": GREEN_BG if v >= 90 else AMBER_BG if v >= 30 else RED_BG}
        if ci == 5 and not b.get("building"):
            return {"color": MUTED}
        return {}

    aligns = ["left", "left", "right", "right", "right"] + ["center"] * 5
    used = pdf.table(x, y + 24, widths, rows, size=size, row_h=row_h, header_size=9.5, styles=style, aligns=aligns)
    # "Not started" spans the work-type columns of the site row.
    cy = y + 24 + row_h + 1
    for b in meta[1:]:
        if not b.get("building") and b.get("not_started"):
            pdf.text(x + sum(widths[:5]) + 6, cy + (row_h - size) / 2, _l("not_started", lang), size=size, color=MUTED)
        cy += row_h
    tail = r["texts"][lang].get("key_message_tail")
    if tail:
        pdf.para(x, y + 24 + used + 10, w, f"<font name='{pdf.bold}'>{escape(tail)}</font>", size=10.5, max_h=h - used - 36, min_size=8.5)


# ------------------------------------------------------------------ page 2
def _page2(pdf: _Pdf, r: Dict[str, Any], project: Dict[str, Any], lang: str) -> None:
    texts = r["texts"][lang]
    y = _header(pdf, r, project, lang, 2, _l("page2_title", lang))
    pdf.text(M, y, _l("footnote2", lang), size=9.5, color=MUTED)
    y += 16
    pdf.line(M, y, PAGE_W - M, y, color=NAVY, width=1.4)
    y += 10

    cards = texts["delay_cards"]
    pdf.text(M, y, f"{_l('cards', lang)} ({len(cards)})" if cards else _l("cards", lang), size=13, bold=True, color=NAVY)
    y += 22
    card_h = 208
    n = max(1, len(cards))
    cw = (PAGE_W - 2 * M - 10 * (n - 1)) / n
    for i, card in enumerate(cards):
        cx = M + i * (cw + 10)
        color, _ = _status_color(card.get("severity", "serious"))
        pdf.rect(cx, y, cw, card_h, fill=PANEL)
        pdf.rect(cx, y, cw, 4, fill=color, stroke=None, radius=1)
        title_h = pdf.para(cx + 10, y + 11, cw - 20, f"<font name='{pdf.bold}'>{i + 1}. {escape(card['title'])}</font>", size=11.5, max_h=30, min_size=10)
        fy = y + 11 + title_h + 4
        pdf.text(cx + 10, fy, card["figure"], size=15, bold=True, color=RED if card.get("severity") == "critical" else AMBER)
        markups = []
        for key in ("cause", "impact", "who"):
            markups.append(f"<font name='{pdf.bold}' color='{NAVY}'>{escape(_l(key, lang))}</font><br/>{escape(card.get(key) or '—')}")
        pdf.para_block(cx + 10, fy + 24, cw - 20, markups, size=10.5, max_h=y + card_h - fy - 30, gap=5)
    y += card_h + 8
    used = pdf.para(M, y, PAGE_W - 2 * M,
                    f"<font name='{pdf.bold}' color='{AMBER}'>{escape(_l('unconfirmed', lang))}</font> {escape(texts['unconfirmed_causes'])}",
                    size=10.5, max_h=30)
    y += used + 10

    # Forecast + finance row.
    row_h = 236
    lw = (PAGE_W - 2 * M - GAP) / 2
    pdf.rect(M, y, lw, row_h, fill=PANEL)
    pdf.rect(M + lw + GAP, y, lw, row_h, fill=PANEL)
    _forecast_panel(pdf, r, lang, M + 10, y + 9, lw - 20, row_h - 18)
    _finance_panel(pdf, r, lang, M + lw + GAP + 10, y + 9, lw - 20, row_h - 18)
    y += row_h + GAP

    # Actions + decisions row.
    h = PAGE_H - M - y
    pdf.rect(M, y, lw, h, fill=PANEL)
    pdf.rect(M + lw + GAP, y, lw, h, fill=PANEL, stroke=NAVY, width=1.4)
    pdf.text(M + 10, y + 9, _l("actions", lang), size=12.5, bold=True, color=INK)
    items = texts["contractor_actions"]
    markups = [f"• <font name='{pdf.bold}'>{escape(i['title'])}</font> {escape(i['text'])}" for i in items]
    pdf.para_block(M + 14, y + 32, lw - 30, markups, size=10.5, max_h=h - 38, gap=4)
    dx = M + lw + GAP
    pdf.text(dx + 10, y + 9, _l("decisions", lang), size=12.5, bold=True, color=INK)
    items = texts["director_decisions"]

    def badge(i: int, cy: float, size: float) -> None:
        pdf.c.setFillColor(pdf.color(NAVY))
        pdf.c.circle(dx + 20, pdf.Y(cy + size * 0.65), 7.5, stroke=0, fill=1)
        pdf.text(dx + 20, cy + size * 0.65 - 4.5, str(i + 1), size=9, bold=True, color="#FFFFFF", align="center")

    markups = [f"<font name='{pdf.bold}'>{escape(i['title'])}</font> {escape(i['text'])}" for i in items]
    pdf.para_block(dx + 10, y + 32, lw - 24, markups, size=10.5, max_h=h - 38, gap=4, indent=24, prefix=badge)


def _forecast_panel(pdf: _Pdf, r: Dict[str, Any], lang: str, x: float, y: float, w: float, h: float) -> None:
    F, texts = r["forecast"], r["texts"][lang]
    money = r["method"] == "estimate_value"
    note = ""
    if money and F.get("remaining_value") is not None:
        note = f"({_l('remaining', lang)}: {mln(F['remaining_value'], lang)} {_l('mln_azn', lang)} {_l('excl_vat', lang)}, {_l('of_estimate', lang)} {pct(F['remaining_pct'], lang)}" + ("-i)" if lang == "az" else ")")
    pdf.panel_title(x, y, _l("forecast", lang), note, size=12.5)
    tiles = []
    earliest = _d(F["earliest_finish"])
    sched = f" ({pace(F, 'schedule_pace', lang, 1)})" if F.get("schedule_pace") else ""
    tiles.append((_l("tile_schedule", lang) + sched, dmy(earliest), SOFT, INK))
    if F.get("required_pace"):
        tiles.append((_l("tile_required", lang), pace(F, "required_pace", lang, 1), RED_BG, RED))
    else:
        tiles.append((_l("tile_required", lang), _l("passed", lang), RED_BG, RED))
    if F.get("recent_pace") is not None:
        cur = _l("years_plus", lang) if F["current_pace_unacceptable"] else dmy(_d(F.get("current_pace_finish")))
        tiles.append((f"{_l('tile_current', lang)} ({pace(F, 'recent_pace', lang)}) {_l('tile_current_tail', lang)}", cur, RED_BG, RED))
    delay = F.get("delay_vs_contract_days")
    if delay is not None:
        months = round(delay / 30.44, 0)
        contract_finish = _d(r["contract"].get("finish"))
        tiles.append((f"{_l('tile_delay', lang)} ({'müqavilə' if lang == 'az' else 'vs contract'} {dmy(contract_finish)})",
                      f"≈{num(months, 0, lang)} {_l('months_short', lang)}" if delay > 0 else "0", SOFT, INK))
    tw = (w - 8 * (len(tiles) - 1)) / max(1, len(tiles))
    ty = y + 24
    for i, (label, value, fill, color) in enumerate(tiles):
        tx = x + i * (tw + 8)
        pdf.rect(tx, ty, tw, 66, fill=fill)
        pdf.para(tx + 8, ty + 6, tw - 16, escape(label), size=9.5, color=MUTED, max_h=28, min_size=8)
        pdf.text(tx + 8, ty + 40, value, size=15, bold=True, color=color)
    cy = ty + 76
    markups = []
    for line in texts["forecast_lines"]:
        first, _, rest = line.partition(":")
        markups.append(f"• <font name='{pdf.bold}'>{escape(first)}</font>:{escape(rest)}" if rest and len(first) < 70 else f"• {escape(line)}")
    pdf.para_block(x + 4, cy, w - 8, markups, size=10.5, max_h=y + h - cy, gap=3)


def _finance_panel(pdf: _Pdf, r: Dict[str, Any], lang: str, x: float, y: float, w: float, h: float) -> None:
    fin, texts = r["finance"], r["texts"][lang]
    pdf.panel_title(x, y, _l("finance", lang), _l("finance_unit", lang), size=12.5)
    value = fin.get("contract_value") or 0
    rows = [
        ("fin_contract", fin.get("contract_value"), "#9AA3B2", ""),
        ("fin_works", fin.get("works_cum_with_vat"), ORANGE, ""),
        ("fin_advance", fin.get("advance_received"), BLUE, f"({pct(fin.get('advance_pct'), lang, 0)})" if fin.get("advance_pct") else ""),
        ("fin_withheld", fin.get("advance_withheld"), None,
         f"{_l('of_f2', lang)} {pct(fin.get('advance_withheld_share_pct'), lang, 0)}{'-i' if lang == 'az' else ''}" if fin.get("advance_withheld_share_pct") else ""),
        ("fin_remaining", fin.get("advance_remaining"), None, _l("not_covered", lang) if fin.get("advance_remaining") else ""),
    ]
    if fin.get("payable_period") is not None:
        rows.append(("fin_payable", fin.get("payable_period"), None, ""))
    rows.append(("fin_register", None, None, _l("not_provided", lang)))
    cy = y + 26
    label_w = w * 0.42
    num_w = w * 0.12
    bar_w = w - label_w - num_w - 16
    for key, amount, color, note in rows:
        bold = key == "fin_remaining"
        label = _l(key, lang) + (f" {note}" if key == "fin_advance" and note else "")
        pdf.text(x + 4, cy, label, size=10.5, bold=bold, color=INK)
        pdf.text(x + label_w + num_w, cy, mln(amount, lang) if amount is not None else "—", size=10.5, bold=bold or key == "fin_contract",
                 color=RED if key == "fin_remaining" and amount else INK, align="right")
        bx = x + label_w + num_w + 12
        if color and amount and value:
            pdf.rect(bx, cy + 2, bar_w, 9, fill="#ECEEF1", stroke=None, radius=1.5)
            pdf.rect(bx, cy + 2, max(2, bar_w * min(1.0, amount / value)), 9, fill=color, stroke=None, radius=1.5)
        elif note and key != "fin_advance":
            pdf.text(bx, cy + 0.5, note, size=9.5, color=RED if key == "fin_remaining" else MUTED)
        cy += 17.5
        pdf.line(x, cy - 3, x + w, cy - 3, color="#EEF0F3", width=0.5)
    cy += 4
    notes = list(texts.get("finance_notes") or [])
    phys = r["physical"]["quantities"]
    if phys:
        parts = []
        for q in phys:
            parts.append(f"{_l(q['kind'], lang)} {num(q['cum_qty'], 0, lang)}/{num(q['estimate_qty'], 0, lang)} {q.get('unit') or ''} ({pct(q['pct'], lang, 0)})")
        notes.append(f"{_l('physical', lang)}: " + "; ".join(parts) + ".")
    pdf.para_block(x + 4, cy, w - 8, [f"• {escape(n)}" for n in notes], size=10.5, max_h=y + h - cy, gap=3)


def build_executive_pdf(result: Dict[str, Any], lang: str = "az") -> bytes:
    lang = "az" if str(lang or "").lower().startswith("az") else "en"
    r = result["executive"]
    project = result.get("project") or {}
    pdf = _Pdf(lang)
    pdf.c.setTitle(f"{project.get('name') or 'DevBareun'} — {_l('status_title', lang)}")
    pdf.c.setAuthor("DevBareun")
    _page1(pdf, r, project, lang)
    pdf.c.showPage()
    _page2(pdf, r, project, lang)
    pdf.c.showPage()
    return pdf.finish()


def report_filename(result: Dict[str, Any], lang: str = "az") -> str:
    """``<Project> icra hesabatı -<month>.<year>.pdf``."""
    project = (result.get("project") or {}).get("name") or "Layihe"
    d = _d((result.get("executive") or {}).get("report_date"))
    stamp = f"{d.month:02d}.{d.year}" if d else ""
    word = "icra hesabatı" if lang == "az" else "execution report"
    safe = "".join(ch for ch in project if ch not in '\\/:*?"<>|').strip()[:80]
    return f"{safe} {word} -{stamp}.pdf"
