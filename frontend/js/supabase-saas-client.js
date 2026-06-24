(function () {
  "use strict";

  if (!window.DevBareunAPI) {
    console.error("Supabase SaaS compatibility client requires js/devbareun-api.js.");
    window.DevBareunSaaS = window.DevBareunSaaS || {};
    return;
  }

  function filePayload(projectId, file) {
    return {
      project_id: projectId,
      filename: file.name,
      mime_type: file.type || "application/octet-stream",
      size_bytes: file.size || 0
    };
  }

  window.DevBareunSaaS = Object.assign(window.DevBareunSaaS || {}, {
    API_BASE: window.DevBareunAPI.getApiBaseUrl(),
    readSession: window.DevBareunAPI.readSession,
    saveSession: window.DevBareunAPI.saveSession,
    clearSession: window.DevBareunAPI.clearAuthToken,
    accessToken: window.DevBareunAPI.getAuthToken,
    api: window.DevBareunAPI.apiRequest,
    register: function (email, password, profile) {
      return window.DevBareunAPI.registerUser(Object.assign({}, profile || {}, { email: email, password: password }));
    },
    login: window.DevBareunAPI.loginUser,
    me: window.DevBareunAPI.getCurrentUser,
    createUploadUrl: function (projectId, file) {
      // Pass the original File object so DevBareunAPI can calculate SHA-256
      // before issuing the signed upload URL.
      return window.DevBareunAPI.createUploadUrl(projectId, file);
    },
    uploadToSignedUrl: window.DevBareunAPI.uploadToSignedUrl,
    markUploadComplete: window.DevBareunAPI.markUploaded,
    createDownloadUrl: function (storagePath, expiresIn) {
      return window.DevBareunAPI.apiRequest("/api/storage/create-download-url", {
        method: "POST",
        body: JSON.stringify({ storage_path: storagePath, expires_in: expiresIn || 3600 })
      });
    },
    deleteFile: window.DevBareunAPI.deleteUpload,
    listFiles: window.DevBareunAPI.listProjectUploads
  });
})();
