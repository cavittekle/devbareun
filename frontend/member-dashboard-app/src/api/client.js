const PRODUCTION_API = "https://devbareun-production.up.railway.app";

export function resolveApiBase() {
  const explicit = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL;
  if (explicit) return explicit.replace(/\/$/, "");
  if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }
  return PRODUCTION_API;
}

function createIdempotencyKey() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `analysis-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export class ApiError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = "ApiError";
    Object.assign(this, details);
  }
}

async function parseResponse(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

function readCookie(name) {
  return document.cookie
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => item.split("="))
    .find(([key]) => decodeURIComponent(key) === name)?.slice(1).join("=") || "";
}

async function ensureCsrfTokenHeader(headers, method) {
  const unsafeMethod = !["GET", "HEAD", "OPTIONS", "TRACE"].includes(String(method || "GET").toUpperCase());
  if (!unsafeMethod || headers.has("X-CSRF-Token")) return;
  let token = readCookie("devbareun_csrf");
  if (!token) {
    try {
      const response = await fetch(`${resolveApiBase()}/api/auth/csrf`, { credentials: "include" });
      const payload = await parseResponse(response);
      token = readCookie("devbareun_csrf") || payload?.csrf_token || "";
    } catch {
      token = "";
    }
  }
  if (token) headers.set("X-CSRF-Token", decodeURIComponent(token));
}

function normalizeError(status, payload, fallback, path) {
  const detail = payload?.detail || payload?.error || payload;
  const message =
    payload?.message ||
    (typeof detail === "string" ? detail : null) ||
    fallback ||
    "Request failed";
  const code =
    payload?.code ||
    (typeof payload?.error === "string" ? payload.error : null) ||
    (typeof detail?.error === "string" ? detail.error : null) ||
    (status === 401 ? "unauthorized" : status === 403 ? "forbidden" : "request_failed");
  return new ApiError(message, { status, code, detail, path });
}

export async function apiRequest(path, options = {}) {
  const url = path.startsWith("http") ? path : `${resolveApiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = new Headers(options.headers || {});
  const body = options.body;
  if (body && !(body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  await ensureCsrfTokenHeader(headers, options.method || "GET");

  let response;
  try {
    response = await fetch(url, {
      ...options,
      credentials: "include",
      headers
    });
  } catch (error) {
    throw new ApiError("Backend is offline or unreachable.", {
      status: 0,
      code: "backend_offline",
      cause: error,
      path
    });
  }

  if (options.rawResponse) return response;
  const payload = await parseResponse(response);
  if (!response.ok) {
    throw normalizeError(response.status, payload, response.statusText, path);
  }
  return payload;
}

export function uploadBinaryToSignedUrl(url, file, onProgress) {
  return new Promise((resolve, reject) => {
    if (!url) {
      resolve({ skipped: true });
      return;
    }
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && typeof onProgress === "function") {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve({ status: xhr.status });
        return;
      }
      reject(new ApiError("File upload failed.", {
        status: xhr.status,
        code: "upload_failed",
        detail: xhr.responseText
      }));
    };
    xhr.onerror = () => reject(new ApiError("File upload network error.", {
      status: 0,
      code: "upload_network_error"
    }));
    xhr.send(file);
  });
}

