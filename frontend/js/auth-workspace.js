/*
DevBareun Auth + Protected Workspace UI
v1.3.10
Connects landing access, authentication and protected workspace pages.
*/
(function () {
  "use strict";

  const LOCAL_DEFAULT_API = `http://${location.hostname === "localhost" ? "127.0.0.1" : location.hostname}:8000`;
  const API_BASE =
    localStorage.getItem("devbareun_api_base") ||
    window.DEVBAREUN_API_URL ||
    ((location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")
      ? LOCAL_DEFAULT_API
      : "https://devbareun-production.up.railway.app");
  const SESSION_KEY = "devbareun_session";
  const LEGACY_SESSION_KEY = "devbareun_supabase_session";
  const LOCAL_PREVIEW = ["localhost", "127.0.0.1"].includes(location.hostname) || location.protocol === "file:";
  const PANEL_ROUTES = new Set([
    "/dashboard.html",
    "/projects.html",
    "/reports.html",
    "/billing.html",
    "/profile.html",
    "/upload.html",
    "/analysis-view.html",
    "/checkout.html",
  ]);

  function $(selector, root = document) {
    return root.querySelector(selector);
  }

  function $all(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function esc(value) {
    return String(value ?? "").replace(/[&<>\"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function readStoredSession(key) {
    try {
      return JSON.parse(localStorage.getItem(key) || "null");
    } catch {
      return null;
    }
  }

  function normalizeSession(session) {
    if (!session) return null;
    if (!session.access_token && session.auth?.access_token) {
      return {
        ...session.auth,
        user: session.user || session.auth.user,
      };
    }
    return session;
  }

  function getSession() {
    return normalizeSession(readStoredSession(SESSION_KEY) || readStoredSession(LEGACY_SESSION_KEY));
  }

  function setSession(session) {
    const normalized = normalizeSession(session);
    localStorage.setItem(SESSION_KEY, JSON.stringify(normalized));
    localStorage.setItem(LEGACY_SESSION_KEY, JSON.stringify(normalized));
    window.DevBareunAPI?.saveSession?.(normalized);
    renderAuthState();
  }

  function clearSession() {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(LEGACY_SESSION_KEY);
    window.DevBareunAPI?.clearAuthToken?.();
    renderAuthState();
  }

  async function api(path, options = {}) {
    if (window.DevBareunAPI?.apiRequest) {
      return window.DevBareunAPI.apiRequest(path, options);
    }
    const session = getSession();
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
    if (session?.access_token) {
      headers.Authorization = `Bearer ${session.access_token}`;
    }
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "object" ? JSON.stringify(data.detail) : data.detail;
      throw new Error(detail || data.message || "Request failed");
    }
    return data;
  }

  async function refreshEntitlements() {
    const session = getSession();
    if (!session?.access_token) return null;
    try {
      const data = await api("/api/workspace/entitlements");
      const next = {
        ...session,
        entitlements: data,
        user: {
          ...(session.user || {}),
          ...(data.user || {}),
          plan: data.plan || session.user?.plan,
          credits_remaining: data.credits_remaining ?? session.user?.credits_remaining,
        },
      };
      setSession(next);
      return data;
    } catch (err) {
      console.warn("Workspace entitlement refresh failed", err);
      return null;
    }
  }

  function planLabel(plan) {
    const labels = {
      single: "Single Project",
      plus: "Plus",
      pro: "Pro",
      free: "Free",
      guest: "Guest",
    };
    return labels[plan] || plan || "Guest";
  }

  function renderAuthState() {
    const session = getSession();
    const loggedIn = Boolean(session?.access_token && session?.user);
    const email = loggedIn ? String(session.user.email || "Workspace") : "Guest";

    document.documentElement.classList.toggle("is-authenticated", loggedIn);
    document.documentElement.classList.toggle("is-guest", !loggedIn);

    $all("[data-auth-email]").forEach((element) => {
      if ("value" in element) element.value = loggedIn ? email : "";
      else element.textContent = email;
    });
    $all("[data-auth-initial]").forEach((element) => {
      element.textContent = loggedIn ? email.slice(0, 1).toUpperCase() : "D";
    });
    $all("[data-auth-plan]").forEach((element) => {
      element.textContent = loggedIn ? planLabel(session.user.plan) : "Guest";
    });
    $all("[data-auth-credits]").forEach((element) => {
      element.textContent = loggedIn ? String(session.user.credits_remaining ?? 0) : "-";
    });

    const usage = session?.entitlements?.usage || {};
    $all("[data-project-count]").forEach((element) => {
      element.textContent = loggedIn ? String(usage.projects ?? 0) : "-";
    });
    $all("[data-analysis-count]").forEach((element) => {
      element.textContent = loggedIn ? String(usage.analyses ?? 0) : "-";
    });
    $all("[data-report-count]").forEach((element) => {
      element.textContent = loggedIn ? String(usage.reports ?? 0) : "-";
    });

    $all("[data-show-auth]").forEach((element) => {
      element.hidden = !loggedIn;
    });
    $all("[data-show-guest]").forEach((element) => {
      element.hidden = loggedIn;
    });

    const userMenu = $("#userWorkspaceMenu");
    if (userMenu && loggedIn) {
      userMenu.innerHTML = `
        <div class="workspace-user-card">
          <span class="workspace-avatar">${esc(email.slice(0, 1).toUpperCase())}</span>
          <div>
            <strong>${esc(email)}</strong>
            <small>${esc(planLabel(session.user.plan))} &middot; ${esc(session.user.credits_remaining ?? 0)} credits</small>
          </div>
          <button class="btn btn-ghost btn-small" data-logout>Logout</button>
        </div>
      `;
    }
  }

  function protectPage() {
    if (document.body?.dataset?.protected !== "true") return;
    const params = new URLSearchParams(location.search);
    const guestSingleCheckout =
      /\/checkout\.html$/.test(location.pathname) &&
      params.get("plan") === "single" &&
      params.get("mode") === "guest";
    if (guestSingleCheckout) return;
    if (!getSession()?.access_token) {
      const target = `${location.pathname}${location.search}${location.hash}`;
      location.replace(`/login.html?next=${encodeURIComponent(target)}`);
    }
  }

  function selectedWorkspacePlan() {
    const params = new URLSearchParams(location.search);
    const selected = params.get("plan") || localStorage.getItem("devbareun_selected_plan") || "plus";
    return selected === "pro" ? "pro" : "plus";
  }

  function safePanelDestination(defaultPath = "/dashboard.html") {
    const raw = new URLSearchParams(location.search).get("next");
    if (!raw) return defaultPath;
    try {
      const url = new URL(raw, location.origin);
      if (url.origin !== location.origin || !PANEL_ROUTES.has(url.pathname)) return defaultPath;
      return `${url.pathname}${url.search}${url.hash}`;
    } catch {
      return defaultPath;
    }
  }

  function destinationLabel(path) {
    if (path.startsWith("/billing.html")) return "Plan and billing";
    if (path.startsWith("/projects.html")) return "Projects";
    if (path.startsWith("/reports.html")) return "Report archive";
    if (path.startsWith("/upload.html")) return "Project upload";
    return "Project control dashboard";
  }

  function preselectPlanFromUrl() {
    const selectedPlan = selectedWorkspacePlan();
    $all("select[name=plan]").forEach((select) => {
      if (Array.from(select.options).some((option) => option.value === selectedPlan)) {
        select.value = selectedPlan;
      }
    });
  }

  function renderAuthPageContext() {
    const destination = safePanelDestination();
    const plan = selectedWorkspacePlan();
    $all("[data-auth-destination]").forEach((element) => {
      element.textContent = destinationLabel(destination);
    });
    $all("[data-selected-plan-label]").forEach((element) => {
      element.textContent = planLabel(plan);
    });
    $all("[data-auth-switch-link]").forEach((link) => {
      const url = new URL(link.getAttribute("href"), location.origin);
      url.searchParams.set("plan", plan);
      url.searchParams.set("next", destination);
      link.setAttribute("href", `${url.pathname}${url.search}`);
    });
    if (($("#loginForm") || $("#registerForm")) && getSession()?.access_token) {
      location.replace(destination);
    }
  }

  function buildSupabaseSession(data, plan) {
    const auth = data?.auth || data?.session || {};
    if (!auth.access_token) return null;
    return {
      ...auth,
      user: {
        ...(auth.user || {}),
        ...(data.user || {}),
        plan: data.user?.plan || auth.user?.plan || plan,
      },
    };
  }

  async function createWorkspaceSession(mode, email, password, plan) {
    if (window.DevBareunAPI?.loginUser && mode === "login") {
      try {
        await window.DevBareunAPI.loginUser({ email, password, plan });
        return window.DevBareunAPI.readSession?.() || getSession();
      } catch (err) {
        if (!LOCAL_PREVIEW || !/Supabase is not configured/i.test(String(err.message))) throw err;
      }
    }
    if (window.DevBareunAPI?.registerUser && mode === "register") {
      try {
        await window.DevBareunAPI.registerUser({ email, password, plan });
        return window.DevBareunAPI.readSession?.() || getSession();
      } catch (err) {
        if (!LOCAL_PREVIEW || !/Supabase is not configured/i.test(String(err.message))) throw err;
      }
    }
    try {
      const data = await api(`/api/auth/supabase/${mode}`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const session = buildSupabaseSession(data, plan);
      if (session) return session;
      throw new Error(mode === "register"
        ? "Check your email confirmation, then log in to open the workspace."
        : "Login did not return a workspace session.");
    } catch (err) {
      if (!LOCAL_PREVIEW || !/Supabase is not configured/i.test(String(err.message))) throw err;
      return api("/api/auth/pilot-login", {
        method: "POST",
        body: JSON.stringify({ email, password, plan }),
      });
    }
  }

  function setSubmitting(form, submitting) {
    const button = form.querySelector("button[type=submit]");
    form.classList.toggle("is-submitting", submitting);
    if (button) button.disabled = submitting;
  }

  function bindLoginForm() {
    const form = $("#loginForm");
    if (!form) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = form.querySelector("[name=email]")?.value?.trim();
      const password = form.querySelector("[name=password]")?.value || "";
      const plan = form.querySelector("[name=plan]")?.value === "pro" ? "pro" : "plus";
      const status = $("#authStatus");
      localStorage.setItem("devbareun_selected_plan", plan);
      try {
        setSubmitting(form, true);
        if (status) status.textContent = "Signing in...";
        const session = await createWorkspaceSession("login", email, password, plan);
        setSession(session);
        if (status) status.textContent = "Login successful. Opening workspace...";
        location.href = safePanelDestination();
      } catch (err) {
        if (status) status.textContent = err.message;
        setSubmitting(form, false);
      }
    });
  }

  function bindRegisterForm() {
    const form = $("#registerForm");
    if (!form) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = form.querySelector("[name=email]")?.value?.trim();
      const password = form.querySelector("[name=password]")?.value || "";
      const plan = form.querySelector("[name=plan]")?.value === "pro" ? "pro" : "plus";
      const status = $("#authStatus");
      localStorage.setItem("devbareun_selected_plan", plan);
      try {
        setSubmitting(form, true);
        if (status) status.textContent = "Creating workspace...";
        const session = await createWorkspaceSession("register", email, password, plan);
        setSession(session);
        if (status) status.textContent = "Workspace ready. Opening panel...";
        location.href = safePanelDestination();
      } catch (err) {
        if (status) status.textContent = err.message;
        setSubmitting(form, false);
      }
    });
  }

  function bindLogout() {
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-logout]");
      if (!button) return;
      event.preventDefault();
      clearSession();
      location.href = "/";
    });
  }

  function injectHeaderAuthControls() {
    const headerActions = document.querySelector(".header-actions, .nav-actions, .site-actions");
    if (!headerActions || document.getElementById("workspaceAuthControls")) return;

    const wrap = document.createElement("div");
    wrap.id = "workspaceAuthControls";
    wrap.className = "workspace-auth-controls";
    wrap.innerHTML = `
      <a class="btn btn-ghost" href="/login.html?next=%2Fdashboard.html" data-show-guest>Login</a>
      <a class="btn btn-primary" href="/register.html?next=%2Fbilling.html" data-show-guest>Register</a>
      <a class="btn btn-ghost" href="/dashboard.html" data-show-auth>Dashboard</a>
      <div id="userWorkspaceMenu" data-show-auth></div>
    `;
    headerActions.appendChild(wrap);
  }

  document.addEventListener("DOMContentLoaded", () => {
    injectHeaderAuthControls();
    preselectPlanFromUrl();
    renderAuthPageContext();
    bindLoginForm();
    bindRegisterForm();
    bindLogout();
    renderAuthState();
    protectPage();
    refreshEntitlements();
  });

  window.DevBareunAuth = {
    getSession,
    setSession,
    clearSession,
    api,
    refreshEntitlements,
    renderAuthState,
    safePanelDestination,
  };
})();
