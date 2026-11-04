import { useMemo, useState } from "react";
import { AlertTriangle, CalendarClock, CheckCircle2, Download, FileSpreadsheet, GitBranch, Printer, Scale, TrendingDown } from "lucide-react";

const LANG_KEY = "devbareun.delay.lang";

export const T = {
  az: {
    eyebrow: "İcra və gecikmə analizi",
    example: "Nümunə hesabat — nümunə məlumatlarla",
    dataDate: "Hesabat tarixi",
    contract: "Müqavilə müddəti",
    client: "Sifarişçi",
    contractor: "Podratçı",
    actualProgress: "Faktiki icra",
    plan: "Plan",
    spi: "SPI (qrafik göstəricisi)",
    spiNote: "1.00 = plan sürəti",
    scheduleDelay: "Qrafikdən geri qalma",
    scheduleDelayNote: "Earned schedule üzrə",
    forecastFinish: "Proqnoz bitmə",
    plannedFinish: "Plan bitmə",
    days: "gün",
    status: { on_track: "Qrafik üzrə", at_risk: "Risk altında", critical: "Kritik gecikmə" },
    scurve: "Plan və faktiki icra (S-əyrisi)",
    scurveSub: "Aylıq kumulyativ %, hesabat tarixinə qədər faktiki",
    reconstructed: "Faktiki tarixçə işlərin faktiki tarixlərindən bərpa olunub.",
    monthlyDelay: "Aylar üzrə gecikmə",
    monthlyDelaySub: "Ay sonuna qrafikdən geri qalma, gün",
    responsibility: "Gecikmə məsuliyyəti",
    responsibilitySub: "Qeydə alınmış hadisələrin təqvim günləri",
    allEvents: "Bütün hadisələr",
    criticalEvents: "Kritik yolda",
    employer: "Sifarişçi",
    contractorParty: "Podratçı",
    neutral: "Neytral",
    concurrent: "Eyni vaxtda",
    unassigned: "Təyin edilməyib",
    excusable: "Üzrlü (EOT)",
    compensable: "Kompensasiyalı",
    nonExcusable: "Üzrsüz",
    noEvents: "Gecikmə hadisələri təqdim olunmayıb. Şablonun Gecikme_Hadiseleri vərəqini doldurun.",
    wbs: "Bölmələr üzrə icra",
    section: "Bölmə",
    share: "Pay",
    finishVar: "Bitmə fərqi",
    delayed: "Gecikən",
    activities: "Ən çox gecikən işlər",
    allActivities: "Bütün işlər",
    showAll: "Bütün işləri göstər",
    showTop: "Yalnız ən çox gecikənlər",
    id: "Kod",
    activity: "İş",
    progress: "İcra",
    pFinish: "Plan bitiş",
    fFinish: "Proqnoz",
    float: "Ehtiyat",
    state: "Status",
    criticalNote: "★ kritik yol",
    cpm: "Kritik yol öncül iş əlaqələrinə görə (CPM).",
    approximate: "Öncül əlaqələr yoxdur: kritik yol təxmini hesablanıb.",
    events: "Gecikmə hadisələri",
    event: "Hadisə",
    period: "Dövr",
    cause: "Səbəb",
    responsible: "Məsul",
    findings: "Nəticələr",
    actions: "Tövsiyə olunan tədbirlər",
    quality: "Məlumat keyfiyyəti",
    noQuality: "Problem aşkar edilmədi.",
    pdf: "PDF hesabat",
    excel: "Excel",
    print: "Çap et",
    st: {
      completed: "Bitib", completed_late: "Gec bitib", on_track: "Qrafik üzrə", not_started: "Başlanmayıb",
      late_start: "Gec başlanğıc", delayed: "Gecikir", major_delay: "Böyük gecikmə", critical_delay: "Kritik gecikmə"
    },
    error: "Analiz alınmadı"
  },
  en: {
    eyebrow: "Execution and delay analysis",
    example: "Example report — sample data",
    dataDate: "Data date",
    contract: "Contract period",
    client: "Client",
    contractor: "Contractor",
    actualProgress: "Actual progress",
    plan: "Plan",
    spi: "SPI (schedule index)",
    spiNote: "1.00 = planned rate",
    scheduleDelay: "Behind schedule",
    scheduleDelayNote: "By earned schedule",
    forecastFinish: "Forecast completion",
    plannedFinish: "Planned",
    days: "days",
    status: { on_track: "On track", at_risk: "At risk", critical: "Critical delay" },
    scurve: "Planned vs actual progress (S-curve)",
    scurveSub: "Monthly cumulative %, actual up to the data date",
    reconstructed: "Actual history reconstructed from activity actual dates.",
    monthlyDelay: "Delay by month",
    monthlyDelaySub: "Days behind schedule at month end",
    responsibility: "Delay responsibility",
    responsibilitySub: "Calendar days of recorded delay events",
    allEvents: "All events",
    criticalEvents: "On critical path",
    employer: "Employer",
    contractorParty: "Contractor",
    neutral: "Neutral",
    concurrent: "Concurrent",
    unassigned: "Unassigned",
    excusable: "Excusable (EOT)",
    compensable: "Compensable",
    nonExcusable: "Non-excusable",
    noEvents: "No delay events were supplied. Fill the Gecikme_Hadiseleri sheet of the template.",
    wbs: "Execution by section",
    section: "Section",
    share: "Share",
    finishVar: "Finish var.",
    delayed: "Delayed",
    activities: "Most delayed activities",
    allActivities: "All activities",
    showAll: "Show all activities",
    showTop: "Most delayed only",
    id: "ID",
    activity: "Activity",
    progress: "Progress",
    pFinish: "Plan finish",
    fFinish: "Forecast",
    float: "Float",
    state: "Status",
    criticalNote: "★ critical path",
    cpm: "Critical path from predecessor logic (CPM).",
    approximate: "No predecessor logic: critical path is approximate.",
    events: "Delay events",
    event: "Event",
    period: "Period",
    cause: "Cause",
    responsible: "Responsible",
    findings: "Findings",
    actions: "Recommended actions",
    quality: "Data quality",
    noQuality: "No issues found.",
    pdf: "PDF report",
    excel: "Excel",
    print: "Print",
    st: {
      completed: "Completed", completed_late: "Completed late", on_track: "On track", not_started: "Not started",
      late_start: "Late start", delayed: "Delayed", major_delay: "Major delay", critical_delay: "Critical delay"
    },
    error: "Analysis failed"
  }
};

