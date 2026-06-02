(function(){
  "use strict";

  const API = window.DevBareunSaaS;
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]));
  const fmt = (v) => v === null || v === undefined || v === "" ? "—" : esc(v);
  const json = (v) => `<pre class="admin-json">${esc(JSON.stringify(v ?? {}, null, 2))}</pre>`;
  const statusPill = (value) => {
    const s = String(value || "unknown").toLowerCase();
    const cls = /fail|error|reject|delete|cancel|expired/.test(s) ? "bad" : /pending|draft|await|created/.test(s) ? "warn" : "";
    return `<span class="admin-pill ${cls}">${esc(value || "unknown")}</span>`;
  };

  const modules = {
    users: {
      title: "Users",
      endpoint: "/api/admin/users",
      key: "users",
      columns: ["email", "user_id", "company_id", "role", "status", "created_at"]
    },
    companies: {
      title: "Companies",
      endpoint: "/api/admin/companies",
      key: "companies",
      columns: ["company_name", "company_id", "email", "contact_person", "subscription_plan", "created_at"]
    },
    projects: {
      title: "Projects",
      endpoint: "/api/admin/projects",
      key: "projects",
      columns: ["project_name", "project_id", "owner_email", "client", "contractor", "analysis_type", "status", "created_at"]
    },
    payments: {
      title: "Payments",
      endpoint: "/api/admin/payments",
      key: "payments",
      columns: ["payment_id", "owner_email", "plan_code", "project_id", "status", "paid_at", "checkout_id"]
    },
    reports: {
      title: "Reports",
      endpoint: "/api/admin/reports",
      key: "reports",
      columns: ["report_id", "analysis_id", "project_id", "project_name", "analysis_type", "print_size", "status", "created_at"]
    },
    "failed-uploads": {
      title: "Failed uploads",
      endpoint: "/api/admin/failed-uploads",
      key: "failed_uploads",
      columns: ["file_id", "project_id", "owner_email", "original_name", "status", "failure_reason", "error_message", "created_at"]
    },
    "credit-usage": {
      title: "Credit usage",
      endpoint: "/api/admin/credit-usage",
      key: "analysis_credits",
      columns: ["credit_id", "owner_email", "plan_code", "project_id", "total_credits", "used_credits", "remaining_credits", "status", "period_start"]
    },
    "activity-logs": {
      title: "Activity logs",
      endpoint: "/api/admin/activity-logs",
      key: "activity_logs",
      columns: ["actor", "actor_email", "event", "entity_type", "entity_id", "created_at", "payload"]
    }
  };

  let activeTab = "users";

  function session(){ return API?.readSession ? API.readSession() : null; }
  function token(){ return API?.accessToken ? API.accessToken() : session()?.access_token; }

  async function request(path){
    if(!API?.api) throw new Error("DevBareun API client is not loaded.");
    return API.api(path);
  }

  function setSessionCard(user){
    const el = $("#adminSessionCard");
    if(!user){ el.innerHTML = `<span class="saas-badge warn">No admin session</span><p class="admin-muted">Login required.</p>`; return; }
    el.innerHTML = `<span class="saas-badge">Admin session</span><strong>${esc(user.email || "Admin")}</strong><p class="admin-muted">Role: ${user.is_admin ? "admin" : "admin email allowlist"}</p>`;
  }

  function showLogin(show){
    $("#adminLoginCard").hidden = !show;
    $("#adminApp").hidden = show;
  }

  function kpiCard(label, value){
    return `<div class="saas-card admin-kpi-card"><p class="saas-eyebrow">${esc(label)}</p><strong>${Number(value || 0).toLocaleString()}</strong></div>`;
  }

  function renderKpis(counts){
    const order = [
      ["Users", "users"], ["Companies", "companies"], ["Projects", "projects"], ["Payments", "payments"],
      ["Reports", "reports"], ["Failed uploads", "failed_uploads"], ["Credit usage", "credit_usage"], ["Activity logs", "activity_logs"]
    ];
    $("#adminKpis").innerHTML = order.map(([label,key]) => kpiCard(label, counts?.[key])).join("");
  }

  function queryString(){
    const q = $("#adminSearch")?.value?.trim();
    const limit = $("#adminLimit")?.value || "200";
    const params = new URLSearchParams({ limit });
    if(q) params.set("q", q);
    return params.toString();
  }

  function normalizeRows(module, data){
    if(module === "payments"){
      const payments = data.payments || [];
      const sessions = (data.checkout_sessions || []).map(r => ({...r, payment_id: r.payment_id || r.checkout_id, status: r.status || "checkout"}));
      return [...payments, ...sessions];
    }
    if(module === "credit-usage"){
      const credits = data.analysis_credits || [];
      const usage = (data.subscription_usage || []).map(r => ({...r, credit_id: r.credit_id || r.usage_id, status: "used"}));
      return [...credits, ...usage];
    }
    return data[modules[module].key] || [];
  }

  function renderTable(module, rows){
    const cfg = modules[module];
    if(!rows.length) return `<div class="admin-empty">No ${esc(cfg.title.toLowerCase())} records found.</div>`;
    const head = cfg.columns.map(c => `<th>${esc(c.replaceAll("_"," "))}</th>`).join("") + `<th>Details</th>`;
    const body = rows.map(row => {
      const cells = cfg.columns.map(col => {
        const value = row[col];
        if(col === "status" || col.endsWith("_status")) return `<td>${statusPill(value)}</td>`;
        if(col === "payload") return `<td>${json(value)}</td>`;
        if(/credits|amount|value|limit|used|remaining|total/.test(col)) return `<td><strong>${fmt(value)}</strong></td>`;
        return `<td>${fmt(value)}</td>`;
      }).join("");
      return `<tr>${cells}<td>${json(row)}</td></tr>`;
    }).join("");
    return `<table class="admin-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  }

  async function loadOverview(){
    const data = await request("/api/admin/overview");
    setSessionCard(data.admin);
    renderKpis(data.counts || {});
    return data;
  }

  async function loadModule(module = activeTab){
    activeTab = module;
    const cfg = modules[module];
    $$("[data-admin-tab]").forEach(btn => btn.classList.toggle("active", btn.dataset.adminTab === module));
    $("#adminModuleEyebrow").textContent = module.replaceAll("-", " ");
    $("#adminModuleTitle").textContent = cfg.title;
    $("#adminModuleCount").textContent = "Loading";
    $("#adminModuleBody").innerHTML = `<div class="admin-loading">Loading ${esc(cfg.title.toLowerCase())}...</div>`;
    try{
      const data = await request(`${cfg.endpoint}?${queryString()}`);
      const rows = normalizeRows(module, data);
      $("#adminModuleCount").textContent = `${data.total ?? rows.length} records`;
      $("#adminModuleBody").innerHTML = renderTable(module, rows);
    }catch(err){
      $("#adminModuleCount").textContent = "Error";
      $("#adminModuleBody").innerHTML = `<div class="admin-error">${esc(err.message || err)}</div>`;
    }
  }

  async function boot(){
    if(!token()){
      setSessionCard(null); showLogin(true); return;
    }
    try{
      showLogin(false);
      await loadOverview();
      await loadModule(activeTab);
    }catch(err){
      console.warn(err);
      setSessionCard(null); showLogin(true);
      $("#adminLoginStatus").textContent = err.message || "Admin session could not be verified.";
    }
  }

  async function pilotLogin(e){
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const payload = Object.fromEntries(fd.entries());
    $("#adminLoginStatus").textContent = "Creating pilot admin session...";
    try{
      const data = await API.api("/api/auth/pilot-login", {
        method: "POST",
        auth: false,
        body: JSON.stringify(payload)
      });
      API.saveSession(data);
      $("#adminLoginStatus").textContent = "Admin session created.";
      await boot();
    }catch(err){
      $("#adminLoginStatus").textContent = err.message || "Could not create admin session.";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("#pilotAdminLogin")?.addEventListener("submit", pilotLogin);
    $$("[data-admin-tab]").forEach(btn => btn.addEventListener("click", () => loadModule(btn.dataset.adminTab)));
    $("#adminRefresh")?.addEventListener("click", async () => { await loadOverview(); await loadModule(activeTab); });
    $("#adminSearch")?.addEventListener("keydown", (e) => { if(e.key === "Enter") loadModule(activeTab); });
    $("#adminLimit")?.addEventListener("change", () => loadModule(activeTab));
    $("#adminLogout")?.addEventListener("click", () => { API.clearSession(); showLogin(true); setSessionCard(null); });
    boot();
  });
})();
