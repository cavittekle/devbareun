// DevBareun v0.6.2 — full EN/AZ upload terminology and construction-sector copy
(function () {
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const $ = (sel, root = document) => root.querySelector(sel);
  const lang = () => localStorage.getItem("devbareun_lang") || "en";

  const t = {
    en: {
      stepSelectAnalysis: "Select analysis type",
      analysisAllTitle: "Full Dashboard",
      analysisAllDesc: "Cost + progress + schedule + workforce signals",
      analysisCostTitle: "Cost Estimate",
      analysisCostDesc: "Cost estimate baseline + F-2 / actual cost for comparison",
      analysisScheduleTitle: "Schedule / Delay",
      analysisScheduleDesc: "Baseline schedule + actual progress for delay comparison",
      analysisWorkforceTitle: "Workforce",
      analysisWorkforceDesc: "Daily manpower, productivity norms, required crews and delay risk",
      analysisProgressTitle: "Progress Payment / Interim Payment (F-2)",
      analysisProgressDesc: "Plan/fact, F-2 certificates and physical execution",
      selectedAnalysisLabel: "Selected analysis",
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
      proofText: "Upload BOQ, cost estimate, progress payment / interim payment F-2 certificates, schedule exports and workforce sheets. DevBareun reviews detected sheets and highlights missing fields before generating reports.",
      proofBadge1: "BOQ / Cost Estimate",
      proofBadge2: "Progress Payment / Interim Payment (F-2)",
      proofBadge3: "Schedule Data",
      proofBadge4: "Workforce Sheets",
      proofBadge5: "PDF + Excel Output",
      proofCard1Title: "Project-control files",
      proofCard1Text: "Upload real construction cost, progress and schedule documents.",
      proofCard2Title: "BOQ, Cost Estimate & F-2",
      proofCard2Text: "Designed for cost estimate baselines and progress payment / interim payment workflows.",
      proofCard3Title: "Bilingual reporting",
      proofCard3Text: "English interface with Azerbaijani project data support.",
      proofCard4Title: "Data confirmation",
      proofCard4Text: "Detected sheets and missing fields are shown before final reporting.",
      priceNote: "per professional project analysis",
      privacyPolicy: "Privacy Policy",
      termsOfService: "Terms of Service",
      siteImagesTitle: "Site Images",
      outputTitle: "Output",

      wizardPhaseAnalysis: "Analysis type",
      wizardPhaseAnalysisSub: "Choose the right control view",
      wizardPhaseUpload: "Upload data",
      wizardPhaseUploadSub: "Add your files and review",
      wizardPhaseResult: "Get results",
      wizardPhaseResultSub: "Start the analysis",
      wizardSelectTitle: "Select analysis type",
      wizardSelectText: "Choose the analysis type that matches your goal. Required data will be shown automatically.",
      analysisAllDescLong: "Full review of cost, F-2, schedule and workforce indicators",
      analysisAllBadge: "Most complete analysis",
      wizardUploadTitle: "Upload data",
      wizardUploadText: "Upload the files required for the selected analysis. Supported formats are shown below.",
      wizardDropTitle: "Drag files here or choose",
      wizardDropText: "Excel, CSV, PDF and XER / XML formats are supported.",
      supportedFileFormats: "Supported file formats",
      dataInfoTitle: "About the data",
      dataInfoText: "File names should preferably avoid special characters and spaces.",
      showRequirements: "Show requirements",
      startAnalysisCta: "Start analysis",
      template_all_title: "Full Dashboard",
      template_all_text: "Upload cost estimate, F-2, schedule, workforce or equipment files. The professional template includes separate sheets for each data type.",
      template_cost_title: "Cost Estimate",
      template_cost_text: "Upload a cost estimate / smeta file and, for comparison, F-2 / interim payment or actual cost data. Professional template is optional; you can also upload your own files.",
      template_schedule_title: "Schedule / Delay",
      template_schedule_text: "Upload a baseline schedule and actual progress / forecast data. Without actual data, only a planning summary is generated.",
      template_workforce_title: "Workforce",
      template_workforce_text: "Upload activity quantities, planned duration and actual worker counts. DevBareun checks required workers, realistic duration and delay risk.",
      template_progress_title: "Progress Payment / Interim Payment (F-2)",
      template_progress_text: "Upload F-2 certificates, progress payment / interim payment files, plan/fact reports or completed work tables. Professional template is optional; you can also upload your own files."
    },
    az: {
      stepSelectAnalysis: "Analiz növünü seçin",
      analysisAllTitle: "Tam dashboard",
      analysisAllDesc: "Smeta + F-2 icra + qrafik + işçi sayı göstəriciləri",
      analysisCostTitle: "Smeta / Xərc hesablaması",
      analysisCostDesc: "Smeta bazası + F-2 / faktiki xərc müqayisəsi",
      analysisScheduleTitle: "Qrafik / Gecikmə",
      analysisScheduleDesc: "Plan qrafiki + faktiki icra üzrə gecikmə müqayisəsi",
      analysisWorkforceTitle: "İşçi qüvvəsi",
      analysisWorkforceDesc: "Gündəlik işçi sayı, məhsuldarlıq norması, tələb olunan briqada və gecikmə riski",
      analysisProgressTitle: "F-2 / Smeta üzrə icra",
      analysisProgressDesc: "Plan/fakt, F-2 aktları və fiziki icra vəziyyəti",
      selectedAnalysisLabel: "Seçilmiş analiz",
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

      wizardPhaseAnalysis: "Analiz növü",
      wizardPhaseAnalysisSub: "Uyğun analiz tipini seçin",
      wizardPhaseUpload: "Məlumat yükləyin",
      wizardPhaseUploadSub: "Fayllarınızı əlavə edin və yoxlayın",
      wizardPhaseResult: "Nəticələri əldə edin",
      wizardPhaseResultSub: "Analizə başlayın",
      wizardSelectTitle: "Analiz növünü seçin",
      wizardSelectText: "Məqsədinizə uyğun analiz tipini seçin. Seçdiyiniz analizə uyğun tələb olunan məlumatlar avtomatik göstəriləcək.",
      analysisAllDescLong: "Smeta, F-2, qrafik, işçi sayı və göstəricilərin tam təhlili",
      analysisAllBadge: "Ən geniş analiz",
      wizardUploadTitle: "Məlumatı yükləyin",
      wizardUploadText: "Seçilmiş analiz növü üçün tələb olunan faylları yükləyin. Dəstəklənən formatlar aşağıda göstərilib.",
      wizardDropTitle: "Faylları buraya sürükləyin və ya seçin",
      wizardDropText: "Excel, CSV, PDF və XER / XML formatları dəstəklənir.",
      supportedFileFormats: "Dəstəklənən fayl formatları",
      dataInfoTitle: "Məlumat haqqında",
      dataInfoText: "Fayl adlarında xüsusi işarələrdən və boşluqlardan istifadə edilməməsi tövsiyə olunur.",
      showRequirements: "Tələbləri göstər",
      startAnalysisCta: "Analizə başla",
      template_all_title: "Tam dashboard",
      template_all_text: "Smeta, F-2, qrafik, işçi sayı və ya texnika fayllarını yükləyin. Peşəkar şablonda hər məlumat növü üçün ayrıca vərəq var.",
      template_cost_title: "Smeta / Xərc hesablaması",
      template_cost_text: "Smeta / xərc hesablaması faylını və müqayisə üçün F-2, ara ödəniş və ya faktiki xərc məlumatını yükləyin. Peşəkar şablon məcburi deyil; öz fayllarınızı da yükləyə bilərsiniz.",
      template_schedule_title: "Qrafik / Gecikmə",
      template_schedule_text: "Plan qrafiki və faktiki icra / proqnoz məlumatını yükləyin. Faktiki məlumat yoxdursa, yalnız plan xülasəsi yaradılır.",
      template_workforce_title: "İşçi qüvvəsi",
      template_workforce_text: "İş həcmi, plan müddəti və faktiki işçi sayı yükləyin. DevBareun tələb olunan işçi sayını, real müddəti və gecikmə riskini yoxlayır.",
      template_progress_title: "F-2 / Smeta üzrə icra",
      template_progress_text: "F-2 aktları, plan/fakt hesabatları və görülmüş iş cədvəllərini yükləyin. Peşəkar şablon məcburi deyil; öz fayllarınızı da yükləyə bilərsiniz."
    }
  };

  const requirements = {
    en: {
      all: {title: "Upload baseline and actual data for a reliable executive comparison", baseline: ["Cost estimate / smeta or contract baseline", "Baseline schedule / planned progress", "Planned workforce or target values"], actual: ["Progress payment / interim payment (F-2) or actual cost", "Actual progress / actual finish / forecast update", "Actual workforce or site records"], guard: "If actual cost or actual progress is missing, DevBareun generates a baseline-only view and does not invent comparison results."},
      cost: {title: "Cost comparison requires a baseline cost and confirmed actual cost", baseline: ["Cost Estimate / Smeta / BOQ", "Contract amount or approved budget", "Work package amounts and totals"], actual: ["Progress Payment / Interim Payment (F-2)", "Actual completed amount or paid amount", "Remaining value, VAT status or approved variations if available"], guard: "Cost variance and actual execution are calculated only when actual cost / F-2 data is detected or confirmed."},
      schedule: {title: "Schedule comparison requires baseline plan and actual progress", baseline: ["Activity ID, WBS or activity name", "Planned start / planned finish", "Baseline duration and planned progress"], actual: ["Actual start / actual finish or forecast finish", "Actual progress % or completed quantity", "Status update or report date"], guard: "Delay and progress gap are not calculated unless actual progress or actual finish data is uploaded or entered."},
      workforce: {title: "Workforce planning requires activity quantity, planned duration and actual manpower", baseline: ["Activity / work type", "Quantity and unit", "Planned start/finish or planned duration"], actual: ["Actual worker count", "Trade / crew records", "Optional custom productivity rate"], guard: "Required workers and realistic duration are calculated only when activity quantity, unit, planned duration and actual workers are detected or confirmed."},
      progress: {title: "F-2 analysis requires smeta baseline and progress payment data", baseline: ["Smeta / contract total / Nokopitelni baseline", "Planned progress or planned amount if available", "Work package totals"], actual: ["F-2 / progress payment / interim payment sheets", "Current or cumulative completed amount", "Remaining amount or previous/current period split"], guard: "Actual execution is calculated only when completed amount can be linked to the smeta / contract baseline."}
    },
    az: {
      all: {title: "Etibarlı ümumi müqayisə üçün plan baza və faktiki məlumat yükləyin", baseline: ["Smeta / müqavilə bazası", "Plan qrafiki / plan icra", "Plan işçi sayı və ya hədəf göstəricilər"], actual: ["F-2 / ara ödəniş və ya faktiki xərc", "Faktiki icra / faktiki bitmə / proqnoz yeniləməsi", "Faktiki işçi sayı və ya sahə qeydləri"], guard: "Faktiki xərc və ya faktiki icra yoxdursa, DevBareun yalnız baza görünüşü yaradır və müqayisə nəticəsi uydurmur."},
      cost: {title: "Xərc müqayisəsi üçün smeta bazası və təsdiqlənmiş faktiki xərc lazımdır", baseline: ["Smeta / BOQ / xərc hesablaması", "Müqavilə dəyəri və ya təsdiqlənmiş büdcə", "İş bölmələri üzrə məbləğlər və yekunlar"], actual: ["F-2 / ara ödəniş / smeta üzrə icra", "Faktiki görülmüş işin məbləği və ya ödənilmiş məbləğ", "Qalıq dəyər, ƏDV statusu və təsdiqlənmiş dəyişikliklər varsa"], guard: "Xərc fərqi və faktiki icra yalnız faktiki xərc / F-2 məlumatı tapıldıqda və ya təsdiqləndikdə hesablanır."},
      schedule: {title: "Qrafik müqayisəsi üçün plan qrafiki və faktiki icra lazımdır", baseline: ["Activity ID, WBS və ya iş adı", "Plan başlanğıc / plan bitmə", "Plan müddəti və plan icra faizi"], actual: ["Faktiki başlanğıc / faktiki bitmə və ya proqnoz bitmə", "Faktiki icra % və ya tamamlanmış həcm", "Status yeniləməsi və ya hesabat tarixi"], guard: "Faktiki icra və ya faktiki bitmə məlumatı yüklənməyibsə, gecikmə və icra fərqi hesablanmır."},
      workforce: {title: "İşçi planlaması üçün iş həcmi, plan müddəti və faktiki işçi sayı lazımdır", baseline: ["İş növü", "Həcm və ölçü vahidi", "Plan başlanğıc/bitmə və ya plan müddəti"], actual: ["Faktiki işçi sayı", "İxtisas / briqada qeydləri", "İstəyə bağlı fərdi məhsuldarlıq norması"], guard: "Tələb olunan işçi sayı və real müddət yalnız iş həcmi, vahid, plan müddəti və faktiki işçi sayı tapıldıqda və ya təsdiqləndikdə hesablanır."},
      progress: {title: "F-2 analizi üçün smeta bazası və icra/ödəniş məlumatı lazımdır", baseline: ["Smeta / müqavilə yekunu / Nokopitelni bazası", "Plan icra və ya plan məbləği varsa", "İş bölmələri üzrə yekunlar"], actual: ["F-2 / ara ödəniş / smeta üzrə icra vərəqləri", "Cari və ya yığılmış görülmüş iş məbləği", "Qalıq məbləğ və ya əvvəlki/cari dövr bölgüsü"], guard: "Faktiki icra yalnız görülmüş iş məbləği smeta / müqavilə bazası ilə əlaqələndiriləndə hesablanır."}
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