const PARTIES = [
  { key: "employer", label: "employer", color: "var(--party-employer)" },
  { key: "contractor", label: "contractorParty", color: "var(--party-contractor)" },
  { key: "neutral", label: "neutral", color: "var(--party-neutral)" },
  { key: "concurrent", label: "concurrent", color: "var(--party-concurrent)" }
];

export function useDelayLang() {
  const [lang, setLangState] = useState(() => {
    try {
      return localStorage.getItem(LANG_KEY) === "en" ? "en" : "az";
    } catch {
      return "az";
    }
  });
  function setLang(next) {
    setLangState(next);
    try {
      localStorage.setItem(LANG_KEY, next);
    } catch {
      /* storage unavailable */
    }
  }
  return [lang, setLang];
}

export function formatDay(value) {
  if (!value) return "—";
  const [y, m, d] = String(value).slice(0, 10).split("-");
  return d && m && y ? `${d}.${m}.${y}` : String(value);
}

function pct(value) {
  return value === null || value === undefined ? "—" : `${Number(value).toFixed(1)}%`;
}

function signed(value) {
  if (value === null || value === undefined) return "—";
  return value > 0 ? `+${value}` : String(value);
}

function statusTone(status) {
  if (["critical_delay", "critical"].includes(status)) return "danger";
  if (["major_delay", "delayed", "late_start", "completed_late", "at_risk"].includes(status)) return "warning";
  if (["completed", "on_track"].includes(status)) return "success";
  return "neutral";
}

