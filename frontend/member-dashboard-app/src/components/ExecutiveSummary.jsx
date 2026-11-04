import { AlertTriangle, CalendarClock, Gavel, TrendingDown, Wallet } from "lucide-react";

// Labels for the execution report (estimate-weighted plan, earned schedule).
export const EX = {
  az: {
    planPct: "Qrafik üzrə plan",
    planCol: "Plan",
    factCol: "Fakt",
    factPct: "Faktiki icra",
    factNote: "kumulyativ F-2 / smeta (ƏDV-siz)",
    factNoteSchedule: "qrafikdəki iş çəkiləri ilə",
    gap: "İcra geriliyi",
    pts: "f.b.",
    behind: "gün geridə",
    level: "qrafikin {date} səviyyəsi",
    earliest: "Proqnoz bitmə (ən tez)",
    contractEnd: "müqavilə sonu",
    penalty: "Cərimə limiti",
    penaltyNote: "{pct}%/gün · limit {cap}% · {days} gün",
    advance: "Qalıq avans",
    advanceNote: "görülmüş iş (ƏDV ilə) {works} mln",
    mln: "mln AZN",
    workTypes: "Tikinti işləri üzrə plan və fakt",
    buildings: "Binalar üzrə icra",
    building: "Bina",
    workType: "İş növü",
    weight: "Çəki",
    planFinish: "Plan bitmə",
    gapCol: "Gerilik",
    statusCol: "Status",
    total: "Cəmi",
    site: "Ərazi abadlığı və şəbəkələr",
    notStarted: "Başlanmayıb",
    cards: "Əsas gecikmələr",
    cause: "Səbəb",
    impact: "Təsir",
    who: "Kim / nə",
    unconfirmed: "Təsdiqlənməmiş səbəblər — yoxlanılmalıdır:",
    forecast: "Tamamlanma proqnozu",
    finance: "Maliyyə və fiziki icra",
    contractorActions: "Podratçıdan tələb olunmalı tədbirlər",
    decisions: "Direktorun qərar verməli olduğu məsələlər",
    factIsMoney: "Fakt % F-2 aktlarının dəyərinə görədir, fiziki icra faizi deyil.",
    cat: { frame: "Torpaq və dəmir-beton", masonry: "Hörgü", envelope: "Dam, fasad, qapı-pəncərə", finishing: "Tamamlama", mep: "MEP və lift", site: "Ərazi abadlığı", other: "Digər işlər" },
    catShort: { frame: "Karkas", masonry: "Hörgü", envelope: "Dam/fasad", finishing: "Tamaml.", mep: "MEP" },
    st: { on_track: "Qrafik üzrə", minor: "Az gecikmə", serious: "Ciddi gerilik", critical: "Kritik" }
  },
  en: {
    planPct: "Planned by the schedule",
    planCol: "Plan",
    factCol: "Actual",
    factPct: "Actual progress",
    factNote: "cumulative F-2 / estimate (excl. VAT)",
    factNoteSchedule: "by schedule activity weights",
    gap: "Progress gap",
    pts: "pts",
    behind: "days behind",
    level: "schedule level of {date}",
    earliest: "Earliest completion",
    contractEnd: "contract end",
    penalty: "Penalty cap",
    penaltyNote: "{pct}%/day · cap {cap}% · {days} days",
    advance: "Outstanding advance",
    advanceNote: "work done (incl. VAT) {works} m",
    mln: "m AZN",
    workTypes: "Plan and actual by work type",
    buildings: "Progress by building",
    building: "Building",
    workType: "Work type",
    weight: "Weight",
    planFinish: "Plan finish",
    gapCol: "Gap",
    statusCol: "Status",
    total: "Total",
    site: "Site works and networks",
    notStarted: "Not started",
    cards: "Key delays",
    cause: "Cause",
    impact: "Impact",
    who: "Who / what",
    unconfirmed: "Unconfirmed causes — to be checked:",
    forecast: "Completion forecast",
    finance: "Finance and physical progress",
    contractorActions: "Actions to require from the contractor",
    decisions: "Decisions for the director",
    factIsMoney: "Actual % is by F-2 certified value, not a physical progress measurement.",
    cat: { frame: "Earthworks and reinforced concrete", masonry: "Masonry", envelope: "Roof, facade, doors and windows", finishing: "Finishing works", mep: "MEP and lifts", site: "Site works and landscaping", other: "Other works" },
    catShort: { frame: "Frame", masonry: "Masonry", envelope: "Envelope", finishing: "Finishing", mep: "MEP" },
    st: { on_track: "On track", minor: "Minor delay", serious: "Serious delay", critical: "Critical" }
  }
};

