(function(){
  const faqText = {
    en: {
      faqQ1:'How does DevBareun work?',
      faqA1:'You upload three documents: the planning (baseline schedule and actual progress at the data date), the current F2 and F3 certificates and the contract. DevBareun runs the construction execution and delay analysis and returns a delay dashboard plus the execution report: progress, SPI, schedule delay in days, forecast completion, critical path and delay responsibility.',
      faqQ2:'Which project files can I upload?',
      faqA2:'Three kinds of documents: the contract (PDF, Word, JPEG or PNG), the planning (Excel/CSV plan-actual tables, Primavera P6 XER, MS Project XML or .mpp, PDF) and the current F2 and F3 certificates (Excel, Word or PDF). All three are required. Delay is calculated from the Excel, CSV, XER or MS Project XML schedule; F2 amounts are compared with physical progress; the contract, PDF schedules and .mpp files are kept with the report as references. Column headers in English, Azerbaijani, Turkish and Russian are recognised.',
      faqQ3:'How is the delay calculated?',
      faqA3:'Planned progress at the data date comes from the baseline. SPI is actual % divided by planned %. Schedule delay is the number of days between the data date and the date on which the baseline reached today\'s actual progress (earned schedule). Forecast completion uses actual finishes, reported forecasts, production rates and predecessor logic, and the critical path comes from total float.',
      faqQ4:'How does payment work?',
      faqA4:'DevBareun offers both a one-time and a subscription model. Single Project ($29) is a one-time payment for one analysis. Plus ($49/month) and Pro ($89/month) plans provide monthly analysis credits for teams with recurring project needs. Plus gives 5 analysis credits a month and Pro gives 20. One credit runs one analysis.',
      faqQ5:'Which report formats will be available?',
      faqA5:'A delay dashboard in the workspace, and the execution and delay analysis report as PDF and Excel, in Azerbaijani or English.',
      faqQ6:'Is my project data secure?',
      faqA6:'Yes. Files are sent over encrypted connections, kept in private storage behind account-level access rules and opened only by you and the colleagues you share a project with. You can ask for them to be deleted at any time.',
      faqQ7:'Which payment options are available?',
      faqA7:'Single Project is a one-time $29 checkout. Plus is $49/month for 5 analysis credits, and Pro is $89/month for 20 analysis credits.',
      faqQ8:'How is responsibility for delay decided?',
      faqA8:'Each delay event carries a responsible party. Days are classified per calendar day: employer delay is excusable and compensable, neutral delay (for example weather) is excusable but not compensable, contractor delay is non-excusable, and days where employer and contractor delay overlap are counted as concurrent.',
      faqQ9:'How is uploaded project data protected?',
      faqA9:'Uploaded files are transferred through secure connections and kept behind account-level access controls. Access is limited to your workspace, and files can be deleted on request or when the related account is closed.',
      faqQ10:'Is there a free preview?',
      faqA10:'Yes. The example report is open to everyone, and the upload check shows which files were recognised before payment. Payment is required only to unlock the full report for your own project.'
    },
    az: {
      faqQ1:'DevBareun necə işləyir?',
      faqA1:'DevBareun müştərilərə tikinti layihə fayllarını yükləyərək strukturlaşdırılmış dashboard və hesabat görünüşü əldə etməyə imkan verən platforma kimi hazırlanır. Platforma layihə nəzarəti, işlərin gedişi üzrə görünürlük, xərc izlənməsi və idarəetmə hesabatlarını dəstəkləmək üçün nəzərdə tutulub.',
      faqQ2:'Hansı layihə fayllarını yükləyə bilərəm?',
      faqA2:'Strukturlaşdırılmış analiz əsasən Excel və CSV faylları üzərindən aparılır. Mətn əsaslı PDF fayllarından qismən məlumat çıxarıla bilər. Primavera XER və MS Project XML qrafik faylları beta qrafik çıxarışı kimi dəstəklənir. Sahə şəkilləri vizual sübut / əlavə sənəd kimi yüklənə bilər.',
      faqQ3:'Dashboard necə yaradılır?',
      faqA3:'Yüklənmiş layihə məlumatları plan üzrə icra, faktiki icra səviyyəsi, gecikmə vəziyyəti, xərc fərqi, işçi göstəriciləri və risk səviyyələri kimi əsas layihə nəzarəti göstəricilərinə çevrilir.',
      faqQ4:'Ödəniş necə edilir?',
      faqA4:'İlk kommersiya modeli hər yaradılan analiz üçün birdəfəlik ödəniş kimi işləyir. Müştəri layihə fayllarını yükləyir, nəticəyə önbaxış edir, bir dəfə ödəniş edir və yaradılmış dashboard + hesabat paketini açır.',
      faqQ5:'Hesabat hansı formatlarda olacaq?',
      faqA5:'Hesabat paketinə dashboard görünüşü, PDF idarəetmə hesabatı və Excel əsaslı analiz nəticəsi daxildir. Bu formatlar sifarişçilər, tikinti menecerləri və texniki nəzarət komandaları üçün nəzərdə tutulur.',
      faqQ6:'Layihə məlumatlarım təhlükəsiz saxlanılırmı?',
      faqA6:'Layihə məlumatlarının təhlükəsizliyi platformanın əsas tələblərindən biridir. Yüklənmiş fayllar giriş nəzarəti, təhlükəsiz autentifikasiya və idarə olunan saxlanma qaydaları ilə qorunur.'
    }
  };
  Object.assign(faqText.az, {
    faqA5:'Workspace-də gecikmə dashboardu və Azərbaycan və ya ingilis dilində PDF və Excel formatında icra və gecikmə analizi hesabatı.',
    faqA3:'Hesabat tarixinə plan icra baza qrafikdən hesablanır. SPI faktiki faizin plan faizə nisbətidir. Qrafik gecikməsi hesabat tarixi ilə baza qrafikin bugünkü faktiki icraya çatdığı tarix arasındakı gün sayıdır (qazanılmış qrafik). Proqnoz bitmə faktiki bitmə tarixləri, bildirilmiş proqnozlar, iş tempi və əlaqə məntiqi ilə, kritik yol isə ümumi ehtiyat vaxtla müəyyən edilir.',
    faqQ3:'Gecikmə necə hesablanır?',
    faqA2:'Üç növ sənəd: müqavilə (PDF, Word, JPEG və ya PNG), planlama (Excel/CSV plan-fakt cədvəlləri, Primavera P6 XER, MS Project XML və ya .mpp, PDF) və cari F2 və F3 aktları (Excel, Word və ya PDF). Hər üçü tələb olunur. Gecikmə Excel, CSV, XER və ya MS Project XML qrafikindən hesablanır; F2 məbləğləri fiziki icra ilə müqayisə olunur; müqavilə, PDF qrafiklər və .mpp faylları hesabata istinad kimi əlavə edilir. İngilis, Azərbaycan, türk və rus dillərində sütun başlıqları tanınır.',
    faqA1:'Üç sənəd yükləyirsiniz: planlama (baza qrafiki və hesabat tarixinə faktiki icra), cari F2 və F3 aktları və müqavilə. DevBareun tikinti layihəsinin icra və gecikmə analizini aparır və gecikmə dashboardu ilə icra hesabatını qaytarır: icra faizi, SPI, gün ilə qrafik gecikməsi, proqnoz bitmə tarixi, kritik yol və gecikmə məsuliyyəti.',
    faqQ4:'Ödəniş necə edilir?',
    faqA4:'DevBareun həm birdəfəlik, həm də abunəlik modeli təklif edir. Single Project ($29) bir analiz üçün birdəfəlik ödənişdir. Plus ($49/ay) və Pro ($89/ay) paketləri davamlı layihə ehtiyacı olan komandalar üçün aylıq analiz kreditləri verir. Plus ayda 5, Pro isə ayda 20 analiz krediti verir. Bir kredit bir analiz üçündür.',
    faqQ6:'Layihə məlumatlarım təhlükəsiz saxlanılırmı?',
    faqA6:'Bəli. Fayllar şifrələnmiş bağlantı ilə göndərilir, hesab səviyyəli giriş qaydaları ilə qapalı yaddaşda saxlanılır və yalnız siz və layihəni paylaşdığınız həmkarlar tərəfindən açılır. Faylların silinməsini istənilən vaxt istəyə bilərsiniz.',
    faqQ7:'Hansı ödəniş seçimləri mövcuddur?',
    faqA7:'Single Project $29 birdəfəlik checkout-dur. Plus $49/ay üçün 5 analiz krediti, Pro isə $89/ay üçün 20 analiz krediti verir.',
    faqQ8:'Gecikməyə görə məsuliyyət necə müəyyən edilir?',
    faqA8:'Hər gecikmə hadisəsində məsul tərəf göstərilir. Günlər təqvim günü üzrə təsnif edilir: sifarişçi gecikməsi üzrlü və kompensasiyalıdır, neytral gecikmə (məsələn hava şəraiti) üzrlüdür, amma kompensasiya edilmir, podratçı gecikməsi üzrsüzdür, sifarişçi və podratçı gecikmələrinin üst-üstə düşdüyü günlər isə eyni vaxtlı sayılır.',
    faqQ9:'Yüklənən layihə məlumatları necə qorunur?',
    faqA9:'Yüklənmiş fayllar təhlükəsiz bağlantılarla ötürülür və hesab səviyyəli giriş nəzarəti arxasında saxlanılır. Giriş yalnız workspace ilə məhdudlaşır; fayllar sorğu əsasında və ya hesab bağlandıqda silinə bilər.',
    faqQ10:'Ödənişsiz önbaxış var?',
    faqA10:'Bəli. Nümunə hesabat hamı üçün açıqdır, yükləmə yoxlaması isə ödənişdən əvvəl hansı faylların tanındığını göstərir. Ödəniş yalnız öz layihəniz üçün tam hesabatı açmaq üçün tələb olunur.'
  });

  function currentLang(){
    return localStorage.getItem('devbareun_lang') || document.documentElement.lang || 'en';
  }

  function applyFaqLang(){
    const lang = currentLang() === 'az' ? 'az' : 'en';
    document.querySelectorAll('[data-faq-key]').forEach(function(el){
      const key = el.getAttribute('data-faq-key');
      if(faqText[lang] && faqText[lang][key]) el.textContent = faqText[lang][key];
    });
  }

  function bindFaqAccordion(){
    document.querySelectorAll('.faq-question').forEach(function(btn){
      if(btn.dataset.bound === 'true') return;
      btn.dataset.bound = 'true';
      btn.addEventListener('click', function(){
        const item = btn.closest('.faq-item');
        if(item){ const open = item.classList.toggle('open'); btn.setAttribute('aria-expanded', String(open)); }
      });
    });
  }

  function bindSearch(){
    const search = document.getElementById('faqSearch');
    if(!search || search.dataset.bound === 'true') return;
    search.dataset.bound = 'true';
    search.addEventListener('input', function(){
      const q = search.value.toLowerCase().trim();
      document.querySelectorAll('.faq-item').forEach(function(item){
        item.style.display = item.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  applyFaqLang();
  bindFaqAccordion();
  bindSearch();

  document.addEventListener('devbareun:lang', applyFaqLang);
  document.querySelectorAll('.langBtn').forEach(function(btn){
    btn.addEventListener('click', function(){
      setTimeout(applyFaqLang, 0);
    });
  });
})();
