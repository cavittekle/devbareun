(function(){
  const dict = {
    en: {
      resultEyebrow:'Generated project report',
      resultTitle:'Your project panel is ready.',
      resultLead:'Review the key project indicators, risk register and recommended management actions below.', paidResult:'Paid result', forecastTitle:'Estimated completion date', forecastText:'Based on the current delay, the projected completion date moves 24 days beyond the baseline target.', baselineFinish:'Baseline finish', delayImpact:'Delay impact', trendDelay:'worse than baseline', howCalculated:'How calculated?', scoreMethodText:'Risk score combines schedule gap, cost variance, workforce gap, procurement pressure and quality signals. Higher score means higher management attention is required.',
      projectLabel:'Project',
      reportIdLabel:'Report ID',
      dateLabel:'Date',
      downloadPdf:'Download PDF',
      downloadExcel:'Download Excel',
      reportLanguage:'Report language',
      shareLink:'Share Link',
      statusHigh:'At Risk',
      execSummaryTitle:'Executive Summary',
      execSummaryText:'The project is behind the planned baseline. Current actual execution is 14 percentage points below plan, with schedule pressure concentrated in structural and MEP activities. Recovery requires workforce adjustment, weekly plan/fact tracking and focused control of critical work packages.',
      riskScore:'Risk Score', riskScoreLegend:'Risk score not available', chartPlan:'Plan —', chartActual:'Actual —', chartGap:'Gap —', riskBarSchedule:'Schedule', riskBarCost:'Cost', riskBarLabor:'Labor', riskBarProcurement:'Procurement', riskBarQuality:'Quality', levelHigh:'High', levelMedium:'Medium', levelNormal:'Normal', riskCount:'0 risks',
      plannedExecution:'Planned execution',
      actualExecution:'Actual execution level',
      baseline:'Baseline target',
      delay:'Delay',
      days:'days',
      costVariance:'Cost variance',
      aboveBudget:'above baseline',
      workforce:'Workforce',
      requiredWorkforce:'required: 160',
      riskLevel:'Risk level',
      actionNeeded:'management action needed',
      planActualChart:'Plan and actual execution',
      riskRadar:'Risk Radar',
      costStatus:'Cost Status',
      forecastOverrun:'Forecast overrun',
      costStatusText:'Cost pressure is mainly linked to delayed work packages and material consumption variance.',
      workforceStatus:'Workforce Status',
      current:'Current',
      required:'Required',
      gap:'Gap',
      riskRegister:'Risk Register',
      risk:'Risk',
      level:'Level',
      reason:'Reason',
      action:'Action',
      riskSchedule:'Schedule delay',
      reasonSchedule:'Actual execution is below baseline.',
      actionSchedule:'Increase critical activity workforce.',
      riskCost:'Cost variance',
      reasonCost:'Material and labor burn rate is increasing.',
      actionCost:'Review cost packages weekly.',
      riskLabor:'Workforce gap',
      reasonLabor:'Current workforce is below recovery requirement.',
      actionLabor:'Add 18 workers to critical crews.',
      riskProcurement:'Procurement delay',
      reasonProcurement:'Selected materials require follow-up.',
      actionProcurement:'Confirm supplier dates and alternatives.',
      recommendedActions:'Recommended Actions',
      rec1:'Increase workforce on critical structural and MEP activities.',
      rec2:'Track plan and actual execution weekly until the gap closes.',
      rec3:'Prepare a recovery schedule for delayed activities.',
      rec4:'Review cost variance by work package.'
    },
    az: {
      resultEyebrow:'Yaradılmış layihə hesabatı',
      resultTitle:'Layihə nəticə panelinuz hazırdır.',
      resultLead:'Əsas layihə göstəricilərinə, risk reyestrinə və tövsiyə olunan idarəetmə tədbirlərinə aşağıda baxın.', paidResult:'Ödənişli nəticə', forecastTitle:'Təxmini tamamlanma tarixi', forecastText:'Cari gecikmə əsasında proqnozlaşdırılan tamamlanma tarixi plan hədəfindən 24 gün sonraya keçir.', baselineFinish:'Plan üzrə bitmə tarixi', delayImpact:'Gecikmə təsiri', trendDelay:'plan göstəricisindən pisdir', howCalculated:'Necə hesablanır?', scoreMethodText:'Risk balı qrafik fərqi, xərc fərqi, işçi sayı çatışmazlığı, təchizat təzyiqi və keyfiyyət siqnallarını birləşdirir. Bal yüksəldikcə idarəetmə diqqəti artırılmalıdır.',
      projectLabel:'Layihə',
      reportIdLabel:'Hesabat ID',
      dateLabel:'Tarix',
      downloadPdf:'PDF yüklə',
      downloadExcel:'Excel yüklə',
      reportLanguage:'Hesabat dili',
      shareLink:'Link paylaş',
      statusHigh:'Risk altındadır',
      execSummaryTitle:'Rəhbərlik xülasəsi',
      execSummaryText:'Layihə plan göstəricilərindən geri qalır. Faktiki icra səviyyəsi plan üzrə icradan 14 faiz bəndi aşağıdır və əsas təzyiq konstruktiv və MEP işlərində toplanır. Bərpa üçün işçi sayı tənzimlənməli, plan/faktiki icra həftəlik izlənməli və kritik iş paketləri fokusda saxlanılmalıdır.',
      riskScore:'Risk balı', riskScoreLegend:'Risk balı mövcud deyil', chartPlan:'Plan —', chartActual:'Faktiki —', chartGap:'Fərq —', riskBarSchedule:'Qrafik', riskBarCost:'Xərc', riskBarLabor:'İşçi qüvvəsi', riskBarProcurement:'Təchizat', riskBarQuality:'Keyfiyyət', levelHigh:'Yüksək', levelMedium:'Orta', levelNormal:'Normal', riskCount:'0 risk',
      plannedExecution:'Plan üzrə icra',
      actualExecution:'Faktiki icra səviyyəsi',
      baseline:'Plan göstəricisi',
      delay:'Gecikmə',
      days:'gün',
      costVariance:'Xərc fərqi',
      aboveBudget:'plan göstəricisindən yuxarı',
      workforce:'İşçi sayı',
      requiredWorkforce:'tələb: 160',
      riskLevel:'Risk səviyyəsi',
      actionNeeded:'idarəetmə tədbiri lazımdır',
      planActualChart:'Plan və faktiki icra',
      riskRadar:'Risk radarı',
      costStatus:'Xərc vəziyyəti',
      forecastOverrun:'Proqnozlaşdırılan xərc artımı',
      costStatusText:'Xərc təzyiqi əsasən gecikmiş iş paketləri və material sərfiyyatı fərqi ilə əlaqəlidir.',
      workforceStatus:'İşçi sayı vəziyyəti',
      current:'Cari',
      required:'Tələb olunan',
      gap:'Fərq',
      riskRegister:'Risk reyestri',
      risk:'Risk',
      level:'Səviyyə',
      reason:'Səbəb',
      action:'Tədbir',
      riskSchedule:'Qrafik gecikməsi',
      reasonSchedule:'Faktiki icra plan göstəricisindən aşağıdır.',
      actionSchedule:'Kritik fəaliyyətlərdə işçi sayı artırılsın.',
      riskCost:'Xərc fərqi',
      reasonCost:'Material və əmək xərcləri üzrə sərfiyyat artır.',
      actionCost:'İş paketləri üzrə xərc həftəlik yoxlanılsın.',
      riskLabor:'İşçi sayı çatışmazlığı',
      reasonLabor:'Cari işçi sayı bərpa tələbindən aşağıdır.',
      actionLabor:'Kritik briqadalara 18 işçi əlavə edilsin.',
      riskProcurement:'Təchizat gecikməsi',
      reasonProcurement:'Seçilmiş materiallar üzrə əlavə izləmə tələb olunur.',
      actionProcurement:'Təchizat tarixləri və alternativlər təsdiqlənsin.',
      recommendedActions:'Tövsiyə olunan tədbirlər',
      rec1:'Kritik konstruktiv və MEP işlərində işçi sayı artırılsın.',
      rec2:'Plan və faktiki icra fərqi bağlanana qədər həftəlik izlənilsin.',
      rec3:'Gecikmiş fəaliyyətlər üçün bərpa qrafiki hazırlansın.',
      rec4:'Xərc fərqi iş paketləri üzrə yoxlanılsın.'
    }
  };

  function applyResultLang(){
    const lang = localStorage.getItem('devbareun_lang') === 'az' ? 'az' : 'en';
    document.querySelectorAll('[data-r-i18n]').forEach(el => {
      const key = el.getAttribute('data-r-i18n');
      if(el.dataset.dbDynamic === 'true' || el.closest('[data-db-dynamic="true"]')) return; if(dict[lang] && dict[lang][key]) el.textContent = dict[lang][key];
    });
    if (lang === 'az' && window.DevBareunI18n && typeof window.DevBareunI18n.translateNode === 'function') {
      window.DevBareunI18n.translateNode(document.body);
    }
  }

  applyResultLang();
  document.addEventListener('devbareun:lang', () => {
    applyResultLang();
    const select = document.getElementById('reportLangSelect');
    const lang = localStorage.getItem('devbareun_lang') === 'az' ? 'az' : 'en';
    if (select && !localStorage.getItem('devbareun_report_lang')) select.value = lang;
  });
  document.querySelectorAll('.langBtn').forEach(btn => btn.addEventListener('click', () => setTimeout(applyResultLang, 0)));

  document.querySelectorAll('.score-info').forEach(btn => {
    btn.addEventListener('click', () => {
      const box = btn.parentElement ? btn.parentElement.querySelector('.score-method') : null;
      if(!box) return;
      const open = box.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
    });
  });

})();
