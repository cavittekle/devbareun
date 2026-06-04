(function () {
  "use strict";

  if (!window.DevBareunAPI) {
    console.error("DevBareun unified API client is missing. Load js/devbareun-api.js before js/api-client.js.");
    window.DevBareunAPI = {};
  }

  window.DEVBAREUN_API_BASE = window.DevBareunAPI.getApiBaseUrl
    ? window.DevBareunAPI.getApiBaseUrl()
    : (window.DEVBAREUN_API_BASE || "");

  window.DevBareunAPI.baseUrl = window.DEVBAREUN_API_BASE;
})();