const CATS = ["frame", "masonry", "envelope", "finishing", "mep"];

function num(value, digits, lang) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const text = Number(value).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return lang === "az" ? text.replace(/,/g, " ").replace(".", ",") : text;
}

const pct = (value, lang, digits = 1) => (value === null || value === undefined ? "—" : `${num(value, digits, lang)}%`);
const mln = (value, lang, digits = 2) => (value === null || value === undefined ? "—" : num(value / 1_000_000, digits, lang));
const day = (value) => {
  if (!value) return "—";
  const [y, m, d] = String(value).slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
};
const fill = (text, values) => Object.entries(values).reduce((out, [k, v]) => out.replace(`{${k}}`, v), text);

function tone(status) {
  return { on_track: "success", minor: "neutral", serious: "warning", critical: "danger" }[status] || "neutral";
}

function cellTone(value) {
  if (value === null || value === undefined) return "";
  if (value >= 90) return "ex-cell-good";
  if (value >= 50) return "ex-cell-mid";
  if (value >= 10) return "ex-cell-low";
  return "ex-cell-none";
}

function Tile({ icon: Icon, label, value, note, toneName = "neutral" }) {
  return (
    <article className={`delay-kpi ${toneName}`}>
      <div className="delay-kpi-head">{Icon && <Icon size={16} />}<span>{label}</span></div>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </article>
  );
}

/** Executive KPIs: plan, actual, gap, forecast, penalty, advance. */
export function ExecutiveKpis({ ex, lang }) {
  const x = EX[lang] || EX.en;
  const T = ex.totals;
  const F = ex.forecast;
  const P = ex.penalty;
  const fin = ex.finance || {};
  const money = ex.method === "estimate_value";
  return (
    <section className="delay-kpis ex-kpis">
      <Tile label={x.planPct} value={pct(T.plan_pct, lang)} note={day(ex.report_date)} />
      <Tile icon={TrendingDown} label={x.factPct} value={pct(T.fact_pct, lang)} note={money ? x.factNote : x.factNoteSchedule} toneName="warning" />
      <Tile icon={AlertTriangle} label={x.gap} value={`${num(T.gap_pp, 1, lang)} ${x.pts}`}
        note={`≈${T.delay_days} ${x.behind} · ${fill(x.level, { date: day(T.earned_schedule_date) })}`} toneName={tone(T.status)} />
      <Tile icon={CalendarClock} label={x.earliest} value={day(F.earliest_finish)}
        note={ex.contract?.finish ? `${x.contractEnd} ${day(ex.contract.finish)}` : ""} toneName={F.contract_feasible ? "success" : "danger"} />
      {P && P.cap_date && (
        <Tile icon={Gavel} label={x.penalty} value={day(P.cap_date)}
          note={`${fill(x.penaltyNote, { pct: num(P.pct_per_day, 1, lang), cap: num(P.cap_pct, 0, lang), days: P.cap_days })}${P.cap_amount ? ` · ${mln(P.cap_amount, lang)} ${x.mln}` : ""}`} toneName="danger" />
      )}
      {fin.advance_remaining !== null && fin.advance_remaining !== undefined && (
        <Tile icon={Wallet} label={x.advance} value={`${mln(fin.advance_remaining, lang)} ${x.mln}`}
          note={fill(x.advanceNote, { works: mln(fin.works_cum_with_vat, lang) })} toneName={fin.advance_guarantee_risk ? "danger" : "neutral"} />
      )}
    </section>
  );
}

