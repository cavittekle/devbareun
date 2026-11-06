import { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, Check, ChevronDown, LockKeyhole, Mail, UserPlus } from "lucide-react";
import { workspaceApi } from "../api/client";
import { LangToggle, useDelayLang } from "../components/DelayDashboard";

const planOptions = [
  { value: "plus", label: "Plus" },
  { value: "pro", label: "Pro" }
];

function nextUrl() {
  const params = new URLSearchParams(location.search);
  const next = params.get("next");
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return "/workspace/";
}

const AUTH_COPY = {
  en: {
    login: {
      eyebrow: "Member workspace",
      title: "Log in to DevBareun",
      description: "Upload your schedule, F2 and F3 certificates and contract, and see how late the project is and why.",
      heading: "Log in",
      button: "Log in"
    },
    register: {
      eyebrow: "Create workspace",
      title: "Create your DevBareun account",
      description: "One account for your delay analyses, monthly credits and past reports.",
      heading: "Create account",
      button: "Create account"
    },
    eyebrow: "Execution and delay analysis",
    point1Title: "Delay in days",
    point1Text: "Planned vs actual, forecast completion and critical path.",
    point2Title: "Your reports stay private",
    point2Text: "Only your team can open past analyses and exports.",
    email: "Email",
    password: "Password",
    passwordHint: "At least 8 characters",
    plan: "Plan (you can change it later)",
    planOptions: "Plan options",
    company: "Company name",
    contact: "Contact person",
    wait: "Please wait...",
    creating: "Creating your account...",
    checking: "Checking your details...",
    registered: "Account created. If we sent you a confirmation email, confirm it before you log in.",
    loggedIn: "Logged in. Opening your workspace...",
    failed: "We couldn't log you in. Check your email and password and try again.",
    haveAccount: "Already have an account?",
    newHere: "New to DevBareun?",
    toLogin: "Log in",
    toRegister: "Create account"
  },
  az: {
    login: {
      eyebrow: "Üzv iş sahəsi",
      title: "DevBareun-a daxil olun",
      description: "Planlamanı, F2 və F3 aktlarını və müqaviləni yükləyin, layihənin nə qədər və niyə gecikdiyini görün.",
      heading: "Daxil ol",
      button: "Daxil ol"
    },
    register: {
      eyebrow: "İş sahəsi yaradın",
      title: "DevBareun hesabı yaradın",
      description: "Gecikmə analizləriniz, aylıq kreditləriniz və keçmiş hesabatlarınız üçün bir hesab.",
      heading: "Hesab yarat",
      button: "Hesab yarat"
    },
    eyebrow: "İcra və gecikmə analizi",
    point1Title: "Gecikmə günlərlə",
    point1Text: "Plan və faktiki, proqnoz bitmə tarixi və kritik yol.",
    point2Title: "Hesabatlarınız məxfidir",
    point2Text: "Keçmiş analizləri və ixracları yalnız komandanız görür.",
    email: "Email",
    password: "Şifrə",
    passwordHint: "Ən azı 8 simvol",
    plan: "Plan (sonra dəyişə bilərsiniz)",
    planOptions: "Plan seçimləri",
    company: "Şirkətin adı",
    contact: "Əlaqə şəxsi",
    wait: "Gözləyin...",
    creating: "Hesab yaradılır...",
    checking: "Məlumatlar yoxlanılır...",
    registered: "Hesab yaradıldı. Təsdiq emaili göndərmişiksə, daxil olmazdan əvvəl onu təsdiqləyin.",
    loggedIn: "Daxil oldunuz. İş sahəsi açılır...",
    failed: "Daxil ola bilmədik. Email və şifrəni yoxlayıb yenidən cəhd edin.",
    haveAccount: "Hesabınız var?",
    newHere: "DevBareun-da yenisiniz?",
    toLogin: "Daxil olun",
    toRegister: "Hesab yaradın"
  }
};

