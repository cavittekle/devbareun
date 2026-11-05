(function () {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const translations = {
    en: {
      fileSelectedToast: "Files selected. Sign in to run the delay analysis.",
      planSelectedToast: "Plan selected. Upload your schedule to continue.",
      loaderTitle: "Construction delay analysis",
      navPlatform: "How it works",
      navUpload: "Upload",
      navPricing: "Pricing",
      navDashboard: "Dashboard",
      navAbout: "About",
      navFAQ: "FAQ",
      navContact: "Contact",
      login: "Login",
      startAnalysis: "Start analysis",
      heroPrimary: "Start analysis",
      heroShowcasePill: "Construction project execution and delay analysis",
      heroShowcaseTitleOne: "See how late",
      heroShowcaseTitleTwo: "the project is,",
      heroShowcaseTitleThree: "and why.",
      heroShowcaseLead: "Upload the baseline schedule, actual progress and delay events. DevBareun calculates SPI, schedule delay in days, forecast completion, the critical path and who is responsible for each delay day, then prepares the execution report in PDF and Excel.",
      heroFlowUpload: "How far behind is the project?",
      heroFlowUploadText: "SPI 0.62, by earned schedule",
      heroFlowMap: "When will it finish?",
      heroFlowMapText: "98 days after the planned 15.12.2024",
      heroFlowDashboard: "Who is responsible for the delay?",
      heroFlowDashboardText: "92 days of recorded delay events",
      heroControlLabel: "Execution report",
      heroControlTitle: "Baku Business Center, sample data",
      heroReportBadge: "Example",
      heroCurvePlan: "Plan 57%",
      heroCurveActual: "Actual 35%",
      heroValueBehind: "67 days",
      heroValueFinish: "23.03.2025",
      heroSplitEmployer: "Employer",
      heroSplitContractor: "Contractor",
      heroSplitNeutral: "Neutral",
      heroSplitConcurrent: "Concurrent",
      heroReportLink: "Open the full example report",
      heroMetricPackagesValue: "Delay in days",
      heroMetricPackages: "Not only a percentage",
      heroMetricFormatsValue: "Critical path",
      heroMetricFormats: "Activities that move the finish",
      heroMetricReportsValue: "Responsibility",
      heroMetricReports: "Who caused each delay day",
      heroMetricLanguagesValue: "PDF and Excel",
      heroMetricLanguages: "Report in AZ and EN",
      workflowLabel: "How it works",
      workflowTitle: "From schedule and progress files to the execution report.",
      stepUploadTitle: "Upload",
      stepUploadText: "Upload the contract, the schedule (DevBareun Excel template, Primavera P6 XER or MS Project) and the F2 certificates of completed work.",
      stepMappingTitle: "Check the data",
      stepMappingText: "Activities, WBS sections, predecessors and delay events are read and checked. Missing dates or progress are listed before you rely on the result.",
      stepDashboardTitle: "Get the report",
      stepDashboardText: "Review the delay dashboard and download the execution and delay analysis report in Azerbaijani or English, as PDF and Excel.",
      uploadLabel: "Upload for delay analysis",
      uploadTitle: "One analysis, built from your schedule and progress.",
      uploadIntro: "Single Project users upload first, check the detected data and pay with Lemon Squeezy to unlock the full report. Plus and Pro users spend monthly project credits.",
      downloadTemplate: "Download Excel template",
      requiredFiles: "Required files",
      youReceive: "You will receive",
      dropTitle: "Drop schedule and progress files here, or browse",
      dropTypesLead: "Which files to upload",
      dropPlanTitle: "1. Schedule (plan and actual)",
      dropPlanFormats: "DevBareun Excel template, Excel/CSV, Primavera P6 (.xer), MS Project (.xml, .mpp), PDF",
      dropF2Title: "2. F2 certificates of completed work",
      dropF2Formats: "Excel or Word, one file per month",
      dropContractTitle: "3. Contract",
      dropContractFormats: "PDF, Word or photo",
      dropRequired: "Required",
      dropOptional: "Optional",
      browseFiles: "Choose files",
      detecting: "Checking selected files...",
      preparingDashboards: "Sign in to run the analysis on these files.",
      mappingTitle: "Detected file types",
      unlockDashboard: "Continue to analysis",
      dashboardLabel: "Example execution report",
      dashboardTitle: "Delay, forecast and responsibility on one page.",
      dashboardText: "The figures below come from the DevBareun example project. Your report uses the same layout with your own schedule, progress and delay events.",
      previewActual: "Actual",
      previewPlanned: "Plan",
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
      priceAnnualBilledNote: "mo, billed annually",
      pricingSingleShort: "One project's delay analysis with the full execution report.",
      pricingPlusShort: "Monthly execution reports for teams running several sites.",
      pricingProShort: "For companies tracking delay across a larger portfolio.",
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
      rowPackages: "Execution and delay analysis",
      rowDashboard: "Delay dashboard and S-curve",
      rowExport: "PDF + Excel report (AZ / EN)",
      rowArchive: "Report archive",
      rowUsage: "Credit usage visibility",
      rowWorkspace: "Multi-project workspace",
      rowAdmin: "Admin usage tracking",
      pricingTrustSecure: "Secure checkout",
      pricingTrustCancel: "Cancel anytime",
      pricingTrustSetup: "No setup fees",
      pricingTrustIncluded: "Full report in every plan",
      footerProduct: "Product",
      footerCompany: "Company",
      footerLegal: "Legal",
      footerPrivacy: "Privacy policy",
      footerTerms: "Terms of service",
      navSecurity: "Security",
      securityLabel: "Security and data handling",
      securityTitle: "Your project files stay private.",
      securityIntro: "How DevBareun stores, checks and opens the files you upload.",
      secStorageTitle: "Private storage",
      secStorageText: "Uploaded files are kept in a private storage bucket, never behind a public link. Access rules tie each file to the account and project it belongs to.",
      secLinksTitle: "Short-lived signed links",
      secLinksText: "Files are uploaded and read through signed links that expire after a short time, so a copied link soon stops working.",
      secChecksTitle: "File checks before analysis",
      secChecksText: "Only project file types are accepted and executable files are rejected. Each file's content is checked against its type before it is read.",
      secPaymentTitle: "Payments through Lemon Squeezy",
      secPaymentText: "Checkout runs on Lemon Squeezy. Your card details go to the payment provider and are never stored by DevBareun.",
      filesLabel: "Supported files",
      filesTitle: "Works with the schedules your team already keeps.",
      filesText: "Upload your planning exports as they are, or start from the DevBareun Excel template. Column headers in English, Azerbaijani, Turkish and Russian are recognised.",
      fileSchedule: "Baseline schedule with WBS and predecessors",
      fileF2: "Actual progress and forecast dates",
      fileCost: "Delay events, causes and responsible party",
      fileMaterial: "Monthly planned and actual progress",
      fileRisk: "Contract start, finish and data date",
      heroExample: "View example report",
      dashboardExampleCta: "Open the full example",
      previewProject: "Baku Business Center (example)",
      previewDataDate: "Data date",
      previewKpiProgress: "Actual progress",
      previewKpiProgressDelta: "−21.8 pts vs plan",
      previewKpiProgressNote: "Plan 57.1%",
      previewKpiSpi: "Schedule performance (SPI)",
      previewKpiSpiDelta: "38% below plan rate",
      previewKpiSpiNote: "Target 1.00",
      previewKpiDelay: "Schedule delay",
      previewKpiDelayValue: "67 days",
      previewKpiDelayDelta: "progress of 25.03.2024",
      previewKpiDelayNote: "Earned schedule vs data date",
      previewKpiForecast: "Forecast completion",
      previewKpiForecastDelta: "+98 days late",
      previewKpiForecastNote: "Contract finish 15.12.2024",
      previewCurveTitle: "Planned vs actual S-curve",
      previewCurveSub: "Cumulative progress, %",
      previewForecast: "Forecast",
      previewDelayTitle: "Monthly delay development",
      previewDelaySub: "Schedule delay at month end, days",
      previewDelayLegend: "Delay, days (2023-09 to 2024-05)",
      previewRespTitle: "Delay responsibility",
      previewRespSub: "Delay event days by party",
      partyContractor: "Contractor",
      partyEmployer: "Employer",
      partyConcurrent: "Concurrent",
      partyNeutral: "Neutral",
      previewDays59: "59 days",
      previewDays14: "14 days",
      previewDays12: "12 days",
      previewDays7: "7 days",
      previewRespTotal: "delay days recorded",
      previewRespSplit: "33 excusable · 14 compensable · 59 non-excusable",
      pkgDelayTitle: "Execution and delay analysis",
      reqBaseline: "Baseline schedule: planned start, finish, weight, predecessors",
      reqActual: "Actual progress at the data date: actual dates and % complete",
      reqEvents: "Delay events with cause and responsible party (recommended)",
      reqMonthly: "Monthly planned and actual cumulative % (optional)",
      outKpis: "Progress, SPI, schedule delay and forecast completion",
      outCurve: "S-curve and monthly delay development",
      outCritical: "Critical path, total float and most delayed activities",
      outResp: "Delay responsibility: employer, contractor, neutral, concurrent",
      outReport: "Findings, recommended actions and PDF / Excel report",
      fileKindTemplate: "DevBareun delay template",
      fileKindXer: "Primavera P6 schedule",
      fileKindXml: "MS Project schedule",
      fileKindTable: "Plan / actual table",
      fileKindOther: "Not readable for delay analysis",
      fmtTemplate: "DevBareun template"
    },
    az: {
      fileSelectedToast: "Fayllar seçildi. Gecikmə analizi üçün daxil olun.",
      planSelectedToast: "Plan seçildi. Davam etmək üçün qrafikinizi yükləyin.",
      loaderTitle: "Tikinti gecikmə analizi",
      navPlatform: "Necə işləyir",
      navUpload: "Yükləmə",
      navPricing: "Qiymət",
      navDashboard: "Dashboard",
      navAbout: "Haqqında",
      navFAQ: "FAQ",
      navContact: "Əlaqə",
      login: "Giriş",
      startAnalysis: "Analizə başla",
      heroPrimary: "Analizə başla",
      heroShowcasePill: "Tikinti layihəsinin icra və gecikmə analizi",
      heroShowcaseTitleOne: "Layihə nə qədər",
      heroShowcaseTitleTwo: "gecikir və",
      heroShowcaseTitleThree: "niyə?",
      heroShowcaseLead: "Baza qrafikini, faktiki icranı və gecikmə hadisələrini yükləyin. DevBareun SPI-ni, gün ilə qrafik gecikməsini, proqnoz bitmə tarixini, kritik yolu və hər gecikmə gününə kimin məsuliyyət daşıdığını hesablayır, sonra icra hesabatını PDF və Excel formatında hazırlayır.",
      heroFlowUpload: "Layihə plandan nə qədər geridədir?",
      heroFlowUploadText: "SPI 0.62, qazanılmış qrafik üzrə",
      heroFlowMap: "Layihə nə vaxt bitəcək?",
      heroFlowMapText: "Plan üzrə 15.12.2024-dən 98 gün sonra",
      heroFlowDashboard: "Gecikməyə kim cavabdehdir?",
      heroFlowDashboardText: "Qeydə alınmış 92 günlük gecikmə hadisəsi",
      heroControlLabel: "İcra hesabatı",
      heroControlTitle: "Baku Business Center, nümunə məlumat",
      heroReportBadge: "Nümunə",
      heroCurvePlan: "Plan 57%",
      heroCurveActual: "Faktiki 35%",
      heroValueBehind: "67 gün",
      heroValueFinish: "23.03.2025",
      heroSplitEmployer: "Sifarişçi",
      heroSplitContractor: "Podratçı",
      heroSplitNeutral: "Neytral",
      heroSplitConcurrent: "Eyni vaxtlı",
      heroReportLink: "Tam nümunə hesabata bax",
      heroMetricPackagesValue: "Gün ilə gecikmə",
      heroMetricPackages: "Yalnız faiz yox",
      heroMetricFormatsValue: "Kritik yol",
      heroMetricFormats: "Bitmə tarixini dəyişən işlər",
      heroMetricReportsValue: "Məsuliyyət",
      heroMetricReports: "Hər gecikmə gününə kim cavabdehdir",
      heroMetricLanguagesValue: "PDF və Excel",
      heroMetricLanguages: "AZ və EN hesabat",
      workflowLabel: "Necə işləyir",
      workflowTitle: "Qrafik və icra fayllarından icra hesabatına.",
      stepUploadTitle: "Yüklə",
      stepUploadText: "Müqaviləni, iş qrafikini (DevBareun Excel şablonu, Primavera P6 XER və ya MS Project) və görülmüş işlərin F2 aktlarını yükləyin.",
      stepMappingTitle: "Məlumatı yoxla",
      stepMappingText: "İşlər, WBS bölmələri, əlaqələr və gecikmə hadisələri oxunur və yoxlanılır. Çatışmayan tarixlər və ya icra faizləri nəticədən əvvəl göstərilir.",
      stepDashboardTitle: "Hesabatı al",
      stepDashboardText: "Gecikmə dashboarduna baxın və icra və gecikmə analizi hesabatını Azərbaycan və ya ingilis dilində, PDF və Excel formatında yükləyin.",
      uploadLabel: "Gecikmə analizi üçün yükləmə",
      uploadTitle: "Bir analiz, sizin qrafik və icra məlumatlarınızdan.",
      uploadIntro: "Single Project istifadəçiləri əvvəl yükləyir, tapılan məlumatı yoxlayır və tam hesabatı açmaq üçün Lemon Squeezy ilə ödəniş edir. Plus və Pro istifadəçiləri aylıq layihə kreditlərindən istifadə edir.",
      downloadTemplate: "Excel şablonunu yüklə",
      requiredFiles: "Lazımi fayllar",
      youReceive: "Alacağınız nəticə",
      dropTitle: "Qrafik və icra fayllarını bura atın və ya seçin",
      dropTypesLead: "Hansı faylları yükləməli",
      dropPlanTitle: "1. İş qrafiki (plan və faktiki icra)",
      dropPlanFormats: "DevBareun Excel şablonu, Excel/CSV, Primavera P6 (.xer), MS Project (.xml, .mpp), PDF",
      dropF2Title: "2. Görülmüş işlərin F2 aktları",
      dropF2Formats: "Excel və ya Word, hər ay üçün bir fayl",
      dropContractTitle: "3. Müqavilə",
      dropContractFormats: "PDF, Word və ya şəkil",
      dropRequired: "Tələb olunur",
      dropOptional: "İstəyə bağlı",
      browseFiles: "Fayl seç",
      detecting: "Seçilmiş fayllar yoxlanılır...",
      preparingDashboards: "Bu fayllar üzrə analizi işə salmaq üçün daxil olun.",
      mappingTitle: "Tapılan fayl növləri",
      unlockDashboard: "Analizə keç",
      dashboardLabel: "Nümunə icra hesabatı",
      dashboardTitle: "Gecikmə, proqnoz və məsuliyyət bir səhifədə.",
      dashboardText: "Aşağıdakı rəqəmlər DevBareun nümunə layihəsindəndir. Sizin hesabatınız eyni quruluşda, öz qrafikiniz, icranız və gecikmə hadisələrinizlə hazırlanır.",
      previewActual: "Faktiki",
      previewPlanned: "Plan",
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
      priceAnnualBilledNote: "ay, illik ödənilir",
      pricingSingleShort: "Tam icra hesabatı ilə bir layihənin gecikmə analizi.",
      pricingPlusShort: "Bir neçə obyekti idarə edən komandalar üçün aylıq icra hesabatları.",
      pricingProShort: "Böyük portfeldə gecikməni izləyən şirkətlər üçün.",
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
      rowPackages: "İcra və gecikmə analizi",
      rowDashboard: "Gecikmə dashboardu və S-əyrisi",
      rowExport: "PDF + Excel hesabat (AZ / EN)",
      rowArchive: "Hesabat arxivi",
      rowUsage: "Kredit istifadəsi görünüşü",
      rowWorkspace: "Çox layihəli workspace",
      rowAdmin: "Admin istifadə izləməsi",
      pricingTrustSecure: "Təhlükəsiz checkout",
      pricingTrustCancel: "İstənilən vaxt ləğv",
      pricingTrustSetup: "Setup xərci yoxdur",
      pricingTrustIncluded: "Hər planda tam hesabat",
      footerProduct: "Məhsul",
      footerCompany: "Şirkət",
      footerLegal: "Hüquqi",
      footerPrivacy: "Məxfilik Siyasəti",
      footerTerms: "Xidmət Şərtləri",
      navSecurity: "Təhlükəsizlik",
      securityLabel: "Təhlükəsizlik və məlumatların qorunması",
      securityTitle: "Layihə fayllarınız məxfi qalır.",
      securityIntro: "DevBareun yüklədiyiniz faylları necə saxlayır, yoxlayır və açır.",
      secStorageTitle: "Qapalı yaddaş",
      secStorageText: "Yüklənən fayllar ictimai keçiddə deyil, qapalı yaddaş bölməsində saxlanılır. Giriş qaydaları hər faylı aid olduğu hesaba və layihəyə bağlayır.",
      secLinksTitle: "Qısamüddətli imzalı keçidlər",
      secLinksText: "Fayllar qısa müddətdən sonra etibarsız olan imzalı keçidlərlə yüklənir və oxunur, buna görə kopyalanmış keçid tezliklə işləməz olur.",
      secChecksTitle: "Analizdən əvvəl fayl yoxlaması",
      secChecksText: "Yalnız layihə fayl növləri qəbul edilir, icra olunan fayllar rədd edilir. Hər faylın məzmunu oxunmazdan əvvəl öz növünə uyğunluğu yoxlanılır.",
      secPaymentTitle: "Ödənişlər Lemon Squeezy ilə",
      secPaymentText: "Ödəniş Lemon Squeezy üzərindən aparılır. Kart məlumatlarınız ödəniş provayderinə ötürülür və DevBareun tərəfindən saxlanılmır.",
      filesLabel: "Dəstəklənən fayllar",
      filesTitle: "Komandanızın artıq istifadə etdiyi qrafiklərlə işləyir.",
      filesText: "Planlama fayllarınızı olduğu kimi yükləyin və ya DevBareun Excel şablonundan başlayın. İngilis, Azərbaycan, türk və rus dillərində sütun başlıqları tanınır.",
      fileSchedule: "WBS və əlaqələri olan baza qrafiki",
      fileF2: "Faktiki icra və proqnoz tarixləri",
      fileCost: "Gecikmə hadisələri, səbəblər və məsul tərəf",
      fileMaterial: "Aylıq plan və faktiki icra",
      fileRisk: "Müqavilə başlanğıcı, bitməsi və hesabat tarixi",
      heroExample: "Nümunə hesabata bax",
      dashboardExampleCta: "Tam nümunəni aç",
      previewProject: "Baku Business Center (nümunə)",
      previewDataDate: "Hesabat tarixi",
      previewKpiProgress: "Faktiki icra",
      previewKpiProgressDelta: "plandan −21.8 bənd",
      previewKpiProgressNote: "Plan 57.1%",
      previewKpiSpi: "Qrafik icra göstəricisi (SPI)",
      previewKpiSpiDelta: "plan tempindən 38% aşağı",
      previewKpiSpiNote: "Hədəf 1.00",
      previewKpiDelay: "Qrafik gecikməsi",
      previewKpiDelayValue: "67 gün",
      previewKpiDelayDelta: "25.03.2024 səviyyəsində",
      previewKpiDelayNote: "Qazanılmış qrafik və hesabat tarixi",
      previewKpiForecast: "Proqnoz bitmə tarixi",
      previewKpiForecastDelta: "+98 gün gecikmə",
      previewKpiForecastNote: "Müqavilə üzrə bitmə 15.12.2024",
      previewCurveTitle: "Plan və faktiki S-əyrisi",
      previewCurveSub: "Kumulyativ icra, %",
      previewForecast: "Proqnoz",
      previewDelayTitle: "Aylıq gecikmə dinamikası",
      previewDelaySub: "Ay sonuna qrafik gecikməsi, gün",
      previewDelayLegend: "Gecikmə, gün (2023-09 – 2024-05)",
      previewRespTitle: "Gecikmə məsuliyyəti",
      previewRespSub: "Tərəflər üzrə gecikmə günləri",
      partyContractor: "Podratçı",
      partyEmployer: "Sifarişçi",
      partyConcurrent: "Eyni vaxtlı",
      partyNeutral: "Neytral",
      previewDays59: "59 gün",
      previewDays14: "14 gün",
      previewDays12: "12 gün",
      previewDays7: "7 gün",
      previewRespTotal: "qeydə alınmış gecikmə günü",
      previewRespSplit: "33 üzrlü · 14 kompensasiyalı · 59 üzrsüz",
      pkgDelayTitle: "İcra və gecikmə analizi",
      reqBaseline: "Baza qrafiki: plan başlanğıc, bitmə, çəki, əvvəlki işlər",
      reqActual: "Hesabat tarixinə faktiki icra: faktiki tarixlər və icra faizi",
      reqEvents: "Səbəbi və məsul tərəfi göstərilmiş gecikmə hadisələri (tövsiyə olunur)",
      reqMonthly: "Aylıq plan və faktiki kumulyativ % (istəyə bağlı)",
      outKpis: "İcra faizi, SPI, qrafik gecikməsi və proqnoz bitmə tarixi",
      outCurve: "S-əyrisi və aylıq gecikmə dinamikası",
      outCritical: "Kritik yol, ümumi ehtiyat vaxt və ən çox gecikən işlər",
      outResp: "Gecikmə məsuliyyəti: sifarişçi, podratçı, neytral, eyni vaxtlı",
      outReport: "Nəticələr, tövsiyə olunan tədbirlər və PDF / Excel hesabat",
      fileKindTemplate: "DevBareun gecikmə şablonu",
      fileKindXer: "Primavera P6 qrafiki",
      fileKindXml: "MS Project qrafiki",
      fileKindTable: "Plan / fakt cədvəli",
      fileKindOther: "Gecikmə analizi üçün oxunmur",
      fmtTemplate: "DevBareun şablonu"
    }
  };

  const READABLE_EXTENSIONS = [".xlsx", ".xlsm", ".xls", ".csv", ".xer", ".xml"];

  function t(key) {
    const lang = document.documentElement.lang || "en";
    return (translations[lang] || translations.en)[key] || translations.en[key] || key;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  }

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

  function classifyFile(name) {
    const lower = name.toLowerCase();
    const dot = lower.lastIndexOf(".");
    const ext = dot >= 0 ? lower.slice(dot) : "";
    if (!READABLE_EXTENSIONS.includes(ext)) return "fileKindOther";
    if (ext === ".xer") return "fileKindXer";
    if (ext === ".xml") return "fileKindXml";
    if (lower.includes("delay-analysis-template") || lower.includes("gecikm")) return "fileKindTemplate";
    return "fileKindTable";
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
      const name = escapeHtml(file.name);
      row.innerHTML = `<div><strong title="${name}">${name}</strong><span>${escapeHtml(t(classifyFile(file.name)))} · ${formatSize(file.size || 0)}</span></div>`;
      list.appendChild(row);
    });
    if (!files.length) {
      status.hidden = true;
      preview.hidden = true;
      return;
    }
    const kinds = Array.from(new Set(files.map((file) => classifyFile(file.name))));
    status.hidden = false;
    preview.hidden = false;
    chips.innerHTML = kinds.map((kind) => `<span>${kind === "fileKindOther" ? "!" : "✓"} ${escapeHtml(t(kind))}</span>`).join("");
    rows.innerHTML = files.map((file) => `<div class="mapping-row"><span>${escapeHtml(file.name)}</span><strong>${escapeHtml(t(classifyFile(file.name)))}</strong></div>`).join("");
    toast(t("fileSelectedToast"));
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
    const loader = $("#db-loading-screen");
    if (loader) {
      loader.classList.add("hide");
      loader.setAttribute("aria-hidden", "true");
      window.setTimeout(() => loader.remove(), 800);
    }

    applyLanguage(localStorage.getItem("devbareun_lang") || "en");
    applyTheme();

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
      toast(t("planSelectedToast"));
    }));
  });
})();
