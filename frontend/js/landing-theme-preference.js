(function () {
  const themeKey = "devbareun_landing_theme";
  const html = document.documentElement;

  function renderButtons(theme) {
    document.querySelectorAll(".themeBtn").forEach(function (button) {
      button.textContent = theme === "dark" ? "\u2600" : "\u263e";
    });
  }

  try {
    const savedTheme = localStorage.getItem(themeKey);
    if (savedTheme === "light" || savedTheme === "dark") {
      html.setAttribute("data-theme", savedTheme);
      renderButtons(savedTheme);
    }
  } catch (error) {
    // Storage access can be disabled; the toggle still works for this visit.
  }

  document.addEventListener("click", function (event) {
    if (!event.target.closest(".themeBtn")) return;
    requestAnimationFrame(function () {
      const selectedTheme = html.getAttribute("data-theme") || "dark";
      try {
        localStorage.setItem(themeKey, selectedTheme);
      } catch (error) {
        return;
      }
    });
  });
})();
