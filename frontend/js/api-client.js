(function () {
  const DEFAULT_REMOTE_API = "https://devbareun-backend-production.up.railway.app";

  function resolveApiBase() {
    const remote = DEFAULT_REMOTE_API.replace(/\/$/, "");
    if (window.DEVBAREUN_API_BASE) return window.DEVBAREUN_API_BASE.replace(/\/$/, "");
    if (location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1") {
      const saved = localStorage.getItem("devbareun_api_base");
      return saved ? saved.replace(/\/$/, "") : remote;
    }
    return remote;
  }

  window.DEVBAREUN_API_BASE = resolveApiBase();

  async function readResponse(res, fallback) {
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (_) { data = null; }
    if (!res.ok) {
      const message = data && data.detail ? data.detail : (text || fallback || "Request failed");
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }
    return data;
  }

  async function dbCreateProject(projectName, customerEmail, analysisType) {
    const res = await fetch(`${window.DEVBAREUN_API_BASE}/api/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_name: projectName || "DevBareun Uploaded Project",
        customer_email: customerEmail || "info@devbareun.com",
        analysis_type: analysisType || "all"
      })
    });
    return readResponse(res, "Project creation failed");
  }

  async function dbUploadFiles(projectId, files) {
    const fd = new FormData();
    Array.from(files).forEach(file => fd.append("files", file));
    const res = await fetch(`${window.DEVBAREUN_API_BASE}/api/projects/${projectId}/upload`, {
      method: "POST",
      body: fd
    });
    return readResponse(res, "File upload failed");
  }

  async function dbPreflightProject(projectId, analysisType) {
    const res = await fetch(`${window.DEVBAREUN_API_BASE}/api/projects/${projectId}/preflight`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis_type: analysisType || "all" })
    });
    return readResponse(res, "Preflight mapping failed");
  }

  async function dbMockPayment(projectId) {
    const res = await fetch(`${window.DEVBAREUN_API_BASE}/api/payments/create-checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId })
    });
    return readResponse(res, "Payment step failed");
  }

  async function dbAnalyzeProject(projectId, analysisType, manualInputs) {
    const res = await fetch(`${window.DEVBAREUN_API_BASE}/api/projects/${projectId}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis_type: analysisType || "all", manual_inputs: manualInputs || {} })
    });
    return readResponse(res, "Project analysis failed");
  }

  async function dbGetDashboard(projectId) {
    const res = await fetch(`${window.DEVBAREUN_API_BASE}/api/projects/${projectId}/dashboard`);
    return readResponse(res, "Dashboard result not found");
  }

  async function dbHealth() {
    const res = await fetch(`${window.DEVBAREUN_API_BASE}/health`);
    return readResponse(res, "Backend health check failed");
  }

  window.DevBareunAPI = {
    baseUrl: window.DEVBAREUN_API_BASE,
    createProject: dbCreateProject,
    uploadFiles: dbUploadFiles,
    preflightProject: dbPreflightProject,
    mockPayment: dbMockPayment,
    analyzeProject: dbAnalyzeProject,
    getDashboard: dbGetDashboard,
    health: dbHealth
  };
})();
