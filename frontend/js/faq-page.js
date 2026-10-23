(function(){
  const faqText = {
    en: {
      faqQ1:'How does DevBareun work?',
      faqA1:'DevBareun allows customers to upload construction project files and receive a structured dashboard and reporting view. The platform is designed to support project control, progress visibility, cost tracking and management reporting.',
      faqQ2:'Which project files can I upload?',
      faqA2:'Excel and CSV files are used for structured analysis. Text-based PDF files can be partially extracted. Primavera XER and MS Project XML schedule files are supported as schedule extraction beta. Site images can be uploaded as supporting visual evidence.',
      faqQ3:'How is the dashboard created?',
      faqA3:'The uploaded project data is processed and organized into key project control indicators such as planned progress, actual progress, delay status, cost variance, workforce indicators and risk levels.',
      faqQ4:'How does payment work?',
      faqA4:'DevBareun offers both a one-time and a subscription model. Single Project ($29) is a one-time payment for one analysis. Plus ($49/month) and Pro ($89/month) plans provide monthly analysis credits for teams with recurring project needs. In all cases, you upload files, review the preview, and unlock the dashboard once payment is confirmed.',
      faqQ5:'Which report formats will be available?',
      faqA5:'The reporting package includes a dashboard view, a PDF management report and an Excel-based analysis output. These formats are intended for project owners, construction managers and technical control teams.',
      faqQ6:'Is my project data secure?',
      faqA6:'Project data security is a core requirement for the platform. Uploaded files are protected with access control, secure authentication and controlled retention rules.',
      faqQ7:'Which payment options are available?',
      faqA7:'Single Project is a one-time $29 checkout. Plus is $49/month for 5 analysis credits, and Pro is $89/month for 20 analysis credits.',
      faqQ8:'Are Azerbaijani construction file formats supported?',
      faqA8:'Yes. DevBareun supports Azerbaijani construction workflows including smeta (BOQ), F-2 / Forma-2 progress payment documents and workforce data files. The platform is designed to detect common Azerbaijani column headers during upload review.',
      faqQ9:'How is uploaded project data protected?',
      faqA9:'Uploaded files are transferred through secure connections and kept behind account-level access controls. Access is limited to your workspace, and files can be deleted on request or when the related account is closed.',
      faqQ10:'Is there a free preview?',
      faqA10:'Yes. The upload preview and mapping review are available before payment. Payment is required only to unlock the full dashboard and report package.'
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
    faqQ4:'Ödəniş necə edilir?',
    faqA4:'DevBareun həm birdəfəlik, həm də abunəlik modeli təklif edir. Single Project ($29) bir analiz üçün birdəfəlik ödənişdir. Plus ($49/ay) və Pro ($89/ay) paketləri davamlı layihə ehtiyacı olan komandalar üçün aylıq analiz kreditləri verir. Bütün hallarda faylları yükləyir, önbaxışı yoxlayır və ödəniş təsdiqləndikdən sonra dashboardu açırsınız.',
    faqQ6:'Layihə məlumatlarım təhlükəsiz saxlanılırmı?',
    faqA6:'Layihə məlumatlarının təhlükəsizliyi platformanın əsas tələblərindən biridir. Yüklənmiş fayllar giriş nəzarəti, təhlükəsiz autentifikasiya və idarə olunan saxlanma qaydaları ilə qorunur.',
    faqQ7:'Hansı ödəniş seçimləri mövcuddur?',
    faqA7:'Single Project $29 birdəfəlik checkout-dur. Plus $49/ay üçün 5 analiz krediti, Pro isə $89/ay üçün 20 analiz krediti verir.',
    faqQ8:'Azərbaycan tikinti fayl formatları dəstəklənirmi?',
    faqA8:'Bəli. DevBareun smeta (BOQ), F-2 / Forma-2 icra aktları və işçi qüvvəsi cədvəlləri daxil olmaqla Azərbaycan tikinti iş axınlarını dəstəkləyir. Platforma yükləmə zamanı ümumi Azərbaycan sütun başlıqlarını tanımaq üçün hazırlanıb.',
    faqQ9:'Yüklənən layihə məlumatları necə qorunur?',
    faqA9:'Yüklənmiş fayllar təhlükəsiz bağlantılarla ötürülür və hesab səviyyəli giriş nəzarəti arxasında saxlanılır. Giriş yalnız workspace ilə məhdudlaşır; fayllar sorğu əsasında və ya hesab bağlandıqda silinə bilər.',
    faqQ10:'Ödənişsiz önbaxış var?',
    faqA10:'Bəli. Fayl yükləmə önbaxışı və mapping yoxlaması ödənişdən əvvəl mümkündür. Tam dashboard və hesabat paketini açmaq üçün ödəniş tələb olunur.'
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
        if(item) item.classList.toggle('open');
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
