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
      navAbout: "About",
      navFAQ: "FAQ",
      navContact: "Contact",
      login: "Login",
      startAnalysis: "Start Analysis",
      heroLabel: "Project control SaaS for construction teams",
      heroTitle: "Turn project files into clear decisions.",
      heroLead: "DevBareun helps construction teams turn schedules, progress files, cost data, and site records into clear reporting, risk visibility, and recovery actions.",
      heroPrimary: "Start analysis",
      heroSecondary: "View dashboard preview",
      heroPointUpload: "Upload files",
      heroPointMap: "Confirm mapping",
      heroPointDash: "Receive dashboard",
      heroShowcasePill: "4 control packages - schedule, cost, material, risk",
      heroShowcaseTitleOne: "Construction project",
      heroShowcaseTitleTwo: "control,",
      heroShowcaseTitleThree: "done right.",
      heroShowcaseLead: "Upload your project files. Get a precise management dashboard - schedule, cost, payment, material and risk - in one view.",
      heroFlowUpload: "Upload project files",
      heroFlowMap: "Confirm detected mapping",
      heroFlowDashboard: "Review dashboard output",
      heroBenefitLabel: "Project control for construction teams",
      heroBenefitTitle: "See what needs action before delays grow.",
      heroBenefitText: "Replace scattered project updates with a clear decision view for schedule, cost, progress, risk, and recovery actions.",
      benefitDelayTitle: "Catch delays earlier",
      benefitDelayText: "Identify critical schedule issues before they affect handover dates.",
      benefitReportsTitle: "Turn files into reports",
      benefitReportsText: "Convert project data into clear executive reporting.",
      benefitTeamsTitle: "Keep teams aligned",
      benefitTeamsText: "Give management, planners, and site teams one shared project view.",
      benefitRecoveryTitle: "Move faster with recovery actions",
      benefitRecoveryText: "See what needs attention now and act before delays grow.",
      benefitTagSchedule: "Schedule analytics",
      benefitTagRisk: "Risk visibility",
      benefitTagRecovery: "Recovery actions",
      benefitTagExports: "PDF / Excel outputs",
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
      downloadTemplate: "Download template",
      statPackages: "Control packages",
      statFormats: "File formats",
      statPlans: "Pricing plans",
      statLanguages: "Languages",
      pkgScheduleTitle: "Delay + workforce logic",
      pkgScheduleText: "Delay, actual progress and workforce recovery planning.",
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
      dashboardLabel: "Live executive dashboard",
      dashboardTitle: "Every signal rolled up into one decision view.",
      dashboardText: "Schedule, cost and risk are read from your uploads and presented as the same management dashboard your team reviews each week.",
      valueOne: "No empty dashboard blocks.",
      valueTwo: "No unclear file assumptions.",
      valueThree: "Outputs are prepared for project review.",
      outputOneTitle: "Mapping review",
      outputOneText: "Detected file types, required fields and unclear columns are shown before the result is finalized.",
      outputTwoTitle: "Relevant dashboards",
      outputTwoText: "Schedule, cost, material or risk views appear only when the uploaded data supports them.",
      outputThreeTitle: "Report package",
      outputThreeText: "Prepared outputs are structured for management review, archive and PDF or Excel export.",
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
      pricingTitle: "Simple, transparent pricing.",
      pricingText: "One project or twenty. Pick the plan that fits. No hidden fees, no lock-in.",
      oneTime: "One-time",
      monthly: "Monthly",
      annual: "Annual",
      saveAnnual: "Save 20%",
      mostPopular: "Most popular",
      recommended: "Recommended",
      highVolume: "High volume",
      priceSingleNote: "one-time",
      priceMonthlyNote: "month",
      priceAnnualNote: "year",
      priceAnnualBilledNote: "mo, billed annually",
      pricingSingleShort: "Perfect for a single project analysis with full dashboard output.",
      pricingPlusShort: "The sweet spot for active project teams managing multiple sites.",
      pricingProShort: "For companies running larger portfolios with admin oversight.",
      singleDesc: "Upload files, preview mapping, then pay to unlock one full dashboard and report package.",
      plusDesc: "5 project credits per month for recurring project control and report archive workflows.",
      proDesc: "20 project credits per month for teams managing multiple active construction sites.",
      singleCta: "Upload one project",
      plusCta: "Start Plus",
      proCta: "Start Pro",
      pricingIncludes: "What's included",
      compareSingle: "Single Project",
      comparePlus: "Plus",
      comparePro: "Pro",
      rowCredits: "Analysis credits",
      rowCreditsSingle: "1 project",
      rowCreditsPlus: "5 / month",
      rowCreditsPro: "20 / month",
      rowCreditsPlusAnnual: "5 / month",
      rowCreditsProAnnual: "20 / month",
      rowPackages: "All 4 control packages",
      rowDashboard: "Package-specific dashboard",
      rowExport: "PDF + Excel export",
      rowArchive: "Report archive",
      rowUsage: "Credit usage visibility",
      rowWorkspace: "Multi-project workspace",
      rowAdmin: "Admin usage tracking",
      pricingTrustSecure: "Secure checkout",
      pricingTrustCancel: "Cancel anytime",
      pricingTrustSetup: "No setup fees",
      pricingTrustIncluded: "All packages included",
      faqTitle: "Questions before uploading.",
      faqQ1: "What files should I upload?",
      faqA1: "Upload the files required by the selected package: schedule, progress, cost, payment, material or risk records.",
      faqQ2: "How does Single Project payment work?",
      faqA2: "You upload files first, review the mapping preview, then use Lemon Squeezy checkout to unlock the full dashboard and reports.",
      faqQ3: "What do Plus and Pro include?",
      faqA3: "Plus includes 5 monthly project credits. Pro includes 20 monthly project credits for larger teams.",
      faqQ4: "Will empty dashboard blocks appear?",
      faqA4: "No. The result view is designed to show only dashboard areas supported by uploaded project data.",
      footerText: "Construction analytics, project control and reporting platform.",
      footerBadgeOne: "Project control",
      footerBadgeTwo: "Report-ready outputs",
      footerProduct: "Product",
      footerCompany: "Company",
      footerPlatform: "Platform",
      footerLegal: "Legal",
      footerPrivacy: "Privacy Policy",
      footerTerms: "Terms of Service",
      footerContact: "Contact",
      footerContactText: "For product, billing and project setup questions.",
      footerBottom: "Built for construction project teams."
    },
    az: {
      loaderTitle: "Tikinti analitika platforması",
      navPlatform: "Platforma",
      navUpload: "Yükləmə",
      navPricing: "Qiymət",
      navReports: "Hesabatlar",
      navAbout: "Haqqında",
      navFAQ: "FAQ",
      navContact: "Əlaqə",
      login: "Giriş",
      startAnalysis: "Analizə başla",
      heroLabel: "Tikinti komandaları üçün layihə nəzarəti SaaS",
      heroTitle: "Layihə fayllarını aydın qərarlara çevirin.",
      heroLead: "DevBareun tikinti komandalarına qrafikləri, icra fayllarını, xərc məlumatlarını və sahə qeydlərini aydın hesabatlara, risk görünürlüğünə və bərpa addımlarına çevirməyə kömək edir.",
      heroPrimary: "Analizə başla",
      heroSecondary: "Dashboard nümunəsinə bax",
      heroPointUpload: "Faylları yüklə",
      heroPointMap: "Mapping-i təsdiqlə",
      heroPointDash: "Dashboard al",
      heroShowcasePill: "4 nəzarət paketi - qrafik, xərc, material, risk",
      heroShowcaseTitleOne: "Tikinti layihəsi",
      heroShowcaseTitleTwo: "nəzarəti,",
      heroShowcaseTitleThree: "düzgün qurulmuş.",
      heroShowcaseLead: "Layihə fayllarınızı yükləyin. Qrafik, xərc, ödəniş, material və risk üzrə dəqiq idarəetmə dashboardunu bir görünüşdə alın.",
      heroFlowUpload: "Layihə fayllarını yüklə",
      heroFlowMap: "Mapping nəticəsini təsdiqlə",
      heroFlowDashboard: "Dashboard nəticəsinə bax",
      heroBenefitLabel: "Tikinti komandaları üçün layihə nəzarəti",
      heroBenefitTitle: "Gecikmələr böyümədən nəyi etmək lazım olduğunu görün.",
      heroBenefitText: "Dağınıq layihə yeniləmələrini qrafik, xərc, icra, risk və bərpa addımları üçün aydın qərar görünüşünə çevirin.",
      benefitDelayTitle: "Gecikmələri daha tez görün",
      benefitDelayText: "Təhvil tarixlərinə təsir etməzdən əvvəl kritik qrafik problemlərini müəyyən edin.",
      benefitReportsTitle: "Faylları hesabatlara çevirin",
      benefitReportsText: "Layihə məlumatlarını aydın rəhbərlik hesabatlarına çevirin.",
      benefitTeamsTitle: "Komandaları eyni xətdə saxlayın",
      benefitTeamsText: "Rəhbərlik, planlama və sahə komandalarına ortaq layihə görünüşü verin.",
      benefitRecoveryTitle: "Bərpa addımları ilə daha sürətli hərəkət edin",
      benefitRecoveryText: "İndi diqqət tələb edənləri görün və gecikmələr böyümədən hərəkət edin.",
      benefitTagSchedule: "Qrafik analitikası",
      benefitTagRisk: "Risk görünürlüğü",
      benefitTagRecovery: "Bərpa addımları",
      benefitTagExports: "PDF / Excel nəticələri",
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
      downloadTemplate: "Şablonu yüklə",
      statPackages: "Nəzarət paketləri",
      statFormats: "Fayl formatları",
      statPlans: "Qiymət planları",
      statLanguages: "Dillər",
      pkgScheduleTitle: "Gecikmə + işçi qüvvəsi məntiqi",
      pkgScheduleText: "Gecikmə, faktiki irəliləyiş və bərpa planlaması.",
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
      dashboardLabel: "Canlı idarəetmə dashboardu",
      dashboardTitle: "Bütün siqnallar bir qərar görünüşündə birləşir.",
      dashboardText: "Qrafik, xərc və risk məlumatları yüklədiyiniz fayllardan oxunur və komandanızın hər həftə baxdığı idarəetmə dashboardu kimi təqdim olunur.",
      valueOne: "Boş dashboard blokları yoxdur.",
      valueTwo: "Aydın olmayan fayl fərziyyələri yoxdur.",
      valueThree: "Nəticələr layihə baxışı üçün hazırlanır.",
      outputOneTitle: "Mapping baxışı",
      outputOneText: "Tapılan fayl tipləri, lazımi sahələr və aydın olmayan sütunlar nəticə tamamlanmadan əvvəl göstərilir.",
      outputTwoTitle: "Uyğun dashboardlar",
      outputTwoText: "Qrafik, xərc, material və ya risk görünüşləri yalnız yüklənən data dəstəklədikdə göstərilir.",
      outputThreeTitle: "Hesabat paketi",
      outputThreeText: "Hazırlanan nəticələr idarəetmə baxışı, arxiv və PDF və ya Excel export üçün strukturlaşdırılır.",
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
      pricingTitle: "Sadə və şəffaf qiymət.",
      pricingText: "Bir layihə və ya aylıq kreditlər. Gizli xərc və uzunmüddətli məcburiyyət yoxdur.",
      oneTime: "Birdəfəlik",
      monthly: "Aylıq",
      annual: "İllik",
      saveAnnual: "20% qənaət",
      mostPopular: "Ən çox seçilən",
      recommended: "Tövsiyə olunur",
      highVolume: "Böyük həcm",
      priceSingleNote: "birdəfəlik",
      priceMonthlyNote: "aylıq",
      priceAnnualNote: "illik",
      priceAnnualBilledNote: "ay, illik ödənilir",
      pricingSingleShort: "Tam dashboard nəticəsi ilə bir layihə analizi üçün uyğundur.",
      pricingPlusShort: "Bir neçə sahəni idarə edən aktiv layihə komandaları üçün ən uyğun seçim.",
      pricingProShort: "Daha böyük portfelləri admin nəzarəti ilə idarə edən şirkətlər üçün.",
      singleDesc: "Faylları yüklə, mapping preview gör, sonra tam dashboard və hesabat paketini açmaq üçün ödə.",
      plusDesc: "Davamlı layihə nəzarəti və hesabat arxivi üçün ayda 5 layihə krediti.",
      proDesc: "Bir neçə aktiv tikinti sahəsi olan komandalar üçün ayda 20 layihə krediti.",
      singleCta: "Bir layihə yüklə",
      plusCta: "Plus başlat",
      proCta: "Pro başlat",
      pricingIncludes: "Nələr daxildir",
      compareSingle: "Single Project",
      comparePlus: "Plus",
      comparePro: "Pro",
      rowCredits: "Analiz kreditləri",
      rowCreditsSingle: "1 layihə",
      rowCreditsPlus: "5 / ay",
      rowCreditsPro: "20 / ay",
      rowCreditsPlusAnnual: "5 / ay",
      rowCreditsProAnnual: "20 / ay",
      rowPackages: "Bütün 4 nəzarət paketi",
      rowDashboard: "Paketə uyğun dashboard",
      rowExport: "PDF + Excel export",
      rowArchive: "Hesabat arxivi",
      rowUsage: "Kredit istifadəsi görünüşü",
      rowWorkspace: "Çox layihəli workspace",
      rowAdmin: "Admin istifadə izləməsi",
      pricingTrustSecure: "Təhlükəsiz checkout",
      pricingTrustCancel: "İstənilən vaxt ləğv",
      pricingTrustSetup: "Setup xərci yoxdur",
      pricingTrustIncluded: "Bütün paketlər daxildir",
      faqTitle: "Yükləmədən əvvəl suallar.",
      faqQ1: "Hansı faylları yükləməliyəm?",
      faqA1: "Seçilmiş paketə uyğun faylları yükləyin: qrafik, irəliləyiş, xərc, ödəniş, material və ya risk qeydləri.",
      faqQ2: "Single Project ödənişi necə işləyir?",
      faqA2: "Əvvəl faylları yükləyirsiniz, mapping preview baxırsınız, sonra Lemon Squeezy checkout ilə tam dashboard və hesabatları açırsınız.",
      faqQ3: "Plus və Pro nələri daxil edir?",
      faqA3: "Plus ayda 5 layihə krediti, Pro isə daha böyük komandalar üçün ayda 20 layihə krediti verir.",
      faqQ4: "Boş dashboard blokları görünəcək?",
      faqA4: "Xeyr. Nəticə yalnız yüklənmiş məlumatla dəstəklənən dashboard sahələrini göstərmək üçün hazırlanıb.",
      footerText: "Tikinti analitikası, layihə nəzarəti və hesabat platforması.",
      footerBadgeOne: "Layihə nəzarəti",
      footerBadgeTwo: "Hesabata hazır nəticələr",
      footerProduct: "Məhsul",
      footerCompany: "Şirkət",
      footerPlatform: "Platforma",
      footerLegal: "Hüquqi",
      footerPrivacy: "Məxfilik Siyasəti",
      footerTerms: "Xidmət Şərtləri",
      footerContact: "Əlaqə",
      footerContactText: "Məhsul, ödəniş və layihə qurulumu sualları üçün.",
      footerBottom: "Tikinti layihə komandaları üçün hazırlanıb."
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
    updateBillingDisplay(document.body.dataset.billingCycle || "monthly");
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

  function updateBillingDisplay(cycle) {
    const lang = document.documentElement.lang || "en";
    const dictionary = translations[lang] || translations.en;
    const selectedCycle = cycle === "annual" ? "annual" : "monthly";
    document.body.dataset.billingCycle = selectedCycle;

    $$("[data-billing]").forEach((button) => {
      const active = button.getAttribute("data-billing") === selectedCycle;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });

    const planValues = selectedCycle === "annual"
      ? { plus: "39", pro: "71" }
      : { plus: "49", pro: "89" };
    Object.entries(planValues).forEach(([plan, value]) => {
      const price = $(`[data-price-plan="${plan}"]`);
      if (price) price.textContent = value;
      const note = $(`[data-billing-note="${plan}"]`);
      if (note) note.textContent = selectedCycle === "annual" ? dictionary.priceAnnualBilledNote : dictionary.priceMonthlyNote;
    });

    const plusCredit = $('[data-credit-plan="plus"]');
    const proCredit = $('[data-credit-plan="pro"]');
    if (plusCredit) plusCredit.textContent = selectedCycle === "annual" ? dictionary.rowCreditsPlusAnnual : dictionary.rowCreditsPlus;
    if (proCredit) proCredit.textContent = selectedCycle === "annual" ? dictionary.rowCreditsProAnnual : dictionary.rowCreditsPro;
  }

  document.addEventListener("DOMContentLoaded", () => {
    window.setTimeout(() => {
      const loader = $("#db-loading-screen");
      if (loader) {
        loader.classList.add("hide");
        loader.setAttribute("aria-hidden", "true");
        window.setTimeout(() => loader.remove(), 800);
      }
    }, 2000);

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
    $$("[data-billing]").forEach((button) => button.addEventListener("click", () => {
      updateBillingDisplay(button.getAttribute("data-billing") || "monthly");
    }));
    updateBillingDisplay("monthly");

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
