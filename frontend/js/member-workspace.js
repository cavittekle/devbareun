(function () {
  "use strict";

  var STATE_KEY = "devbareun_member_workspace_state";
  var SESSION_KEY = "devbareun_member_workspace_session";
  var APP_ID = "memberWorkspaceApp";
  var WORKSPACE_VERSION = "2026-06-04-member-panel-v2";
  var authEventsBound = false;
  var workspaceEventsBound = false;

  var analysisModules = {
    "Schedule Recovery": {
      short: "Delay and workforce logic",
      files: ["Baseline schedule", "Actual progress", "Workforce data (optional)"],
      outputs: ["Delay dashboard", "Critical path", "Workforce gap", "Recovery plan"],
      reportType: "Schedule Recovery Report"
    },
    "Cost Control": {
      short: "Estimate and payment tracking",
      files: ["Cost estimate / BOQ", "Progress payment / F-2", "Actual cost records"],
      outputs: ["Cost variance dashboard", "Payment status", "Budget pressure", "Export package"],
      reportType: "Cost Control Report"
    },
    "Material Continuity": {
      short: "Stock and consumption logic",
      files: ["Material list / BOQ", "Stock records", "Delivery or procurement updates"],
      outputs: ["Material dashboard", "Shortage alerts", "Delivery risk", "Continuity actions"],
      reportType: "Material Continuity Report"
    },
    "Risk & Decisions": {
      short: "Risk register and decision tracking",
      files: ["Risk register", "Decision log", "Meeting notes or issue records"],
      outputs: ["Risk dashboard", "Decision status", "Priority actions", "Management notes"],
      reportType: "Risk & Decisions Report"
    }
  };

  var pages = {
    login: { title: "Login", path: "login.html" },
    register: { title: "Create account", path: "register.html" },
    dashboard: { title: "Overview", path: "dashboard.html" },
    upload: { title: "Upload Project", path: "upload.html" },
    projects: { title: "My Projects", path: "projects.html" },
    "project-detail": { title: "Project Dashboard", path: "project-detail.html" },
    reports: { title: "Reports", path: "reports.html" },
    billing: { title: "Billing", path: "billing.html" },
    settings: { title: "Settings", path: "settings.html" }
  };

  var planCatalog = {
    plus: {
      id: "plus",
      name: "Plus",
      price: "$49",
      limit: 5,
      label: "Plus Plan",
      badge: "5 reviews / month",
      description: "For teams that need recurring project credits, upload history and essential reporting.",
      features: [
        "5 project credits per month",
        "Basic dashboard access",
        "Project upload",
        "Schedule, cost, material and risk modules",
        "PDF export",
        "Basic reporting"
      ]
    },
    pro: {
      id: "pro",
      name: "Pro",
      price: "$89",
      limit: 20,
      label: "Pro Plan",
      badge: "20 reviews / month",
      description: "For companies managing multiple active sites with stronger reporting and priority status.",
      features: [
        "20 project credits per month",
        "Advanced management dashboard",
        "Schedule recovery module",
        "Cost control",
        "Material continuity tracking",
        "Risk and decision register",
        "PDF and Excel export",
        "Priority review status",
        "Advanced reporting"
      ]
    }
  };

  var defaultProjects = [
    {
      id: "residential-complex",
      name: "Residential Complex",
      location: "Baku, White City",
      client: "Caspian Development",
      type: "Residential",
      phase: "Construction",
      uploadedDate: "2026-05-05",
      reviewDate: "2026-05-11",
      module: "Schedule Recovery",
      status: "Ready",
      risk: "High",
      progressScore: 72,
      plannedProgress: 72,
      actualProgress: 68,
      delayDays: 14,
      costVariance: "+$185K",
      paymentStatus: "Delayed",
      workforceGap: "12%",
      materialContinuity: "Medium",
      openDecisions: 5,
      criticalRisks: 2,
      lastUpdated: "2026-05-24"
    },
    {
      id: "public-building",
      name: "Public Building",
      location: "Ganja",
      client: "Municipal Authority",
      type: "Public Building",
      phase: "Construction",
      uploadedDate: "2026-05-08",
      reviewDate: "2026-05-14",
      module: "Schedule Recovery",
      status: "Processing",
      risk: "Medium",
      progressScore: 61,
      plannedProgress: 58,
      actualProgress: 51,
      delayDays: 9,
      costVariance: "+$72K",
      paymentStatus: "On watch",
      workforceGap: "8%",
      materialContinuity: "Medium",
      openDecisions: 3,
      criticalRisks: 1,
      lastUpdated: "2026-05-25"
    },
    {
      id: "infrastructure-road-works",
      name: "Infrastructure Road Works",
      location: "Absheron corridor",
      client: "Road Works Group",
      type: "Infrastructure",
      phase: "Construction",
      uploadedDate: "2026-05-10",
      reviewDate: "2026-05-16",
      module: "Risk & Decisions",
      status: "Action Required",
      risk: "Critical",
      progressScore: 48,
      plannedProgress: 64,
      actualProgress: 47,
      delayDays: 22,
      costVariance: "+$310K",
      paymentStatus: "Blocked",
      workforceGap: "21%",
      materialContinuity: "Low",
      openDecisions: 8,
      criticalRisks: 4,
      lastUpdated: "2026-05-26"
    },
    {
      id: "mixed-use-development",
      name: "Mixed-use Development",
      location: "Sumgait",
      client: "North Bay Assets",
      type: "Mixed-use",
      phase: "Design",
      uploadedDate: "2026-05-15",
      reviewDate: "2026-05-15",
      module: "Document Control",
      status: "Draft",
      risk: "Low",
      progressScore: 84,
      plannedProgress: 36,
      actualProgress: 34,
      delayDays: 2,
      costVariance: "+$18K",
      paymentStatus: "Clear",
      workforceGap: "3%",
      materialContinuity: "High",
      openDecisions: 2,
      criticalRisks: 0,
      lastUpdated: "2026-05-21"
    },
    {
      id: "commercial-center",
      name: "Commercial Center",
      location: "Baku, Yasamal",
      client: "Urban Retail Partners",
      type: "Commercial",
      phase: "Handover",
      uploadedDate: "2026-05-18",
      reviewDate: "2026-05-19",
      module: "Cost Control",
      status: "Ready",
      risk: "Medium",
      progressScore: 79,
      plannedProgress: 91,
      actualProgress: 87,
      delayDays: 5,
      costVariance: "+$94K",
      paymentStatus: "Partial",
      workforceGap: "6%",
      materialContinuity: "High",
      openDecisions: 4,
      criticalRisks: 1,
      lastUpdated: "2026-05-26"
    },
    {
      id: "industrial-facility",
      name: "Industrial Facility",
      location: "Alat Free Zone",
      client: "Logistics Build Co.",
      type: "Industrial",
      phase: "Tender",
      uploadedDate: "2026-05-20",
      reviewDate: "2026-05-20",
      module: "Material Continuity",
      status: "Uploaded",
      risk: "High",
      progressScore: 57,
      plannedProgress: 44,
      actualProgress: 39,
      delayDays: 7,
      costVariance: "+$121K",
      paymentStatus: "Pending",
      workforceGap: "10%",
      materialContinuity: "Low",
      openDecisions: 6,
      criticalRisks: 2,
      lastUpdated: "2026-05-27"
    }
  ];

  var defaultReports = [
    {
      id: "rpt-residential-full",
      name: "Residential Complex Control Report",
      projectId: "residential-complex",
      projectName: "Residential Complex",
      type: "Schedule Recovery Report",
      createdDate: "2026-05-11",
      format: "PDF",
      status: "Ready"
    },
    {
      id: "rpt-commercial-cost",
      name: "Commercial Center Payment Report",
      projectId: "commercial-center",
      projectName: "Commercial Center",
      type: "Cost Control Report",
      createdDate: "2026-05-19",
      format: "PDF + Excel",
      status: "Ready"
    },
    {
      id: "rpt-road-risk",
      name: "Road Works Risk Register",
      projectId: "infrastructure-road-works",
      projectName: "Infrastructure Road Works",
      type: "Risk & Decisions Report",
      createdDate: "2026-05-22",
      format: "PDF",
      status: "Action Required"
    }
  ];

  var defaultNotifications = [
    {
      id: "n1",
      title: "Project review completed",
      body: "Residential Complex dashboard and report are ready.",
      time: "Today"
    },
    {
      id: "n2",
      title: "Monthly limit almost used",
      body: "Plus workspace has used 3 of 5 project reviews.",
      time: "Yesterday"
    },
    {
      id: "n3",
      title: "Critical risk found",
      body: "Infrastructure Road Works needs action on payment and site sequence.",
      time: "May 26"
    },
    {
      id: "n4",
      title: "Payment reminder",
      body: "Next billing date is June 1, 2026.",
      time: "May 25"
    },
    {
      id: "n5",
      title: "Report ready for download",
      body: "Commercial Center PDF and Excel exports are available.",
      time: "May 24"
    }
  ];

  function initialState() {
    return {
      currentPlan: "plus",
      version: WORKSPACE_VERSION,
      activePlan: true,
      usage: {
        plus: { used: 3, limit: 5, nextBillingDate: "2026-06-01", paymentStatus: "Active" },
        pro: { used: 7, limit: 20, nextBillingDate: "2026-06-01", paymentStatus: "Active" }
      },
      profile: {
        fullName: "DevBareun Demo User",
        email: "member@devbareun.com",
        company: "DevBareun Construction",
        position: "Project Controls Manager",
        phone: "",
        city: "Baku",
        country: "Azerbaijan"
      },
      preferences: {
        dashboardLanguage: "English",
        reportLanguage: "English",
        exportFormat: "PDF + Excel",
        notifications: {
          completed: true,
          limit: true,
          billing: true,
          risk: true
        }
      },
      projects: defaultProjects.slice(),
      reports: defaultReports.slice(),
      notifications: defaultNotifications.slice()
    };
  }

  /**
   * WARNING: plan and usage data here is display-only.
   * A user can modify these values in DevTools. Server must enforce limits.
   * NOTE: plan and usage data must be re-validated server-side on every API call. Client state is display-only.
   */
  function loadState() {
    try {
      var raw = localStorage.getItem(STATE_KEY);
      if (!raw) {
        return verifyStateIntegrity(initialState());
      }
      return verifyStateIntegrity(normalizeState(JSON.parse(raw)));
    } catch (error) {
      return verifyStateIntegrity(initialState());
    }
  }

  function normalizeState(state) {
    var fresh = initialState();
    var needsMigration = !state || state.version !== WORKSPACE_VERSION;
    state = state && typeof state === "object" ? state : fresh;
    state.currentPlan = state.currentPlan || fresh.currentPlan;
    state.version = state.version || "";
    state.activePlan = typeof state.activePlan === "boolean" ? state.activePlan : true;
    state.usage = Object.assign({}, fresh.usage, state.usage || {});
    state.profile = Object.assign({}, fresh.profile, state.profile || {});
    state.preferences = Object.assign({}, fresh.preferences, state.preferences || {});
    state.projects = Array.isArray(state.projects) && state.projects.length ? state.projects : fresh.projects;
    state.reports = Array.isArray(state.reports) ? state.reports : fresh.reports;
    state.notifications = Array.isArray(state.notifications) ? state.notifications : fresh.notifications;
    if (needsMigration) {
      state.projects.forEach(normalizeProjectModule);
      state.reports.forEach(normalizeReportType);
    }
    state.version = WORKSPACE_VERSION;
    return state;
  }

  function verifyStateIntegrity(state) {
    var fresh = initialState();
    state = state && typeof state === "object" ? state : fresh;
    if (!Object.prototype.hasOwnProperty.call(planCatalog, state.currentPlan)) {
      console.warn("DevBareun: state integrity check failed, field reset:", "currentPlan");
      state.currentPlan = fresh.currentPlan;
    }
    state.usage = state.usage && typeof state.usage === "object" ? state.usage : {};
    Object.keys(planCatalog).forEach(function (plan) {
      var catalog = planCatalog[plan];
      var freshUsage = fresh.usage[plan];
      var usage = state.usage[plan] && typeof state.usage[plan] === "object" ? state.usage[plan] : {};
      var used = Number(usage.used);
      if (!Number.isInteger(used) || used < 0 || used > catalog.limit) {
        console.warn("DevBareun: state integrity check failed, field reset:", "usage." + plan + ".used");
        usage.used = freshUsage.used;
      }
      usage.limit = catalog.limit;
      usage.nextBillingDate = usage.nextBillingDate || freshUsage.nextBillingDate;
      usage.paymentStatus = usage.paymentStatus || freshUsage.paymentStatus;
      state.usage[plan] = usage;
    });
    return state;
  }

  function normalizeProjectModule(project) {
    if (!project) return;
    if (project.module === "Full Project Control" || project.module === "Document Control") {
      project.module = "Schedule Recovery";
    }
    if (project.module === "Cost & Payment Control") {
      project.module = "Cost Control";
    }
    if (project.module === "Material Flow") {
      project.module = "Material Continuity";
    }
    if (project.status === "Completed") {
      project.status = "Ready";
    }
  }

  function normalizeReportType(report) {
    if (!report) return;
    report.type = String(report.type || "")
      .replace("Full Project Control", "Schedule Recovery")
      .replace("Cost & Payment", "Cost Control")
      .replace("Material Flow", "Material Continuity");
  }

  function saveState(state) {
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
  }

  /**
   * WARNING: session is stored in localStorage and is client-readable.
   * Always re-validate access server-side (Supabase JWT) on protected API calls.
   */
  function getSession() {
    try {
      var local = JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
      if (local && local.loggedIn) {
        return local;
      }
      var apiSession = window.DevBareunAPI && window.DevBareunAPI.readSession ? window.DevBareunAPI.readSession() : null;
      if (apiSession && apiSession.access_token) {
        return {
          loggedIn: true,
          activePlan: true,
          plan: (apiSession.user && apiSession.user.plan) || localStorage.getItem("devbareun_selected_plan") || "plus",
          email: (apiSession.user && apiSession.user.email) || "member@devbareun.com",
          access_token: apiSession.access_token
        };
      }
      return local;
    } catch (error) {
      return null;
    }
  }

  function setSession(session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    if (session && session.access_token && window.DevBareunAPI && window.DevBareunAPI.saveSession) {
      window.DevBareunAPI.saveSession(session);
    }
  }

  function clearSession() {
    localStorage.removeItem(SESSION_KEY);
    if (window.DevBareunAPI && window.DevBareunAPI.clearAuthToken) {
      window.DevBareunAPI.clearAuthToken();
    }
  }

  function checkoutEmail() {
    var session = getSession();
    var state = loadState();
    return String((session && session.email) || (state.profile && state.profile.email) || localStorage.getItem("devbareun_checkout_email") || "").trim();
  }

  function requestCheckoutEmail() {
    var email = checkoutEmail();
    email = String(email).trim().toLowerCase();
    if (email && email.indexOf("@") !== -1) {
      localStorage.setItem("devbareun_checkout_email", email);
      return email;
    }
    throw new Error("Please update your email in Settings before checkout.");
  }

  /**
   * Demo mode bypasses real auth. Only enable via window.DEVBAREUN_ENABLE_DEV_AUTH
   * in development. Never set this to true in production builds.
   */
  function devMemberDemoEnabled() {
    return window.DEVBAREUN_ENABLE_DEV_AUTH === true;
  }

  function getApp() {
    return document.getElementById(APP_ID);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function slug(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/&/g, "and")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function statusClass(value) {
    return slug(value);
  }

  function riskClass(value) {
    return slug(value);
  }

  function formatDate(value) {
    if (!value) {
      return "Not set";
    }
    var parts = String(value).split("-");
    if (parts.length === 3) {
      return parts[2] + "." + parts[1] + "." + parts[0];
    }
    return value;
  }

  function currentUsage(state) {
    var plan = state.currentPlan || "plus";
    var usage = state.usage[plan] || { used: 0, limit: planCatalog[plan] ? planCatalog[plan].limit : 0 };
    var limit = Number(usage.limit || (planCatalog[plan] && planCatalog[plan].limit) || 0);
    var used = Math.min(Number(usage.used || 0), limit);
    return {
      plan: plan,
      used: used,
      limit: limit,
      remaining: Math.max(limit - used, 0),
      percent: limit ? Math.min(Math.round((used / limit) * 100), 100) : 0,
      nextBillingDate: usage.nextBillingDate || "2026-06-01",
      paymentStatus: usage.paymentStatus || "Active"
    };
  }

  function setCurrentPlan(planId, active) {
    var state = loadState();
    if (planCatalog[planId]) {
      state.currentPlan = planId;
    }
    state.activePlan = active !== false;
    saveState(state);
    setSession({
      loggedIn: true,
      activePlan: state.activePlan,
      plan: state.currentPlan,
      email: state.profile.email
    });
    return state;
  }

  function redirect(path) {
    window.location.href = path;
  }

  function pageFromLocation() {
    var page = document.body.getAttribute("data-member-page") || "";
    if (page) {
      return page;
    }
    var file = window.location.pathname.split("/").pop().replace(".html", "");
    return file || "dashboard";
  }

  function routeProjectId() {
    var params = new URLSearchParams(window.location.search);
    if (params.get("id")) {
      return params.get("id");
    }
    var parts = window.location.pathname.split("/").filter(Boolean);
    if (parts[0] === "projects" && parts[1]) {
      return parts[1];
    }
    return "";
  }

  function ensureAccess(page, state) {
    activateDemoSessionFromUrl(state);
    var session = getSession();
    if (page === "login" || page === "register") {
      return true;
    }
    if (!session || !session.loggedIn) {
      redirect("login.html?next=" + encodeURIComponent(window.location.pathname + window.location.search));
      return false;
    }
    if (!state.activePlan && page !== "billing" && page !== "settings") {
      redirect("billing.html?choose=1");
      return false;
    }
    return true;
  }

  function activateDemoSessionFromUrl(state) {
    var params = new URLSearchParams(window.location.search);
    if (params.get("demo") !== "1" || !devMemberDemoEnabled()) {
      return;
    }
    var plan = params.get("plan") === "pro" ? "pro" : "plus";
    if (planCatalog[plan]) {
      state.currentPlan = plan;
    }
    state.activePlan = true;
    saveState(state);
    setSession({
      loggedIn: true,
      activePlan: true,
      plan: state.currentPlan,
      email: state.profile.email
    });
    if (window.history && window.history.replaceState) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }

  function brandMarkup() {
    return '<a class="mw-brand" href="dashboard.html" aria-label="DevBareun workspace">' +
      '<img src="assets/devbareun-logo-horizontal-white.svg?v=3" alt="DevBareun" />' +
      '</a>';
  }

  function authPage(type) {
    var isRegister = type === "register";
    var action = isRegister ? "Create workspace account" : "Login to workspace";
    var introTitle = isRegister ? "Create your project control workspace." : "Welcome back to your member workspace.";
    var introText = isRegister
      ? "Create your member workspace, choose Plus or Pro, and continue to project control."
      : "Open your personal construction analytics dashboard, upload project files, track usage and download reports.";
    var formTitle = isRegister ? "Create account" : "Login";
    var submitLabel = isRegister ? "Create account and continue" : "Login and open dashboard";
    var demoControls = devMemberDemoEnabled()
      ? '<div class="mw-demo-row">' +
        '<button class="mw-btn" type="button" data-demo-login="plus">View as Plus user</button>' +
        '<button class="mw-btn" type="button" data-demo-login="pro">View as Pro user</button>' +
        '<button class="mw-btn" type="button" data-demo-login="none">No active plan</button>' +
        '</div>'
      : "";
    return '<main class="mw-auth-shell">' +
      '<section class="mw-auth-layout">' +
      '<article class="mw-auth-intro">' +
      brandMarkup() +
      '<p class="mw-eyebrow">Member workspace</p>' +
      '<h1>' + introTitle + '</h1>' +
      '<p>' + introText + '</p>' +
      '<div class="mw-auth-steps">' +
      '<article><b>01</b><div><strong>Plan and usage control</strong><p class="mw-muted">View monthly project review limits for Plus and Pro accounts.</p></div></article>' +
      '<article><b>02</b><div><strong>Project upload flow</strong><p class="mw-muted">Add files, choose analysis modules and start a project performance review.</p></div></article>' +
      '<article><b>03</b><div><strong>Reports and billing</strong><p class="mw-muted">Manage exports, subscription status, invoices and workspace settings.</p></div></article>' +
      '</div>' +
      '</article>' +
      '<article class="mw-auth-card">' +
      '<p class="mw-eyebrow">' + action + '</p>' +
      '<h1>' + formTitle + '</h1>' +
      '<p>Production login uses your Supabase Auth session and opens the protected DevBareun workspace.</p>' +
      '<form class="mw-form" data-auth-form="' + type + '">' +
      '<label>Email<input name="email" type="email" value="member@devbareun.com" autocomplete="email" required /></label>' +
      '<label>Password<input name="password" type="password" value="devbareun-demo" autocomplete="current-password" required /></label>' +
      (isRegister ? '<label>Company name<input name="company" type="text" value="DevBareun Construction" /></label>' : "") +
      '<label>Plan<select name="plan"><option value="plus">Plus</option><option value="pro">Pro</option><option value="none">No active plan</option></select></label>' +
      '<button class="mw-btn primary" type="submit">' + submitLabel + '</button>' +
      '<p class="mw-muted" data-auth-status></p>' +
      '</form>' +
      demoControls +
      '<p class="mw-muted">' + (isRegister ? 'Already have an account? <a href="login.html">Login</a>.' : 'New workspace? <a href="register.html">Create account</a>.') + '</p>' +
      '</article>' +
      '</section>' +
      '</main>';
  }

  function shell(page, body) {
    var state = loadState();
    var usage = currentUsage(state);
    var plan = planCatalog[usage.plan] || planCatalog.plus;
    var nav = [
      ["dashboard", navIcon("overview"), "Overview", "dashboard.html"],
      ["upload", navIcon("upload"), "Upload Project", "upload.html"],
      ["projects", navIcon("projects"), "My Projects", "projects.html"],
      ["reports", navIcon("reports"), "Reports", "reports.html"],
      ["billing", navIcon("billing"), "Billing", "billing.html"],
      ["settings", navIcon("settings"), "Settings", "settings.html"]
    ];
    var navMarkup = nav.map(function (item) {
      var active = page === item[0] || (page === "project-detail" && item[0] === "projects");
      return '<a class="mw-nav-link ' + (active ? "active" : "") + '" href="' + item[3] + '">' +
        '<i>' + item[1] + '</i><span>' + item[2] + '</span></a>';
    }).join("");
    var warning = limitWarning(state);
    return '<div class="mw-layout">' +
      '<aside class="mw-sidebar">' +
      brandMarkup() +
      '<nav>' + navMarkup + '<button class="mw-nav-link" type="button" data-logout><i>' + navIcon("logout") + '</i><span>Logout</span></button></nav>' +
      '<div class="mw-sidebar-card"><strong>' + escapeHtml(plan.label) + '</strong>' +
      '<p class="mw-muted">' + usage.used + ' of ' + usage.limit + ' monthly project credits used.</p>' +
      '<div class="mw-meter" aria-label="Usage"><i style="--value:' + usage.percent + '%"></i></div>' +
      '</div>' +
      '</aside>' +
      '<main class="mw-main">' +
      '<header class="mw-topbar">' +
      '<input class="mw-search" type="search" placeholder="Search projects..." data-global-search />' +
      '<button class="mw-icon-btn mw-notification-btn has-dot" type="button" data-notification-toggle aria-label="Notifications"><span>' + navIcon("notifications") + '</span><b>Notifications</b></button>' +
      '<span class="mw-plan-badge">' + escapeHtml(plan.name) + ' plan</span>' +
      '<button class="mw-avatar" type="button" data-account-toggle aria-label="Account menu">DB</button>' +
      '<div class="mw-dropdown" data-notification-menu>' + notificationMarkup(state) + '</div>' +
      '<div class="mw-dropdown mw-account-dropdown" data-account-menu>' + accountMenuMarkup(state, usage) + '</div>' +
      '</header>' +
      (warning ? '<section class="mw-card mw-limit-warning">' + warning + '</section>' : "") +
      body +
      '<div class="mw-toast" data-toast></div>' +
      '</main>' +
      '</div>';
  }

  function navIcon(type) {
    var icons = {
      overview: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13h7V4H4v9Zm9 7h7V4h-7v16ZM4 20h7v-5H4v5Z"/></svg>',
      upload: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 7 8h3v7h4V8h3l-5-5ZM5 17v3h14v-3h2v5H3v-5h2Z"/></svg>',
      projects: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6.5A2.5 2.5 0 0 1 5.5 4h4l2 2H19a2 2 0 0 1 2 2v10.5A2.5 2.5 0 0 1 18.5 21h-13A2.5 2.5 0 0 1 3 18.5v-12Z"/></svg>',
      reports: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l4 4v14H6V3Zm8 1.8V8h3.2L14 4.8ZM8 12h8v2H8v-2Zm0 4h8v2H8v-2Z"/></svg>',
      billing: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16a2 2 0 0 1 2 2v1H2V8a2 2 0 0 1 2-2Zm-2 5h20v5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-5Zm3 3v2h5v-2H5Z"/></svg>',
      notifications: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a4 4 0 0 1 4 4v2.2c0 .9.3 1.7.8 2.4l1.2 1.6c.6.8 1 1.8 1 2.8V17H5v-1c0-1 .4-2 1-2.8l1.2-1.6c.5-.7.8-1.5.8-2.4V7a4 4 0 0 1 4-4Zm-2.7 16a2.8 2.8 0 0 0 5.4 0H9.3Z"/></svg>',
      settings: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m19.4 13.5.1-1.5-.1-1.5 2-1.5-2-3.5-2.4 1a7.3 7.3 0 0 0-2.6-1.5L14 2h-4l-.4 2.5A7.3 7.3 0 0 0 7 6L4.6 5 2.6 8.5l2 1.5-.1 1.5.1 1.5-2 1.5 2 3.5 2.4-1a7.3 7.3 0 0 0 2.6 1.5L10 22h4l.4-2.5A7.3 7.3 0 0 0 17 18l2.4 1 2-3.5-2-1.5ZM12 15.5A3.5 3.5 0 1 1 12 8a3.5 3.5 0 0 1 0 7.5Z"/></svg>',
      logout: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h9v2H6v12h7v2H4V4Zm12.5 4.5L20 12l-3.5 3.5-1.4-1.4 1.1-1.1H10v-2h6.2l-1.1-1.1 1.4-1.4Z"/></svg>'
    };
    return icons[type] || icons.overview;
  }

  function notificationMarkup(state) {
    if (!state.notifications.length) {
      return '<article><strong>No notifications</strong><p class="mw-muted">Workspace updates will appear here.</p></article>';
    }
    return state.notifications.slice(0, 6).map(function (item) {
      return '<article><strong>' + escapeHtml(item.title) + '</strong><p class="mw-muted">' + escapeHtml(item.body) + '</p><small>' + escapeHtml(item.time) + '</small></article>';
    }).join("");
  }

  function accountMenuMarkup(state, usage) {
    return '<article><strong>' + escapeHtml(state.profile.fullName) + '</strong>' +
      '<p class="mw-muted">' + escapeHtml(state.profile.email) + '</p></article>' +
      '<article><strong>' + escapeHtml(planCatalog[usage.plan].label) + '</strong>' +
      '<p class="mw-muted">' + usage.remaining + ' project credits remaining this month.</p></article>' +
      '<div class="mw-action-row"><a class="mw-btn" href="settings.html">Settings</a><button class="mw-btn danger" type="button" data-logout>Logout</button></div>';
  }

  function limitWarning(state) {
    if (!state.activePlan) {
      return '<strong>Choose Your Plan</strong><p class="mw-muted">Select Plus or Pro to activate project upload and dashboard features.</p>';
    }
    var usage = currentUsage(state);
    if (usage.percent >= 100) {
      return '<strong>Monthly project credit limit reached.</strong><p class="mw-muted">Upload can stay visible, but new analyses are disabled until upgrade or next billing cycle.</p><a class="mw-btn primary" href="billing.html">Upgrade Plan</a>';
    }
    if (usage.percent >= 80) {
      return '<strong>You have used 80% of your monthly project credits.</strong><p class="mw-muted">Consider upgrading before the next project upload.</p>';
    }
    return "";
  }

  function pageHead(title, text, actions) {
    return '<section class="mw-page-head"><div><p class="mw-eyebrow">DevBareun workspace</p><h1>' +
      title + '</h1><p class="mw-muted">' + text + '</p></div><div class="mw-page-actions">' + (actions || "") + '</div></section>';
  }

  function renderOverview() {
    var state = loadState();
    var usage = currentUsage(state);
    var plan = planCatalog[usage.plan] || planCatalog.plus;
    var projects = state.projects;
    var activeProjects = projects.filter(function (p) { return p.status !== "Archived"; }).length;
    var completedReports = state.reports.filter(function (r) { return r.status === "Ready"; }).length;
    var pending = projects.filter(function (p) { return p.status === "Mapping" || p.status === "Processing" || p.status === "Uploaded"; }).length;
    var highRisk = projects.filter(function (p) { return p.risk === "High" || p.risk === "Critical"; }).length;
    var kpis = [
      ["Current Plan", plan.name, plan.badge],
      ["Used Credits This Month", usage.used + "/" + usage.limit, usage.percent + "% used"],
      ["Remaining Credits", usage.remaining, "Available project analyses"],
      ["Active Projects", activeProjects, "Open workspaces"],
      ["Reports Ready", completedReports, "PDF / Excel exports"],
      ["In Progress", pending, "Mapping or processing"],
      ["High Risk Projects", highRisk, "Needs attention"],
      ["Next Billing Date", formatDate(usage.nextBillingDate), usage.paymentStatus]
    ];
    var kpiMarkup = kpis.map(kpiCard).join("");
    var recent = projects.slice(0, 5).map(projectListRow).join("");
    var reports = state.reports.slice(0, 4).map(function (report) {
      return '<div class="mw-list-row"><div><strong>' + escapeHtml(report.name) + '</strong><small>' + escapeHtml(report.projectName) + ' | ' + escapeHtml(report.type) + '</small></div><span class="mw-format-badge">' + escapeHtml(report.format) + '</span></div>';
    }).join("");
    var actionItems = projects.filter(function (p) { return p.status === "Action Required" || p.risk === "Critical"; }).map(function (project) {
      return '<div class="mw-list-row"><div><strong>' + escapeHtml(project.name) + '</strong><small>' + escapeHtml(project.module) + ' needs follow-up.</small></div><a class="mw-btn" href="project-detail.html?id=' + encodeURIComponent(project.id) + '">Open</a></div>';
    }).join("") || '<div class="mw-empty">No urgent action items in this demo workspace.</div>';
    return shell("dashboard",
      pageHead("Workspace Dashboard", "This is what a customer sees after login: credits, project status, dashboards, reports and billing in one place.", '<a class="mw-btn primary" href="upload.html">Start New Analysis</a><a class="mw-btn" href="reports.html">Download Reports</a>') +
      '<section class="mw-stage-strip">' +
      '<article><b>01</b><strong>Upload files</strong><span>Schedule, BOQ, F-2, stock or risk records.</span></article>' +
      '<article><b>02</b><strong>Confirm mapping</strong><span>Review detected columns before analysis starts.</span></article>' +
      '<article><b>03</b><strong>Get dashboard</strong><span>Only relevant dashboards and reports are shown.</span></article>' +
      '</section>' +
      '<section class="mw-grid kpis">' + kpiMarkup + '</section>' +
      usageCard(state) +
      '<section class="mw-grid two">' +
      '<article class="mw-panel"><h2>Recent Projects</h2><div class="mw-list">' + recent + '</div></article>' +
      '<article class="mw-panel"><h2>Latest Reports</h2><div class="mw-list">' + (reports || '<div class="mw-empty">No reports yet.</div>') + '</div></article>' +
      '</section>' +
      '<section class="mw-grid two">' +
      '<article class="mw-panel"><h2>Action Required</h2><div class="mw-list">' + actionItems + '</div></article>' +
      '<article class="mw-panel"><h2>Alert Summary</h2>' + alertSummary(projects) + '</article>' +
      '</section>'
    );
  }

  function kpiCard(item) {
    return '<article class="mw-card mw-kpi"><span>' + escapeHtml(item[0]) + '</span><strong>' + escapeHtml(item[1]) + '</strong><p class="mw-muted">' + escapeHtml(item[2]) + '</p></article>';
  }

  function usageCard(state) {
    var usage = currentUsage(state);
    var plan = planCatalog[usage.plan] || planCatalog.plus;
    var steps = [];
    for (var index = 0; index <= usage.limit; index += 1) {
      steps.push('<span class="' + (index <= usage.used ? "is-filled" : "") + '">' + index + '</span>');
    }
    return '<section class="mw-panel">' +
      '<div class="mw-usage-head"><div><h2>Monthly Project Credits</h2><p class="mw-muted">' + escapeHtml(plan.label) + ' includes ' + usage.limit + ' project analyses per month.</p></div><strong>' + usage.used + '/' + usage.limit + '</strong></div>' +
      '<div class="mw-meter"><i style="--value:' + usage.percent + '%"></i></div>' +
      '<div class="mw-limit-steps">' + steps.join("") + '</div>' +
      (usage.remaining === 0 ? '<p class="mw-muted">Monthly project credit limit reached.</p><a class="mw-btn primary" href="billing.html">Upgrade Plan</a>' : '<p class="mw-muted">' + usage.remaining + ' project credits remaining this month.</p>') +
      '</section>';
  }

  function projectListRow(project) {
    return '<div class="mw-list-row"><div><strong>' + escapeHtml(project.name) + '</strong><small>' +
      escapeHtml(project.location) + ' | ' + escapeHtml(project.module) + '</small></div>' +
      '<span class="mw-status ' + statusClass(project.status) + '">' + escapeHtml(project.status) + '</span>' +
      '<span class="mw-risk ' + riskClass(project.risk) + '">' + escapeHtml(project.risk) + '</span>' +
      '<a class="mw-btn" href="project-detail.html?id=' + encodeURIComponent(project.id) + '">Open</a></div>';
  }

  function alertSummary(projects) {
    var critical = projects.filter(function (p) { return p.risk === "Critical"; }).length;
    var schedule = projects.filter(function (p) { return Number(p.delayDays || 0) > 7; }).length;
    var cost = projects.filter(function (p) { return String(p.costVariance || "").indexOf("+") === 0; }).length;
    var material = projects.filter(function (p) { return p.materialContinuity === "Low"; }).length;
    return '<div class="mw-list mw-alert-list">' +
      '<div class="mw-list-row"><div><strong>Risk Summary</strong><small>' + critical + ' critical project risk records need review.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>Schedule Alerts</strong><small>' + schedule + ' projects show delay pressure above the target range.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>Cost Alerts</strong><small>' + cost + ' projects have cost variance to monitor.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>Material Continuity Alerts</strong><small>' + material + ' projects show low material continuity.</small></div></div>' +
      '</div>';
  }

  function renderUpload() {
    var state = loadState();
    var usage = currentUsage(state);
    var limitReached = usage.remaining <= 0;
    var moduleNames = Object.keys(analysisModules);
    return shell("upload",
      pageHead("Upload Project", "Add project files, confirm the detected mapping and generate the matching dashboard.", '<a class="mw-btn" href="projects.html">My Projects</a>') +
      '<section class="mw-grid two">' +
      '<article class="mw-panel">' +
      '<form class="mw-form" data-upload-form>' +
      '<div class="mw-form-grid">' +
      '<label>Project name<input name="projectName" type="text" placeholder="Example: Residential Tower A" required /></label>' +
      '<label>Project location<input name="location" type="text" placeholder="City, district or site code" required /></label>' +
      '<label>Client / company name<input name="client" type="text" placeholder="Client or company" required /></label>' +
      '<label>Project type<select name="type" required>' + optionList(["Residential", "Commercial", "Infrastructure", "Public Building", "Mixed-use", "Industrial"]) + '</select></label>' +
      '<label>Project phase<select name="phase" required>' + optionList(["Concept", "Design", "Tender", "Construction", "Handover"]) + '</select></label>' +
      '<label>Analysis module<select name="module" required data-module-select>' + optionList(moduleNames) + '</select></label>' +
      '<div class="full" data-module-helper>' + moduleHelper("Schedule Recovery") + '</div>' +
      '<div class="full">' + uploadBox() + '</div>' +
      '</div>' +
      '<p class="mw-muted" data-upload-status>' + (limitReached ? 'Your monthly limit is used. Upgrade to Pro or wait for next billing cycle.' : 'Supported formats: PDF, XLS, XLSX, DOC, DOCX, CSV, Primavera schedule export placeholder and MS Project export placeholder.') + '</p>' +
      '<button class="mw-btn primary" type="submit" ' + (limitReached ? "disabled" : "") + '>Start Project Review</button>' +
      '</form>' +
      '</article>' +
      '<aside class="mw-panel">' +
      '<h2>Review Capacity</h2>' +
      usageCard(state) +
      '<h2>How It Works</h2>' +
      '<div class="mw-list">' +
      '<div class="mw-list-row"><div><strong>1. Upload</strong><small>Add project files for the selected package.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>2. Mapping preview</strong><small>Detected file types and fields are shown before the dashboard is prepared.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>3. Dashboard and report</strong><small>The workspace shows only relevant dashboard blocks and export files.</small></div></div>' +
      '</div>' +
      '</aside>' +
      '</section>'
    );
  }

  function moduleHelper(name) {
    var module = analysisModules[name] || analysisModules["Schedule Recovery"];
    return '<section class="mw-module-helper">' +
      '<article><p class="mw-eyebrow">Required files</p><h3>' + escapeHtml(name) + '</h3><ol>' + module.files.map(function (file) { return '<li>' + escapeHtml(file) + '</li>'; }).join("") + '</ol></article>' +
      '<article><p class="mw-eyebrow">You will receive</p><h3>Prepared outputs</h3><ul class="mw-check-list">' + module.outputs.map(function (output) { return '<li>' + escapeHtml(output) + '</li>'; }).join("") + '</ul></article>' +
      '</section>';
  }

  function optionList(values) {
    return values.map(function (value) {
      return '<option value="' + escapeHtml(value) + '">' + escapeHtml(value) + '</option>';
    }).join("");
  }

  function uploadBox() {
    return '<label class="mw-upload-area" data-upload-drop>' +
      '<input type="file" multiple data-file-input accept=".pdf,.xls,.xlsx,.doc,.docx,.csv" />' +
      '<span><strong>Drag and drop project files here</strong><br /><small>or select files from your device</small></span>' +
      '</label>' +
      '<div class="mw-file-list" data-file-list></div>';
  }

  function renderProjects() {
    var state = loadState();
    return shell("projects",
      pageHead("My Projects", "Track every uploaded project, status, risk level, progress score and report action.", '<a class="mw-btn primary" href="upload.html">Upload New Project</a>') +
      '<section class="mw-panel">' +
      '<div class="mw-filter-grid" data-project-filters>' +
      '<input class="mw-filter" name="search" placeholder="Search project name" />' +
      '<select class="mw-filter" name="status"><option value="">All statuses</option>' + optionList(["Draft", "Uploaded", "Mapping", "Processing", "Ready", "Action Required", "Archived"]) + '</select>' +
      '<select class="mw-filter" name="risk"><option value="">All risk levels</option>' + optionList(["Low", "Medium", "High", "Critical"]) + '</select>' +
      '<select class="mw-filter" name="type"><option value="">All project types</option>' + optionList(["Residential", "Commercial", "Infrastructure", "Public Building", "Mixed-use", "Industrial"]) + '</select>' +
      '<select class="mw-filter" name="module"><option value="">All modules</option>' + optionList(Object.keys(analysisModules)) + '</select>' +
      '</div>' +
      '<div class="mw-action-row" style="margin-top:14px"><button class="mw-btn primary" type="button" data-view-mode="table">Table view</button><button class="mw-btn" type="button" data-view-mode="cards">Card view</button></div>' +
      '</section>' +
      '<section data-project-results>' + projectsTable(state.projects) + '</section>'
    );
  }

  function projectsTable(projects) {
    if (!projects.length) {
      return '<div class="mw-empty">No projects match the selected filters.</div>';
    }
    var rows = projects.map(function (project) {
      return '<tr>' +
        '<td><strong>' + escapeHtml(project.name) + '</strong></td>' +
        '<td>' + escapeHtml(project.location) + '</td>' +
        '<td>' + escapeHtml(project.type) + '</td>' +
        '<td>' + formatDate(project.uploadedDate) + '</td>' +
        '<td>' + escapeHtml(project.module) + '</td>' +
        '<td><span class="mw-status ' + statusClass(project.status) + '">' + escapeHtml(project.status) + '</span></td>' +
        '<td><span class="mw-risk ' + riskClass(project.risk) + '">' + escapeHtml(project.risk) + '</span></td>' +
        '<td>' + escapeHtml(project.progressScore) + '%</td>' +
        '<td>' + formatDate(project.lastUpdated) + '</td>' +
        '<td><div class="mw-action-row">' +
        '<a class="mw-btn" href="project-detail.html?id=' + encodeURIComponent(project.id) + '">Open Dashboard</a>' +
        '<button class="mw-btn" type="button" data-download="pdf" data-project-id="' + escapeHtml(project.id) + '">PDF</button>' +
        '<button class="mw-btn" type="button" data-download="excel" data-project-id="' + escapeHtml(project.id) + '">Excel</button>' +
        '<button class="mw-btn" type="button" data-archive-project="' + escapeHtml(project.id) + '">Archive</button>' +
        '<button class="mw-btn danger" type="button" data-delete-project="' + escapeHtml(project.id) + '">Delete</button>' +
        '</div></td>' +
        '</tr>';
    }).join("");
    return '<div class="mw-table-wrap"><table class="mw-table"><thead><tr>' +
      '<th>Project Name</th><th>Location</th><th>Type</th><th>Uploaded Date</th><th>Analysis Module</th><th>Status</th><th>Risk Level</th><th>Progress Score</th><th>Last Updated</th><th>Actions</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  function projectsCards(projects) {
    if (!projects.length) {
      return '<div class="mw-empty">No projects match the selected filters.</div>';
    }
    return '<div class="mw-card-grid">' + projects.map(function (project) {
      return '<article class="mw-card mw-project-card"><span class="mw-status ' + statusClass(project.status) + '">' + escapeHtml(project.status) + '</span>' +
        '<h2>' + escapeHtml(project.name) + '</h2><p class="mw-muted">' + escapeHtml(project.location) + ' | ' + escapeHtml(project.type) + '</p>' +
        '<p><strong>' + escapeHtml(project.module) + '</strong></p>' +
        '<div class="mw-meter"><i style="--value:' + Number(project.progressScore || 0) + '%"></i></div>' +
        '<p class="mw-muted">Progress score: ' + escapeHtml(project.progressScore) + '%</p>' +
        '<div class="mw-action-row"><span class="mw-risk ' + riskClass(project.risk) + '">' + escapeHtml(project.risk) + '</span><a class="mw-btn" href="project-detail.html?id=' + encodeURIComponent(project.id) + '">Open Dashboard</a></div>' +
        '</article>';
    }).join("") + '</div>';
  }

  function renderProjectDetail() {
    var state = loadState();
    var id = routeProjectId();
    var project = state.projects.find(function (item) { return item.id === id; }) || state.projects[0];
    if (!project) {
      return shell("project-detail", pageHead("Project Dashboard", "No project data is available.", '<a class="mw-btn" href="projects.html">Back to Projects</a>') + '<div class="mw-empty">No project found.</div>');
    }
    var kpis = [
      ["Planned Progress", project.plannedProgress + "%", "Baseline target"],
      ["Actual Progress", project.actualProgress + "%", "Current site status"],
      ["Progress Variance", (project.actualProgress - project.plannedProgress) + "%", "Planned vs actual"],
      ["Delay Days", project.delayDays, "Schedule pressure"],
      ["Cost Variance", project.costVariance, "Baseline vs actual"],
      ["Payment Status", project.paymentStatus, "Commercial control"],
      ["Workforce Gap", project.workforceGap, "Required vs available"],
      ["Material Continuity", project.materialContinuity, "Flow status"],
      ["Open Decisions", project.openDecisions, "Decision register"],
      ["Critical Risks", project.criticalRisks, "High priority items"]
    ];
    return shell("project-detail",
      '<section class="mw-detail-hero mw-panel">' +
      '<div><p class="mw-eyebrow">Project result dashboard</p><h1>' + escapeHtml(project.name) + '</h1>' +
      '<p class="mw-muted">' + escapeHtml(project.location) + ' | ' + escapeHtml(project.type) + ' | Review date: ' + formatDate(project.reviewDate) + '</p>' +
      '<div class="mw-action-row"><span class="mw-status ' + statusClass(project.status) + '">' + escapeHtml(project.status) + '</span><span class="mw-risk ' + riskClass(project.risk) + '">' + escapeHtml(project.risk) + '</span></div></div>' +
      '<div class="mw-action-row"><button class="mw-btn primary" type="button" data-download="pdf" data-project-id="' + escapeHtml(project.id) + '">Export PDF</button><button class="mw-btn" type="button" data-download="excel" data-project-id="' + escapeHtml(project.id) + '">Export Excel</button></div>' +
      '</section>' +
      '<section class="mw-grid kpis">' + kpis.map(kpiCard).join("") + '</section>' +
      '<section class="mw-chart-grid">' +
      '<article class="mw-panel mw-chart"><h2>Planned vs Actual Progress</h2>' + chartPlaceholderNote() + lineChart() + '</article>' +
      '<article class="mw-panel mw-chart"><h2>Cost Baseline vs Actual</h2>' + chartPlaceholderNote() + barChart([52, 60, 65, 72, 74, 86]) + '</article>' +
      '<article class="mw-panel mw-chart"><h2>Risk Distribution</h2>' + chartPlaceholderNote() + donutChart() + '</article>' +
      '<article class="mw-panel mw-chart"><h2>Material Continuity Status</h2>' + chartPlaceholderNote() + barChart([68, 54, 42, 70, 48, 63]) + '</article>' +
      '<article class="mw-panel mw-chart"><h2>Workforce Requirement</h2>' + chartPlaceholderNote() + lineChart("workforce") + '</article>' +
      '<article class="mw-panel mw-chart"><h2>Decision Status</h2>' + chartPlaceholderNote() + barChart([35, 52, 46, 61, 75, 68]) + '</article>' +
      '</section>' +
      '<section class="mw-panel"><h2>Risk Table</h2>' + riskTable(project) + '</section>' +
      '<section class="mw-summary-grid">' +
      '<article class="mw-panel"><h2>Recovery Actions</h2>' + recoveryActions() + '</article>' +
      '<article class="mw-panel"><h2>Report Summary</h2>' + reportSummary(project) + '</article>' +
      '</section>'
    );
  }

  function chartPlaceholderNote() {
    return '<p class="mw-muted" style="font-size:11px;margin-top:4px">Illustrative chart &mdash; connect project data to populate.</p>';
  }

  function lineChart(kind) {
    var actual = kind === "workforce" ? "18,150 86,126 154,118 222,92 290,82 358,58" : "18,154 86,136 154,116 222,98 290,79 358,68";
    var planned = kind === "workforce" ? "18,130 86,122 154,104 222,88 290,64 358,52" : "18,146 86,126 154,108 222,87 290,67 358,53";
    return '<div class="mw-line-chart"><svg viewBox="0 0 380 190" role="img" aria-label="Line chart">' +
      '<polyline class="muted-line" points="' + planned + '"></polyline>' +
      '<polyline points="' + actual + '"></polyline>' +
      '<circle cx="290" cy="' + (kind === "workforce" ? "82" : "79") + '" r="5" fill="#28d8ff"></circle>' +
      '</svg><p class="mw-muted">Dotted line is baseline, solid line is current project review trend.</p></div>';
  }

  function barChart(values) {
    return '<div class="mw-bars">' + values.map(function (value) {
      return '<i style="--h:' + Math.max(18, Number(value)) + '%"></i>';
    }).join("") + '</div>';
  }

  function donutChart() {
    return '<div class="mw-donut-wrap"><div class="mw-donut"><svg viewBox="0 0 120 120" role="img" aria-label="Risk distribution donut">' +
      '<circle class="base" cx="60" cy="60" r="43"></circle><circle class="a" cx="60" cy="60" r="43" pathLength="100"></circle><circle class="b" cx="60" cy="60" r="43" pathLength="100"></circle><circle class="c" cx="60" cy="60" r="43" pathLength="100"></circle><circle class="d" cx="60" cy="60" r="43" pathLength="100"></circle>' +
      '</svg></div><ul class="mw-check-list"><li class="mw-muted">Chart data will reflect project analysis results.</li></ul></div>';
  }

  function riskTable(project) {
    var risks = [
      ["Delayed material delivery", "Material Continuity", "Steel delivery sequence is not aligned with next work front.", "High", "Medium", "High", "Adjust material delivery", "Procurement lead", "2026-06-02", "Open"],
      ["Payment approval delay", "Cost Control", "Payment package approval is behind the target date.", "High", "High", "Critical", "Update payment schedule", "Commercial manager", "2026-05-31", "Action Required"],
      ["Workforce shortage", "Schedule", "Concrete crew capacity is below recovery requirement.", "Medium", "Medium", project.risk, "Increase workforce", "Site manager", "2026-06-04", "Open"]
    ];
    return '<div class="mw-table-wrap"><table class="mw-table"><thead><tr><th>Risk title</th><th>Category</th><th>Description</th><th>Impact</th><th>Probability</th><th>Priority</th><th>Recommended action</th><th>Responsible party</th><th>Deadline</th><th>Status</th></tr></thead><tbody>' +
      risks.map(function (risk) {
        return '<tr>' + risk.map(function (cell, index) {
          if (index === 5) {
            return '<td><span class="mw-risk ' + riskClass(cell) + '">' + escapeHtml(cell) + '</span></td>';
          }
          return '<td>' + escapeHtml(cell) + '</td>';
        }).join("") + '</tr>';
      }).join("") + '</tbody></table></div>';
  }

  function recoveryActions() {
    return '<ul class="mw-check-list">' +
      '<li>Increase workforce</li>' +
      '<li>Adjust material delivery</li>' +
      '<li>Revise work sequence</li>' +
      '<li>Resolve pending decisions</li>' +
      '<li>Update payment schedule</li>' +
      '<li>Rebaseline schedule</li>' +
      '<li>Improve document control</li>' +
      '<li>Escalate critical issues</li>' +
      '</ul>';
  }

  function reportSummary(project) {
    return '<div class="mw-list">' +
      '<div class="mw-list-row"><div><strong>Executive project summary</strong><small>' + escapeHtml(project.name) + ' requires focused control on schedule, cost and decision flow.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>Key findings</strong><small>Progress variance and payment status are the main review points.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>Main risks</strong><small>' + escapeHtml(project.criticalRisks) + ' critical risks remain open.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>Recommended actions</strong><small>Rebaseline sequence, close decisions and align delivery dates.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>Required decisions</strong><small>' + escapeHtml(project.openDecisions) + ' decisions should be assigned with owners and deadlines.</small></div></div>' +
      '<div class="mw-list-row"><div><strong>Next steps</strong><small>Export the PDF report and assign recovery actions to the project team.</small></div></div>' +
      '</div>';
  }

  function renderReports() {
    var state = loadState();
    var rows = state.reports.map(function (report) {
      return '<tr><td><strong>' + escapeHtml(report.name) + '</strong></td><td>' + escapeHtml(report.projectName) + '</td><td>' +
        escapeHtml(report.type) + '</td><td>' + formatDate(report.createdDate) + '</td><td><span class="mw-format-badge">' +
        escapeHtml(report.format) + '</span></td><td>' + escapeHtml(report.status) + '</td><td><button class="mw-btn" type="button" data-download-report="' + escapeHtml(report.id) + '">Download</button></td></tr>';
    }).join("");
    return shell("reports",
      pageHead("Reports", "All generated project reports and export packages appear here.", '<a class="mw-btn primary" href="upload.html">Upload Project</a>') +
      '<section class="mw-panel"><div class="mw-table-wrap"><table class="mw-table"><thead><tr><th>Report name</th><th>Project name</th><th>Report type</th><th>Created date</th><th>Format</th><th>Status</th><th>Download</th></tr></thead><tbody>' + rows + '</tbody></table></div></section>'
    );
  }

  function renderBilling() {
    var state = loadState();
    var usage = currentUsage(state);
    var chooseMode = new URLSearchParams(window.location.search).get("choose") === "1" || !state.activePlan;
    var plan = planCatalog[usage.plan] || planCatalog.plus;
    return shell("billing",
      pageHead(chooseMode ? "Choose Your Plan" : "Billing", chooseMode ? "Select Plus or Pro to activate the member workspace." : "Manage subscription status, usage and checkout.", "") +
      '<section class="mw-grid three">' +
      kpiCard(["Current Plan", state.activePlan ? plan.name : "No active plan", state.activePlan ? plan.badge : "Plan required"]) +
      kpiCard(["Monthly limit", usage.limit + " reviews", "Plan capacity"]) +
      kpiCard(["Used analyses", usage.used + "/" + usage.limit, usage.remaining + " remaining"]) +
      kpiCard(["Remaining analyses", usage.remaining, "Available this cycle"]) +
      kpiCard(["Next billing date", formatDate(usage.nextBillingDate), "Subscription cycle"]) +
      kpiCard(["Payment status", state.activePlan ? usage.paymentStatus : "Inactive", "payment provider"]) +
      '</section>' +
      '<section class="mw-plan-grid">' + planCard("plus", state) + planCard("pro", state) + '</section>' +
      '<section class="mw-grid three">' +
      '<article class="mw-panel"><h2>Single Project</h2><p class="mw-muted">Buy one project analysis credit with the payment provider checkout.</p><button class="mw-btn primary" type="button" data-checkout-plan="single">Analyze One Project</button></article>' +
      '<article class="mw-panel"><h2>Customer Portal</h2><p class="mw-muted">Portal placeholder for subscription management and invoice history.</p><button class="mw-btn" type="button" data-portal-placeholder>Manage subscription</button></article>' +
      '<article class="mw-panel"><h2>Webhook Status</h2><p class="mw-muted">Payment webhook listener is connected through the backend.</p><span class="mw-status processing">Waiting for checkout event</span></article>' +
      '</section>' +
      '<section class="mw-panel"><h2>Billing Actions</h2><div class="mw-action-row"><button class="mw-btn primary" data-checkout-plan="pro" type="button">Upgrade to Pro</button><button class="mw-btn" data-checkout-plan="plus" type="button">Start Plus</button><button class="mw-btn danger" data-cancel-placeholder type="button">Cancel subscription placeholder</button></div></section>'
    );
  }

  function planCard(planId, state) {
    var plan = planCatalog[planId];
    var current = state.activePlan && state.currentPlan === planId;
    return '<article class="mw-plan-card ' + (current ? "current" : "") + '">' +
      '<p class="mw-eyebrow">' + (current ? "Current plan" : plan.badge) + '</p>' +
      '<h2>' + escapeHtml(plan.name) + '</h2>' +
      '<p class="mw-muted">' + escapeHtml(plan.description) + '</p>' +
      '<div class="mw-price">' + escapeHtml(plan.price) + '<small>/ month</small></div>' +
      '<ul class="mw-check-list">' + plan.features.map(function (feature) { return '<li>' + escapeHtml(feature) + '</li>'; }).join("") + '</ul>' +
      '<button class="mw-btn primary" type="button" data-checkout-plan="' + planId + '">' + (current ? "Use this plan" : "Select " + plan.name) + '</button>' +
      '</article>';
  }

  async function openCheckout(plan, button) {
    if (!window.DevBareunAPI) {
      throw new Error("Checkout API is not ready.");
    }
    var email = requestCheckoutEmail();
    var origin = window.location.origin;
    var payload = {
      plan: plan,
      plan_code: plan,
      customer_email: email,
      success_url: origin + "/payment-success.html?plan=" + encodeURIComponent(plan),
      cancel_url: origin + "/payment-failed.html?plan=" + encodeURIComponent(plan)
    };
    var originalText = button ? button.textContent : "";
    if (button) {
      button.disabled = true;
      button.textContent = "Creating checkout...";
    }
    try {
      var data = plan === "single"
        ? await window.DevBareunAPI.createOneTimeCheckout(payload)
        : await window.DevBareunAPI.createSubscriptionCheckout(payload);
      var checkoutUrl = data && (data.checkout_url || data.url);
      if (!checkoutUrl) {
        throw new Error("Checkout URL was not returned.");
      }
      localStorage.setItem("devbareun_last_checkout", JSON.stringify({ plan: plan, email: email, data: data }));
      window.location.href = checkoutUrl;
    } catch (error) {
      if (button) {
        button.disabled = false;
        button.textContent = originalText;
      }
      throw error;
    }
  }

  function renderSettings() {
    var state = loadState();
    var profile = state.profile;
    var prefs = state.preferences;
    return shell("settings",
      pageHead("Settings", "Manage profile, preferences, notification options and security placeholders.", "") +
      '<section class="mw-grid two">' +
      '<article class="mw-panel"><h2>Profile</h2><form class="mw-form" data-settings-form><div class="mw-form-grid">' +
      settingsInput("Full name", "fullName", profile.fullName) +
      settingsInput("Email", "email", profile.email, "email") +
      settingsInput("Company name", "company", profile.company) +
      settingsInput("Position", "position", profile.position) +
      settingsInput("Phone placeholder", "phone", profile.phone) +
      settingsInput("Country / city", "city", profile.country + " / " + profile.city) +
      '</div><button class="mw-btn primary" type="submit">Save settings</button></form></article>' +
      '<article class="mw-panel"><h2>Preferences</h2><form class="mw-form" data-preferences-form>' +
      '<label>Dashboard language<select name="dashboardLanguage"><option ' + selected(prefs.dashboardLanguage, "English") + '>English</option><option ' + selected(prefs.dashboardLanguage, "Azerbaijani") + '>Azerbaijani</option></select><p class="mw-muted">Language switching is coming soon. Reports are currently generated in English.</p></label>' +
      '<label>Default report language<select name="reportLanguage"><option ' + selected(prefs.reportLanguage, "English") + '>English</option><option ' + selected(prefs.reportLanguage, "Azerbaijani") + '>Azerbaijani</option></select><p class="mw-muted">Language switching is coming soon. Reports are currently generated in English.</p></label>' +
      '<label>Default export format<select name="exportFormat"><option ' + selected(prefs.exportFormat, "PDF") + '>PDF</option><option ' + selected(prefs.exportFormat, "Excel") + '>Excel</option><option ' + selected(prefs.exportFormat, "PDF + Excel") + '>PDF + Excel</option></select></label>' +
      '<label><input type="checkbox" name="completed" ' + checked(prefs.notifications.completed) + ' /> Project completed</label>' +
      '<label><input type="checkbox" name="limit" ' + checked(prefs.notifications.limit) + ' /> Limit warning</label>' +
      '<label><input type="checkbox" name="billing" ' + checked(prefs.notifications.billing) + ' /> Billing reminder</label>' +
      '<label><input type="checkbox" name="risk" ' + checked(prefs.notifications.risk) + ' /> Critical risk alert</label>' +
      '<button class="mw-btn primary" type="submit">Save preferences</button></form></article>' +
      '</section>' +
      '<section class="mw-grid three">' +
      '<article class="mw-panel"><h2>Change password</h2><p class="mw-muted">Password update placeholder for Supabase Auth or Clerk.</p><button class="mw-btn" type="button" data-placeholder-action>Password placeholder</button></article>' +
      '<article class="mw-panel"><h2>Two-factor authentication</h2><p class="mw-muted">Security setup placeholder for future authentication provider.</p><button class="mw-btn" type="button" data-placeholder-action>Enable placeholder</button></article>' +
      '<article class="mw-panel"><h2>Login history</h2><p class="mw-muted">Recent session history will appear here after backend connection.</p><button class="mw-btn" type="button" data-placeholder-action>View placeholder</button></article>' +
      '</section>'
    );
  }

  function settingsInput(label, name, value, type) {
    return '<label>' + escapeHtml(label) + '<input name="' + escapeHtml(name) + '" type="' + (type || "text") + '" value="' + escapeHtml(value || "") + '" /></label>';
  }

  function selected(current, value) {
    return current === value ? "selected" : "";
  }

  function checked(value) {
    return value ? "checked" : "";
  }

  function showToast(message) {
    var toast = document.querySelector("[data-toast]");
    if (!toast) {
      return;
    }
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(function () {
      toast.classList.remove("show");
    }, 2600);
  }

  function downloadMock(filename, content) {
    showToast("Export ready: " + filename + " - connect backend storage to enable real downloads.");
    return;
  }

  function bindAuth() {
    if (authEventsBound) {
      return;
    }
    authEventsBound = true;
    document.addEventListener("submit", async function (event) {
      var form = event.target.closest("[data-auth-form]");
      if (!form) {
        return;
      }
      event.preventDefault();
      var data = new FormData(form);
      var plan = data.get("plan") || "plus";
      var status = form.querySelector("[data-auth-status]");
      if (plan === "none") {
        var inactive = setCurrentPlan("plus", false);
        inactive.activePlan = false;
        saveState(inactive);
        redirect("billing.html?choose=1");
        return;
      }
      try {
        var email = String(data.get("email") || "").trim();
        var password = String(data.get("password") || "");
        var mode = form.getAttribute("data-auth-form");
        if (status) status.textContent = mode === "register" ? "Creating workspace..." : "Signing in...";
        if (window.DevBareunAPI && window.DevBareunAPI.loginUser) {
          if (mode === "register") {
            await window.DevBareunAPI.registerUser({
              email: email,
              password: password,
              plan: plan,
              company_name: data.get("company") || ""
            });
          } else {
            await window.DevBareunAPI.loginUser({ email: email, password: password, plan: plan });
          }
          setSession({
            loggedIn: true,
            activePlan: true,
            plan: plan,
            email: email,
            access_token: window.DevBareunAPI.getAuthToken && window.DevBareunAPI.getAuthToken()
          });
          if (status) status.textContent = "Workspace ready. Opening dashboard...";
          redirect("dashboard.html");
          return;
        }
        if (!devMemberDemoEnabled()) {
          throw new Error("Unified API client is not loaded.");
        }
        setCurrentPlan(plan, true);
        redirect("dashboard.html");
      } catch (error) {
        if (devMemberDemoEnabled()) {
          setCurrentPlan(plan, true);
          redirect("dashboard.html");
          return;
        }
        if (status) status.textContent = error.message || "Login failed.";
      }
    });
    document.addEventListener("click", function (event) {
      var button = event.target.closest("[data-demo-login]");
      if (!button) {
        return;
      }
      var plan = button.getAttribute("data-demo-login");
      if (plan === "none") {
        var state = setCurrentPlan("plus", false);
        state.activePlan = false;
        saveState(state);
        redirect("billing.html?choose=1");
        return;
      }
      setCurrentPlan(plan, true);
      redirect("dashboard.html");
    });
  }

  function bindWorkspace() {
    if (!workspaceEventsBound) {
      workspaceEventsBound = true;
      document.addEventListener("click", async function (event) {
      var notifyButton = event.target.closest("[data-notification-toggle]");
      var accountButton = event.target.closest("[data-account-toggle]");
      if (notifyButton) {
        toggleDropdown("[data-notification-menu]");
        closeDropdown("[data-account-menu]");
      }
      if (accountButton) {
        toggleDropdown("[data-account-menu]");
        closeDropdown("[data-notification-menu]");
      }
      var logout = event.target.closest("[data-logout]");
      if (logout) {
        clearSession();
        redirect("login.html");
      }
      var checkoutPlan = event.target.closest("[data-checkout-plan]");
      if (checkoutPlan) {
        event.preventDefault();
        try {
          await openCheckout(checkoutPlan.getAttribute("data-checkout-plan") || "plus", checkoutPlan);
        } catch (error) {
          showToast(error.message || "Checkout could not be opened.");
        }
        return;
      }
      var setPlan = event.target.closest("[data-set-plan]");
      if (setPlan) {
        setCurrentPlan(setPlan.getAttribute("data-set-plan"), true);
        showToast("Plan updated for demo workspace.");
        window.setTimeout(function () { window.location.reload(); }, 500);
      }
      var archive = event.target.closest("[data-archive-project]");
      if (archive) {
        mutateProject(archive.getAttribute("data-archive-project"), function (project) { project.status = "Archived"; });
        renderCurrentPage();
      }
      var del = event.target.closest("[data-delete-project]");
      if (del) {
        deleteProject(del.getAttribute("data-delete-project"));
        renderCurrentPage();
      }
      var download = event.target.closest("[data-download]");
      if (download) {
        var format = download.getAttribute("data-download");
        var projectId = download.getAttribute("data-project-id");
        var project = loadState().projects.find(function (item) { return item.id === projectId; });
        var name = project ? project.name : "Project";
        downloadMock(slug(name) + "-" + format + "-report.txt", "DevBareun " + format.toUpperCase() + " export placeholder for " + name + ".");
      }
      var reportDownload = event.target.closest("[data-download-report]");
      if (reportDownload) {
        var report = loadState().reports.find(function (item) { return item.id === reportDownload.getAttribute("data-download-report"); });
        downloadMock(slug(report ? report.name : "report") + ".txt", "DevBareun report download placeholder.");
      }
      if (event.target.closest("[data-checkout-placeholder]")) {
        showToast("Payment provider checkout placeholder is ready for backend connection.");
      }
      if (event.target.closest("[data-portal-placeholder]")) {
        showToast("Customer portal placeholder is ready for backend connection.");
      }
      if (event.target.closest("[data-cancel-placeholder]")) {
        showToast("Cancel subscription placeholder only. No billing action was made.");
      }
      if (event.target.closest("[data-placeholder-action]")) {
        showToast("Placeholder action. Connect backend provider later.");
      }
      });

      document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeDropdown("[data-notification-menu]");
        closeDropdown("[data-account-menu]");
      }
      if (event.key === "Enter" && event.target.matches("[data-global-search]")) {
        var query = event.target.value.trim();
        if (query) {
          sessionStorage.setItem("devbareun_project_search", query);
          redirect("projects.html");
        }
      }
      });

      document.addEventListener("input", function (event) {
      if (event.target.closest("[data-project-filters]")) {
        applyProjectFilters();
      }
      if (event.target.matches("[data-module-select]")) {
        updateModuleHelper(event.target.value);
      }
      });

      document.addEventListener("change", function (event) {
      if (event.target.matches("[data-module-select]")) {
        updateModuleHelper(event.target.value);
      }
      });

      document.addEventListener("submit", function (event) {
      var upload = event.target.closest("[data-upload-form]");
      var settings = event.target.closest("[data-settings-form]");
      var prefs = event.target.closest("[data-preferences-form]");
      if (upload) {
        event.preventDefault();
        startProjectReview(upload);
      }
      if (settings) {
        event.preventDefault();
        saveSettings(settings);
      }
      if (prefs) {
        event.preventDefault();
        savePreferences(prefs);
      }
      });

      bindUploadArea();
      updateModuleHelper();
    }

    initSearchFromSession();
  }

  function updateModuleHelper(value) {
    var helper = document.querySelector("[data-module-helper]");
    var select = document.querySelector("[data-module-select]");
    if (!helper || !select) {
      return;
    }
    helper.innerHTML = moduleHelper(value || select.value || "Schedule Recovery");
  }

  function toggleDropdown(selector) {
    var menu = document.querySelector(selector);
    if (menu) {
      menu.classList.toggle("open");
    }
  }

  function closeDropdown(selector) {
    var menu = document.querySelector(selector);
    if (menu) {
      menu.classList.remove("open");
    }
  }

  function mutateProject(id, updater) {
    var state = loadState();
    var project = state.projects.find(function (item) { return item.id === id; });
    if (project) {
      updater(project);
      project.lastUpdated = todayIso();
      saveState(state);
      showToast("Project updated.");
    }
  }

  function deleteProject(id) {
    var state = loadState();
    state.projects = state.projects.filter(function (project) { return project.id !== id; });
    saveState(state);
    showToast("Project deleted from demo workspace.");
  }

  function applyProjectFilters(viewMode) {
    var state = loadState();
    var form = document.querySelector("[data-project-filters]");
    var target = document.querySelector("[data-project-results]");
    if (!form || !target) {
      return;
    }
    var data = {};
    form.querySelectorAll("[name]").forEach(function (field) {
      data[field.name] = String(field.value || "").toLowerCase();
    });
    var projects = state.projects.filter(function (project) {
      return (!data.search || project.name.toLowerCase().indexOf(data.search) !== -1) &&
        (!data.status || project.status.toLowerCase() === data.status) &&
        (!data.risk || project.risk.toLowerCase() === data.risk) &&
        (!data.type || project.type.toLowerCase() === data.type) &&
        (!data.module || project.module.toLowerCase() === data.module);
    });
    var mode = viewMode || target.getAttribute("data-mode") || "table";
    target.setAttribute("data-mode", mode);
    target.innerHTML = mode === "cards" ? projectsCards(projects) : projectsTable(projects);
  }

  function initSearchFromSession() {
    var pending = sessionStorage.getItem("devbareun_project_search");
    var field = document.querySelector('[data-project-filters] [name="search"]');
    if (pending && field) {
      field.value = pending;
      sessionStorage.removeItem("devbareun_project_search");
      applyProjectFilters();
    }
    document.querySelectorAll("[data-view-mode]").forEach(function (button) {
      button.addEventListener("click", function () {
        applyProjectFilters(button.getAttribute("data-view-mode"));
      });
    });
  }

  function bindUploadArea() {
    document.addEventListener("dragover", function (event) {
      var area = event.target.closest && event.target.closest("[data-upload-drop]");
      if (!area) {
        return;
      }
      event.preventDefault();
      area.classList.add("is-drag");
    });
    document.addEventListener("dragleave", function (event) {
      var area = event.target.closest && event.target.closest("[data-upload-drop]");
      if (area) {
        area.classList.remove("is-drag");
      }
    });
    document.addEventListener("drop", function (event) {
      var area = event.target.closest && event.target.closest("[data-upload-drop]");
      if (!area) {
        return;
      }
      event.preventDefault();
      area.classList.remove("is-drag");
      renderFiles(event.dataTransfer.files);
    });
    document.addEventListener("change", function (event) {
      if (event.target.matches("[data-file-input]")) {
        renderFiles(event.target.files);
      }
    });
    document.addEventListener("click", function (event) {
      var remove = event.target.closest("[data-remove-file]");
      if (!remove) {
        return;
      }
      remove.closest(".mw-file").remove();
      var status = document.querySelector("[data-upload-status]");
      if (status) {
        status.textContent = document.querySelectorAll(".mw-file").length ? "Files uploaded successfully." : "Supported formats: PDF, XLS, XLSX, DOC, DOCX, CSV, Primavera schedule export placeholder and MS Project export placeholder.";
      }
    });
  }

  function renderFiles(fileList) {
    var target = document.querySelector("[data-file-list]");
    var status = document.querySelector("[data-upload-status]");
    if (!target) {
      return;
    }
    var files = Array.prototype.slice.call(fileList || []);
    target.innerHTML = files.map(function (file, index) {
      return '<div class="mw-file"><div><strong>' + escapeHtml(file.name) + '</strong><small class="mw-muted">' + Math.max(1, Math.round(file.size / 1024)) + ' KB</small></div><button class="mw-btn" type="button" data-remove-file="' + index + '">Remove</button></div>';
    }).join("");
    if (status && files.length) {
      status.textContent = "Files uploaded successfully.";
    }
  }

  function startProjectReview(form) {
    var state = loadState();
    var usage = currentUsage(state);
    if (usage.remaining <= 0) {
      showToast("Your monthly limit is used. Upgrade to Pro or wait for next billing cycle.");
      return;
    }
    var data = new FormData(form);
    var name = String(data.get("projectName") || "").trim();
    if (!name) {
      showToast("Project name is required.");
      return;
    }
    var selectedModule = data.get("module") || "Schedule Recovery";
    var moduleInfo = analysisModules[selectedModule] || analysisModules["Schedule Recovery"];
    var project = {
      id: slug(name) + "-" + Date.now(),
      name: name,
      location: data.get("location") || "Not set",
      client: data.get("client") || "Not set",
      type: data.get("type") || "Commercial",
      phase: data.get("phase") || "Construction",
      uploadedDate: todayIso(),
      reviewDate: todayIso(),
      module: selectedModule,
      status: "Mapping",
      risk: "Medium",
      progressScore: 58,
      plannedProgress: 54,
      actualProgress: 47,
      delayDays: 6,
      costVariance: "+$42K",
      paymentStatus: "On watch",
      workforceGap: "7%",
      materialContinuity: "Medium",
      openDecisions: 3,
      criticalRisks: 1,
      lastUpdated: todayIso()
    };
    state.projects.unshift(project);
    state.usage[usage.plan].used = Math.min(usage.limit, usage.used + 1);
    state.notifications.unshift({
      id: "n" + Date.now(),
      title: "Mapping started",
      body: project.name + " files are being mapped.",
      time: "Now"
    });
    saveState(state);
    showToast("Files uploaded. Mapping preview is being prepared.");
    window.setTimeout(function () {
      var mappedState = loadState();
      var mapped = mappedState.projects.find(function (item) { return item.id === project.id; });
      if (mapped) {
        mapped.status = "Processing";
        mapped.lastUpdated = todayIso();
        mappedState.notifications.unshift({
          id: "n" + Date.now(),
          title: "Dashboard preparation started",
          body: project.name + " mapping is confirmed and dashboards are being prepared.",
          time: "Now"
        });
        saveState(mappedState);
      }
    }, 900);
    window.setTimeout(function () {
      var nextState = loadState();
      var saved = nextState.projects.find(function (item) { return item.id === project.id; });
      if (saved) {
        saved.status = "Ready";
        saved.progressScore = 74;
        saved.lastUpdated = todayIso();
        nextState.reports.unshift({
          id: "rpt-" + project.id,
          name: project.name + " " + moduleInfo.reportType,
          projectId: project.id,
          projectName: project.name,
          type: moduleInfo.reportType,
          createdDate: todayIso(),
          format: "PDF + Excel",
          status: "Ready"
        });
        nextState.notifications.unshift({
          id: "n" + Date.now(),
          title: "Dashboard ready",
          body: project.name + " dashboard and report are ready.",
          time: "Now"
        });
        saveState(nextState);
      }
    }, 1400);
    window.setTimeout(function () {
      redirect("projects.html");
    }, 800);
  }

  function saveSettings(form) {
    var state = loadState();
    var data = new FormData(form);
    state.profile.fullName = data.get("fullName") || state.profile.fullName;
    state.profile.email = data.get("email") || state.profile.email;
    state.profile.company = data.get("company") || state.profile.company;
    state.profile.position = data.get("position") || state.profile.position;
    state.profile.phone = data.get("phone") || "";
    var location = String(data.get("city") || "").split("/");
    state.profile.country = (location[0] || state.profile.country).trim();
    state.profile.city = (location[1] || state.profile.city).trim();
    saveState(state);
    showToast("Profile settings saved.");
  }

  function savePreferences(form) {
    var state = loadState();
    var data = new FormData(form);
    state.preferences.dashboardLanguage = data.get("dashboardLanguage") || "English";
    state.preferences.reportLanguage = data.get("reportLanguage") || "English";
    state.preferences.exportFormat = data.get("exportFormat") || "PDF + Excel";
    state.preferences.notifications = {
      completed: data.has("completed"),
      limit: data.has("limit"),
      billing: data.has("billing"),
      risk: data.has("risk")
    };
    saveState(state);
    showToast("Preferences saved. Language settings will apply when this feature is activated.");
  }

  function todayIso() {
    return new Date().toISOString().slice(0, 10);
  }

  function renderCurrentPage() {
    var page = pageFromLocation();
    var app = getApp();
    var state = loadState();
    if (!app) {
      return;
    }
    if (!ensureAccess(page, state)) {
      return;
    }
    if (page === "login" || page === "register") {
      app.innerHTML = authPage(page);
      bindAuth();
      return;
    }
    if (page === "dashboard") {
      app.innerHTML = renderOverview();
    } else if (page === "upload") {
      app.innerHTML = renderUpload();
    } else if (page === "projects") {
      app.innerHTML = renderProjects();
    } else if (page === "project-detail") {
      app.innerHTML = renderProjectDetail();
    } else if (page === "reports") {
      app.innerHTML = renderReports();
    } else if (page === "billing") {
      app.innerHTML = renderBilling();
    } else if (page === "settings") {
      app.innerHTML = renderSettings();
    } else {
      app.innerHTML = renderOverview();
    }
    bindWorkspace();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var state = loadState();
    saveState(state);
    renderCurrentPage();
  });
})();