export function Auth({ mode = "login" }) {
  const isRegister = mode === "register";
  const [form, setForm] = useState({
    email: "",
    password: "",
    plan: "plus",
    company_name: "",
    contact_person: ""
  });
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const planPickerRef = useRef(null);

  useEffect(() => {
    if (!planOpen) return undefined;

    function closePlanPicker(event) {
      if (!planPickerRef.current?.contains(event.target)) setPlanOpen(false);
    }

    function closeOnEscape(event) {
      if (event.key === "Escape") setPlanOpen(false);
    }

    document.addEventListener("pointerdown", closePlanPicker);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closePlanPicker);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [planOpen]);

  const [lang, setLang] = useDelayLang();
  const copy = useMemo(() => AUTH_COPY[lang][isRegister ? "register" : "login"], [lang, isRegister]);
  const t = AUTH_COPY[lang];

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setStatus({ type: "info", text: isRegister ? t.creating : t.checking });
    try {
      if (isRegister) {
        await workspaceApi.register(form);
        setStatus({ type: "success", text: t.registered });
        return;
      }

      try {
        await workspaceApi.login(form);
      } catch (error) {
        if (error.status === 503 || error.code === "backend_offline") {
          await workspaceApi.pilotLogin(form);
        } else {
          throw error;
        }
      }
      setStatus({ type: "success", text: t.loggedIn });
      setTimeout(() => {
        location.href = nextUrl();
      }, 450);
    } catch (error) {
      setStatus({ type: "error", text: error.message || t.failed });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-intro panel">
        <img src="/assets/devbareun-logo-horizontal-white.svg" alt="DevBareun" />
        <span className="workspace-eyebrow">{t.eyebrow}</span>
        <h1>{copy.title}</h1>
        <p>{copy.description}</p>
        <div className="auth-points">
          <article>
            <BarChart3 size={20} />
            <div><strong>{t.point1Title}</strong><span>{t.point1Text}</span></div>
          </article>
          <article>
            <LockKeyhole size={20} />
            <div><strong>{t.point2Title}</strong><span>{t.point2Text}</span></div>
          </article>
        </div>
      </section>

      <section className="auth-card panel">
        <div className="auth-card-head">
          <span className="workspace-eyebrow">{copy.eyebrow}</span>
          <LangToggle lang={lang} onChange={setLang} />
        </div>
        <h2>{copy.heading}</h2>
        <form onSubmit={submit}>
          <label className="field-label">
            {t.email}
            <span className="field-with-icon"><Mail size={17} aria-hidden="true" /><input type="email" autoComplete="email" required value={form.email} onChange={(event) => update("email", event.target.value)} placeholder="you@company.com" /></span>
          </label>
          <label className="field-label">
            {t.password}
            <span className="field-with-icon"><LockKeyhole size={17} aria-hidden="true" /><input type="password" autoComplete={isRegister ? "new-password" : "current-password"} required minLength={8} value={form.password} onChange={(event) => update("password", event.target.value)} placeholder={t.passwordHint} /></span>
          </label>
          {isRegister && (
            <>
          <div className="field-label" ref={planPickerRef}>
            <span>{t.plan}</span>
            <div className={`plan-select${planOpen ? " open" : ""}`}>
              <button
                className="plan-select-trigger"
                type="button"
                aria-haspopup="listbox"
                aria-expanded={planOpen}
                onClick={() => setPlanOpen((current) => !current)}
              >
                <span>{planOptions.find((option) => option.value === form.plan)?.label}</span>
                <ChevronDown size={17} aria-hidden="true" />
              </button>
              {planOpen && (
                <div className="plan-select-menu" role="listbox" aria-label={t.planOptions}>
                  {planOptions.map((option) => (
                    <button
                      className={`plan-select-option${form.plan === option.value ? " active" : ""}`}
                      type="button"
                      role="option"
                      aria-selected={form.plan === option.value}
                      key={option.value}
                      onClick={() => {
                        update("plan", option.value);
                        setPlanOpen(false);
                      }}
                    >
                      <span>{option.label}</span>
                      {form.plan === option.value && <Check size={16} aria-hidden="true" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
              <label className="field-label">
                {t.company}
                <input autoComplete="organization" value={form.company_name} onChange={(event) => update("company_name", event.target.value)} />
              </label>
              <label className="field-label">
                {t.contact}
                <span className="field-with-icon"><UserPlus size={17} aria-hidden="true" /><input autoComplete="name" value={form.contact_person} onChange={(event) => update("contact_person", event.target.value)} /></span>
              </label>
            </>
          )}
          <button className="primary-button full" type="submit" disabled={busy}>{busy ? t.wait : copy.button}</button>
        </form>
        <div role={status?.type === "error" ? "alert" : "status"} aria-live={status?.type === "error" ? "assertive" : "polite"}>
          {status && <div className={`status-box ${status.type}`}>{status.text}</div>}
        </div>
        <p className="auth-switch">
          {isRegister ? t.haveAccount : t.newHere}{" "}
          <a href={isRegister ? "/workspace/?view=login" : "/workspace/?view=register"}>
            {isRegister ? t.toLogin : t.toRegister}
          </a>
        </p>
      </section>
    </main>
  );
}
