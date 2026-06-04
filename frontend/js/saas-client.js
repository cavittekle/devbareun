(function () {
  "use strict";

  if (!window.DevBareunAPI) {
    console.error("DevBareun SaaS client requires js/devbareun-api.js.");
    window.DevBareunSaaS = window.DevBareunSaaS || {};
    return;
  }

  window.DevBareunSaaS = Object.assign(window.DevBareunSaaS || {}, {
    API_BASE: window.DevBareunAPI.getApiBaseUrl(),
    api: window.DevBareunAPI.apiRequest,
    startGuest: function (payload) {
      return window.DevBareunAPI.apiRequest("/api/guest/start", {
        method: "POST",
        body: JSON.stringify(payload || {})
      });
    },
    createProject: window.DevBareunAPI.createProject,
    listProjects: window.DevBareunAPI.getProjects,
    getProject: window.DevBareunAPI.getProject,
    createOneTimeCheckout: window.DevBareunAPI.createOneTimeCheckout,
    createSubscriptionCheckout: window.DevBareunAPI.createSubscriptionCheckout,
    creditStatus: function (projectId) {
      return window.DevBareunAPI.apiRequest("/api/credits/status" + (projectId ? "?project_id=" + encodeURIComponent(projectId) : ""));
    },
    adminOverview: function () {
      return window.DevBareunAPI.apiRequest("/api/admin/overview");
    }
  });
})();