export function LangToggle({ lang, onChange }) {
  return (
    <div className="delay-lang" role="group" aria-label="Language">
      {["az", "en"].map((code) => (
        <button key={code} type="button" className={lang === code ? "active" : ""} aria-pressed={lang === code} onClick={() => onChange(code)}>
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

function Kpi({ label, value, note, tone = "neutral", icon: Icon, bar }) {
  return (
    <article className={`delay-kpi ${tone}`}>
      <div className="delay-kpi-head">
        {Icon && <Icon size={16} />}
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
      {bar !== undefined && (
        <div className="delay-kpi-bar" aria-hidden="true">
          <i style={{ width: `${Math.max(0, Math.min(100, bar.actual))}%` }} />
          <b style={{ left: `${Math.max(0, Math.min(100, bar.plan))}%` }} />
        </div>
      )}
      <small>{note}</small>
    </article>
  );
}

function SCurve({ monthly, dataDate, t }) {
  const [hover, setHover] = useState(null);
  const W = 640, H = 240, L = 40, R = 12, TOP = 12, B = 28;
  const n = monthly.length;
  if (!n) return null;
  const x = (i) => L + (n === 1 ? 0 : (i / (n - 1)) * (W - L - R));
  const y = (v) => TOP + (1 - v / 100) * (H - TOP - B);
  const planned = monthly.map((m, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(m.planned_cumulative_pct ?? 0).toFixed(1)}`).join(" ");
  const actualPts = monthly.map((m, i) => [i, m.actual_cumulative_pct]).filter(([, v]) => v !== null && v !== undefined);
  const actual = actualPts.map(([i, v], k) => `${k ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const ddIndex = monthly.findIndex((m) => m.month === String(dataDate || "").slice(0, 7));
  const step = Math.max(1, Math.ceil(n / 8));
  const active = hover !== null ? monthly[hover] : null;

  function onMove(event) {
    const box = event.currentTarget.getBoundingClientRect();
    const px = ((event.clientX - box.left) / box.width) * W;
    const index = Math.round(((px - L) / (W - L - R)) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, index)));
  }

  return (
    <div className="delay-chart">
      <div className="delay-legend">
        <span><i className="swatch plan" /> {t.plan}</span>
        <span><i className="swatch actual" /> {t.actualProgress}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.scurve} onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="grid" />
            <text x={L - 6} y={y(v) + 4} textAnchor="end" className="tick">{v}%</text>
          </g>
        ))}
        {monthly.map((m, i) => (i % step === 0 || i === n - 1) && (
          <text key={m.month} x={x(i)} y={H - 8} textAnchor={i === n - 1 ? "end" : i === 0 ? "start" : "middle"} className="tick">{m.month}</text>
        ))}
        {ddIndex >= 0 && <line x1={x(ddIndex)} x2={x(ddIndex)} y1={TOP} y2={H - B} className="data-date" />}
        <path d={planned} className="line plan" />
        {actual && <path d={actual} className="line actual" />}
        {active && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={TOP} y2={H - B} className="crosshair" />
            <circle cx={x(hover)} cy={y(active.planned_cumulative_pct ?? 0)} r="4" className="dot plan" />
            {active.actual_cumulative_pct !== null && active.actual_cumulative_pct !== undefined && (
              <circle cx={x(hover)} cy={y(active.actual_cumulative_pct)} r="4.5" className="dot actual" />
            )}
          </g>
        )}
      </svg>
      {active && (
        <div className="delay-tooltip" style={{ left: `${(x(hover) / W) * 100}%` }}>
          <strong>{active.month}</strong>
          <span>{t.plan}: {pct(active.planned_cumulative_pct)}</span>
          <span>{t.actualProgress}: {pct(active.actual_cumulative_pct)}</span>
          {active.schedule_delay_days !== null && active.schedule_delay_days !== undefined && <span>{t.scheduleDelay}: {active.schedule_delay_days} {t.days}</span>}
        </div>
      )}
    </div>
  );
}

