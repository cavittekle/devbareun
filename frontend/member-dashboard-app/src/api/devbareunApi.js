function localApiBase() {
  const host = window.location.hostname === "localhost" ? "127.0.0.1" : window.location.hostname;
  return `${window.location.protocol === "https:" ? "https:" : "http:"}//${host || "127.0.0.1"}:8000`;
}

export function getApiBaseUrl() {
  return (
    import.meta.env.VITE_DEVBAREUN_API_URL ||
    import.meta.env.VITE_API_BASE_URL ||
    window.DEVBAREUN_API_BASE_URL ||
    (["localhost", "127.0.0.1"].includes(window.location.hostname) ? localApiBase() : "")
  ).replace(/\/$/, "");
}

export function getAuthToken() {
  return (
    localStorage.getItem("devbareun_access_token") ||
    localStorage.getItem("devbareun_auth_token") ||
    sessionStorage.getItem("devbareun_access_token") ||
    ""
  );
}

export async function apiRequest(path, options = {}) {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...options,
      headers
    });
  } catch (error) {
    const offline = new Error("Backend is not reachable. Demo dashboard data is shown.");
    offline.code = "backend_offline";
    offline.cause = error;
    throw offline;
  }

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }

  if (!response.ok) {
    const error = new Error(data?.message || data?.detail?.message || data?.detail || `Request failed with ${response.status}`);
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return data;
}

export function getPortfolioDashboard() {
  return apiRequest("/api/dashboard/portfolio");
}

export function getExecutiveDashboard(projectId) {
  return apiRequest(`/api/dashboard/executive/${encodeURIComponent(projectId)}`);
}

export async function getProjects() {
  const data = await apiRequest("/api/projects/list");
  return data.projects || [];
}
