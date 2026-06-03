(function () {
  const html = document.documentElement;

  function lockDarkTheme() {
    html.setAttribute("data-theme", "dark");
    try {
      localStorage.removeItem("devbareun_theme");
      localStorage.removeItem("devbareun_landing_theme");
    } catch (error) {
      // Storage can be unavailable in private or restricted browser contexts.
    }
  }

  lockDarkTheme();
  document.addEventListener("DOMContentLoaded", lockDarkTheme);
})();
