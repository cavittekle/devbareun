(function () {
  "use strict";

  const LOCAL_DEFAULT_API = `http://${location.hostname === "localhost" ? "127.0.0.1" : location.hostname}:8000`;
  const DEFAULT_API = (location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")
    ? LOCAL_DEFAULT_API
    : "https://devbareun-production.up.railway.app";
  const API_BASE = (window.DEVBAREUN_API_BASE || localStorage.getItem("devbareun_api_base") || DEFAULT_API).replace(/\/$/, "");
  const SESSION_KEY = "devbareun_supabase_session";
  const WORKSPACE_SESSION_KEY = "devbareun_session";

  function readSession() {
    try {
      return JSON.parse(localStorage.getItem(SESSION_KEY) || localStorage.getItem(WORKSPACE_SESSION_KEY) || "null");
    } catch (_) {
      return null;
    }
  }

  function saveSession(session) {
    if (!session) return;
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    localStorage.setItem(WORKSPACE_SESSION_KEY, JSON.stringify(session));
  }

  function clearSession() {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(WORKSPACE_SESSION_KEY);
  }

  function accessToken() {
    const session = readSession();
    return session?.access_token || session?.auth?.access_token || null;
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    const token = accessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    const text = await response.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (_) { data = { raw: text }; }
    if (!response.ok) {
      const detail = data?.detail || data?.message || response.statusText;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  async function register(email, password, profile = {}) {
    const data = await api("/api/auth/supabase/register", {
      method: "POST",
      body: JSON.stringify({ email, password, ...profile })
    });
    if (data?.auth?.access_token) saveSession(data.auth);
    return data;
  }

  async function login(email, password) {
    const data = await api("/api/auth/supabase/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    if (data?.auth?.access_token) saveSession(data.auth);
    return data;
  }

  async function me() {
    return api("/api/auth/me");
  }

  async function createUploadUrl(projectId, file) {
    return api("/api/storage/create-upload-url", {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        file_name: file.name,
        content_type: file.type || "application/octet-stream",
        size_bytes: file.size
      })
    });
  }

  async function uploadToSignedUrl(uploadPayload, file, onProgress) {
    const signedUrl = uploadPayload?.upload?.signedURL || uploadPayload?.upload?.signedUrl || uploadPayload?.upload?.url;
    if (!signedUrl) throw new Error("Signed upload URL was not returned by backend.");

    // XMLHttpRequest is used here because fetch does not expose upload progress events.
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("PUT", signedUrl, true);
      xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && typeof onProgress === "function") {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve();
        else reject(new Error(`Supabase upload failed: ${xhr.status}`));
      };
      xhr.onerror = () => reject(new Error("Supabase upload network error."));
      xhr.send(file);
    });
    return markUploadComplete(uploadPayload.file);
  }

  async function markUploadComplete(fileRecord) {
    return api("/api/storage/mark-uploaded", {
      method: "POST",
      body: JSON.stringify({
        file_id: fileRecord.file_id,
        project_id: fileRecord.project_id,
        storage_path: fileRecord.storage_path,
        uploaded: true
      })
    });
  }

  async function createDownloadUrl(storagePath, expiresIn = 3600) {
    return api("/api/storage/create-download-url", {
      method: "POST",
      body: JSON.stringify({ storage_path: storagePath, expires_in: expiresIn })
    });
  }

  async function deleteFile(fileId) {
    return api(`/api/files/delete?file_id=${encodeURIComponent(fileId)}`, { method: "DELETE" });
  }

  async function listFiles(projectId) {
    return api(`/api/files/list?project_id=${encodeURIComponent(projectId)}`);
  }

  window.DevBareunSaaS = {
    API_BASE,
    readSession,
    saveSession,
    clearSession,
    accessToken,
    api,
    register,
    login,
    me,
    createUploadUrl,
    uploadToSignedUrl,
    markUploadComplete,
    createDownloadUrl,
    deleteFile,
    listFiles
  };
})();
