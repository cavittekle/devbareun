// DevBareun guided upload flow — analysis type + optional templates + confirmed mapping before dashboard generation
// v1.0.7: full dynamic EN/TR -> AZ language audit for upload and mapping UI
(function () {
  const API = window.DevBareunAPI;
  let isRunning = false;
  let selectedAnalysisType = "all";
  let lastProjectId = null;
  let lastPreflight = null;
  let flowStage = "idle"; // idle | mapping-ready

  const analysisMeta = {
    en: {
      all: {
        title: "Full Project Control",
        text: "Complete project-control package combining Schedule Recovery, Cost & Payment Control, Material Continuity, Risk & Decisions and PDF/Excel reporting.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "schedule, workforce, cost, progress payment, material continuity, risk and management reporting",
        reqTitle: "Full Project Control requires all core project-control datasets",
        baseline: ["Cost estimate / smeta or contract baseline", "Baseline schedule / planned progress", "Material/procurement baseline if available"],
        actual: ["Progress payment or actual cost", "Actual progress / actual finish / forecast update", "Actual workforce, material, site notes or risk records"],
        guardrail: "Full Project Control consolidates schedule recovery, cost/payment control, material continuity and executive risk. Missing actual data is shown as missing; comparison values are not invented."
      },
      cost: {
        title: "Cost & Payment Control",
        text: "Upload cost estimate / smeta baseline plus progress payment or actual cost data. DevBareun compares approved budget, completed amount, remaining value and payment risk.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "cost estimate, BOQ, progress payment records, paid amount, remaining works, actual completed amount and total cost",
        reqTitle: "Cost & Payment Control requires cost baseline and progress payment evidence",
        baseline: ["Cost Estimate / Smeta / BOQ", "Contract amount or approved budget", "Work package totals, VAT and approved variations if available"],
        actual: ["Progress Payment", "Actual completed amount or paid amount", "Remaining value, advance offset or current/cumulative payment split"],
        guardrail: "Cost variance, completed amount and payment risk are calculated only when actual cost or progress payment data is detected or confirmed."
      },
      schedule: {
        title: "Schedule Recovery",
        text: "Upload baseline schedule, actual progress and workforce data. DevBareun connects delay, manpower gap and recovery actions in one dashboard.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "baseline schedule, actual progress, delay, workforce gap, productivity and recovery action",
        reqTitle: "Schedule Recovery requires schedule status and workforce evidence",
        baseline: ["Activity ID, WBS or activity name", "Planned start / planned finish / baseline duration", "Planned workforce or target productivity assumptions"],
        actual: ["Actual progress %", "completed quantity or forecast finish", "Actual worker count / crew records", "Site status update or report date"],
        guardrail: "Recovery logic connects delay and workforce gap. If actual progress or manpower is missing, DevBareun generates a review note instead of inventing a recovery plan."
      },
      material: {
        title: "Material Continuity",
        text: "Upload material stock, delivery, procurement or consumption data. DevBareun highlights shortages, delivery risks and continuity actions.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "material stock, procurement, supplier delivery, long-lead items, shortages and continuity actions",
        reqTitle: "Material Continuity requires stock, delivery and consumption evidence",
        baseline: ["Material list / BOQ material baseline", "Planned procurement dates", "Minimum stock or delivery targets"],
        actual: ["Current stock or warehouse records", "Supplier delivery status", "Site consumption / shortage notes"],
        guardrail: "Continuity risk is shown only from detected stock, delivery or procurement evidence; missing data is shown as a confirmation need."
      },
      risk: {
        title: "Risk & Decisions",
        text: "Upload risk logs, site notes, cost/schedule/material signals or decision records. DevBareun creates a decision-focused risk dashboard.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "risk register, decision prompts, open issues, owner actions and management priorities",
        reqTitle: "Risk & Decisions requires confirmed project risk signals",
        baseline: ["Risk categories or decision topics", "Approved baseline assumptions", "Management thresholds"],
        actual: ["Open issues and site notes", "Cost, schedule, material or workforce risk evidence", "Owner/contractor decisions and required actions"],
        guardrail: "Decision prompts are generated from detected evidence and missing data is flagged instead of being invented."
      }
    },
    az: {
      all: {
        title: "Tam layihə nəzarəti",
        text: "Qrafik bərpası, xərc və F-2 nəzarəti, material davamlılığı, risk və qərarlar, rəhbərlik xülasəsi və PDF/Excel hesabatlarını birləşdirən tam layihə nəzarət paneli.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "qrafik, işçi qüvvəsi, xərc, F-2, material davamlılığı, risk və rəhbərlik hesabatı",
        reqTitle: "Tam layihə nəzarəti üçün bütün əsas layihə nəzarət məlumatları lazımdır",
        baseline: ["Smeta / müqavilə bazası", "Plan qrafiki / plan icra", "Material / təchizat bazası varsa"],
        actual: ["F-2 / faktiki xərc", "Faktiki icra / faktiki bitmə / proqnoz yeniləməsi", "Faktiki işçi sayı, material, sahə qeydi və ya risk qeydləri"],
        guardrail: "Tam layihə nəzarəti qrafik bərpası, xərc və F-2 nəzarəti, material davamlılığı və rəhbərlik risk xülasəsini birləşdirir. Faktiki məlumat yoxdursa, müqayisə uydurulmur."
      },
      cost: {
        title: "Xərc və F-2 nəzarəti",
        text: "Smeta bazasını, F-2 və ya faktiki xərc məlumatlarını yükləyin. DevBareun büdcə, görülmüş iş, qalıq dəyər və ödəniş riskini müqayisə edir.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "smeta, BOQ, F-2, ödəniş aktları, ödənilmiş məbləğ, qalıq işlər, faktiki görülmüş iş məbləği və ümumi xərc",
        reqTitle: "Xərc və F-2 nəzarəti üçün smeta bazası və F-2 sübutu lazımdır",
        baseline: ["Smeta / BOQ / xərc hesablaması", "Müqavilə dəyəri və ya təsdiqlənmiş büdcə", "İş bölmələri üzrə yekunlar, ƏDV və təsdiqlənmiş dəyişikliklər varsa"],
        actual: ["F-2 / smeta üzrə icra", "Faktiki görülmüş işin məbləği və ya ödənilmiş məbləğ", "Qalıq dəyər, avans azaldılması və ya cari/yığılmış ödəniş bölgüsü"],
        guardrail: "Xərc fərqi, görülmüş iş məbləği və ödəniş riski yalnız faktiki xərc və ya F-2 məlumatı tapıldıqda və ya təsdiqləndikdə hesablanır."
      },
      schedule: {
        title: "Qrafik bərpası",
        text: "Plan qrafiki, faktiki icra və işçi sayı məlumatlarını yükləyin. DevBareun gecikmə, resurs fərqi və bərpa tədbirlərini bir dashboardda birləşdirir.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "plan qrafiki, faktiki icra, gecikmə, işçi sayı fərqi, məhsuldarlıq və bərpa tədbiri",
        reqTitle: "Qrafik bərpası üçün qrafik vəziyyəti və işçi sayı məlumatı lazımdır",
        baseline: ["Activity ID, WBS və ya iş adı", "Plan başlanğıc / plan bitmə / plan müddəti", "Plan işçi sayı və ya məhsuldarlıq hədəfi"],
        actual: ["Faktiki icra %", "tamamlanmış həcm və ya proqnoz bitmə", "Faktiki işçi sayı / briqada qeydləri", "Sahə statusu və ya hesabat tarixi"],
        guardrail: "Bərpa məntiqi gecikmə və işçi qüvvəsi fərqini birləşdirir. Faktiki icra və ya işçi sayı yoxdursa, DevBareun uydurma bərpa planı yaratmır, yoxlama qeydi göstərir."
      },
      material: {
        title: "Material davamlılığı",
        text: "Material qalığı, çatdırılma, satınalma və ya sərfiyyat məlumatlarını yükləyin. DevBareun çatışmazlığı, tədarük riskini və davamlılıq tədbirlərini göstərir.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "material qalığı, satınalma, təchizatçı çatdırılması, uzunmüddətli sifarişlər, çatışmazlıq və davamlılıq tədbirləri",
        reqTitle: "Material davamlılığı üçün qalıq, çatdırılma və sərfiyyat sübutu lazımdır",
        baseline: ["Material siyahısı / BOQ material bazası", "Planlaşdırılmış tədarük tarixləri", "Minimum qalıq və ya çatdırılma hədəfləri"],
        actual: ["Cari qalıq və ya anbar qeydləri", "Təchizatçı çatdırılma statusu", "Sahə sərfiyyatı və çatışmazlıq qeydləri"],
        guardrail: "Davamlılıq riski yalnız qalıq, çatdırılma və ya satınalma sübutu əsasında göstərilir; çatışmayan məlumat təsdiq tələbi kimi göstərilir."
      },
      risk: {
        title: "Risk və qərarlar",
        text: "Risk qeydləri, sahə qeydləri, xərc/qrafik/material siqnalları və qərar məlumatlarını yükləyin. DevBareun qərar yönümlü risk paneli yaradır.",
        template: "templates/devbareun-professional-upload-template-v2.xlsx",
        focus: "risk reyestri, qərar siqnalları, açıq məsələlər, sifarişçi tədbirləri və idarəetmə prioritetləri",
        reqTitle: "Risk və qərarlar üçün təsdiqlənmiş layihə risk siqnalları lazımdır",
        baseline: ["Risk kateqoriyaları və ya qərar mövzuları", "Təsdiqlənmiş baza fərziyyələri", "Rəhbərlik hədləri"],
        actual: ["Açıq məsələlər və sahə qeydləri", "Xərc, qrafik, material və ya işçi qüvvəsi risk sübutları", "Sifarişçi/podratçı qərarları və tələb olunan tədbirlər"],
        guardrail: "Qərar siqnalları tapılmış sübutlara əsasən yaradılır, çatışmayan məlumat isə uydurulmadan göstərilir."
      }
    }
  };

  const fieldLabels = {
    en: {
      planned_execution: "Planned execution %",
      actual_execution: "Actual execution %",
      baseline_finish: "Baseline finish date",
      estimated_finish: "Estimated finish date",
      total_cost: "Total smeta / contract amount",
      actual_cost: "Actual completed amount",
      planned_cost: "Cost estimate baseline",
      workforce_current: "Current workforce",
      workforce_required: "Required workforce"
    },
    az: {
      planned_execution: "Plan üzrə icra faizi",
      actual_execution: "Faktiki icra faizi",
      baseline_finish: "Plan üzrə bitmə tarixi",
      estimated_finish: "Təxmini bitmə tarixi",
      total_cost: "Smeta / müqavilə üzrə ümumi məbləğ",
      actual_cost: "Faktiki görülmüş iş məbləği",
      planned_cost: "Smeta üzrə baza məbləği",
      workforce_current: "Faktiki işçi sayı",
      workforce_required: "Tələb olunan işçi sayı"
    }
  };

  const kpiLabels = {
    en: {
      project_name: "Project name",
      currency: "Currency",
      total_cost: "Cost estimate / contract total",
      planned_cost: "Cost estimate baseline",
      actual_cost: "Detected actual completed amount",
      planned_execution: "Planned execution",
      actual_execution: "Actual execution",
      baseline_finish: "Baseline finish",
      estimated_finish: "Estimated finish",
      workforce_current: "Current workforce",
      workforce_required: "Required workforce"
    },
    az: {
      project_name: "Layihə adı",
      currency: "Valyuta",
      total_cost: "Smeta / müqavilə üzrə yekun məbləğ",
      planned_cost: "Smeta üzrə baza məbləği",
      actual_cost: "Tapılmış faktiki görülmüş iş məbləği",
      planned_execution: "Plan üzrə icra",
      actual_execution: "Faktiki icra",
      baseline_finish: "Plan üzrə bitmə tarixi",
      estimated_finish: "Təxmini bitmə tarixi",
      workforce_current: "Faktiki işçi sayı",
      workforce_required: "Tələb olunan işçi sayı"
    }
  };

  const ui = {
    en: {
      notDetected: "Not detected",
      optional: "Optional",
      confidence: "Confidence",
      noSheetProfileTitle: "No sheet profile",
      noSheetProfileText: "Upload a supported Excel/CSV/PDF file.",
      missing: "Missing",
      noClearColumns: "No clear columns",
      sheet: "Sheet",
      unknown: "unknown",
      reviewValues: "Review these values. If something is missing or unclear, fill the field below before generating the dashboard.",
      noRequiredMissing: "No required missing fields were detected for this analysis type.",
      optionalMissingTitle: "Optional missing data",
      optionalMissingTextOne: "1 field not detected. Open only if you want to enter manually.",
      optionalMissingTextMany: "{count} fields not detected. Open only if you want to enter manually.",
      fillManually: "Fill manually",
      actualRequiredTitle: "Additional actual data required",
      actualRequiredText: "{label} is needed before DevBareun can calculate a reliable comparison. You can still continue with a baseline-only view, but actual variance and execution will stay unavailable.",
      uploadLimit: "Upload limit: {maxFiles} files · {maxFileSizeMb}MB per file · {maxTotalSizeMb}MB total.",
      addActualFiles: "Add actual data files",
      actualCostFile: "Progress Payment / actual cost file",
      actualProgressFile: "Progress payment file",
      actualScheduleFile: "actual progress / forecast update file",
      actualWorkforceFile: "actual workforce / site manpower file",
      actualGeneralFile: "actual progress, payment or site record file",
      generatePreview: "Generate Preview",
      confirmGenerate: "Confirm & Generate Dashboard",
      processing: "Processing...",
      generatingDashboard: "Generating dashboard...",
      preparingMapping: "Preparing mapping...",
      apiClientNotLoaded: "API client was not loaded. Check js/api-client.js script order.",
      apiClientMissing: "API client is missing.",
      noFileSelected: "No file selected. Please choose at least one construction file.",
      chooseFileFirst: "Please choose a file first.",
      creatingProject: "1/3 Creating project record for {type} analysis...",
      uploadingFiles: "2/3 Uploading {count} file(s)... Project ID: {projectId}",
      detectingFields: "3/3 Detecting sheets, key values and missing fields...",
      mappingUnavailable: "Preflight mapping unavailable:",
      mappingReady: "Mapping preview is ready. Review the detected values, add missing fields if needed, then confirm.",
      confirmingUnlock: "1/3 Confirming result unlock step...",
      calculatingDashboard: "2/3 Calculating {type} dashboard from confirmed mapping...",
      dashboardReady: "3/3 Dashboard ready. Opening result page...",
      generationFailed: "Generation failed: {message}",
      generationFailedToast: "Generation failed. Check backend deployment and file format.",
      noPreparedProject: "No prepared project found. Please upload again.",
      selectedStatus: "{count} file(s) selected. Parser focus: {focus}. Limit: {maxFiles} files, {maxFileSizeMb}MB each.",
      defaultProject: "DevBareun Uploaded Project"
    },
    az: {
      notDetected: "Aşkar edilmədi",
      optional: "İstəyə bağlı",
      confidence: "Etibarlılıq",
      noSheetProfileTitle: "Vərəq profili tapılmadı",
      noSheetProfileText: "Dəstəklənən Excel/CSV/PDF faylı yükləyin.",
      missing: "Çatışmır",
      noClearColumns: "Aydın sütunlar tapılmadı",
      sheet: "Vərəq",
      unknown: "bilinmir",
      reviewValues: "Bu dəyərləri yoxlayın. Çatışmayan və ya qeyri-müəyyən məlumat varsa, dashboard yaratmazdan əvvəl aşağıdakı sahəni doldurun.",
      noRequiredMissing: "Bu analiz növü üçün məcburi çatışmayan sahə aşkar edilmədi.",
      optionalMissingTitle: "İstəyə bağlı çatışmayan məlumatlar",
      optionalMissingTextOne: "1 sahə aşkar edilmədi. Əllə daxil etmək istəyirsinizsə açın.",
      optionalMissingTextMany: "{count} sahə aşkar edilmədi. Əllə daxil etmək istəyirsinizsə açın.",
      fillManually: "Əllə doldur",
      actualRequiredTitle: "Əlavə faktiki məlumat tələb olunur",
      actualRequiredText: "Etibarlı müqayisə hesablanması üçün {label} lazımdır. Yalnız baza görünüşü ilə davam edə bilərsiniz, lakin faktiki fərq və icra göstəriciləri əlçatan olmayacaq.",
      uploadLimit: "Yükləmə limiti: {maxFiles} fayl · hər fayl {maxFileSizeMb}MB · ümumi {maxTotalSizeMb}MB.",
      addActualFiles: "Faktiki məlumat faylları əlavə et",
      actualCostFile: "F-2 / smeta üzrə icra / faktiki xərc faylı",
      actualProgressFile: "F-2 / smeta üzrə icra faylı",
      actualScheduleFile: "faktiki icra / proqnoz yeniləmə faylı",
      actualWorkforceFile: "faktiki işçi sayı / sahə işçi qeydi faylı",
      actualGeneralFile: "faktiki icra, ödəniş və ya sahə qeydi faylı",
      generatePreview: "Önbaxış yarat",
      confirmGenerate: "Təsdiqlə və dashboard yarat",
      processing: "Emal olunur...",
      generatingDashboard: "Dashboard yaradılır...",
      preparingMapping: "Məlumat uyğunluğu hazırlanır...",
      apiClientNotLoaded: "API client yüklənməyib. js/api-client.js script ardıcıllığını yoxlayın.",
      apiClientMissing: "API client tapılmadı.",
      noFileSelected: "Fayl seçilməyib. Ən azı bir tikinti faylı seçin.",
      chooseFileFirst: "Əvvəl fayl seçin.",
      creatingProject: "1/3 {type} analizi üçün layihə qeydi yaradılır...",
      uploadingFiles: "2/3 {count} fayl yüklənir... Layihə ID: {projectId}",
      detectingFields: "3/3 Vərəqlər, əsas dəyərlər və çatışmayan sahələr yoxlanılır...",
      mappingUnavailable: "İlkin məlumat uyğunluğu əlçatan deyil:",
      mappingReady: "Məlumat önbaxışı hazırdır. Tapılmış dəyərləri yoxlayın, lazım olduqda çatışmayan sahələri əlavə edin və təsdiqləyin.",
      confirmingUnlock: "1/3 Nəticənin açılması addımı təsdiqlənir...",
      calculatingDashboard: "2/3 Təsdiqlənmiş məlumatlara əsasən {type} dashboard hesablanır...",
      dashboardReady: "3/3 Dashboard hazırdır. Nəticə səhifəsi açılır...",
      generationFailed: "Yaratma uğursuz oldu: {message}",
      generationFailedToast: "Yaratma uğursuz oldu. Backend deploy və fayl formatını yoxlayın.",
      noPreparedProject: "Hazırlanmış layihə tapılmadı. Zəhmət olmasa yenidən yükləyin.",
      selectedStatus: "{count} fayl seçildi. Yoxlama fokusu: {focus}. Limit: {maxFiles} fayl, hər biri {maxFileSizeMb}MB.",
      defaultProject: "DevBareun yüklənmiş layihə"
    }
  };

  const uploadLimits = {
    maxFiles: 6,
    maxFileSizeMb: 30,
    maxTotalSizeMb: 120
  };

  function lang() {
    const current = (localStorage.getItem("devbareun_lang") || document.documentElement.lang || "en").toLowerCase();
    return current.startsWith("az") ? "az" : "en";
  }

  function t(key, vars = {}) {
    const dict = ui[lang()] || ui.en;
    let value = dict[key] || ui.en[key] || key;
    Object.entries(vars).forEach(([k, v]) => { value = value.replace(new RegExp("\\{" + k + "\\}", "g"), String(v)); });
    return value;
  }

  function metaFor(type) {
    const current = lang();
    return (analysisMeta[current] && analysisMeta[current][type]) || analysisMeta.en[type] || analysisMeta.en.all;
  }

  function labelFor(field, map) {
    const current = lang();
    const fromMap = (map[current] && map[current][field]) || (map.en && map.en[field]);
    if (fromMap) return fromMap;
    if (current === "az" && window.DevBareunI18n) return window.DevBareunI18n.label(field);
    return field;
  }

  function localizeText(value) {
    return lang() === "az" && window.DevBareunI18n ? window.DevBareunI18n.text(value) : value;
  }

  function localizeDetectedType(value) {
    const v = value || t("unknown");
    return localizeText(v);
  }

  function localizeMappedColumns(mappedColumns) {
    if (!mappedColumns || !Object.keys(mappedColumns).length) return t("noClearColumns");
    return Object.entries(mappedColumns).map(([k, v]) => `${labelFor(k, fieldLabels)}: ${v}`).join(", ");
  }

  function hasActualSignal(preflight) {
    const kpis = preflight && preflight.detected_kpis ? preflight.detected_kpis : {};
    const warnings = (preflight && Array.isArray(preflight.warnings) ? preflight.warnings : []).join(" ").toLowerCase();
    const missing = new Set(preflight && Array.isArray(preflight.missing_fields) ? preflight.missing_fields : []);
    const profiles = Array.isArray(preflight && preflight.sheet_profiles) ? preflight.sheet_profiles : [];
    const hasProgressSheet = profiles.some(p => String(p.detected_type || "").toLowerCase().includes("progress") || /f-?\s*2|forma\s*-?\s*2|progress payment|interim payment/i.test(String(p.sheet_name || "")));
    if (selectedAnalysisType === "cost" || selectedAnalysisType === "progress") {
      if (kpis.actual_cost || kpis.actual_execution || hasProgressSheet) return true;
      if (missing.has("actual_cost") || missing.has("actual_execution")) return false;
      return !/actual cost|f-2|progress payment|interim payment|actual completed|faktiki/.test(warnings);
    }
    if (selectedAnalysisType === "schedule") {
      if (kpis.actual_execution || kpis.estimated_finish || kpis.delay_days) return true;
      if (missing.has("actual_execution") || missing.has("estimated_finish")) return false;
      return !/actual progress|actual finish|forecast|faktiki|actual data/.test(warnings);
    }
    if (selectedAnalysisType === "workforce") {
      if (kpis.workforce_current) return true;
      if (missing.has("workforce_current")) return false;
      return !/actual workforce|current workforce|işçi|isci/.test(warnings);
    }
    return true;
  }

  function actualDataLabel() {
    if (selectedAnalysisType === "cost") return t("actualCostFile");
    if (selectedAnalysisType === "schedule") return t("actualScheduleFile") + " + " + t("actualWorkforceFile");
    return t("actualGeneralFile");
  }

  function qs(sel) { return document.querySelector(sel); }
  function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }
  function analysisCards() { return qsa("[data-analysis-type]"); }
  function fileInput() { return qs("#fileInput") || qs('input[type="file"]'); }
  function generateButton() { return qs("#generatePreviewBtn"); }
  function clearButton() { return qs("#clearFilesBtn"); }

  function getSelectedFiles() {
    if (Array.isArray(window.DevBareunSelectedFiles) && window.DevBareunSelectedFiles.length) return window.DevBareunSelectedFiles;
    const input = fileInput();
    return input && input.files ? Array.from(input.files) : [];
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
  }

  function formatValue(value, field) {
    if (value === null || value === undefined || value === "") return t("notDetected");
    if (typeof value === "number") {
      if (field && field.includes("execution")) return value.toFixed(2).replace(/\.00$/, "") + "%";
      if (field && (field.includes("cost") || field === "total_cost")) return value.toLocaleString(undefined, {maximumFractionDigits: 2}) + " AZN";
      return value.toLocaleString(undefined, {maximumFractionDigits: 2});
    }
    return String(localizeText(value));
  }

  function toast(message) {
    const el = qs("#toast");
    if (el) {
      el.textContent = message;
      el.classList.add("show");
      clearTimeout(window.__dbBackendToast);
      window.__dbBackendToast = setTimeout(() => el.classList.remove("show"), 4200);
    } else console.log(message);
  }

  function status(message, type = "info") {
    let box = qs(".backend-status-box");
    const target = qs("#analysisPreview") || qs("#upload") || qs("main");
    if (!box && target) {
      box = document.createElement("div");
      box.className = "backend-status-box";
      if (target.id === "analysisPreview") target.parentNode.insertBefore(box, target);
      else target.appendChild(box);
    }
    if (box) {
      box.className = "backend-status-box " + type;
      box.textContent = message;
    }
  }

  function deriveProjectName(files) {
    const first = files && files[0] ? files[0].name || "" : "";
    const clean = first.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
    return clean && clean.length > 3 ? clean : t("defaultProject");
  }

  function resetFlow() {
    flowStage = "idle";
    lastProjectId = null;
    lastPreflight = null;
    const panel = qs("#mappingPreviewPanel");
    if (panel) panel.hidden = true;
    const btn = generateButton();
    if (btn) btn.textContent = btn.dataset.defaultText || t("generatePreview");
  }

  function renderRequirements(meta) {
    const title = qs("#requirementsTitle");
    const baseList = qs("#baselineRequirements");
    const actualList = qs("#actualRequirements");
    const guard = qs("#requirementsGuardrail");
    if (!meta) return;
    if (title) title.textContent = meta.reqTitle || metaFor("all").reqTitle;
    if (baseList) baseList.innerHTML = (meta.baseline || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
    if (actualList) actualList.innerHTML = (meta.actual || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
    if (guard) guard.textContent = meta.guardrail || metaFor("all").guardrail;
  }

  function updateAnalysisType(type) {
    selectedAnalysisType = type || "all";
    analysisCards().forEach(btn => {
      btn.classList.add("analysis-type-card");
      const active = btn.dataset.analysisType === selectedAnalysisType;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
    const meta = metaFor(selectedAnalysisType);
    const title = qs("#templateTitle");
    const text = qs("#templateText");
    const dl = qs("#templateDownload");
    if (title) title.textContent = meta.title;
    if (text) text.textContent = meta.text;
    if (dl) dl.setAttribute("href", meta.template);
    renderRequirements(meta);
    resetFlow();
    updateGenerateState();
  }

  function renderMappingPreview(preflight) {
    const panel = qs("#mappingPreviewPanel");
    if (!panel || !preflight) return;
    lastPreflight = preflight;
    panel.hidden = false;
    const conf = qs("#mappingConfidence");
    if (conf) conf.textContent = t("confidence") + ": " + (preflight.confidence || "—") + "/100";

    const rows = qs("#mappingRows");
    const profiles = Array.isArray(preflight.sheet_profiles) ? preflight.sheet_profiles : [];
    if (rows) {
      rows.innerHTML = "";
      const kpis = Object.assign({project_name: preflight.project_name, currency: preflight.currency}, preflight.detected_kpis || {});
      const kpiEntries = Object.entries(kpis).filter(([_, v]) => v !== null && v !== undefined && v !== "");
      if (kpiEntries.length) {
        rows.insertAdjacentHTML("beforeend", '<div class="mapping-kpis">' + kpiEntries.slice(0, 8).map(([k, v]) => `<div class="mapping-kpi"><small>${escapeHtml(labelFor(k, kpiLabels))}</small><b>${escapeHtml(formatValue(v, k))}</b></div>`).join("") + '</div>');
      }
      const topProfiles = profiles.slice(0, 9);
      if (!topProfiles.length) {
        rows.insertAdjacentHTML("beforeend", `<div class="mapping-row"><b>${escapeHtml(t("noSheetProfileTitle"))}</b><span>${escapeHtml(t("noSheetProfileText"))}</span><small class="warn">${escapeHtml(t("missing"))}</small><small>—</small></div>`);
      } else {
        topProfiles.forEach(p => {
          const mapped = localizeMappedColumns(p.mapped_columns);
          const ok = (p.confidence || 0) >= 75 ? "ok" : "warn";
          rows.insertAdjacentHTML("beforeend", `<div class="mapping-row"><b>${escapeHtml(localizeText(p.sheet_name || t("sheet")))}</b><span>${escapeHtml(localizeDetectedType(p.detected_type))}</span><small class="${ok}">${p.confidence || 0}%</small><small>${escapeHtml(mapped)}</small></div>`);
        });
      }
      rows.insertAdjacentHTML("beforeend", `<div class="mapping-confirm-note">${escapeHtml(t("reviewValues"))}</div>`);
    }

    const missing = qs("#missingFields");
    if (missing) {
      const fields = Array.isArray(preflight.missing_fields) ? preflight.missing_fields : [];
      missing.innerHTML = "";
      if (!fields.length) {
        missing.innerHTML = `<div class="mapping-confirm-note compact-ok">${escapeHtml(t("noRequiredMissing"))}</div>`;
      } else {
        const fieldInputs = fields.map(field => {
          const label = localizeText(labelFor(field, fieldLabels));
          return `<label class="missing-compact-field"><span>${escapeHtml(label)}</span><input data-manual-field="${escapeHtml(field)}" placeholder="${escapeHtml(t("optional"))}" /></label>`;
        }).join("");
        const countText = fields.length === 1 ? t("optionalMissingTextOne") : t("optionalMissingTextMany", {count: fields.length});
        missing.insertAdjacentHTML("beforeend", `
          <details class="missing-compact-card">
            <summary>
              <span><strong>${escapeHtml(t("optionalMissingTitle"))}</strong><small>${escapeHtml(countText)}</small></span>
              <b>${escapeHtml(t("fillManually"))}</b>
            </summary>
            <div class="missing-compact-grid">${fieldInputs}</div>
          </details>
        `);
      }
    }

    const extra = qs("#additionalActualRequest");
    if (extra) extra.remove();
    if (!hasActualSignal(preflight)) {
      const request = document.createElement("div");
      request.id = "additionalActualRequest";
      request.className = "additional-actual-request";
      request.innerHTML = `<div><strong>${escapeHtml(t("actualRequiredTitle"))}</strong><p>${escapeHtml(t("actualRequiredText", {label: actualDataLabel()}))}</p><small>${escapeHtml(t("uploadLimit", uploadLimits))}</small></div><button type="button" class="btn ghost" id="addActualFilesBtn">${escapeHtml(t("addActualFiles"))}</button>`;
      panel.appendChild(request);
      const addBtn = qs("#addActualFilesBtn");
      const input = fileInput();
      if (addBtn && input) addBtn.addEventListener("click", e => { e.preventDefault(); input.click(); });
    }
  }

  function collectManualInputs() {
    const data = {};
    qsa("[data-manual-field]").forEach(input => {
      if (input.value && input.value.trim()) data[input.dataset.manualField] = input.value.trim();
    });
    return data;
  }

  function setLoading(btn, on, label) {
    if (!btn) return;
    if (!btn.dataset.defaultText) btn.dataset.defaultText = btn.textContent || t("generatePreview");
    if (on) {
      btn.textContent = label || t("processing");
      btn.disabled = true;
      btn.classList.add("is-loading");
    } else {
      if (flowStage === "mapping-ready") btn.textContent = t("confirmGenerate");
      else btn.textContent = btn.dataset.defaultText || t("generatePreview");
      btn.disabled = getSelectedFiles().length === 0;
      btn.classList.remove("is-loading");
    }
  }

  function updateGenerateState() {
    const btn = generateButton();
    const clear = clearButton();
    const count = getSelectedFiles().length;
    if (btn) {
      if (!btn.dataset.defaultText) btn.dataset.defaultText = btn.textContent || t("generatePreview");
      btn.disabled = count === 0 || isRunning;
      if (!isRunning) btn.textContent = flowStage === "mapping-ready" ? t("confirmGenerate") : btn.dataset.defaultText;
    }
    if (clear) clear.disabled = count === 0 || isRunning;
    if (count > 0) {
      const meta = metaFor(selectedAnalysisType);
      status(t("selectedStatus", {count, focus: meta.focus, maxFiles: uploadLimits.maxFiles, maxFileSizeMb: uploadLimits.maxFileSizeMb}), "success");
    }
  }

  async function prepareMapping(files) {
    const draftProjectName = deriveProjectName(files);
    status(t("creatingProject", {type: selectedAnalysisType}), "info");
    const project = await API.createProject(draftProjectName, "info@devbareun.com", selectedAnalysisType);
    const projectId = project.project_id;
    lastProjectId = projectId;

    status(t("uploadingFiles", {count: files.length, projectId}), "info");
    await API.uploadFiles(projectId, files);

    status(t("detectingFields"), "info");
    let preflight = null;
    try {
      preflight = await API.preflightProject(projectId, selectedAnalysisType);
    } catch (preflightErr) {
      console.warn(t("mappingUnavailable"), preflightErr);
      preflight = { confidence: 50, missing_fields: ["planned_execution", "baseline_finish"], sheet_profiles: [], detected_kpis: {} };
    }
    renderMappingPreview(preflight);
    flowStage = "mapping-ready";
    status(t("mappingReady"), "success");
  }

  async function finalizeDashboard() {
    if (!lastProjectId) throw new Error(t("noPreparedProject"));
    status(t("confirmingUnlock"), "info");
    const payment = await API.mockPayment(lastProjectId);
    if (payment && payment.checkout_url) {
      window.location.href = payment.checkout_url;
      return;
    }
    status(t("calculatingDashboard", {type: selectedAnalysisType}), "info");
    await API.analyzeProject(lastProjectId, selectedAnalysisType, collectManualInputs());
    status(t("dashboardReady"), "success");
    window.location.href = "result-dashboard.html?project_id=" + encodeURIComponent(lastProjectId);
  }

  async function runGenerateFlow(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
      if (event.stopImmediatePropagation) event.stopImmediatePropagation();
    }
    if (isRunning) return false;
    const files = getSelectedFiles();
    const btn = generateButton();
    if (!API) {
      status(t("apiClientNotLoaded"), "error");
      toast(t("apiClientMissing"));
      return false;
    }
    if (!files.length && flowStage !== "mapping-ready") {
      status(t("noFileSelected"), "warning");
      toast(t("chooseFileFirst"));
      return false;
    }

    isRunning = true;
    try {
      if (flowStage === "mapping-ready") {
        setLoading(btn, true, t("generatingDashboard"));
        await finalizeDashboard();
      } else {
        setLoading(btn, true, t("preparingMapping"));
        await prepareMapping(files);
        setLoading(btn, false);
      }
    } catch (err) {
      console.error(err);
      status(t("generationFailed", {message: err.message || err}), "error");
      toast(t("generationFailedToast"));
      setLoading(btn, false);
    } finally {
      isRunning = false;
      updateGenerateState();
    }
    return false;
  }

  function refreshDynamicLanguage() {
    const meta = metaFor(selectedAnalysisType);
    const title = qs("#templateTitle");
    const text = qs("#templateText");
    if (title) title.textContent = meta.title;
    if (text) text.textContent = meta.text;
    renderRequirements(meta);
    if (flowStage === "mapping-ready" && lastPreflight) renderMappingPreview(lastPreflight);
    updateGenerateState();
  }

  function bind() {
    analysisCards().forEach(btn => {
      btn.classList.add("analysis-type-card");
      if (btn.dataset.analysisBound) return;
      btn.dataset.analysisBound = "true";
      btn.addEventListener("click", e => {
        e.preventDefault();
        updateAnalysisType(btn.dataset.analysisType || "all");
      });
    });
    const useOwn = qs("#useOwnFileBtn");
    const input = fileInput();
    const drop = qs("#dropZone");
    const chooseBtn = qs('[data-i18n="uploadBtn"]');
    const btn = generateButton();
    const clear = clearButton();
    if (useOwn && input && !useOwn.dataset.ownFileBound) {
      useOwn.dataset.ownFileBound = "true";
      useOwn.addEventListener("click", e => { e.preventDefault(); input.click(); });
    }
    if (drop && input && !drop.dataset.backendPickerBound) {
      drop.dataset.backendPickerBound = "true";
      drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
    }
    if (chooseBtn && input && !chooseBtn.dataset.backendPickerBound) {
      chooseBtn.dataset.backendPickerBound = "true";
      chooseBtn.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); input.click(); }, true);
    }
    if (btn && !btn.dataset.backendGenerateBound) {
      btn.dataset.backendGenerateBound = "true";
      btn.addEventListener("click", runGenerateFlow, true);
    }
    if (clear && !clear.dataset.backendClearBound) {
      clear.dataset.backendClearBound = "true";
      clear.addEventListener("click", () => { resetFlow(); updateGenerateState(); });
    }
    updateAnalysisType(selectedAnalysisType);
    updateGenerateState();
  }

  document.addEventListener("DOMContentLoaded", bind);
  window.addEventListener("load", bind);
  document.addEventListener("devbareun:files", () => { resetFlow(); updateGenerateState(); });
  document.addEventListener("devbareun:lang", () => setTimeout(refreshDynamicLanguage, 0));
  bind();

  window.DevBareunRunGenerate = runGenerateFlow;
})();
