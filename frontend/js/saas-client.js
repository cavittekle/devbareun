
(function () {
  const LOCAL_DEFAULT_API = `http://${location.hostname === "localhost" ? "127.0.0.1" : location.hostname}:8000`;
  const DEFAULT_API = (location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")
    ? LOCAL_DEFAULT_API
    : "https://devbareun-production.up.railway.app";
  const API = window.DEVBAREUN_API_BASE || localStorage.getItem('devbareun_api_base') || DEFAULT_API;

  function readBearer() {
    try {
      const session = JSON.parse(localStorage.getItem("devbareun_session") || "null");
      if (session?.access_token) return session.access_token;
    } catch (_) {}
    try {
      const supa = JSON.parse(localStorage.getItem("devbareun_supabase_session") || "null");
      return supa?.access_token || supa?.auth?.access_token || null;
    } catch (_) {}
    return null;
  }

  async function request(path, options = {}) {
    const token = readBearer();
    const response = await fetch(`${API}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {})
      },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.message || `Request failed: ${response.status}`);
    return data;
  }

  window.DevBareunSaaS = {
    apiBase: API,
    startGuest: (payload) => request('/api/guest/start', { method: 'POST', body: JSON.stringify(payload) }),
    createProject: (payload) => request('/api/projects/create', { method: 'POST', body: JSON.stringify(payload) }),
    listProjects: () => request('/api/projects/list'),
    getProject: (projectId) => request(`/api/projects/${encodeURIComponent(projectId)}`),
    createOneTimeCheckout: (payload) => request('/api/payments/create-one-time-checkout', { method: 'POST', body: JSON.stringify(payload) }),
    createSubscriptionCheckout: (payload) => request('/api/payments/create-subscription-checkout', { method: 'POST', body: JSON.stringify(payload) }),
    creditStatus: (projectId) => request(`/api/credits/status${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`),
    adminOverview: () => request('/api/admin/overview'),
  };
})();
