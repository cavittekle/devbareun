import { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, Check, ChevronDown, LockKeyhole, Mail, UserPlus } from "lucide-react";
import { workspaceApi } from "../api/client";

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

  const copy = useMemo(() => ({
    eyebrow: isRegister ? "Create workspace" : "Member workspace",
    title: isRegister ? "Create your DevBareun workspace." : "Login to your workspace.",
    description: isRegister
      ? "Create a protected account for project uploads, monthly credits, dashboard history and reports."
      : "Open your protected project control dashboard, upload files and review reports.",
    button: isRegister ? "Create account" : "Login and open dashboard"
  }), [isRegister]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setStatus({ type: "info", text: isRegister ? "Creating account..." : "Checking account..." });
    try {
      if (isRegister) {
        await workspaceApi.register(form);
        setStatus({
          type: "success",
          text: "Account request was created. If email confirmation is enabled, confirm your email before login."
        });
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
      setStatus({ type: "success", text: "Login successful. Opening workspace..." });
      setTimeout(() => {
        location.href = nextUrl();
      }, 450);
    } catch (error) {
      setStatus({ type: "error", text: error.message || "Authentication could not be completed." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-intro panel">
        <img src="/assets/devbareun-logo-horizontal-white.svg" alt="DevBareun" />
        <span className="workspace-eyebrow">Construction analytics workspace</span>
        <h1>{copy.title}</h1>
        <p>{copy.description}</p>
        <div className="auth-points">
          <article>
            <BarChart3 size={20} />
            <div><strong>Project control</strong><span>Schedule, cost, material and risk views.</span></div>
          </article>
          <article>
            <LockKeyhole size={20} />
            <div><strong>Protected reports</strong><span>Dashboard history and exports stay in your workspace.</span></div>
          </article>
        </div>
      </section>

      <section className="auth-card panel">
        <span className="workspace-eyebrow">{copy.eyebrow}</span>
        <h2>{isRegister ? "Create account" : "Login"}</h2>
        <form onSubmit={submit}>
          <label className="field-label">
            Email
            <span className="field-with-icon"><Mail size={17} /><input type="email" required value={form.email} onChange={(event) => update("email", event.target.value)} placeholder="you@company.com" /></span>
          </label>
          <label className="field-label">
            Password
            <span className="field-with-icon"><LockKeyhole size={17} /><input type="password" required minLength={8} value={form.password} onChange={(event) => update("password", event.target.value)} placeholder="Minimum 8 characters" /></span>
          </label>
          <div className="field-label" ref={planPickerRef}>
            <span>Plan</span>
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
                <div className="plan-select-menu" role="listbox" aria-label="Plan options">
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
          {isRegister && (
            <>
              <label className="field-label">
                Company name
                <input value={form.company_name} onChange={(event) => update("company_name", event.target.value)} placeholder="Company name" />
              </label>
              <label className="field-label">
                Contact person
                <span className="field-with-icon"><UserPlus size={17} /><input value={form.contact_person} onChange={(event) => update("contact_person", event.target.value)} placeholder="Contact person" /></span>
              </label>
            </>
          )}
          <button className="primary-button full" type="submit" disabled={busy}>{busy ? "Please wait..." : copy.button}</button>
        </form>
        {status && <div className={`status-box ${status.type}`}>{status.text}</div>}
        <p className="auth-switch">
          {isRegister ? "Already have an account?" : "New workspace?"}{" "}
          <a href={isRegister ? "/workspace/?view=login" : "/workspace/?view=register"}>
            {isRegister ? "Login" : "Create account"}
          </a>
        </p>
      </section>
    </main>
  );
}
