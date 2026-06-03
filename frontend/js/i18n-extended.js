// DevBareun v0.6.2 — full EN/AZ upload terminology and construction-sector copy
(function () {
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const $ = (sel, root = document) => root.querySelector(sel);
  const lang = () => localStorage.getItem("devbareun_lang") || "en";

  const t = {
    en: {
      stepSelectAnalysis: "Select analysis type",
      analysisAllTitle: "Full Project Control",
      analysisAllDesc: "Complete control package combining schedule, workforce, cost, payment, material and decisions",
      analysisCostTitle: "Cost & Payment Control",
      analysisCostDesc: "Cost estimate, actual cost and progress payment control",
      analysisScheduleTitle: "Schedule Recovery",
      analysisScheduleDesc: "Delay analysis, workforce gap and recovery planning",
      analysisMaterialTitle: "Material Continuity",
      analysisMaterialDesc: "Stock, delivery risk and procurement continuity",
      analysisMaterialBadge: "Supply chain",
      analysisRiskTitle: "Risk & Decisions",
      analysisRiskDesc: "Risk register, decision prompts and management actions",
      analysisRiskBadge: "Executive focus",
      packageMaterialKicker: "Material Flow",
      packageRiskKicker: "Risk + Decisions",
      analysisWorkforceTitle: "Workforce",
      analysisWorkforceDesc: "Daily manpower, productivity norms, required crews and delay risk",
      analysisProgressTitle: "Progress Payment",
      analysisProgressDesc: "Plan/fact, progress payment records and physical execution",
      selectedAnalysisLabel: "Selected package",
      requiredDataLabel: "Required data logic",
      baselineDataLabel: "Baseline / plan data",
      actualDataLabel: "Actual / factual data",
      noActualGuardrail: "No actual data → no comparison result. Unclear actual data → needs confirmation.",
      downloadOptionalTemplate: "Download professional template",
      supportedInputs: "Supported inputs and parser status:",
      siteImagesChip: "▨ Site Images",
      outputChip: "▣ Output: PDF + Excel",
      confirmMappingStep: "Confirm detected mapping",
      mappingTitle: "We found these data signals",
      mappingText: "Review the detected sheets, key values and missing fields. The final dashboard is generated only after you confirm this mapping.",
      projectDataPreview: "Project Data Preview",
      projectDataPreviewText: "After upload, DevBareun shows a mapping confirmation screen. Review detected values, add missing fields, then generate the selected dashboard and report package.",
      readsTitle: "What DevBareun reads",
      secureNote: "Your data is secure.",
      proofEyebrow: "Construction reporting workflow",
      proofTitle: "Built for real construction control files.",
      proofText: "Upload BOQ, cost estimate, progress payment records, schedule exports and workforce sheets. DevBareun reviews detected sheets and highlights missing fields before generating reports.",
      proofBadge1: "BOQ / Cost Estimate",
      proofBadge2: "Progress Payment",
      proofBadge3: "Schedule Data",
      proofBadge4: "Workforce Sheets",
      proofBadge5: "PDF + Excel Output",
      proofCard1Title: "Project-control files",
      proofCard1Text: "Upload real construction cost, progress and schedule documents.",
      proofCard2Title: "BOQ, Cost Estimate & Progress Payment",
      proofCard2Text: "Designed for cost estimate baselines and progress payment workflows.",
      proofCard3Title: "Bilingual reporting",
      proofCard3Text: "English interface with Azerbaijani project data support.",
      proofCard4Title: "Data confirmation",
      proofCard4Text: "Detected sheets and missing fields are shown before final reporting.",
      priceNote: "per professional project analysis",
      privacyPolicy: "Privacy Policy",
      termsOfService: "Terms of Service",
      siteImagesTitle: "Site Images",
      outputTitle: "Output",

      wizardPhaseAnalysis: "Control package",
      wizardPhaseAnalysisSub: "Choose the project problem",
      wizardPhaseUpload: "Upload data",
      wizardPhaseUploadSub: "Add required files",
      wizardPhaseResult: "Get results",
      wizardPhaseResultSub: "Review dashboard",
      wizardSelectTitle: "Choose control package",
      wizardSelectText: "Choose the package that matches the main project problem. DevBareun prepares the right dashboard and upload logic.",
      analysisAllDescLong: "Complete control across schedule, workforce, cost, payment, material, risk and decisions",
      analysisAllBadge: "Recommended",
      packageScheduleKicker: "Schedule + Workforce",
      packageCostKicker: "Cost + Payment",
      packageFullKicker: "All modules",
      analysisScheduleBadge: "Recovery plan",
      analysisCostBadge: "Commercial control",
      packageComboTitle: "Selected package: Full Project Control",
      packageComboText: "Choose one project problem and DevBareun prepares the matching dashboard, review logic and export package.",
      flowInputLabel: "You upload",
      flowInputTitle: "Project control files",
      flowInputText: "BOQ, cost estimate, F-2, schedule, workforce, procurement or risk files depending on the selected package.",
      flowAnalyzeLabel: "We analyze",
      flowAnalyzeTitle: "Baseline vs actual performance",
      flowAnalyzeText: "DevBareun checks delays, cost pressure, payment status, material continuity and executive risk from the files you upload.",
      flowReceiveLabel: "You receive",
      flowReceiveTitle: "Dashboard plus report package",
      flowReceiveText: "A package-specific dashboard, detected issues, decision prompts, and PDF or Excel outputs ready for review and export.",
      wizardUploadTitle: "Upload required data",
      wizardUploadText: "Upload only the files required for the selected package. The package decides which dashboard sections and outputs will be generated.",
      wizardDropTitle: "Drag files here or choose",
      wizardDropText: "Excel, CSV, PDF and XER / XML formats are supported.",
      supportedFileFormats: "Supported file formats",
      dataInfoTitle: "Required data logic",
      dataInfoText: "The required baseline and actual data changes according to the selected package.",
      showRequirements: "Show requirements",
      startAnalysisCta: "Generate Preview",
      template_all_title: "Full Project Control",
      template_all_text: "Upload cost estimate, progress payment, schedule, workforce, material or risk files. Result: one executive dashboard with schedule, cost, payment, material and risk views.",
      template_cost_title: "Cost & Payment Control",
      template_cost_text: "Upload cost estimate / smeta baseline plus progress payment or actual cost data. Result: cost variance, completed amount, remaining value and payment-risk dashboard.",
      template_schedule_title: "Schedule Recovery",
      template_schedule_text: "Upload baseline schedule, actual progress and workforce data. Result: delay status, manpower gap, critical activities and recovery-action dashboard.",
      template_material_title: "Material Continuity",
      template_material_text: "Upload material stock, delivery, procurement or consumption data. Result: shortage alerts, delivery-risk checks and continuity-action dashboard.",
      template_risk_title: "Risk & Decisions",
      template_risk_text: "Upload risk logs, site notes, cost or schedule signals, or decision records. Result: risk register, decision prompts and management-action dashboard.",
      template_workforce_title: "Workforce",
      template_workforce_text: "Upload activity quantities, planned duration and actual worker counts. Result: workforce sufficiency, realistic duration and delay-risk dashboard.",
      template_progress_title: "Progress Payment",
      template_progress_text: "Upload progress payment records, plan/fact reports or completed work tables. Result: interim payment, execution status and payment-progress dashboard."
    },
    az: {
      stepSelectAnalysis: "Analiz növünü seçin",
      analysisAllTitle: "Tam layihə nəzarəti",
      analysisAllDesc: "Qrafik, işçi qüvvəsi, xərc, F-2, material və qərar göstəriciləri",
      analysisCostTitle: "Xərc və F-2 nəzarəti",
      analysisCostDesc: "Smeta, faktiki xərc, F-2 və ödəniş nəzarəti",
      analysisScheduleTitle: "Qrafik bərpası",
      analysisScheduleDesc: "Gecikmə analizi, işçi sayı fərqi və bərpa planı",
      analysisMaterialTitle: "Material davamlılığı",
      analysisMaterialDesc: "Material qalığı, tədarük riski və təchizat davamlılığı",
      analysisMaterialBadge: "Təchizat zənciri",
      analysisRiskTitle: "Risk və qərarlar",
      analysisRiskDesc: "Risk reyestri, qərar siqnalları və idarəetmə tədbirləri",
      analysisRiskBadge: "Rəhbərlik fokusu",
      packageMaterialKicker: "Material axını",
      packageRiskKicker: "Risk + Qərarlar",
      analysisWorkforceTitle: "İşçi qüvvəsi",
      analysisWorkforceDesc: "Gündəlik işçi sayı, məhsuldarlıq norması, tələb olunan briqada və gecikmə riski",
      analysisProgressTitle: "F-2 / Smeta üzrə icra",
      analysisProgressDesc: "Plan/fakt, F-2 aktları və fiziki icra vəziyyəti",
      selectedAnalysisLabel: "Seçilmiş paket",
      requiredDataLabel: "Tələb olunan məlumat məntiqi",
      baselineDataLabel: "Baza / plan məlumatı",
      actualDataLabel: "Faktiki məlumat",
      noActualGuardrail: "Faktiki məlumat yoxdursa → müqayisə nəticəsi yoxdur. Şübhəli faktiki məlumat → təsdiq tələb edir.",
      downloadOptionalTemplate: "Peşəkar şablonu yükləyin",
      supportedInputs: "Dəstəklənən fayllar və parser statusu:",
      siteImagesChip: "▨ Sahə şəkilləri",
      outputChip: "▣ Çıxış: PDF + Excel",
      confirmMappingStep: "Tapılmış məlumatları təsdiqləyin",
      mappingTitle: "Sistem bu məlumat siqnallarını tapdı",
      mappingText: "Tapılmış vərəqləri, əsas dəyərləri və çatışmayan sahələri yoxlayın. Yekun dashboard yalnız təsdiqdən sonra yaradılır.",
      projectDataPreview: "Layihə məlumatlarına önbaxış",
      projectDataPreviewText: "Yükləmədən sonra DevBareun məlumat uyğunluğunu göstərir. Tapılmış dəyərləri yoxlayın, çatışmayan sahələri əlavə edin və seçilmiş dashboard + hesabat paketini yaradın.",
      readsTitle: "DevBareun nələri oxuyur",
      secureNote: "Məlumatlarınız təhlükəsizdir.",
      proofEyebrow: "Tikinti hesabat axını",
      proofTitle: "Real tikinti nəzarət faylları üçün hazırlanıb.",
      proofText: "BOQ, smeta, F-2 aktları, layihə qrafikləri və işçi sayı cədvəllərini yükləyin. DevBareun hesabat yaratmazdan əvvəl tapılmış vərəqləri və çatışmayan sahələri göstərir.",
      proofBadge1: "BOQ / Smeta",
      proofBadge2: "F-2 / Smeta üzrə icra",
      proofBadge3: "Qrafik məlumatları",
      proofBadge4: "İşçi sayı cədvəlləri",
      proofBadge5: "PDF + Excel çıxışı",
      proofCard1Title: "Layihə nəzarət faylları",
      proofCard1Text: "Real tikinti xərc, icra və qrafik sənədlərini yükləyin.",
      proofCard2Title: "BOQ, Smeta və F-2",
      proofCard2Text: "Smeta bazası və F-2 icra aktları üzrə hesabat axını üçün hazırlanıb.",
      proofCard3Title: "İkidilli hesabat",
      proofCard3Text: "İngilis interfeysi və Azərbaycan dilində layihə məlumatı dəstəyi.",
      proofCard4Title: "Məlumat təsdiqi",
      proofCard4Text: "Tapılmış vərəqlər və çatışmayan sahələr yekun hesabatdan əvvəl göstərilir.",
      priceNote: "bir peşəkar layihə analizi üçün",
      privacyPolicy: "Məxfilik siyasəti",
      termsOfService: "Xidmət şərtləri",
      siteImagesTitle: "Sahə şəkilləri",
      outputTitle: "Çıxış",

      wizardPhaseAnalysis: "Nəzarət paketi",
      wizardPhaseAnalysisSub: "Layihə problemini seçin",
      wizardPhaseUpload: "Məlumat yükləyin",
      wizardPhaseUploadSub: "Tələb olunan faylları əlavə edin",
      wizardPhaseResult: "Nəticələri əldə edin",
      wizardPhaseResultSub: "Dashboardu yoxlayın",
      wizardSelectTitle: "Nəzarət paketini seçin",
      wizardSelectText: "Layihədə əsas problemi seçin. DevBareun uyğun dashboard və yükləmə məntiqini hazırlayacaq.",
      analysisAllDescLong: "Qrafik, işçi qüvvəsi, xərc, F-2, material, risk və qərarların tam nəzarəti",
      analysisAllBadge: "Tövsiyə olunur",
      packageScheduleKicker: "Qrafik + işçi",
      packageCostKicker: "Smeta + F-2",
      packageFullKicker: "Bütün modullar",
      analysisScheduleBadge: "Bərpa planı",
      analysisCostBadge: "Kommersiya nəzarəti",
      packageComboTitle: "Seçilmiş paket: Tam layihə nəzarəti",
      packageComboText: "Rəhbərlik qərarları və hesabatı üçün tam layihə nəzarət görünüşü.",
      wizardUploadTitle: "Tələb olunan məlumatları yükləyin",
      wizardUploadText: "Seçilmiş nəzarət paketi üçün tələb olunan faylları yükləyin. Dəstəklənən formatlar aşağıda göstərilib.",
      wizardDropTitle: "Faylları buraya sürükləyin və ya seçin",
      wizardDropText: "Excel, CSV, PDF və XER / XML formatları dəstəklənir.",
      supportedFileFormats: "Dəstəklənən fayl formatları",
      dataInfoTitle: "Tələb olunan məlumat məntiqi",
      dataInfoText: "Tələb olunan plan və faktiki məlumat seçilmiş paketə görə dəyişir.",
      showRequirements: "Tələbləri göstər",
      startAnalysisCta: "Ön baxış yarat",
      template_all_title: "Tam layihə nəzarəti",
      template_all_text: "Smeta, F-2, qrafik, işçi sayı, material və risk fayllarını yükləyin. Peşəkar şablonda hər məlumat növü üçün ayrıca vərəq var.",
      template_cost_title: "Xərc və F-2 nəzarəti",
      template_cost_text: "Smeta bazasını, F-2 / ara ödəniş və ya faktiki xərc məlumatlarını yükləyin. DevBareun büdcə, görülmüş iş, qalıq dəyər və ödəniş riskini müqayisə edir.",
      template_schedule_title: "Qrafik bərpası",
      template_schedule_text: "Plan qrafiki, faktiki icra və işçi sayı məlumatlarını yükləyin. DevBareun gecikmə, resurs fərqi və bərpa tədbirlərini bir dashboardda birləşdirir.",
      template_material_title: "Material davamlılığı",
      template_material_text: "Material qalığı, çatdırılma, satınalma və ya sərfiyyat məlumatlarını yükləyin. DevBareun çatışmazlığı, tədarük riskini və davamlılıq tədbirlərini göstərir.",
      template_risk_title: "Risk və qərarlar",
      template_risk_text: "Risk qeydləri, sahə qeydləri, xərc/qrafik siqnalları və qərar məlumatlarını yükləyin. DevBareun qərar yönümlü risk paneli yaradır.",
      template_workforce_title: "İşçi qüvvəsi",
      template_workforce_text: "İş həcmi, plan müddəti və faktiki işçi sayı yükləyin. DevBareun tələb olunan işçi sayını, real müddəti və gecikmə riskini yoxlayır.",
      template_progress_title: "F-2 / Smeta üzrə icra",
      template_progress_text: "F-2 aktları, plan/fakt hesabatları və görülmüş iş cədvəllərini yükləyin. Peşəkar şablon məcburi deyil; öz fayllarınızı da yükləyə bilərsiniz."
    }
  };

  const requirements = {
    en: {
      all: {title: "Full Project Control requires all core project-control datasets", baseline: ["Cost estimate / smeta or contract baseline", "Baseline schedule / planned progress", "Material/procurement baseline if available"], actual: ["Progress payment or actual cost", "Actual progress / actual finish / forecast update", "Actual workforce, material, site notes or risk records"], guard: "Full Project Control consolidates schedule recovery, cost/payment control, material continuity and executive risk. Missing actual data is shown as missing; comparison values are not invented."},
      cost: {title: "Cost & Payment Control requires cost baseline and progress payment evidence", baseline: ["Cost Estimate / Smeta / BOQ", "Contract amount or approved budget", "Work package totals, VAT and approved variations if available"], actual: ["Progress Payment", "Actual completed amount or paid amount", "Remaining value, advance offset or current/cumulative payment split"], guard: "Cost variance, completed amount and payment risk are calculated only when actual cost or progress payment data is detected or confirmed."},
      schedule: {title: "Schedule Recovery requires schedule status and workforce evidence", baseline: ["Activity ID, WBS or activity name", "Planned start / planned finish / baseline duration", "Planned workforce or target productivity assumptions"], actual: ["Actual progress %, completed quantity or forecast finish", "Actual worker count / crew records", "Site status update or report date"], guard: "Recovery logic connects delay and workforce gap. If actual progress or manpower is missing, DevBareun generates a review note instead of inventing a recovery plan."},
      material: {title: "Material Continuity requires stock, delivery and consumption evidence", baseline: ["Material list / BOQ material baseline", "Planned procurement dates", "Minimum stock or delivery targets"], actual: ["Current stock or warehouse records", "Supplier delivery status", "Site consumption / shortage notes"], guard: "Continuity risk is shown only from detected stock, delivery or procurement evidence; missing data is shown as a confirmation need."},
      risk: {title: "Risk & Decisions requires confirmed project risk signals", baseline: ["Risk categories or decision topics", "Approved baseline assumptions", "Management thresholds"], actual: ["Open issues and site notes", "Cost, schedule, material or workforce risk evidence", "Owner/contractor decisions and required actions"], guard: "Decision prompts are generated from detected evidence and missing data is flagged instead of being invented."}
    },
    az: {
      all: {title: "Tam layihə nəzarəti üçün bütün əsas layihə nəzarət məlumatları lazımdır", baseline: ["Smeta / müqavilə bazası", "Plan qrafiki / plan icra", "Material / təchizat bazası varsa"], actual: ["F-2 / faktiki xərc", "Faktiki icra / faktiki bitmə / proqnoz yeniləməsi", "Faktiki işçi sayı, material, sahə qeydi və ya risk qeydləri"], guard: "Tam layihə nəzarəti qrafik bərpası, xərc və F-2 nəzarəti, material davamlılığı və rəhbərlik risk xülasəsini birləşdirir. Faktiki məlumat yoxdursa, müqayisə uydurulmur."},
      cost: {title: "Xərc və F-2 nəzarəti üçün smeta bazası və F-2 sübutu lazımdır", baseline: ["Smeta / BOQ / xərc hesablaması", "Müqavilə dəyəri və ya təsdiqlənmiş büdcə", "İş bölmələri üzrə yekunlar, ƏDV və təsdiqlənmiş dəyişikliklər varsa"], actual: ["F-2 / smeta üzrə icra", "Faktiki görülmüş işin məbləği və ya ödənilmiş məbləğ", "Qalıq dəyər, avans azaldılması və ya cari/yığılmış ödəniş bölgüsü"], guard: "Xərc fərqi, görülmüş iş məbləği və ödəniş riski yalnız faktiki xərc və ya F-2 məlumatı tapıldıqda və ya təsdiqləndikdə hesablanır."},
      schedule: {title: "Qrafik bərpası üçün qrafik vəziyyəti və işçi sayı məlumatı lazımdır", baseline: ["Activity ID, WBS və ya iş adı", "Plan başlanğıc / plan bitmə / plan müddəti", "Plan işçi sayı və ya məhsuldarlıq hədəfi"], actual: ["Faktiki icra %, tamamlanmış həcm və ya proqnoz bitmə", "Faktiki işçi sayı / briqada qeydləri", "Sahə statusu və ya hesabat tarixi"], guard: "Bərpa məntiqi gecikmə və işçi qüvvəsi fərqini birləşdirir. Faktiki icra və ya işçi sayı yoxdursa, DevBareun uydurma bərpa planı yaratmır, yoxlama qeydi göstərir."},
      material: {title: "Material davamlılığı üçün qalıq, çatdırılma və sərfiyyat sübutu lazımdır", baseline: ["Material siyahısı / BOQ material bazası", "Planlaşdırılmış tədarük tarixləri", "Minimum qalıq və ya çatdırılma hədəfləri"], actual: ["Cari qalıq və ya anbar qeydləri", "Təchizatçı çatdırılma statusu", "Sahə sərfiyyatı və çatışmazlıq qeydləri"], guard: "Davamlılıq riski yalnız qalıq, çatdırılma və ya satınalma sübutu əsasında göstərilir; çatışmayan məlumat təsdiq tələbi kimi göstərilir."},
      risk: {title: "Risk və qərarlar üçün təsdiqlənmiş layihə risk siqnalları lazımdır", baseline: ["Risk kateqoriyaları və ya qərar mövzuları", "Təsdiqlənmiş baza fərziyyələri", "Rəhbərlik hədləri"], actual: ["Açıq məsələlər və sahə qeydləri", "Xərc, qrafik, material və ya işçi qüvvəsi risk sübutları", "Sifarişçi/podratçı qərarları və tələb olunan tədbirlər"], guard: "Qərar siqnalları tapılmış sübutlara əsasən yaradılır, çatışmayan məlumat isə uydurulmadan göstərilir."}
    }
  };

  function updateRequirements() {
    const current = lang();
    const type = selectedType();
    const data = (requirements[current] && requirements[current][type]) || requirements.en.all;
    const title = $('#requirementsTitle');
    const baseList = $('#baselineRequirements');
    const actualList = $('#actualRequirements');
    const guard = $('#requirementsGuardrail');
    if (title) title.textContent = data.title;
    if (baseList) baseList.innerHTML = data.baseline.map(item => `<li>${item}</li>`).join('');
    if (actualList) actualList.innerHTML = data.actual.map(item => `<li>${item}</li>`).join('');
    if (guard) guard.textContent = data.guard;
  }

  function translateStatic() {
    const current = lang();
    const dict = t[current] || t.en;
    $$('[data-i18n-ext]').forEach(el => {
      const key = el.getAttribute('data-i18n-ext');
      if (dict[key]) el.textContent = dict[key];
    });
    updateTemplateAssist();
    updateRequirements();
  }

  function selectedType() {
    const active = $('.analysis-type-card.active[data-analysis-type]');
    return active ? active.getAttribute('data-analysis-type') : 'all';
  }

  function updateTemplateAssist() {
    const current = lang();
    const dict = t[current] || t.en;
    const type = selectedType();
    const title = $('#templateTitle');
    const text = $('#templateText');
    if (title && dict[`template_${type}_title`]) title.textContent = dict[`template_${type}_title`];
    if (text && dict[`template_${type}_text`]) text.textContent = dict[`template_${type}_text`];
    updateRequirements();
  }

  // Ensure backend-integration English updates do not overwrite visible selected-analysis copy.
  document.addEventListener('click', event => {
    if (event.target.closest('[data-analysis-type]')) {
      setTimeout(updateTemplateAssist, 0);
      setTimeout(updateTemplateAssist, 30);
    }
  }, true);

  document.addEventListener('devbareun:lang', translateStatic);
  document.addEventListener('DOMContentLoaded', translateStatic);
  window.addEventListener('load', translateStatic);
  translateStatic();
})();
