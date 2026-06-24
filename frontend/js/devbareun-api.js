(function () {
  "use strict";

  var DEFAULT_REMOTE_API = "https://devbareun-production.up.railway.app";
  var AUTH_TOKEN_KEY = "devbareun_auth_token";
  var SESSION_KEY = "devbareun_session";
  var LEGACY_SESSION_KEY = "devbareun_supabase_session";
  var PROJECT_TOKEN_PREFIX = "devbareun_project_token_";
  var PREMIUM_ANALYSIS_TYPE = "schedule";

  function trimSlash(value) {
    return String(value || "").replace(/\/+$/, "");
  }

  function isLocalPreview() {
    return location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1";
  }

  function isProductionFrontendHost() {
    return location.hostname === "devbareun.com" || location.hostname === "www.devbareun.com";
  }

  function shouldPersistBearerToken() {
    // Bearer-token persistence is restricted to local/dev previews. Production
    // hosts must rely on the backend-managed HTTP-only auth cookie.
    return !isProductionFrontendHost();
  }

  function localDefaultApi() {
    if (localStorage.getItem("devbareun_use_local_backend") !== "true") {
      return DEFAULT_REMOTE_API;
    }
    var host = location.hostname === "localhost" ? "127.0.0.1" : (location.hostname || "127.0.0.1");
    return "http://" + host + ":8000";
  }

  function getApiBaseUrl() {
    var configured =
      (window.DEVBAREUN_CONFIG && window.DEVBAREUN_CONFIG.apiBaseUrl) ||
      window.DEVBAREUN_API_BASE_URL ||
      window.DEVBAREUN_API_URL ||
      window.DEVBAREUN_API_BASE;
    if (!configured && !isProductionFrontendHost()) {
      configured =
        localStorage.getItem("devbareun_api_base") ||
        localStorage.getItem("devbareun_api_url");
    }
    var resolved = configured || (isLocalPreview() ? localDefaultApi() : DEFAULT_REMOTE_API);
    resolved = trimSlash(resolved);
    window.DEVBAREUN_API_BASE = resolved;
    return resolved;
  }

  function safeJsonParse(value) {
    try {
      return JSON.parse(value || "null");
    } catch (_) {
      return null;
    }
  }

  function readCookie(name) {
    return document.cookie.split(";").map(function (item) { return item.trim(); }).filter(Boolean).map(function (item) { return item.split("="); }).reduce(function (found, parts) {
      if (found) return found;
      return decodeURIComponent(parts[0] || "") === name ? parts.slice(1).join("=") : "";
    }, "");
  }

  async function ensureCsrfTokenHeader(headers, method) {
    var unsafe = ["GET", "HEAD", "OPTIONS", "TRACE"].indexOf(String(method || "GET").toUpperCase()) === -1;
    if (!unsafe || headers.has("X-CSRF-Token")) return;
    var token = readCookie("devbareun_csrf");
    if (!token) {
      try {
        var response = await fetch(requestUrl("/api/auth/csrf"), { credentials: "include" });
        var payload = await parseResponse(response);
        token = readCookie("devbareun_csrf") || (payload && payload.csrf_token) || "";
      } catch (_) {
        token = "";
      }
    }
    if (token) headers.set("X-CSRF-Token", decodeURIComponent(token));
  }

  function normalizeSession(session) {
    if (!session) return null;
    if (!session.access_token && session.auth && session.auth.access_token) {
      return Object.assign({}, session.auth, { user: session.user || session.auth.user });
    }
    return session;
  }

  function readSession() {
    if (isProductionFrontendHost() && !shouldPersistBearerToken()) {
      return safeJsonParse(localStorage.getItem(SESSION_KEY)) || null;
    }
    return normalizeSession(
      safeJsonParse(localStorage.getItem(SESSION_KEY)) ||
      safeJsonParse(localStorage.getItem(LEGACY_SESSION_KEY))
    );
  }

  function saveSession(session) {
    if (!session) return;
    var normalized = normalizeSession(session);
    var persisted = Object.assign({}, normalized || {});
    if (!shouldPersistBearerToken()) {
      delete persisted.access_token;
      delete persisted.refresh_token;
      if (persisted.auth) {
        persisted.auth = Object.assign({}, persisted.auth);
        delete persisted.auth.access_token;
        delete persisted.auth.refresh_token;
      }
    }
    localStorage.setItem(SESSION_KEY, JSON.stringify(persisted));
    if (shouldPersistBearerToken()) {
      localStorage.setItem(LEGACY_SESSION_KEY, JSON.stringify(persisted));
    } else {
      localStorage.removeItem(LEGACY_SESSION_KEY);
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
    if (normalized && normalized.access_token && shouldPersistBearerToken()) {
      localStorage.setItem(AUTH_TOKEN_KEY, normalized.access_token);
    }
  }

  function getAuthToken() {
    if (!shouldPersistBearerToken()) return null;
    var direct = localStorage.getItem(AUTH_TOKEN_KEY);
    if (direct) return direct;
    var session = readSession();
    return session && (session.access_token || (session.auth && session.auth.access_token)) || null;
  }

  function setAuthToken(token, sessionPatch) {
    if (!token) return;
    if (!shouldPersistBearerToken()) return;
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    var session = Object.assign({}, readSession() || {}, sessionPatch || {}, { access_token: token });
    saveSession(session);
  }

  function clearAuthToken() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(LEGACY_SESSION_KEY);
  }

  function normalizeError(status, data, fallback, meta) {
    var detail = data && (data.details || data.detail || data.error);
    var message = data && data.message ? String(data.message) : (typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : fallback));
    var code = data && (data.code || (typeof data.error === "string" ? data.error : null));
    return {
      ok: false,
      status: status || 0,
      code: code || (status === 401 ? "unauthorized" : status === 403 ? "forbidden" : status === 0 ? "backend_offline" : "request_failed"),
      message: message || "Request failed",
      detail: detail || data || null,
      path: meta && meta.path,
      method: meta && meta.method,
      backendOffline: status === 0,
      unauthorized: status === 401,
      forbidden: status === 403
    };
  }

  async function parseResponse(response) {
    var text = await response.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch (_) {
      return { raw: text };
    }
  }

  function requestUrl(path) {
    if (/^https?:\/\//i.test(path)) return path;
    return getApiBaseUrl() + (String(path).charAt(0) === "/" ? path : "/" + path);
  }

  async function apiRequest(path, options) {
    options = options || {};
    var method = (options.method || "GET").toUpperCase();
    var headers = new Headers(options.headers || {});
    var body = options.body;
    var auth = options.auth !== false;
    var isForm = body instanceof FormData;

    if (!headers.has("Content-Type") && body && !isForm) {
      headers.set("Content-Type", "application/json");
    }
    if (auth && !headers.has("Authorization")) {
      var token = getAuthToken();
      if (token) headers.set("Authorization", "Bearer " + token);
    }
    await ensureCsrfTokenHeader(headers, method);

    try {
      var response = await fetch(requestUrl(path), Object.assign({ credentials: "include" }, options, { method: method, headers: headers }));
      if (options.rawResponse) return response;
      var data = await parseResponse(response);
      if (!response.ok) {
        var normalized = normalizeError(response.status, data, response.statusText, { path: path, method: method });
        if (response.status === 401) clearAuthToken();
        if (options.throwOnError === false) return normalized;
        var err = new Error(normalized.message);
        Object.assign(err, normalized);
        throw err;
      }
      return data;
    } catch (error) {
      if (error && error.ok === false) throw error;
      var offline = normalizeError(0, null, "Backend is offline or unreachable.", { path: path, method: method });
      if (options.throwOnError === false) return offline;
      var networkError = new Error(offline.message);
      Object.assign(networkError, offline, { cause: error });
      throw networkError;
    }
  }

  function sessionFromAuthPayload(data, fallbackPlan) {
    var auth = (data && (data.auth || data.session)) || {};
    var token = auth.access_token || data && data.access_token;
    if (!token) return null;
    return Object.assign({}, auth, {
      access_token: token,
      user: Object.assign({}, auth.user || {}, data && data.user || {}, {
        plan: (data && data.user && data.user.plan) || (auth.user && auth.user.plan) || fallbackPlan || "plus"
      })
    });
  }

  async function getCurrentUser() {
    return apiRequest("/api/auth/me");
  }

  async function loginUser(email, password, plan) {
    var payload = typeof email === "object" ? email : { email: email, password: password, plan: plan || "plus" };
    var data = await apiRequest("/api/auth/supabase/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload)
    });
    var session = sessionFromAuthPayload(data, payload.plan);
    if (session) saveSession(session);
    return data;
  }

  async function registerUser(payload) {
    var data = await apiRequest("/api/auth/supabase/register", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload || {})
    });
    var session = sessionFromAuthPayload(data, payload && payload.plan);
    if (session) saveSession(session);
    return data;
  }

  async function logoutUser() {
    var result = await apiRequest("/api/auth/logout", { method: "POST", throwOnError: false });
    clearAuthToken();
    return result;
  }

  function projectTokenKey(projectId) {
    return PROJECT_TOKEN_PREFIX + projectId;
  }

  function setProjectToken(projectId, token) {
    if (projectId && token) localStorage.setItem(projectTokenKey(projectId), token);
  }

  function getProjectToken(projectId) {
    return projectId ? localStorage.getItem(projectTokenKey(projectId)) : null;
  }

  function projectHeaders(projectId, withJson) {
    var headers = {};
    if (withJson) headers["Content-Type"] = "application/json";
    var token = getProjectToken(projectId);
    if (token) headers["X-Project-Token"] = token;
    return headers;
  }

  async function getProjects() {
    return apiRequest("/api/projects/list");
  }

  async function calculateSha256(file) {
    if (!file || typeof file.arrayBuffer !== "function" || !window.crypto || !window.crypto.subtle) {
      throw new Error("Your browser cannot calculate the required SHA-256 file integrity check.");
    }
    var digest = await window.crypto.subtle.digest("SHA-256", await file.arrayBuffer());
    return Array.prototype.map.call(new Uint8Array(digest), function (value) {
      return value.toString(16).padStart(2, "0");
    }).join("");
  }

  async function createProject(payloadOrName, customerEmail, analysisType) {
    var payload = payloadOrName && typeof payloadOrName === "object" && !(payloadOrName instanceof String)
      ? payloadOrName
      : {
          project_name: payloadOrName || "DevBareun Uploaded Project",
          owner_email: customerEmail || undefined,
          analysis_type: analysisType || PREMIUM_ANALYSIS_TYPE
        };
    return apiRequest("/api/projects/create", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async function getProject(projectId) {
    return apiRequest("/api/projects/" + encodeURIComponent(projectId));
  }

  async function updateProject(projectId, payload) {
    return apiRequest("/api/projects/" + encodeURIComponent(projectId), {
      method: "PATCH",
      body: JSON.stringify(payload || {})
    });
  }

  async function deleteProject(projectId) {
    return apiRequest("/api/projects/" + encodeURIComponent(projectId), { method: "DELETE" });
  }

  async function createUploadUrl(projectId, fileMeta) {
    var file = fileMeta || {};
    var checksum = file.checksum || file.sha256 || null;
    if (!checksum && typeof file.arrayBuffer === "function") checksum = await calculateSha256(file);
    return apiRequest("/api/uploads/create-url", {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId || file.project_id,
        filename: file.filename || file.file_name || file.name,
        mime_type: file.mime_type || file.content_type || file.type || "application/octet-stream",
        size_bytes: file.size_bytes || file.size || 0,
        checksum: checksum
      })
    });
  }

  async function markUploaded(payload) {
    return apiRequest("/api/uploads/mark-uploaded", {
      method: "POST",
      body: JSON.stringify(payload || {})
    });
  }

  async function listProjectUploads(projectId) {
    return apiRequest("/api/uploads/project/" + encodeURIComponent(projectId));
  }

  async function deleteUpload(fileId) {
    return apiRequest("/api/uploads/" + encodeURIComponent(fileId), { method: "DELETE" });
  }

  async function uploadToSignedUrl(uploadPayload, file, onProgress) {
    var signedUrl = uploadPayload && (uploadPayload.signed_upload_url || uploadPayload.signedUrl || uploadPayload.signedURL || uploadPayload.url || (uploadPayload.upload && (uploadPayload.upload.signedURL || uploadPayload.upload.signedUrl || uploadPayload.upload.url)));
    if (!signedUrl) throw new Error("Signed upload URL was not returned by backend.");
    await new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open("PUT", signedUrl, true);
      xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
      xhr.upload.onprogress = function (event) {
        if (event.lengthComputable && typeof onProgress === "function") {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) resolve();
        else reject(new Error("Storage upload failed: " + xhr.status));
      };
      xhr.onerror = function () { reject(new Error("Storage upload network error.")); };
      xhr.send(file);
    });
    return markUploaded({
      upload_id: uploadPayload.upload_id || uploadPayload.file_id || (uploadPayload.file && uploadPayload.file.file_id),
      file_id: uploadPayload.file_id || (uploadPayload.file && uploadPayload.file.file_id),
      project_id: uploadPayload.project_id || (uploadPayload.file && uploadPayload.file.project_id),
      storage_path: uploadPayload.storage_path || (uploadPayload.file && uploadPayload.file.storage_path),
      uploaded: true,
      checksum: uploadPayload.checksum || (uploadPayload.file && uploadPayload.file.checksum) || null
    });
  }

  function createIdempotencyKey() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") return window.crypto.randomUUID();
    return "analysis-" + Date.now() + "-" + Math.random().toString(36).slice(2, 12);
  }

  async function startAnalysis(projectId, payload) {
    var request = Object.assign({}, payload || {});
    var idempotencyKey = request.idempotency_key || createIdempotencyKey();
    delete request.idempotency_key;
    return apiRequest("/api/analysis/start/" + encodeURIComponent(projectId), {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(Object.assign({ analysis_type: PREMIUM_ANALYSIS_TYPE }, request))
    });
  }

  async function getAnalysisJob(jobId) {
    return apiRequest("/api/analysis/jobs/" + encodeURIComponent(jobId));
  }

  async function getExecutiveDashboard(projectId) {
    return apiRequest("/api/dashboard/executive/" + encodeURIComponent(projectId));
  }

  async function getPortfolioDashboard() {
    return apiRequest("/api/dashboard/portfolio");
  }

  async function getReports(projectId) {
    if (!projectId) return apiRequest("/api/workspace/reports", { throwOnError: false });
    return apiRequest("/api/reports/project/" + encodeURIComponent(projectId));
  }

  async function createOneTimeCheckout(projectId, payload) {
    if (projectId && typeof projectId === "object") {
      payload = projectId;
      projectId = payload.project_id || null;
    }
    var auth = !(payload && payload.auth === false);
    var body = Object.assign({ plan: "single", project_id: projectId || null }, payload || {});
    delete body.auth;
    var data = await apiRequest("/api/billing/create-one-time-checkout", {
      method: "POST",
      auth: auth,
      body: JSON.stringify(body)
    });
    if (data && data.checkout_url && !data.url) data.url = data.checkout_url;
    return data;
  }

  async function createSubscriptionCheckout(plan, payload) {
    if (plan && typeof plan === "object") {
      payload = plan;
      plan = payload.plan_code || payload.plan || "plus";
    }
    var data = await apiRequest("/api/billing/create-subscription-checkout", {
      method: "POST",
      body: JSON.stringify(Object.assign({ plan: plan || "plus" }, payload || {}))
    });
    if (data && data.checkout_url && !data.url) data.url = data.checkout_url;
    return data;
  }

  async function getBillingStatus() {
    return apiRequest("/api/billing/status", { throwOnError: false });
  }

  async function getHealth() {
    return apiRequest("/api/health", { auth: false });
  }

  async function uploadFiles(projectId, files) {
    var uploaded = [];
    for (var i = 0; i < (files || []).length; i += 1) {
      var file = files[i];
      var ticket = await createUploadUrl(projectId, file);
      await uploadToSignedUrl(ticket, file);
      uploaded.push(ticket.file || ticket);
    }
    return { project_id: projectId, uploaded_files: uploaded };
  }

  async function preflightProject(projectId, analysisType) {
    var uploads = await listProjectUploads(projectId);
    return {
      project_id: projectId,
      analysis_type: analysisType || PREMIUM_ANALYSIS_TYPE,
      uploaded_files: uploads.uploaded_files || [],
      ready: Boolean((uploads.uploaded_files || []).length)
    };
  }

  async function mockPayment(projectId, options) {
    return createOneTimeCheckout(projectId, Object.assign({ auth: false }, options || {}));
  }

  async function analyzeProject(projectId, analysisType, manualInputs) {
    return startAnalysis(projectId, { analysis_type: analysisType || PREMIUM_ANALYSIS_TYPE, manual_inputs: manualInputs || {} });
  }

  async function getDashboard(projectId) {
    return getExecutiveDashboard(projectId);
  }

  var api = {
    baseUrl: getApiBaseUrl(),
    getApiBaseUrl: getApiBaseUrl,
    getAuthToken: getAuthToken,
    setAuthToken: setAuthToken,
    clearAuthToken: clearAuthToken,
    readSession: readSession,
    saveSession: saveSession,
    apiRequest: apiRequest,
    getCurrentUser: getCurrentUser,
    loginUser: loginUser,
    registerUser: registerUser,
    logoutUser: logoutUser,
    getProjects: getProjects,
    createProject: createProject,
    getProject: getProject,
    updateProject: updateProject,
    deleteProject: deleteProject,
    createUploadUrl: createUploadUrl,
    markUploaded: markUploaded,
    listProjectUploads: listProjectUploads,
    deleteUpload: deleteUpload,
    uploadToSignedUrl: uploadToSignedUrl,
    startAnalysis: startAnalysis,
    getAnalysisJob: getAnalysisJob,
    getExecutiveDashboard: getExecutiveDashboard,
    getPortfolioDashboard: getPortfolioDashboard,
    getReports: getReports,
    createOneTimeCheckout: createOneTimeCheckout,
    createSubscriptionCheckout: createSubscriptionCheckout,
    getBillingStatus: getBillingStatus,
    getHealth: getHealth,
    health: getHealth,
    uploadFiles: uploadFiles,
    preflightProject: preflightProject,
    createOneTimeCheckout: createOneTimeCheckout,
    mockPayment: mockPayment,
    analyzeProject: analyzeProject,
    getDashboard: getDashboard,
    getProjectToken: getProjectToken
  };

  window.DevBareunAPI = Object.assign(window.DevBareunAPI || {}, api);
  window.DevBareunSaaS = Object.assign(window.DevBareunSaaS || {}, {
    API_BASE: api.baseUrl,
    api: apiRequest,
    readSession: readSession,
    saveSession: saveSession,
    clearSession: clearAuthToken,
    accessToken: getAuthToken,
    register: function (email, password, profile) {
      return registerUser(Object.assign({}, profile || {}, { email: email, password: password }));
    },
    login: loginUser,
    me: getCurrentUser,
    createUploadUrl: createUploadUrl,
    uploadToSignedUrl: uploadToSignedUrl,
    markUploadComplete: markUploaded,
    deleteFile: deleteUpload,
    listFiles: listProjectUploads,
    startGuest: function (payload) {
      return apiRequest("/api/guest/start", { method: "POST", body: JSON.stringify(payload || {}) });
    },
    createProject: createProject,
    listProjects: getProjects,
    getProject: getProject,
    createOneTimeCheckout: createOneTimeCheckout,
    createSubscriptionCheckout: createSubscriptionCheckout,
    creditStatus: function (projectId) {
      return apiRequest("/api/credits/status" + (projectId ? "?project_id=" + encodeURIComponent(projectId) : ""));
    },
    adminOverview: function () {
      return apiRequest("/api/admin/overview");
    }
  });
})();
