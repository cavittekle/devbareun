(function(){
  "use strict";

  if ((location.hostname === "localhost" || location.hostname === "127.0.0.1") && !window.DEVBAREUN_API_BASE_URL) {
    window.DEVBAREUN_API_BASE_URL = "http://127.0.0.1:8000";
  }

  const API = window.DevBareunSaaS;
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]));
  const fmt = (v) => v === null || v === undefined || v === "" ? "-" : esc(v);
  const json = (v) => `<pre class="admin-json">${esc(JSON.stringify(v ?? {}, null, 2))}</pre>`;
  const statusPill = (value) => {
    const s = String(value || "unknown").toLowerCase();
    const cls = /fail|error|reject|delete|cancel|expired/.test(s) ? "bad" : /pending|draft|await|created/.test(s) ? "warn" : "";
    return `<span class="admin-pill ${cls}">${esc(value || "unknown")}</span>`;
  };

  const modules = {
    customers: {
      title: "Customers",
      endpoint: "/api/super-admin/customers",
      key: "users",
      permission: "customers",
      columns: ["email", "user_id", "company_id", "role", "status", "plan", "created_at"]
    },
    companies: {
      title: "Companies",
      endpoint: "/api/super-admin/companies",
      key: "companies",
      permission: "customers",
      columns: ["company_name", "company_id", "email", "contact_person", "subscription_plan", "created_at"]
    },
    projects: {
      title: "Projects",
      endpoint: "/api/super-admin/projects",
      key: "projects",
      permission: "projects",
      columns: ["project_name", "project_id", "owner_email", "client", "contractor", "analysis_type", "status", "created_at"]
    },
    uploads: {
      title: "Uploads",
      endpoint: "/api/super-admin/uploads",
      key: "uploads",
      permission: "uploads",
      columns: ["file_id", "project_id", "owner_email", "original_name", "content_type", "size_bytes", "status", "created_at"]
    },
    payments: {
      title: "Payments",
      endpoint: "/api/super-admin/payments",
      key: "payments",
      permission: "payments",
      columns: ["payment_id", "owner_email", "plan_code", "project_id", "status", "paid_at", "checkout_id"]
    },
    reports: {
      title: "Reports",
      endpoint: "/api/super-admin/reports",
      key: "reports",
      permission: "reports",
      columns: ["report_id", "analysis_id", "project_id", "project_name", "analysis_type", "print_size", "status", "created_at"]
    },
    "credit-usage": {
      title: "Credits",
      endpoint: "/api/super-admin/credit-usage",
      key: "analysis_credits",
      permission: "credits",
      columns: ["credit_id", "owner_email", "plan_code", "project_id", "total_credits", "used_credits", "remaining_credits", "status", "period_start"]
    },
    "support-tickets": {
      title: "Support",
      endpoint: "/api/super-admin/support-tickets",
      key: "support_tickets",
      permission: "support",
      columns: ["ticket_id", "customer_email", "subject", "status", "created_by_email", "created_at"]
    },
    "activity-logs": {
      title: "Activity logs",
      endpoint: "/api/super-admin/activity-logs",
      key: "activity_logs",
      permission: "activity",
      columns: ["actor", "actor_email", "event", "entity_type", "entity_id", "created_at", "payload"]
    },
    "audit-logs": {
      title: "Audit logs",
      endpoint: "/api/super-admin/audit-logs",
      key: "audit_logs",
      permission: "audit",
      columns: ["actor_email", "actor_role", "action", "entity_type", "entity_id", "created_at", "metadata"]
    },
    "audit-integrity": {
      title: "Audit integrity",
      endpoint: "/api/super-admin/audit-integrity",
      key: "audit_integrity",
      permission: "audit",
      columns: []
    },
    "operations-health": {
      title: "Operations health",
      endpoint: "/api/super-admin/operations-health",
      key: "operations_health",
      permission: "operations",
      columns: []
    },
    "audit-archive": {
      title: "Audit archive",
      endpoint: "/api/super-admin/audit-archive",
      key: "audit_archive",
      permission: "audit",
      columns: []
    },
    staff: {
      title: "Staff",
      endpoint: "/api/super-admin/staff",
      key: "staff",
      permission: "staff",
      columns: ["email", "full_name", "role", "status", "created_at", "updated_at"]
    }
  };

  let activeTab = "customers";
  let permissions = new Set();

  function session(){ return API?.readSession ? API.readSession() : null; }
  function token(){ return API?.accessToken ? API.accessToken() : session()?.access_token; }

  async function request(path){
    if(!API?.api) throw new Error("DevBareun API client is not loaded.");
    return API.api(path);
  }

  async function sendJson(path, method, payload){
    if(!API?.api) throw new Error("DevBareun API client is not loaded.");
    return API.api(path, {
      method,
      body: JSON.stringify(payload)
    });
  }

  function setSessionCard(user){
    const el = $("#adminSessionCard");
    if(!user){ el.innerHTML = `<span class="saas-badge warn">No admin session</span><p class="admin-muted">Login required.</p>`; return; }
    const role = user.role || (user.is_admin ? "owner" : "staff");
    const note = `Role: ${esc(role)}`;
    el.innerHTML = `<span class="saas-badge">Super admin session</span><strong>${esc(user.email || "Admin")}</strong><p class="admin-muted">${note}</p>`;
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
      ["Customers", "users"], ["Companies", "companies"], ["Projects", "projects"], ["Uploads", "uploads"],
      ["Reports", "reports"], ["Payments", "payments"], ["Support", "support_tickets"], ["Audit logs", "audit_logs"],
      ["Pending analyses", "pending_analyses"], ["Failed analyses", "failed_analyses"], ["Used credits", "used_credits"], ["Activity logs", "activity_logs"]
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
    if(module === "audit-integrity" || module === "audit-archive" || module === "operations-health") return [];
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

  function valueFor(row, col){
    const fallbacks = {
      user_id: ["user_id", "auth_user_id", "id"],
      company_id: ["company_id", "company_uuid", "id"],
      company_name: ["company_name", "name"],
      project_id: ["project_id", "id"],
      owner_email: ["owner_email", "customer_email", "email"],
      client: ["client", "client_name"],
      contractor: ["contractor", "contractor_name"],
      status: ["status", "current_status", "upload_status", "parser_status"],
      file_id: ["file_id", "id"],
      original_name: ["original_name", "original_filename"],
      content_type: ["content_type", "mime_type"],
      payment_id: ["payment_id", "provider_payment_id", "id"],
      checkout_id: ["checkout_id", "provider_session_id"],
      plan_code: ["plan_code", "plan_name", "plan"],
      paid_at: ["paid_at", "created_at"],
      report_id: ["report_id", "id"],
      analysis_id: ["analysis_id", "analysis_result_id", "job_id"],
      credit_id: ["credit_id", "id"],
      total_credits: ["total_credits", "amount"],
      remaining_credits: ["remaining_credits", "remaining"],
      period_start: ["period_start", "current_period_start", "created_at"],
      event: ["event", "action"],
      payload: ["payload", "metadata"]
    };
    const keys = fallbacks[col] || [col];
    for(const key of keys){
      if(row[key] !== null && row[key] !== undefined && row[key] !== "") return row[key];
    }
    return undefined;
  }

  function applyPermissions(admin){
    permissions = new Set(admin?.permissions || []);
    const allowedTabs = [];
    $$("[data-admin-tab]").forEach(btn => {
      const cfg = modules[btn.dataset.adminTab];
      const allowed = !cfg?.permission || permissions.has(cfg.permission);
      btn.hidden = !allowed;
      btn.disabled = !allowed;
      if(allowed) allowedTabs.push(btn.dataset.adminTab);
    });
    if(!allowedTabs.includes(activeTab)){
      activeTab = allowedTabs[0] || "customers";
    }
  }

  function renderTable(module, rows){
    const cfg = modules[module];
    if(!rows.length) return `<div class="admin-empty">No ${esc(cfg.title.toLowerCase())} records found.</div>`;
    const head = cfg.columns.map(c => `<th>${esc(c.replaceAll("_"," "))}</th>`).join("") + `<th>Details</th>`;
    const body = rows.map(row => {
      const cells = cfg.columns.map(col => {
        const value = valueFor(row, col);
        if(col === "status" || col.endsWith("_status")) return `<td>${statusPill(value)}</td>`;
        if(col === "payload" || col === "metadata") return `<td>${json(value)}</td>`;
        if(/credits|amount|value|limit|used|remaining|total/.test(col)) return `<td><strong>${fmt(value)}</strong></td>`;
        return `<td>${fmt(value)}</td>`;
      }).join("");
      return `<tr>${cells}<td>${json(row)}</td></tr>`;
    }).join("");
    return `<table class="admin-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  }

  function renderAuditIntegrity(data){
    const status = data?.audit_integrity || {};
    const verified = status.verified === true;
    const available = status.available !== false;
    const label = verified ? "Verified" : (available ? "Review required" : "Unavailable");
    const cls = verified ? "" : "bad";
    const items = [
      ["Checked events", status.checked_events ?? 0],
      ["Verification limit", status.checked_limit ?? "-"],
      ["Integrity version", status.integrity_version ?? "-"],
      ["Broken audit ID", status.broken_audit_id || "None"],
      ["Last event hash", status.last_event_hash ? `${String(status.last_event_hash).slice(0, 18)}…` : "-"],
      ["Reason", status.reason || "-"],
    ];
    return `<div class="admin-integrity-card">
      <div class="admin-integrity-head"><span class="admin-pill ${cls}">${esc(label)}</span><p class="admin-muted">Append-only v1 audit-chain verification. Investigate any non-verified result before making further privileged changes.</p></div>
      <dl class="admin-integrity-grid">${items.map(([key,value]) => `<div><dt>${esc(key)}</dt><dd>${fmt(value)}</dd></div>`).join("")}</dl>
    </div>`;
  }

  function renderOperationsHealth(data){
    const health = data?.operations_health || {};
    const state = String(health.status || "unknown");
    const cls = state === "healthy" ? "" : "bad";
    const components = Array.isArray(health.components) ? health.components : [];
    const incidents = Array.isArray(health.incidents) ? health.incidents : [];
    return `<div class="admin-integrity-card">
      <div class="admin-integrity-head"><span class="admin-pill ${cls}">${esc(state)}</span><p class="admin-muted">Cross-service status for runtime readiness, analysis workers and external audit archive delivery. This view contains only operational counts and incident codes.</p></div>
      <h4 class="admin-subtitle">Components</h4>
      ${components.length ? `<div class="admin-mini-list">${components.map(component => `<div><strong>${fmt(component.name)}</strong><span>${fmt(component.status)} · ${fmt(component.incident_codes?.join(", ") || "no incidents")}</span></div>`).join("")}</div>` : `<div class="admin-empty">No component health data is available.</div>`}
      <h4 class="admin-subtitle">Active incidents</h4>
      ${incidents.length ? `<div class="admin-mini-list">${incidents.map(item => `<div><strong>${fmt(item.code)}</strong><span>${fmt(item.severity)} · ${fmt(item.message)}</span></div>`).join("")}</div>` : `<div class="admin-empty">No active operational incidents.</div>`}
    </div>`;
  }

  function renderAuditArchive(data){
    const status = data?.audit_archive || {};
    const enabled = status.mode === "webhook" && status.delivery_ready === true;
    const available = status.available !== false;
    const label = enabled ? "Delivery enabled" : (available ? "Delivery disabled / review" : "Unavailable");
    const cls = enabled ? "" : "bad";
    const items = [
      ["Mode", status.mode || "-"],
      ["Pending", status.pending ?? 0],
      ["Retry", status.retry ?? 0],
      ["Delivering", status.delivering ?? 0],
      ["Delivered", status.delivered ?? 0],
      ["Dead-lettered", status.dead_lettered ?? 0],
      ["Oldest pending", status.oldest_pending_at || "-"],
      ["Last delivered", status.last_delivered_at || "-"],
    ];
    const workers = Array.isArray(status.workers) ? status.workers : [];
    const dead = Array.isArray(status.recent_dead_lettered) ? status.recent_dead_lettered : [];
    return `<div class="admin-integrity-card">
      <div class="admin-integrity-head"><span class="admin-pill ${cls}">${esc(label)}</span><p class="admin-muted">The database outbox stores immutable audit snapshots before webhook delivery. A dead-lettered item requires owner review and explicit retry.</p></div>
      <dl class="admin-integrity-grid">${items.map(([key,value]) => `<div><dt>${esc(key)}</dt><dd>${fmt(value)}</dd></div>`).join("")}</dl>
      <h4 class="admin-subtitle">Archive workers</h4>
      ${workers.length ? `<div class="admin-mini-list">${workers.map(w => `<div><strong>${fmt(w.worker_id)}</strong><span>${fmt(w.status)} · last seen ${fmt(w.last_seen_at)} · delivered ${fmt(w.processed_events)}</span></div>`).join("")}</div>` : `<div class="admin-empty">No audit archive worker heartbeat has been received.</div>`}
      <h4 class="admin-subtitle">Recent dead-lettered deliveries</h4>
      ${dead.length ? `<div class="admin-mini-list">${dead.map(item => `<div><strong>${fmt(item.archive_id)}</strong><span>${fmt(item.last_error || "No error detail")} · ${fmt(item.attempts)}/${fmt(item.max_attempts)} attempts</span></div>`).join("")}</div>` : `<div class="admin-empty">No dead-lettered archive delivery.</div>`}
    </div>`;
  }

  function renderModuleTools(module){
    if(module === "audit-archive"){
      return `<form class="admin-action-form" id="adminAuditArchiveRetryForm">
        <input name="archive_id" placeholder="Archive ID (dead-lettered item)" required />
        <label class="admin-check"><input name="reset_attempts" type="checkbox" /> Reset attempts</label>
        <button class="saas-btn secondary" type="submit">Retry archive delivery</button>
        <span class="admin-muted" id="adminActionStatus"></span>
      </form>`;
    }
    if(module === "staff"){
      return `<form class="admin-action-form" id="adminStaffForm">
        <input name="email" type="email" placeholder="staff@devbareun.com" required />
        <input name="full_name" placeholder="Full name" />
        <select name="role">
          <option value="support">Support</option>
          <option value="analyst">Analyst</option>
          <option value="finance">Finance</option>
          <option value="operator">Operator</option>
          <option value="owner">Owner</option>
        </select>
        <button class="saas-btn secondary" type="submit">Create staff</button>
        <span class="admin-muted" id="adminActionStatus"></span>
      </form>`;
    }
    if(module === "support-tickets"){
      return `<form class="admin-action-form" id="adminSupportForm">
        <input name="customer_email" type="email" placeholder="customer@company.com" required />
        <input name="subject" placeholder="Subject" required />
        <input name="message" placeholder="Message" required />
        <button class="saas-btn secondary" type="submit">Create ticket</button>
        <span class="admin-muted" id="adminActionStatus"></span>
      </form>`;
    }
    if(module === "credit-usage"){
      return `<form class="admin-action-form" id="adminCreditForm">
        <input name="owner_email" type="email" placeholder="customer@company.com" required />
        <input name="amount" type="number" step="1" placeholder="+1 / -1" required />
        <input name="reason" placeholder="Reason" required />
        <button class="saas-btn secondary" type="submit">Adjust credits</button>
        <span class="admin-muted" id="adminActionStatus"></span>
      </form>`;
    }
    if(module === "customers"){
      return `<form class="admin-action-form" id="adminCustomerStatusForm">
        <input name="email" type="email" placeholder="customer@company.com" required />
        <select name="status">
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
        <input name="note" placeholder="Optional admin note" />
        <button class="saas-btn secondary" type="submit">Update status</button>
        <span class="admin-muted" id="adminActionStatus"></span>
      </form>`;
    }
    return "";
  }

  function bindModuleActions(module){
    const status = $("#adminActionStatus");
    const setStatus = (msg) => { if(status) status.textContent = msg; };
    $("#adminAuditArchiveRetryForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      const archiveId = payload.archive_id;
      delete payload.archive_id;
      payload.reset_attempts = payload.reset_attempts === "on";
      setStatus("Retrying archive delivery...");
      await sendJson(`/api/super-admin/audit-archive/${encodeURIComponent(archiveId)}/retry`, "POST", payload);
      setStatus("Archive item requeued.");
      await loadModule("audit-archive");
    });
    $("#adminStaffForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      setStatus("Saving staff...");
      await sendJson("/api/super-admin/staff", "POST", payload);
      setStatus("Staff saved.");
      await loadModule("staff");
    });
    $("#adminSupportForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      setStatus("Creating ticket...");
      await sendJson("/api/super-admin/support-tickets", "POST", payload);
      setStatus("Ticket created.");
      await loadModule("support-tickets");
    });
    $("#adminCreditForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      payload.amount = Number(payload.amount || 0);
      setStatus("Adjusting credits...");
      await sendJson("/api/super-admin/credits/adjust", "POST", payload);
      setStatus("Credit adjustment recorded.");
      await loadModule("credit-usage");
    });
    $("#adminCustomerStatusForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      const email = payload.email;
      delete payload.email;
      setStatus("Updating customer...");
      await sendJson(`/api/super-admin/customers/${encodeURIComponent(email)}/status`, "PATCH", payload);
      setStatus("Customer updated.");
      await loadModule("customers");
    });
  }

  async function loadOverview(){
    const data = await request("/api/super-admin/overview");
    applyPermissions(data.admin);
    setSessionCard(data.admin);
    renderKpis(data.counts || {});
    return data;
  }

  async function loadModule(module = activeTab){
    activeTab = module;
    const cfg = modules[module];
    if(cfg?.permission && !permissions.has(cfg.permission)){
      $("#adminModuleCount").textContent = "Forbidden";
      $("#adminModuleBody").innerHTML = `<div class="admin-error">Your role cannot access ${esc(cfg.title)}.</div>`;
      return;
    }
    $$("[data-admin-tab]").forEach(btn => btn.classList.toggle("active", btn.dataset.adminTab === module));
    $("#adminModuleEyebrow").textContent = module.replaceAll("-", " ");
    $("#adminModuleTitle").textContent = cfg.title;
    $("#adminModuleCount").textContent = "Loading";
    $("#adminModuleBody").innerHTML = `<div class="admin-loading">Loading ${esc(cfg.title.toLowerCase())}...</div>`;
    try{
      const data = await request(`${cfg.endpoint}?${queryString()}`);
      const rows = normalizeRows(module, data);
      $("#adminModuleCount").textContent = module === "audit-integrity" ? "Integrity status" : (module === "audit-archive" ? "Archive status" : (module === "operations-health" ? "Operations health" : `${data.total ?? rows.length} records`));
      $("#adminModuleBody").innerHTML = module === "audit-integrity"
        ? renderAuditIntegrity(data)
        : (module === "audit-archive" ? renderModuleTools(module) + renderAuditArchive(data) : (module === "operations-health" ? renderOperationsHealth(data) : renderModuleTools(module) + renderTable(module, rows)));
      bindModuleActions(module);
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

  async function adminLogin(e){
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const payload = Object.fromEntries(fd.entries());
    $("#adminLoginStatus").textContent = "Signing in to super admin...";
    try{
      await API.login(payload.email, payload.password, payload.plan || "pro");
      $("#adminLoginStatus").textContent = "Super admin session is ready.";
      await boot();
    }catch(err){
      $("#adminLoginStatus").textContent = err.message || "Could not sign in to super admin.";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("#pilotAdminLogin")?.addEventListener("submit", adminLogin);
    $$("[data-admin-tab]").forEach(btn => btn.addEventListener("click", () => loadModule(btn.dataset.adminTab)));
    $("#adminRefresh")?.addEventListener("click", async () => { await loadOverview(); await loadModule(activeTab); });
    $("#adminSearch")?.addEventListener("keydown", (e) => { if(e.key === "Enter") loadModule(activeTab); });
    $("#adminLimit")?.addEventListener("change", () => loadModule(activeTab));
    $("#adminLogout")?.addEventListener("click", () => { API.clearSession(); showLogin(true); setSessionCard(null); });
    boot();
  });
})();