export const workspaceApi = {
  me: () => apiRequest("/api/auth/me"),
  login: (payload) =>
    apiRequest("/api/auth/supabase/login", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  pilotLogin: (payload) =>
    apiRequest("/api/auth/pilot-login", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  register: (payload) =>
    apiRequest("/api/auth/supabase/register", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  logout: () =>
    apiRequest("/api/auth/logout", {
      method: "POST"
    }),
  health: () => apiRequest("/api/saas/health"),
  privacyPolicy: () => apiRequest("/api/privacy/policy"),
  privacyRequests: () => apiRequest("/api/privacy/requests"),
  requestDataExport: (payload = {}) =>
    apiRequest("/api/privacy/export-requests", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  requestDataErasure: (payload) =>
    apiRequest("/api/privacy/erasure-requests", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  cancelPrivacyRequest: (requestId, payload = {}) =>
    apiRequest(`/api/privacy/requests/${encodeURIComponent(requestId)}/cancel`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  companyWorkspace: () => apiRequest("/api/company/workspace"),
  createCompanyWorkspace: (payload) =>
    apiRequest("/api/company/workspace", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  inviteCompanyMember: (payload) =>
    apiRequest("/api/company/invitations", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  acceptCompanyInvitation: (payload) =>
    apiRequest("/api/company/invitations/accept", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  revokeCompanyInvitation: (invitationId) =>
    apiRequest(`/api/company/invitations/${encodeURIComponent(invitationId)}/revoke`, {
      method: "POST"
    }),
  updateCompanyMember: (membershipId, payload) =>
    apiRequest(`/api/company/members/${encodeURIComponent(membershipId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  // Explicit project-access list contains owned projects plus active shares.
  projectAccessProjects: () => apiRequest("/api/project-access/projects"),
  projects: () => apiRequest("/api/project-access/projects"),
  projectAccessMembers: (projectId) => apiRequest(`/api/project-access/${encodeURIComponent(projectId)}/members`),
  projectActivity: (projectId, limit = 80) => apiRequest(`/api/project-activity/${encodeURIComponent(projectId)}?limit=${Math.min(Math.max(Number(limit) || 80, 1), 200)}`),
  grantProjectAccess: (projectId, payload) =>
    apiRequest(`/api/project-access/${encodeURIComponent(projectId)}/members`, { method: "POST", body: JSON.stringify(payload) }),
  updateProjectAccess: (projectId, grantId, payload) =>
    apiRequest(`/api/project-access/${encodeURIComponent(projectId)}/members/${encodeURIComponent(grantId)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  revokeProjectAccess: (projectId, grantId) =>
    apiRequest(`/api/project-access/${encodeURIComponent(projectId)}/members/${encodeURIComponent(grantId)}`, { method: "DELETE" }),
  credits: () => apiRequest("/api/credits/status"),
  subscriptions: () => apiRequest("/api/subscriptions/status"),
  guestResult: (token) => apiRequest(`/api/guest-result/${encodeURIComponent(token)}`),
  executiveDashboard: (projectId) => apiRequest(`/api/dashboard/executive/${encodeURIComponent(projectId)}`),
  reports: (projectId) => apiRequest(`/api/reports/project/${encodeURIComponent(projectId)}`),
  reportDownloadUrl: (reportId) => `${resolveApiBase()}/api/reports/${encodeURIComponent(reportId)}/download`,
  files: (projectId) => apiRequest(`/api/uploads/project/${encodeURIComponent(projectId)}`),
  createProject: (payload) =>
    apiRequest("/api/projects/create", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  createUploadUrl: (payload) =>
    apiRequest("/api/uploads/create-url", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  markUploaded: (payload) =>
    apiRequest("/api/uploads/mark-uploaded", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  createAnalysis: (payload) => {
    const projectId = payload?.project_id;
    if (!projectId) throw new ApiError("project_id is required to start analysis.", { code: "project_id_required" });
    return apiRequest(`/api/analysis/start/${encodeURIComponent(projectId)}`, {
      method: "POST",
      headers: { "Idempotency-Key": payload?.idempotency_key || createIdempotencyKey() },
      body: JSON.stringify({ analysis_type: payload?.analysis_type || payload?.package_name || "all" })
    });
  },
  analysisResult: (projectId) => apiRequest(`/api/analysis/results/${encodeURIComponent(projectId)}`),
  checkout: (planCode, payload) =>
    apiRequest(planCode === "single" ? "/api/billing/create-one-time-checkout" : "/api/billing/create-subscription-checkout", {
      method: "POST",
      body: JSON.stringify({ ...payload, plan_code: planCode })
    }),
  checkoutStatus: (checkoutId) =>
    apiRequest(`/api/billing/checkouts/${encodeURIComponent(checkoutId)}`)
};
