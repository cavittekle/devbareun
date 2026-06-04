(function () {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const translations = {
    en: {
      loaderTitle: "Construction analytics platform",
      navPlatform: "Platform",
      navUpload: "Upload",
      navPricing: "Pricing",
      navReports: "Reports",
      navFAQ: "FAQ",
      login: "Login",
      startAnalysis: "Start Analysis",
      heroLabel: "Project control SaaS for construction teams",
      heroTitle: "Upload project files. Confirm mapping. Get a management dashboard.",
      heroLead: "DevBareun converts schedules, progress files, cost estimates, material records and risk logs into clean project control dashboards and report-ready outputs.",
      heroPrimary: "Start analysis",
      heroSecondary: "View dashboard preview",
      heroPointUpload: "Upload files",
      heroPointMap: "Confirm mapping",
      heroPointDash: "Receive dashboard",
      dashTitle: "Project Control Dashboard",
      chartTitle: "Baseline vs actual progress",
      miniDelay: "Delay signal",
      miniPayment: "Payment status",
      miniReport: "Report output",
      workflowLabel: "Workflow",
      workflowTitle: "Three clear steps from files to management view.",
      stepUploadTitle: "Upload",
      stepUploadText: "Add schedules, progress payment files, cost estimates, material records or risk logs.",
      stepMappingTitle: "Confirm Mapping",
      stepMappingText: "Review detected file types and confirm which data belongs to each dashboard area.",
      stepDashboardTitle: "Dashboard",
      stepDashboardText: "Unlock the full dashboard and export management reports for review.",
      uploadLabel: "Upload and analysis packages",
      uploadTitle: "Choose the problem, then upload the right files.",
      uploadIntro: "Single Project users upload first, preview mapping and pay with Lemon Squeezy to unlock the full dashboard. Plus and Pro users spend monthly project credits.",
      pkgScheduleTitle: "Delay + workforce logic",
      pkgScheduleText: "Baseline, actual progress and workforce recovery planning.",
      pkgCostTitle: "Cost + F-2 tracking",
      pkgCostText: "Cost estimate, actual cost and progress payment visibility.",
      pkgMaterialTitle: "Stock + consumption logic",
      pkgMaterialText: "Material stock, consumption and procurement continuity.",
      pkgRiskTitle: "Risk register + decisions",
      pkgRiskText: "Risk tracking, decision records and management actions.",
      requiredFiles: "Required files",
      youReceive: "You will receive",
      dropTitle: "Drop project files here, or browse",
      dropText: "Excel, CSV, PDF, Primavera XER, MS Project XML and supporting images are accepted.",
      browseFiles: "Choose files",
      detecting: "Analyzing uploaded files...",
      preparingDashboards: "Preparing dashboards...",
      mappingTitle: "Detected mapping preview",
      unlockDashboard: "Unlock dashboard",
      dashboardLabel: "Dashboard and report value",
      dashboardTitle: "Only relevant dashboards are shown.",
      dashboardText: "DevBareun detects available data and prepares matching dashboard blocks. Empty sections stay hidden so the result stays focused.",
      valueOne: "Schedule + progress files show delay and recovery dashboards.",
      valueTwo: "Cost, material and risk files show only the matching control views.",
      valueThree: "Reports are prepared for management review and export.",
      previewLabel: "Example output",
      previewTitle: "Schedule Recovery Dashboard",
      previewSubtitle: "Created from baseline schedule and actual progress files.",
      previewMetricOne: "Delay status",
      previewMetricOneNote: "behind baseline",
      previewMetricTwo: "Schedule score",
      previewMetricTwoNote: "needs recovery",
      previewMetricThree: "Critical path",
      previewMetricThreeNote: "need attention",
      previewMetricFour: "Report output",
      previewMetricFourNote: "ready for review",
      previewChartTitle: "Plan vs actual progress",
      previewChartRange: "Jan - Nov",
      previewActual: "Actual",
      previewPlanned: "Planned",
      previewInsightTitle: "What you understand",
      previewInsightText: "The dashboard shows how late the project is, which tasks drive the delay, and what recovery actions should be reviewed.",
      pricingLabel: "Pricing",
      pricingTitle: "Choose one project or monthly project credits.",
      pricingText: "Billing is prepared around Lemon Squeezy checkout. No payment details are collected on the DevBareun page.",
      oneTime: "One-time",
      monthly: "Monthly",
      singleDesc: "Upload files, preview mapping, then pay to unlock one full dashboard and report package.",
      plusDesc: "5 project credits per month for recurring project control and report archive workflows.",
      proDesc: "20 project credits per month for teams managing multiple active construction sites.",
      singleCta: "Upload one project",
      plusCta: "Start Plus",
      proCta: "Start Pro",
      faqTitle: "Questions before uploading.",
      faqQ1: "What files should I upload?",
      faqA1: "Upload the files required by the selected package: schedule, progress, cost, payment, material or risk records.",
      faqQ2: "How does Single Project payment work?",
      faqA2: "You upload files first, review the mapping preview, then use Lemon Squeezy checkout to unlock the full dashboard and reports.",
      faqQ3: "What do Plus and Pro include?",
      faqA3: "Plus includes 5 monthly project credits. Pro includes 20 monthly project credits for larger teams.",
      faqQ4: "Will empty dashboard blocks appear?",
      faqA4: "No. The result view is designed to show only dashboard areas supported by uploaded project data.",
      footerText: "Construction analytics, project control and reporting platform."
    },
    az: {
      loaderTitle: "Tikinti analitika platforması",
      navPlatform: "Platforma",
      navUpload: "Yükləmə",
      navPricing: "Qiymət",
      navReports: "Hesabatlar",
      navFAQ: "FAQ",
      login: "Giriş",
      startAnalysis: "Analizə başla",
      heroLabel: "Tikinti komandaları üçün layihə nəzarəti SaaS",
      heroTitle: "Layihə fayllarını yüklə. Mapping-i təsdiqlə. İdarəetmə dashboardu al.",
      heroLead: "DevBareun qrafikləri, icra fayllarını, smeta məlumatlarını, material qeydlərini və risk siyahılarını aydın layihə nəzarəti dashboardlarına və hesabat nəticələrinə çevirir.",
      heroPrimary: "Analizə başla",
      heroSecondary: "Dashboard nümunəsinə bax",
      heroPointUpload: "Faylları yüklə",
      heroPointMap: "Mapping-i təsdiqlə",
      heroPointDash: "Dashboard al",
      dashTitle: "Layihə nəzarəti dashboardu",
      chartTitle: "Plan və faktiki irəliləyiş",
      miniDelay: "Gecikmə siqnalı",
      miniPayment: "Ödəniş statusu",
      miniReport: "Hesabat çıxışı",
      workflowLabel: "İş axını",
      workflowTitle: "Fayllardan idarəetmə görünüşünə üç aydın addım.",
      stepUploadTitle: "Yüklə",
      stepUploadText: "Qrafik, F-2, smeta, material qeydləri və ya risk siyahılarını əlavə et.",
      stepMappingTitle: "Mapping-i təsdiqlə",
      stepMappingText: "Tapılan fayl tiplərini yoxla və hansı məlumatın hansı dashboard sahəsinə aid olduğunu təsdiqlə.",
      stepDashboardTitle: "Dashboard",
      stepDashboardText: "Tam dashboardu aç və idarəetmə hesabatlarını ixrac et.",
      uploadLabel: "Yükləmə və analiz paketləri",
      uploadTitle: "Problemi seç, sonra düzgün faylları yüklə.",
      uploadIntro: "Single Project istifadəçiləri əvvəl yükləyir, mapping preview görür və tam dashboardu açmaq üçün Lemon Squeezy ilə ödəniş edir. Plus və Pro istifadəçiləri aylıq layihə kreditlərindən istifadə edir.",
      pkgScheduleTitle: "Gecikmə + işçi qüvvəsi məntiqi",
      pkgScheduleText: "Baseline, faktiki irəliləyiş və bərpa planlaması.",
      pkgCostTitle: "Smeta + F-2 izləmə",
      pkgCostText: "Smeta, faktiki xərc və icra ödənişi görünürlüğü.",
      pkgMaterialTitle: "Anbar + sərfiyyat məntiqi",
      pkgMaterialText: "Material ehtiyatı, sərfiyyat və təchizat davamlılığı.",
      pkgRiskTitle: "Risk siyahısı + qərarlar",
      pkgRiskText: "Risk izləmə, qərar qeydləri və idarəetmə tədbirləri.",
      requiredFiles: "Lazımi fayllar",
      youReceive: "Alacağınız nəticə",
      dropTitle: "Layihə fayllarını bura at və ya seç",
      dropText: "Excel, CSV, PDF, Primavera XER, MS Project XML və əlavə şəkillər qəbul edilir.",
      browseFiles: "Fayl seç",
      detecting: "Yüklənən fayllar analiz edilir...",
      preparingDashboards: "Dashboardlar hazırlanır...",
      mappingTitle: "Tapılan mapping preview",
      unlockDashboard: "Dashboardu aç",
      dashboardLabel: "Dashboard və hesabat dəyəri",
      dashboardTitle: "Yalnız uyğun dashboardlar göstərilir.",
      dashboardText: "DevBareun mövcud məlumatları tanıyır və uyğun dashboard bloklarını hazırlayır. Boş bölmələr gizlədilir.",
      valueOne: "Qrafik + irəliləyiş faylları gecikmə və bərpa dashboardu göstərir.",
      valueTwo: "Smeta, material və risk faylları yalnız uyğun nəzarət görünüşlərini göstərir.",
      valueThree: "Hesabatlar idarəetmə baxışı və ixrac üçün hazırlanır.",
      previewLabel: "Nümunə nəticə",
      previewTitle: "Schedule Recovery Dashboard",
      previewSubtitle: "Baseline schedule və actual progress fayllarından hazırlanır.",
      previewMetricOne: "Gecikmə statusu",
      previewMetricOneNote: "plandan geri",
      previewMetricTwo: "Qrafik göstəricisi",
      previewMetricTwoNote: "bərpa lazımdır",
      previewMetricThree: "Kritik yol",
      previewMetricThreeNote: "diqqət tələb edir",
      previewMetricFour: "Hesabat çıxışı",
      previewMetricFourNote: "baxış üçün hazır",
      previewChartTitle: "Plan və faktiki irəliləyiş",
      previewChartRange: "Yan - Noy",
      previewActual: "Faktiki",
      previewPlanned: "Plan",
      previewInsightTitle: "Nə başa düşürsən",
      previewInsightText: "Dashboard layihənin neçə gün gecikdiyini, gecikməni yaradan tapşırıqları və baxılmalı bərpa addımlarını göstərir.",
      pricingLabel: "Qiymət",
      pricingTitle: "Bir layihə və ya aylıq layihə kreditləri seç.",
      pricingText: "Ödəniş axını Lemon Squeezy checkout istiqamətində hazırlanıb. Kart məlumatları DevBareun səhifəsində toplanmır.",
      oneTime: "Birdəfəlik",
      monthly: "Aylıq",
      singleDesc: "Faylları yüklə, mapping preview gör, sonra tam dashboard və hesabat paketini açmaq üçün ödə.",
      plusDesc: "Davamlı layihə nəzarəti və hesabat arxivi üçün ayda 5 layihə krediti.",
      proDesc: "Bir neçə aktiv tikinti sahəsi olan komandalar üçün ayda 20 layihə krediti.",
      singleCta: "Bir layihə yüklə",
      plusCta: "Plus başlat",
      proCta: "Pro başlat",
      faqTitle: "Yükləmədən əvvəl suallar.",
      faqQ1: "Hansı faylları yükləməliyəm?",
      faqA1: "Seçilmiş paketə uyğun faylları yükləyin: qrafik, irəliləyiş, xərc, ödəniş, material və ya risk qeydləri.",
      faqQ2: "Single Project ödənişi necə işləyir?",
      faqA2: "Əvvəl faylları yükləyirsiniz, mapping preview baxırsınız, sonra Lemon Squeezy checkout ilə tam dashboard və hesabatları açırsınız.",
      faqQ3: "Plus və Pro nələri daxil edir?",
      faqA3: "Plus ayda 5 layihə krediti, Pro isə daha böyük komandalar üçün ayda 20 layihə krediti verir.",
      faqQ4: "Boş dashboard blokları görünəcək?",
      faqA4: "Xeyr. Nəticə yalnız yüklənmiş məlumatla dəstəklənən dashboard sahələrini göstərmək üçün hazırlanıb.",
      footerText: "Tikinti analitikası, layihə nəzarəti və hesabat platforması."
    }
  };

  const packages = {
    schedule: {
      title: "Schedule Recovery",
      files: ["Baseline Schedule", "Actual Progress", "Workforce Data (optional)"],
      outputs: ["Delay Dashboard", "Critical Path", "Workforce Gap", "Recovery Plan"],
      detections: ["Schedule detected", "Progress detected", "Workforce optional"]
    },
    cost: {
      title: "Cost Control",
      files: ["Cost Estimate / BOQ", "Actual Cost", "Progress Payment / F-2"],
      outputs: ["Cost Dashboard", "Payment Tracking", "Budget Variance", "Remaining Value"],
      detections: ["Cost detected", "F-2 detected", "Payment data detected"]
    },
    material: {
      title: "Material Continuity",
      files: ["Material List / BOQ", "Stock Records", "Consumption or Procurement Updates"],
      outputs: ["Material Dashboard", "Shortage Alerts", "Consumption Trend", "Procurement Actions"],
      detections: ["Material data detected", "Stock detected", "Procurement detected"]
    },
    risk: {
      title: "Risk & Decisions",
      files: ["Risk Register", "Site Notes", "Decision Records", "Cost or Schedule Signals"],
      outputs: ["Risk Dashboard", "Priority Register", "Decision Prompts", "Management Actions"],
      detections: ["Risk register detected", "Decision data detected", "Site notes detected"]
    },
  };

  function applyLanguage(lang) {
    const dictionary = translations[lang] || translations.en;
    document.documentElement.lang = lang;
    $$("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      if (dictionary[key]) node.textContent = dictionary[key];
    });
    const currentLang = $("[data-current-lang]");
    if (currentLang) currentLang.textContent = lang.toUpperCase();
    try { localStorage.setItem("devbareun_lang", lang); } catch (e) {}
  }

  function applyTheme() {
    document.documentElement.setAttribute("data-theme", "dark");
    try { localStorage.setItem("devbareun_theme", "dark"); } catch (e) {}
  }

  function toast(message) {
    const box = $("#toast");
    if (!box) return;
    box.textContent = message;
    box.classList.add("show");
    window.clearTimeout(window.__dbModernToast);
    window.__dbModernToast = window.setTimeout(() => box.classList.remove("show"), 2800);
  }

  function renderPackage(key) {
    const data = packages[key] || packages.schedule;
    $("#selectedPackageTitle").textContent = data.title;
    $("#requiredFilesList").innerHTML = data.files.map((file) => `<li>${file}</li>`).join("");
    $("#outputList").innerHTML = data.outputs.map((item) => `<li>${item}</li>`).join("");
    $$(".package-card").forEach((card) => {
      const active = card.getAttribute("data-package") === key;
      card.classList.toggle("active", active);
      card.setAttribute("aria-selected", String(active));
    });
    document.body.dataset.selectedPackage = key;
  }

  function classifyFile(name) {
    const lower = name.toLowerCase();
    if (lower.endsWith(".xer") || lower.includes("schedule") || lower.includes("baseline")) return "Schedule";
    if (lower.includes("f-2") || lower.includes("f2") || lower.includes("payment")) return "F-2 / Payment";
    if (lower.includes("boq") || lower.includes("cost") || lower.includes("estimate")) return "Cost";
    if (lower.includes("material") || lower.includes("stock")) return "Material";
    if (lower.includes("risk") || lower.includes("decision")) return "Risk";
    if (lower.endsWith(".pdf")) return "PDF report";
    return "Project file";
  }

  function formatSize(bytes) {
    if (bytes > 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes > 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  }

  function renderFiles(files) {
    const list = $("#fileList");
    const status = $("#smartStatus");
    const chips = $("#detectChips");
    const preview = $("#mappingPreview");
    const rows = $("#mappingRows");
    if (!list || !status || !chips || !preview || !rows) return;
    list.innerHTML = "";
    files.forEach((file) => {
      const row = document.createElement("div");
      row.className = "file-row";
      row.innerHTML = `<div><strong title="${file.name}">${file.name}</strong><span>${classifyFile(file.name)} · ${formatSize(file.size || 0)}</span></div><span>Uploading</span><div class="progress"><i></i></div>`;
      list.appendChild(row);
    });
    if (!files.length) {
      status.hidden = true;
      preview.hidden = true;
      return;
    }
    const selectedPackage = document.body.dataset.selectedPackage || "schedule";
    status.hidden = false;
    preview.hidden = false;
    chips.innerHTML = packages[selectedPackage].detections.map((item) => `<span>✓ ${item}</span>`).join("");
    rows.innerHTML = files.map((file) => `<div class="mapping-row"><span>${file.name}</span><strong>${classifyFile(file.name)}</strong></div>`).join("");
    toast("Files selected. Mapping preview is ready.");
  }

  document.addEventListener("DOMContentLoaded", () => {
    window.setTimeout(() => {
      const loader = $("#db-loading-screen");
      if (loader) {
        loader.classList.add("hide");
        loader.setAttribute("aria-hidden", "true");
        window.setTimeout(() => loader.remove(), 800);
      }
    }, 5000);

    applyLanguage(localStorage.getItem("devbareun_lang") || "en");
    applyTheme();
    renderPackage("schedule");

    $("[data-language-toggle]")?.addEventListener("click", () => {
      applyLanguage((document.documentElement.lang || "en") === "en" ? "az" : "en");
    });

    const menuBtn = $(".mobile-menu-btn");
    const menu = $(".mobile-menu");
    menuBtn?.addEventListener("click", () => {
      const open = !menu.classList.contains("open");
      menu.classList.toggle("open", open);
      menuBtn.setAttribute("aria-expanded", String(open));
      document.body.classList.toggle("menu-open", open);
    });
    $$(".mobile-menu a").forEach((link) => link.addEventListener("click", () => {
      menu?.classList.remove("open");
      menuBtn?.setAttribute("aria-expanded", "false");
      document.body.classList.remove("menu-open");
    }));

    $$(".package-card").forEach((card) => card.addEventListener("click", () => renderPackage(card.getAttribute("data-package") || "schedule")));

    const drop = $("#dropZone");
    const input = $("#fileInput");
    const browse = $("#browseBtn");
    browse?.addEventListener("click", (event) => {
      event.preventDefault();
      input?.click();
    });
    drop?.addEventListener("click", () => input?.click());
    drop?.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        input?.click();
      }
    });
    input?.addEventListener("change", () => renderFiles(Array.from(input.files || [])));
    ["dragenter", "dragover"].forEach((eventName) => {
      drop?.addEventListener(eventName, (event) => {
        event.preventDefault();
        drop.classList.add("is-dragover");
      });
    });
    ["dragleave", "drop"].forEach((eventName) => {
      drop?.addEventListener(eventName, (event) => {
        event.preventDefault();
        drop.classList.remove("is-dragover");
      });
    });
    drop?.addEventListener("drop", (event) => renderFiles(Array.from(event.dataTransfer?.files || [])));

    $$("[data-plan]").forEach((link) => link.addEventListener("click", () => {
      toast(`${link.textContent.trim()} selected. Upload files to continue.`);
    }));
  });
})();
