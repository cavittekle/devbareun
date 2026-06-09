(function () {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const PREMIUM_TYPE = "full_project_control_premium";
  const DEFAULT_TYPE = "schedule";

  const packages = {
    full_project_control_premium: {
      name: "Full Project Control Premium",
      combo: "Selected package: Full Project Control Premium",
      text: "Complete project-control dashboard combining schedule, cost, payment, workforce, material, risk and recovery actions.",
      exampleText: "A premium management dashboard with executive summary, main KPIs, recovery actions, section cards and PDF / Excel export.",
      kpis: [["Progress", "68%"], ["SPI", "0.92"], ["CPI", "0.97"], ["Open Risks", "8"]],
      bars: [62, 74, 54, 82, 68, 88]
    },
    all: null,
    schedule: {
      name: "Schedule Recovery",
      combo: "Selected package: Schedule Recovery",
      text: "Delay analysis, critical path visibility and recovery planning.",
      exampleText: "A schedule-focused dashboard showing delay movement, critical path pressure and workforce recovery needs.",
      kpis: [["Delay", "21 days"], ["SPI", "0.88"], ["Critical Tasks", "14"], ["Workforce Gap", "+18%"]],
      bars: [42, 50, 58, 63, 70, 79]
    },
    cost: {
      name: "Cost & Payment Control",
      combo: "Selected package: Cost & Payment Control",
      text: "Commercial control for budget variance, actual cost and payment status.",
      exampleText: "A commercial dashboard showing cost pressure, payment progress and remaining project value.",
      kpis: [["CPI", "0.94"], ["Variance", "AZN 82K"], ["Paid", "64%"], ["Remaining", "AZN 410K"]],
      bars: [55, 60, 72, 68, 82, 76]
    },
    material: {
      name: "Material Continuity",
      combo: "Selected package: Material Continuity",
      text: "Material availability, stock status and procurement continuity.",
      exampleText: "A material-control dashboard showing shortages, delivery risk and continuity actions before work slows.",
      kpis: [["Stock Risk", "High"], ["Late Items", "9"], ["Shortage", "14%"], ["Actions", "6"]],
      bars: [68, 44, 74, 58, 82, 66]
    },
    risk: {
      name: "Risk & Decisions",
      combo: "Selected package: Risk & Decisions",
      text: "Risk register, decision prompts and management actions.",
      exampleText: "An executive risk dashboard showing priority issues, open decisions and recommended management actions.",
      kpis: [["High Risks", "5"], ["Open Decisions", "7"], ["Exposure", "Medium"], ["Actions", "11"]],
      bars: [48, 72, 64, 86, 58, 78]
    }
  };
  packages.all = packages[PREMIUM_TYPE];

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>'"]/g, ch => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;"
    }[ch]));
  }

  function activeType() {
    const active = $(".analysis-type-card.active[data-analysis-type]");
    return active ? active.dataset.analysisType : DEFAULT_TYPE;
  }

  function renderGuidance(type) {
    const data = packages[type] || packages[DEFAULT_TYPE];
    const comboTitle = $("#packageComboTitle");
    const comboText = $("#packageComboText");

    if (comboTitle) comboTitle.textContent = data.combo;
    if (comboText) comboText.textContent = data.text;
  }

  function setActivePackage(type) {
    const selected = type === "all" ? DEFAULT_TYPE : (packages[type] ? type : DEFAULT_TYPE);
    const data = packages[selected];
    $$(".analysis-type-card[data-analysis-type]").forEach(card => {
      const active = card.dataset.analysisType === selected;
      card.classList.toggle("active", active);
      card.setAttribute("aria-pressed", active ? "true" : "false");
      card.setAttribute("aria-checked", active ? "true" : "false");
    });
    renderGuidance(selected);
    document.dispatchEvent(new CustomEvent("devbareun:package-guide", { detail: { type: selected, name: data.name } }));
  }

  function clickPackage(type) {
    const selected = type === "all" ? DEFAULT_TYPE : type;
    const card = $(`.analysis-type-card[data-analysis-type="${selected}"]`);
    if (card) card.click();
    setTimeout(() => setActivePackage(selected), 0);
    setTimeout(() => setActivePackage(selected), 40);
  }

  function updateHeaderLanguageState() {
    const current = localStorage.getItem("devbareun_lang") || "en";
    $$(".header-lang-choice").forEach(btn => {
      const active = btn.dataset.headerLang === current;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function bindHeaderDynamics() {
    $$(".header-lang-choice").forEach(btn => {
      if (btn.dataset.boundHeaderLang) return;
      btn.dataset.boundHeaderLang = "true";
      btn.addEventListener("click", () => {
        const next = btn.dataset.headerLang || "en";
        const current = localStorage.getItem("devbareun_lang") || "en";
        const proxy = $(".header-lang-proxy");
        if (current !== next && proxy) {
          proxy.click();
          setTimeout(updateHeaderLanguageState, 0);
        } else {
          localStorage.setItem("devbareun_lang", next);
          document.dispatchEvent(new CustomEvent("devbareun:lang", { detail: { lang: next } }));
          updateHeaderLanguageState();
        }
      });
    });
    $$(".nav-solutions-trigger").forEach(btn => {
      if (btn.dataset.boundSolutions) return;
      btn.dataset.boundSolutions = "true";
      btn.addEventListener("click", () => {
        const open = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", open ? "false" : "true");
      });
    });
    $$("[data-solution-jump]").forEach(link => {
      if (link.dataset.boundSolutionJump) return;
      link.dataset.boundSolutionJump = "true";
      link.addEventListener("click", () => clickPackage(link.dataset.solutionJump || DEFAULT_TYPE));
    });
    updateHeaderLanguageState();
  }

  function fileNames(files) {
    return Array.from(files || []).map(file => (file && file.name ? file.name : "")).filter(Boolean);
  }

  function detectFiles(files) {
    const names = fileNames(files);
    const combined = names.join(" ").toLowerCase();
    const has = pattern => pattern.test(combined);
    const detected = [];
    const flags = {
      schedule: has(/\b(xer|xml|schedule|baseline|primavera|msp|ms project|critical path)\b/),
      progress: has(/\b(actual progress|progress|execution|performed|daily report|weekly report)\b/),
      cost: has(/\b(cost|boq|budget|estimate|smeta|commercial|actual cost)\b/),
      payment: has(/\b(f-2|f2|payment|progress payment|invoice|certificate)\b/),
      material: has(/\b(material|stock|delivery|procurement|warehouse|supply)\b/),
      workforce: has(/\b(workforce|labor|labour|manpower|crew|worker)\b/),
      risk: has(/\b(risk|issue|decision|rfi|claim|change order)\b/)
    };

    if (flags.schedule) detected.push("Schedule detected");
    if (flags.progress && !flags.schedule) detected.push("Progress detected");
    if (flags.progress && flags.schedule) detected.push("Progress detected");
    if (flags.cost) detected.push("Cost detected");
    if (flags.payment) detected.push("F-2 detected");
    if (flags.material) detected.push("Material detected");
    if (flags.workforce) detected.push("Workforce detected");
    if (flags.risk) detected.push("Risk detected");
    if (!detected.length && names.length) detected.push("Files detected");

    return { names, flags, detected };
  }

  function renderDetection(files) {
    const panel = $("#smartDetectionPanel");
    const chips = $("#smartDetectionChips");
    const title = $("#smartDetectionTitle");
    const status = $("#smartDetectionStatus");
    const type = activeType();
    const detection = detectFiles(files);

    if (!panel || !chips) return;
    if (!detection.names.length) {
      panel.hidden = true;
      renderGuidance(type);
      return;
    }

    panel.hidden = false;
    if (title) title.textContent = "Analyzing uploaded files...";
    chips.innerHTML = detection.detected
      .map(label => `<span class="detection-chip"><span aria-hidden="true">&#10003;</span>${escapeHtml(label)}</span>`)
      .join("");
    if (status) status.textContent = "Preparing dashboards...";
    renderGuidance(type);
  }

  function openExample(type) {
    const data = packages[type] || packages[DEFAULT_TYPE];
    const modal = $("[data-package-example-modal]");
    const title = $("#exampleModalTitle");
    const text = $("#exampleModalText");
    const kpis = $("#exampleModalKpis");
    const chart = $("#exampleModalChart");
    if (!modal) return;

    if (title) title.textContent = data.name;
    if (text) text.textContent = data.exampleText;
    if (kpis) {
      kpis.innerHTML = data.kpis
        .map(([label, value]) => `<span><small>${escapeHtml(label)}</small><b>${escapeHtml(value)}</b></span>`)
        .join("");
    }
    if (chart) {
      chart.innerHTML = data.bars
        .map(value => `<span style="height:${Math.max(20, Math.min(96, value))}%"></span>`)
        .join("");
    }

    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    const close = $(".package-example-close", modal);
    if (close) close.focus();
  }

  function closeExample() {
    const modal = $("[data-package-example-modal]");
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
  }

  function bind() {
    bindHeaderDynamics();
    $$(".analysis-type-card[data-analysis-type]").forEach(card => {
      if (!card.hasAttribute("tabindex")) card.setAttribute("tabindex", "0");
      if (card.dataset.guideBound) return;
      card.dataset.guideBound = "true";
      card.addEventListener("click", event => {
        if (event.target.closest(".package-example-link")) return;
        setTimeout(() => setActivePackage(card.dataset.analysisType || DEFAULT_TYPE), 0);
      });
      card.addEventListener("keydown", event => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        clickPackage(card.dataset.analysisType || DEFAULT_TYPE);
      });
    });

    document.addEventListener("click", event => {
      const example = event.target.closest(".package-example-link");
      if (example) {
        event.preventDefault();
        event.stopPropagation();
        openExample(example.dataset.examplePackage || DEFAULT_TYPE);
        return;
      }
      if (event.target.closest("[data-example-modal-close]")) {
        event.preventDefault();
        closeExample();
      }
    }, true);

    document.addEventListener("keydown", event => {
      if (event.key === "Escape") closeExample();
    });

    document.addEventListener("devbareun:files", event => {
      renderDetection(event.detail && event.detail.files ? event.detail.files : window.DevBareunSelectedFiles || []);
    });

    setActivePackage(activeType());
    renderDetection(window.DevBareunSelectedFiles || []);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
  window.addEventListener("load", () => {
    setActivePackage(activeType());
    renderDetection(window.DevBareunSelectedFiles || []);
  });
})();