function MonthlyDelay({ monthly, t }) {
  const rows = monthly.filter((m) => m.schedule_delay_days !== null && m.schedule_delay_days !== undefined);
  const [hover, setHover] = useState(null);
  if (!rows.length) return null;
  const max = Math.max(1, ...rows.map((m) => m.schedule_delay_days));
  return (
    <div className="delay-bars" role="img" aria-label={t.monthlyDelay}>
      {rows.map((m, i) => (
        <div key={m.month} className="delay-bar-col" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} tabIndex={0}>
          <div className="delay-bar-track">
            {hover === i && (
              <div className="delay-tooltip inline">
                <strong>{m.month}</strong>
                <span>{m.schedule_delay_days} {t.days} ({signed(m.delay_change_days)})</span>
              </div>
            )}
            <i style={{ height: `${(m.schedule_delay_days / max) * 100}%` }} />
          </div>
          <small>{m.month.slice(2)}</small>
          {(i === rows.length - 1 || m.schedule_delay_days === max) && <b>{m.schedule_delay_days}</b>}
        </div>
      ))}
    </div>
  );
}

function Responsibility({ events, t }) {
  if (!events?.available) return <div className="status-box info">{t.noEvents}</div>;
  const rows = [
    [t.allEvents, events.by_party_days],
    [t.criticalEvents, events.critical_by_party_days]
  ];
  return (
    <div className="delay-resp">
      <div className="delay-legend">
        {PARTIES.map((p) => <span key={p.key}><i className="swatch" style={{ background: p.color }} /> {t[p.label]}</span>)}
      </div>
      {rows.map(([label, data]) => {
        const total = PARTIES.reduce((sum, p) => sum + (data?.[p.key] || 0), 0);
        return (
          <div key={label} className="delay-resp-row">
            <div className="delay-resp-label"><strong>{label}</strong><span>{total} {t.days}</span></div>
            <div className="delay-stack" aria-label={`${label}: ${PARTIES.map((p) => `${t[p.label]} ${data?.[p.key] || 0}`).join(", ")}`}>
              {total === 0 ? <i className="empty" /> : PARTIES.filter((p) => data?.[p.key]).map((p) => (
                <i key={p.key} style={{ flexGrow: data[p.key], background: p.color }} title={`${t[p.label]}: ${data[p.key]} ${t.days}`}>
                  {data[p.key] / total >= 0.1 ? data[p.key] : ""}
                </i>
              ))}
            </div>
            <div className="delay-resp-tags">
              <span>{t.excusable}: <b>{data?.excusable ?? 0}</b></span>
              <span>{t.compensable}: <b>{data?.compensable ?? 0}</b></span>
              <span>{t.nonExcusable}: <b>{data?.non_excusable ?? 0}</b></span>
            </div>
          </div>
        );
      })}
      {events.unassigned_days > 0 && <small className="delay-note">{t.unassigned}: {events.unassigned_days} {t.days}</small>}
    </div>
  );
}

function Bar({ plan, actual }) {
  return (
    <div className="delay-mini" aria-hidden="true">
      <i style={{ width: `${Math.max(0, Math.min(100, actual ?? 0))}%` }} />
      <b style={{ left: `${Math.max(0, Math.min(100, plan ?? 0))}%` }} />
    </div>
  );
}

