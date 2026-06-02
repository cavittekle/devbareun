/* DevBareun v1.3.9 landing SaaS hotfix */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const SESSION_KEY = "devbareun_session";
  const SELECTED_PLAN_KEY = "devbareun_selected_plan";

  const dict = {
    en: {
      previewStoryKicker: "Project-control analytics",
      previewStoryTitle: "Turn project data into decisions before delays grow.",
      previewStoryText: "DevBareun brings schedule, cost and risk signals into one reliable view for faster reporting and clearer action.",
      previewStoryTag1: "Plan vs actual",
      previewStoryTag2: "Cost visibility",
      previewStoryTag3: "Risk control",
      previewCapability1Title: "Unified control",
      previewCapability1Text: "See schedule progress, cost movement and key risks in one management-ready view.",
      previewCapability2Title: "Early warning",
      previewCapability2Text: "Identify variance and delay signals before they become expensive project issues.",
      previewCapability3Title: "Report-ready output",
      previewCapability3Text: "Convert project files into structured dashboards and exportable reports.",
      headerTagline: "CONSTRUCTION ANALYTICS",
      navFeatures: "Features",
      headerCta: "Start with 1 project",
      selectedHeroEyebrow: "CONSTRUCTION ANALYTICS PLATFORM",
      selectedHeroLine1: "Control your projects",
      selectedHeroLine2: "with reliable data,",
      selectedHeroLine3: "clarify the outcome.",
      selectedHeroLead: "Complete your projects on time and within budget with real-time indicators, planned vs actual analysis, cost control and risk management.",
      selectedHeroUpload: "Upload report and analyze",
      selectedTrustRealtime: "Real-time data",
      selectedTrustMetrics: "Reliable indicators",
      selectedTrustSecure: "Controlled workflow",
      selectedPartnersTitle: "TRUSTED PARTNERS",
      selectedStatProjects: "Active projects",
      selectedStatBudget: "Managed budget",
      selectedStatArea: "Construction area",
      selectedStatSatisfaction: "Client satisfaction",
      selectedDashTitle: "Project Panel",
      selectedExport: "Export",
      selectedKpiProgress: "Overall progress",
      selectedKpiSpi: "Schedule Performance (SPI)",
      selectedKpiCpi: "Cost Performance (CPI)",
      selectedKpiCost: "Total Cost",
      selectedProgressChart: "Progress Analysis",
      selectedCostChart: "Cost Analysis",
      selectedCostCategories: "Cost Categories",
      selectedRiskIndicators: "Risk Indicators",
      selectedControlSummary: "Project Control Summary",
      selectedActual: "Actual",
      selectedPlan: "Plan",
      selectedTotal: "Total",
      selectedScheduleRisk: "Schedule risk",
      selectedFinancialRisk: "Financial risk",
      selectedSupplyRisk: "Supply risk",
      selectedHigh: "High",
      selectedMedium: "Medium",
      selectedLow: "Low",
      selectedDelayedWorks: "Delayed works",
      selectedCriticalTasks: "Critical path tasks",
      selectedIssueAreas: "Issue areas",
      selectedOpenRisks: "Open risks",
      navLogin: "Login",
      navCreateAccount: "Create account",
      navWorkspace: "Workspace",
      navReports: "Reports",
      navBilling: "Billing",
      heroPackages: "View packages",
      heroLogin: "Login",
      heroDashboard: "Open workspace",
      loginCardBadge: "Workspace login",
      loginCardTitle: "Access your workspace",
      loginCardText: "Login to upload project files, generate dashboards and view your saved reports.",
      loginEmailLabel: "Email",
      loginPasswordLabel: "Password",
      loginPlanLabel: "Package",
      loginSubmit: "Login to workspace",
      loginCreateText: "New to DevBareun? Create account",
      loginForgotText: "Forgot password?",
      workspaceCardBadge: "Workspace active",
      workspaceCardTitle: "Continue from your workspace",
      pkgSingleName: "Single Project",
      pkgSingleShort: "one paid analysis",
      pkgPlusName: "Plus",
      pkgPlusShort: "5 projects / month",
      pkgProName: "Pro",
      pkgProShort: "20 projects / month",
      accessKicker: "SaaS access flow",
      accessTitle: "Buy one project without an account, or log in for a recurring workspace package.",
      accessText: "Single Project is a one-time guest checkout. Plus and Pro connect projects, payments, reports, credit usage and activity records to a workspace account.",
      accessGuestTitle: "Start with an account",
      accessGuestText: "Create a workspace before payment so your project results and exports are saved.",
      accessAuthTitle: "Workspace active",
      currentPlan: "Current plan",
      creditsLeft: "Credits",
      flowAccountTitle: "Choose access",
      flowAccountText: "Single Project needs no account. Plus and Pro include workspace history.",
      flowPaymentTitle: "Payment package",
      flowPaymentText: "Single Project, Plus or Pro package with credit usage tracking.",
      flowUploadTitle: "Upload & dashboard",
      flowUploadText: "Upload construction files and generate the selected control dashboard.",
      flowArchiveTitle: "Report archive",
      flowArchiveText: "Saved reports, A4/A3 print output, PDF and Excel export history.",
      pricingKicker: "Payment packages",
      pricingTitle: "Choose how many project analyses you need.",
      pricingText: "Packages connect to checkout, credits, report archive, PDF/Excel export and admin usage tracking.",
      pkgSingleType: "One-time",
      pkgSingleBadge: "No subscription",
      pkgSingleUnit: "project analysis",
      pkgSinglePricePeriod: "one-time / project",
      pkgSingleDesc: "No account needed: one project upload, one dashboard, A4/A3 print and PDF/Excel export.",
      pkgMonthlyType: "Monthly",
      pkgPopularBadge: "Recommended",
      pkgPlusUnit: "projects / month",
      pkgPlusDesc: "For small teams that need repeated project checks, report archive and workspace history.",
      pkgProBadge: "Higher volume",
      pkgProUnit: "projects / month",
      pkgProDesc: "For companies running multiple active sites with stronger reporting and usage control needs.",
      pkgMonthlyPricePeriod: "/ month",
      pkgQuotePrice: "Contact us",
      pkgQuotePeriod: "pricing",
      pkgFeatureUpload: "Project file upload",
      pkgFeatureDashboard: "Package-specific dashboard",
      pkgFeatureExports: "PDF / Excel / A4 / A3 outputs",
      pkgPlusFeature1: "5 monthly analysis credits",
      pkgPlusFeature2: "Projects and reports archive",
      pkgPlusFeature3: "Credit usage visibility",
      pkgProFeature1: "20 monthly analysis credits",
      pkgProFeature2: "Multi-project workflow readiness",
      pkgProFeature3: "Admin panel usage tracking",
      pkgSingleCta: "Upload one project",
      pkgPlusCta: "Start Plus",
      pkgProCta: "Start Pro",
      paymentNote: "Single Project is $29 once. Plus is $49/month for 5 analyses. Pro is $89/month for 20 analyses.",
      singleEntryBadge: "Single Project selected",
      singleEntryTitle: "Upload first. Pay only to unlock the completed analysis.",
      singleEntryText: "No account required. One-time price: $29 for one project dashboard and report package.",
      singleEntryChange: "View packages"
    },
    az: {
      previewStoryKicker: "LAYIHE NEZARETI ANALITIKASI",
      previewStoryTitle: "Gecikmeler boyumeden layihe melumatini qerara cevirin.",
      previewStoryText: "DevBareun qrafik, xerc ve risk siqnallarini daha suretli hesabat ve aydin addimlar ucun vahid etibarli gorunusde birlesdirir.",
      previewStoryTag1: "Plan ve fakt",
      previewStoryTag2: "Xerc gorunurluyu",
      previewStoryTag3: "Risk nezareti",
      previewCapability1Title: "Vahid nezaret",
      previewCapability1Text: "Qrafik irelileyisini, xerc deyisimini ve esas riskleri tek idareetme gorunusunde izleyin.",
      previewCapability2Title: "Erken xeberdarliq",
      previewCapability2Text: "Ferq ve gecikme siqnallarini bahali layihe problemlerine cevrilmeden once gorun.",
      previewCapability3Title: "Hazir hesabatlar",
      previewCapability3Text: "Layihe fayllarini struktur dashboardlara ve ixrac oluna bilen hesabatlara cevirin.",
      headerTagline: "İNŞAAT ANALİTİĞİ",
      navFeatures: "İmkanlar",
      headerCta: "1 layihə ilə başla",
      selectedHeroEyebrow: "İNŞAAT ANALİTİKASI PLATFORMASI",
      selectedHeroLine1: "Layihələrinizə",
      selectedHeroLine2: "məlumatla nəzarət edin,",
      selectedHeroLine3: "nəticəni dəqiqləşdirin.",
      selectedHeroLead: "Real vaxtda göstəricilər, plan-fakt analizi, maliyyət nəzarəti və risklərin idarə olunması ilə layihələrinizi vaxtında və büdcəyə uyğun tamamlayın.",
      selectedHeroUpload: "Hesabat yüklə və analiz et",
      selectedTrustRealtime: "Real vaxtda məlumat",
      selectedTrustMetrics: "Etibarlı göstəricilər",
      selectedTrustSecure: "Nəzarətli iş axını",
      selectedPartnersTitle: "ETİBAR EDƏN TƏRƏFDAŞLAR",
      selectedStatProjects: "Aktiv layihə",
      selectedStatBudget: "İdarə olunan büdcə",
      selectedStatArea: "Tikinti sahəsi",
      selectedStatSatisfaction: "Müştəri məmnuniyyəti",
      selectedDashTitle: "Layihə Paneli",
      selectedExport: "İxrac et",
      selectedKpiProgress: "Ümumi irəliləyiş",
      selectedKpiSpi: "Vaxt Performansı (SPI)",
      selectedKpiCpi: "Xərc Performansı (CPI)",
      selectedKpiCost: "Ümumi Xərc",
      selectedProgressChart: "İrəliləyiş Analizi",
      selectedCostChart: "Maliyyət Analizi",
      selectedCostCategories: "Xərc Kateqoriyaları",
      selectedRiskIndicators: "Risk Göstəriciləri",
      selectedControlSummary: "Layihə Nəzarət Xülasəsi",
      selectedActual: "Fakt",
      selectedPlan: "Plan",
      selectedTotal: "Ümumi",
      selectedScheduleRisk: "Cədvəl riski",
      selectedFinancialRisk: "Maliyyə riski",
      selectedSupplyRisk: "Təchizat riski",
      selectedHigh: "Yüksək",
      selectedMedium: "Orta",
      selectedLow: "Aşağı",
      selectedDelayedWorks: "Gecikdirilən işlər",
      selectedCriticalTasks: "Kritik yol tapşırıqları",
      selectedIssueAreas: "Problemli sahələr",
      selectedOpenRisks: "Açıq risklər",
      navLogin: "Giriş",
      navCreateAccount: "Hesab yarat",
      navWorkspace: "Workspace",
      navReports: "Hesabatlar",
      navBilling: "Ödənişlər",
      heroPackages: "Paketlərə bax",
      heroLogin: "Giriş",
      heroDashboard: "Workspace aç",
      loginCardBadge: "Workspace girişi",
      loginCardTitle: "Workspace-ə daxil ol",
      loginCardText: "Layihə fayllarını yükləmək, dashboard yaratmaq və saxlanılmış hesabatlara baxmaq üçün giriş et.",
      loginEmailLabel: "Email",
      loginPasswordLabel: "Şifrə",
      loginPlanLabel: "Paket",
      loginSubmit: "Workspace-ə giriş",
      loginCreateText: "DevBareun-da yenisən? Hesab yarat",
      loginForgotText: "Şifrəni unutdun?",
      workspaceCardBadge: "Workspace aktivdir",
      workspaceCardTitle: "Workspace-dən davam et",
      pkgSingleName: "Tək layihə",
      pkgSingleShort: "bir ödənişli analiz",
      pkgPlusName: "Plus",
      pkgPlusShort: "aylıq 5 layihə",
      pkgProName: "Pro",
      pkgProShort: "aylıq 20 layihə",
      accessKicker: "SaaS giriş axını",
      accessTitle: "Bir layihəni hesabsız al, davamlı iş üçün workspace paketinə giriş et.",
      accessText: "Tək layihə birdəfəlik qonaq checkout-dur. Plus və Pro isə layihələri, ödənişləri, hesabatları və kredit istifadəsini workspace hesabına bağlayır.",
      accessGuestTitle: "Hesabla başla",
      accessGuestText: "Ödənişdən əvvəl workspace yarat ki, layihə nəticələrin və export faylların saxlanılsın.",
      accessAuthTitle: "Workspace aktivdir",
      currentPlan: "Cari paket",
      creditsLeft: "Kredit",
      flowAccountTitle: "Giriş növünü seç",
      flowAccountText: "Tək layihə üçün hesab lazım deyil. Plus və Pro workspace tarixçəsi yaradır.",
      flowPaymentTitle: "Ödəniş paketi",
      flowPaymentText: "Tək layihə, Plus və ya Pro paketi; kredit istifadəsi izlənir.",
      flowUploadTitle: "Yükləmə və dashboard",
      flowUploadText: "Tikinti fayllarını yüklə və seçilmiş nəzarət dashboardunu yarat.",
      flowArchiveTitle: "Hesabat arxivi",
      flowArchiveText: "Saxlanılmış hesabatlar, A4/A3 çap, PDF və Excel export tarixçəsi.",
      pricingKicker: "Ödəniş paketləri",
      pricingTitle: "Neçə layihə analizi lazım olduğunu seç.",
      pricingText: "Paketlər checkout, kredit, hesabat arxivi, PDF/Excel export və admin istifadə izlənməsi ilə birləşir.",
      pkgSingleType: "Birdəfəlik",
      pkgSingleBadge: "Abunəlik yoxdur",
      pkgSingleUnit: "layihə analizi",
      pkgSinglePricePeriod: "birdəfəlik / layihə",
      pkgSingleDesc: "Hesab lazım deyil: bir layihə yükləməsi, bir dashboard, A4/A3 çap və PDF/Excel export.",
      pkgMonthlyType: "Aylıq",
      pkgPopularBadge: "Tövsiyə olunur",
      pkgPlusUnit: "layihə / ay",
      pkgPlusDesc: "Təkrar layihə yoxlaması, hesabat arxivi və workspace tarixçəsi lazım olan kiçik komandalar üçün.",
      pkgProBadge: "Daha yüksək həcm",
      pkgProUnit: "layihə / ay",
      pkgProDesc: "Bir neçə aktiv sahəni idarə edən və daha güclü hesabat/istifadə nəzarəti istəyən şirkətlər üçün.",
      pkgQuotePrice: "Əlaqə saxlayın",
      pkgQuotePeriod: "qiymətləndirmə",
      pkgFeatureUpload: "Layihə faylı yükləmə",
      pkgFeatureDashboard: "Paketə uyğun dashboard",
      pkgFeatureExports: "PDF / Excel / A4 / A3 çıxışları",
      pkgPlusFeature1: "Aylıq 5 analiz krediti",
      pkgPlusFeature2: "Layihə və hesabat arxivi",
      pkgPlusFeature3: "Kredit istifadəsinə nəzarət",
      pkgProFeature1: "Aylıq 20 analiz krediti",
      pkgProFeature2: "Çoxlayihəli iş axınına hazır baza",
      pkgProFeature3: "Admin paneldə istifadə izlənməsi",
      pkgSingleCta: "Tək layihə yüklə",
      pkgPlusCta: "Plus başlat",
      pkgProCta: "Pro başlat",
      paymentNote: "Tək layihə birdəfəlik $29-dur: əvvəl faylı yüklə, analizi açmaq üçün ödə. Plus və Pro workspace qiyməti üçün əlaqə saxlayın.",
      singleEntryBadge: "Tək layihə seçildi",
      singleEntryTitle: "Əvvəl faylı yüklə. Hazır analizi açmaq üçün sonra ödə.",
      singleEntryText: "Hesab tələb olunmur. Birdəfəlik qiymət: bir layihə dashboardu və hesabat paketi üçün $29.",
      singleEntryChange: "Paketlərə bax"
    }
  };

  function getLang() {
    return localStorage.getItem("devbareun_lang") || document.documentElement.lang || "en";
  }

  function applyLandingLang() {
    const lang = getLang() === "az" ? "az" : "en";
    dict.az.pkgMonthlyPricePeriod = "/ ay";
    dict.az.paymentNote = "T\u0259k layih\u0259 $29 bird\u0259f\u0259likdir. Plus 5 analiz \u00fc\u00e7\u00fcn $49/ay, Pro 20 analiz \u00fc\u00e7\u00fcn $89/ayd\u0131r.";
    $$('[data-i18n-landing]').forEach((el) => {
      const key = el.getAttribute('data-i18n-landing');
      if (dict[lang][key]) el.textContent = dict[lang][key];
    });
  }

  function getSession() {
    try { return JSON.parse(localStorage.getItem(SESSION_KEY) || "null"); }
    catch { return null; }
  }

  function selectedPlanFromUrl() {
    const params = new URLSearchParams(location.search);
    return params.get("plan") || localStorage.getItem(SELECTED_PLAN_KEY) || "plus";
  }

  function markSelectedPlan(plan) {
    $$('[data-plan-card]').forEach((card) => {
      const selected = card.getAttribute('data-plan-card') === plan;
      card.classList.toggle('is-selected', selected);
      card.setAttribute('aria-checked', String(selected));
    });
  }

  function showSingleUploadEntry() {
    const entry = $('[data-single-upload-entry]');
    if (entry) entry.hidden = false;
  }

  function startSingleUpload() {
    showSingleUploadEntry();
    const target = $('#upload');
    if (!target) return;
    history.replaceState(null, "", `${location.pathname}${location.search}#upload`);
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function bindLandingPlanButtons() {
    document.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-landing-plan]');
      const card = event.target.closest('[data-plan-card]');
      if (!btn && card) {
        const chosen = card.getAttribute('data-plan-card') || 'plus';
        localStorage.setItem(SELECTED_PLAN_KEY, chosen);
        markSelectedPlan(chosen);
        return;
      }
      if (!btn) return;
      event.preventDefault();
      const plan = btn.getAttribute('data-landing-plan') || 'plus';
      localStorage.setItem(SELECTED_PLAN_KEY, plan);
      markSelectedPlan(plan);
      const billingPath = `/billing.html?plan=${encodeURIComponent(plan)}`;
      const session = getSession();
      if (plan === "single") {
        startSingleUpload();
        return;
      }
      if (session?.access_token) {
        location.href = billingPath;
      } else {
        location.href = `/register.html?plan=${encodeURIComponent(plan)}&next=${encodeURIComponent(billingPath)}`;
      }
    });
    $$('[data-plan-card]').forEach((card) => {
      card.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        const plan = card.getAttribute('data-plan-card') || 'plus';
        localStorage.setItem(SELECTED_PLAN_KEY, plan);
        markSelectedPlan(plan);
      });
    });
  }

  function rewriteAuthLinksWithPlan() {
    const plan = selectedPlanFromUrl();
    $$('a[href^="register.html"]').forEach((link) => {
      const url = new URL(link.getAttribute('href'), location.origin);
      if (!url.searchParams.get('plan')) url.searchParams.set('plan', plan);
      if (!url.searchParams.get('next')) url.searchParams.set('next', `/billing.html?plan=${encodeURIComponent(plan)}`);
      link.setAttribute('href', url.pathname.replace(/^\//, '') + url.search);
    });
    $$('a[href^="login.html"]').forEach((link) => {
      const url = new URL(link.getAttribute('href'), location.origin);
      if (!url.searchParams.get('next')) url.searchParams.set('next', '/dashboard.html');
      link.setAttribute('href', url.pathname.replace(/^\//, '') + url.search);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    applyLandingLang();
    bindLandingPlanButtons();
    rewriteAuthLinksWithPlan();
    markSelectedPlan(selectedPlanFromUrl());
    if (location.hash === "#upload" && selectedPlanFromUrl() === "single") showSingleUploadEntry();
    $('[data-single-entry-change]')?.addEventListener("click", () => {
      location.hash = "pricing";
    });
  });

  document.addEventListener('devbareun:lang', applyLandingLang);
})();