/** Work-type and building tables, delay cards, forecast, finance, actions. */
export function ExecutiveDetails({ ex, lang }) {
  const x = EX[lang] || EX.en;
  const texts = ex.texts?.[lang] || ex.texts?.en || {};
  const rows = ex.categories || [];
  const buildings = ex.buildings || [];
  const T = ex.totals;
  const cats = CATS.filter((c) => buildings.some((b) => b.categories && b.categories[c] !== undefined));
  return (
    <>
      <section className="delay-grid">
        <article className="panel delay-wide">
          <header className="delay-section-head"><h2>{x.workTypes}</h2><span>{day(ex.report_date)}</span></header>
          <div className="delay-table-wrap">
            <table className="delay-table ex-table">
              <thead><tr><th>{x.workType}</th><th>{x.weight}</th><th>{x.planCol}</th><th>{x.factCol}</th><th>{x.gapCol}</th><th>{x.statusCol}</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.category}>
                    <td>{x.cat[r.category] || r.category}</td>
                    <td>{pct(r.share_pct, lang)}</td>
                    <td>{pct(r.plan_pct, lang, 0)}</td>
                    <td>{pct(r.fact_pct, lang)}</td>
                    <td className={r.gap_pp < -5 ? "late" : ""}>{num(r.gap_pp, 0, lang)}</td>
                    <td><span className={`status-pill ${tone(r.status)}`}>{x.st[r.status] || r.status}</span></td>
                  </tr>
                ))}
                <tr className="ex-total">
                  <td>{x.total}</td><td>100%</td><td>{pct(T.plan_pct, lang, 0)}</td><td>{pct(T.fact_pct, lang)}</td>
                  <td className="late">{num(T.gap_pp, 0, lang)}</td>
                  <td><span className={`status-pill ${tone(T.status)}`}>{x.st[T.status] || T.status}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
        <article className="panel delay-wide">
          <header className="delay-section-head"><h2>{x.buildings}</h2><span>{x.factPct} %</span></header>
          <div className="delay-table-wrap">
            <table className="delay-table ex-table">
              <thead><tr><th>{x.building}</th><th>{x.planFinish}</th><th>{x.planCol}</th><th>{x.factCol}</th><th>{x.gapCol}</th>{cats.map((c) => <th key={c}>{x.catShort[c]}</th>)}</tr></thead>
              <tbody>
                {buildings.map((b) => (
                  <tr key={b.building || b.row}>
                    <td>{b.row === "site" ? x.site : b.building || x.total}</td>
                    <td>{day(b.plan_finish)}</td>
                    <td>{pct(b.plan_pct, lang, 0)}</td>
                    <td>{pct(b.fact_pct, lang)}</td>
                    <td className={b.gap_pp < -5 ? "late" : ""}>{num(b.gap_pp, 0, lang)}</td>
                    {b.not_started
                      ? <td colSpan={cats.length} className="ex-muted">{x.notStarted}</td>
                      : cats.map((c) => <td key={c} className={cellTone(b.categories?.[c])}>{b.categories?.[c] === undefined ? "" : num(b.categories[c], 0, lang)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {ex.method === "estimate_value" && <small className="delay-note">{x.factIsMoney}</small>}
        </article>
      </section>

      {texts.delay_cards?.length > 0 && (
        <section className="panel">
          <header className="delay-section-head"><h2>{x.cards}</h2></header>
          <div className="ex-cards">
            {texts.delay_cards.map((c, i) => (
              <article key={`${c.category}-${i}`} className={`ex-card ${tone(c.severity)}`}>
                <h3>{i + 1}. {c.title}</h3>
                <strong>{c.figure}</strong>
                <dl>
                  <dt>{x.cause}</dt><dd>{c.cause}</dd>
                  {c.impact && (<><dt>{x.impact}</dt><dd>{c.impact}</dd></>)}
                  <dt>{x.who}</dt><dd>{c.who}</dd>
                </dl>
              </article>
            ))}
          </div>
          {texts.unconfirmed_causes && <p className="ex-unconfirmed"><b>{x.unconfirmed}</b> {texts.unconfirmed_causes}</p>}
        </section>
      )}

      <section className="delay-grid">
        <article className="panel">
          <header className="delay-section-head"><h2>{x.forecast}</h2></header>
          <ul className="delay-findings">{(texts.forecast_lines || []).map((line, i) => <li key={i} className="warning">{line}</li>)}</ul>
        </article>
        <article className="panel">
          <header className="delay-section-head"><h2>{x.finance}</h2></header>
          <ul className="delay-findings">{(texts.finance_notes || []).map((line, i) => <li key={i}>{line}</li>)}</ul>
          {texts.monthly_note && <small className="delay-note">{texts.monthly_note}</small>}
        </article>
        <article className="panel">
          <header className="delay-section-head"><h2>{x.contractorActions}</h2></header>
          <ol className="result-action-list">{(texts.contractor_actions || []).map((a, i) => <li key={i}><b>{a.title}</b> {a.text}</li>)}</ol>
        </article>
        <article className="panel ex-decisions">
          <header className="delay-section-head"><h2>{x.decisions}</h2></header>
          <ol className="result-action-list">{(texts.director_decisions || []).map((a, i) => <li key={i}><b>{a.title}</b> {a.text}</li>)}</ol>
        </article>
      </section>
    </>
  );
}

/** The executive monthly series in the shape the S-curve expects. */
export function executiveCurve(ex) {
  return (ex.monthly || []).map((p) => ({
    month: String(p.month).slice(0, 7),
    planned_cumulative_pct: p.plan_pct,
    actual_cumulative_pct: p.fact_pct ?? null,
    schedule_delay_days: null
  }));
}
