(function () {
  "use strict";
  try {
    var savedLang = localStorage.getItem("devbareun_lang") || document.documentElement.getAttribute("lang") || "en";
    localStorage.setItem("devbareun_theme", "dark");
    document.documentElement.setAttribute("data-theme", "dark");
    document.documentElement.setAttribute("lang", savedLang);
  } catch (error) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();