export function DelayDashboard({ result, lang, onLangChange, downloads, isExample = false }) {
  const t = T[lang] || T.az;
  const [showAll, setShowAll] = useState(false);
  const k = result?.kpis || {};
  const project = result?.project || {};
  const criticalIds = useMemo(() => new Set((result?.critical_path?.activities || []).map((a) => a.id)), [result]);

  if (!result?.ok) {
    return (
      <section className="panel">
        <div className="status-box error"><strong>{t.error}.</strong> {result?.error?.[lang] || result?.error?.en || ""}</div>
        <QualityList items={result?.data_quality || []} lang={lang} t={t} />
      </section>
    );
  }

  const activities = showAll ? result.activities : (result.top_delays?.length ? result.top_delays : result.activities.slice(0, 10));
  const statusLabel = t.status[k.status] || k.status;

  return (
    <div className="delay-dashboard">
      <section className="delay-head panel featured">
        <div>
          <span className="workspace-eyebrow">{t.eyebrow}</span>
          <h1>{project.name}</h1>
          {isExample && <span className="status-pill neutral">{t.example}</span>}
          <dl className="delay-meta">
            <div><dt>{t.dataDate}</dt><dd>{formatDay(k.data_date)}</dd></div>
            <div><dt>{t.contract}</dt><dd>{formatDay(project.contract_start || k.project_start)} – {formatDay(project.contract_finish || k.planned_finish)}</dd></div>
            {project.client && <div><dt>{t.client}</dt><dd>{project.client}</dd></div>}
            {project.contractor && <div><dt>{t.contractor}</dt><dd>{project.contractor}</dd></div>}
          </dl>
        </div>
        <div className="delay-head-actions">
          <LangToggle lang={lang} onChange={onLangChange} />
          <span className={`status-pill ${statusTone(k.status)}`}>
            {k.status === "on_track" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />} {statusLabel}
          </span>
          {downloads && (
            <div className="delay-downloads">
              <a className="primary-button" href={downloads.pdf}><Download size={16} /> {t.pdf}</a>
              <a className="secondary-button" href={downloads.xlsx}><FileSpreadsheet size={16} /> {t.excel}</a>
            </div>
          )}
          <button className="secondary-button" type="button" onClick={() => window.print()}><Printer size={16} /> {t.print}</button>
        </div>
      </section>

      <section className="delay-kpis">
        <Kpi icon={TrendingDown} label={t.actualProgress} value={pct(k.actual_progress_pct)} note={`${t.plan} ${pct(k.planned_progress_pct)}`}
          tone={k.progress_gap_pct < -5 ? "danger" : k.progress_gap_pct < 0 ? "warning" : "success"} bar={{ actual: k.actual_progress_pct, plan: k.planned_progress_pct }} />
        <Kpi icon={Scale} label={t.spi} value={k.spi ?? "—"} note={t.spiNote} tone={k.spi >= 0.95 ? "success" : k.spi >= 0.85 ? "warning" : "danger"} />
        <Kpi icon={CalendarClock} label={t.scheduleDelay} value={`${k.schedule_delay_days ?? 0} ${t.days}`} note={t.scheduleDelayNote}
          tone={k.schedule_delay_days > 30 ? "danger" : k.schedule_delay_days > 0 ? "warning" : "success"} />
        <Kpi icon={GitBranch} label={t.forecastFinish} value={formatDay(k.forecast_finish)} note={`${t.plannedFinish} ${formatDay(k.planned_finish)} · ${signed(k.forecast_delay_days)} ${t.days}`}
          tone={k.forecast_delay_days > 30 ? "danger" : k.forecast_delay_days > 0 ? "warning" : "success"} />
      </section>

      <section className="delay-grid">
        <article className="panel delay-wide">
          <header className="delay-section-head"><h2>{t.scurve}</h2><span>{t.scurveSub}</span></header>
          <SCurve monthly={result.monthly || []} dataDate={k.data_date} t={t} />
          {result.monthly_actual_source === "reconstructed" && <small className="delay-note">{t.reconstructed}</small>}
        </article>
        <article className="panel">
          <header className="delay-section-head"><h2>{t.monthlyDelay}</h2><span>{t.monthlyDelaySub}</span></header>
          <MonthlyDelay monthly={result.monthly || []} t={t} />
        </article>
        <article className="panel">
          <header className="delay-section-head"><h2>{t.responsibility}</h2><span>{t.responsibilitySub}</span></header>
          <Responsibility events={result.events} t={t} />
        </article>
      </section>

      <section className="card-grid result-section-grid">
        <article className="panel">
          <header className="delay-section-head"><h2>{t.findings}</h2></header>
          <ul className="delay-findings">
            {(result.findings || []).map((item, index) => <li key={`${item.code}-${index}`} className={item.severity}>{item[lang] || item.en}</li>)}
          </ul>
        </article>
        <article className="panel">
          <header className="delay-section-head"><h2>{t.actions}</h2></header>
          <ol className="result-action-list">
            {(result.actions || []).map((item, index) => <li key={`${item.code}-${index}`}>{item[lang] || item.en}</li>)}
          </ol>
        </article>
      </section>

      {result.wbs?.length > 0 && (
        <section className="panel">
          <header className="delay-section-head"><h2>{t.wbs}</h2></header>
          <div className="delay-table-wrap">
            <table className="delay-table">
              <thead><tr><th>{t.section}</th><th>{t.share}</th><th>{t.progress}</th><th>SPI</th><th>{t.fFinish}</th><th>{t.finishVar}</th><th>{t.delayed}</th></tr></thead>
              <tbody>
                {result.wbs.map((w) => (
                  <tr key={w.wbs}>
                    <td>{w.wbs}</td>
                    <td>{pct(w.weight_share)}</td>
                    <td className="delay-progress-cell"><Bar plan={w.planned_pct} actual={w.actual_pct} /><span>{pct(w.actual_pct)} / {pct(w.planned_pct)}</span></td>
                    <td>{w.spi ?? "—"}</td>
                    <td>{formatDay(w.forecast_finish)}</td>
                    <td className={w.finish_variance_days > 0 ? "late" : ""}>{signed(w.finish_variance_days)}</td>
                    <td>{w.delayed_activities}/{w.activities}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="panel">
        <header className="delay-section-head">
          <h2>{showAll ? t.allActivities : t.activities}</h2>
          <button type="button" className="secondary-button" onClick={() => setShowAll((v) => !v)}>{showAll ? t.showTop : t.showAll}</button>
        </header>
        <div className="delay-table-wrap">
          <table className="delay-table">
            <thead><tr><th>{t.id}</th><th>{t.activity}</th><th>{t.progress}</th><th>{t.pFinish}</th><th>{t.fFinish}</th><th>{t.finishVar}</th><th>{t.float}</th><th>{t.state}</th></tr></thead>
            <tbody>
              {activities.map((a) => (
                <tr key={a.id}>
                  <td>{a.id}</td>
                  <td>{criticalIds.has(a.id) && <span className="delay-star" title={t.criticalNote}>★ </span>}{a.name}{a.wbs && <small>{a.wbs}</small>}</td>
                  <td className="delay-progress-cell"><Bar plan={a.planned_pct} actual={a.actual_pct} /><span>{pct(a.actual_pct)}</span></td>
                  <td>{formatDay(a.planned_finish)}</td>
                  <td>{formatDay(a.forecast_finish)}</td>
                  <td className={a.finish_variance_days > 0 ? "late" : ""}>{signed(a.finish_variance_days)}</td>
                  <td>{a.total_float_days ?? "—"}</td>
                  <td><span className={`status-pill ${statusTone(a.status)}`}>{t.st[a.status] || a.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <small className="delay-note">{t.criticalNote} · {result.critical_path?.method === "cpm" ? t.cpm : t.approximate}</small>
      </section>

      {result.events?.available && (
        <section className="panel">
          <header className="delay-section-head"><h2>{t.events}</h2></header>
          <div className="delay-table-wrap">
            <table className="delay-table">
              <thead><tr><th>{t.id}</th><th>{t.event}</th><th>{t.period}</th><th>{t.days}</th><th>{t.cause}</th><th>{t.responsible}</th></tr></thead>
              <tbody>
                {result.events.events.map((e) => (
                  <tr key={e.id}>
                    <td>{e.id}</td>
                    <td>{e.description}{e.activity_ids?.length > 0 && <small>{e.activity_ids.join(", ")}</small>}</td>
                    <td>{formatDay(e.start)} – {e.finish ? formatDay(e.finish) : "…"}</td>
                    <td>{e.days}</td>
                    <td>{e.cause || "—"}</td>
                    <td>{t[{ contractor: "contractorParty" }[e.responsible] || e.responsible] || e.responsible}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="panel">
        <header className="delay-section-head"><h2>{t.quality}</h2></header>
        <QualityList items={result.data_quality || []} lang={lang} t={t} />
      </section>
    </div>
  );
}

function QualityList({ items, lang, t }) {
  if (!items.length) return <div className="status-box success">{t.noQuality}</div>;
  return (
    <ul className="delay-quality">
      {items.map((item, index) => <li key={`${item.code}-${index}`} className={item.severity}><AlertTriangle size={14} /> {item[lang] || item.en}</li>)}
    </ul>
  );
}
