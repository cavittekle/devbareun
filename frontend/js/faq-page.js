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
      faqQ1:'DevBareun nec? isl?yir?',
      faqA1:'DevBareun müst?ril?r? tikinti layih? fayllarini yükl?y?r?k strukturlasdirilmis dashboard v? hesabat görünüsü ?ld? etm?y? imkan ver?n platforma kimi hazirlanir. Platforma layih? n?zar?ti, isl?rin gedisi üzr? görünürlük, x?rc izl?nm?si v? idar?etm? hesabatlarini d?st?kl?m?k üçün n?z?rd? tutulub.',
      faqQ2:'Hansi layih? fayllarini yükl?y? bil?r?m?',
      faqA2:'Strukturlasdirilmis analiz ?sas?n Excel v? CSV fayllari üz?rind?n aparilir. M?tn ?sasli PDF fayllarindan qism?n m?lumat çixarila bil?r. Primavera XER v? MS Project XML qrafik fayllari beta qrafik çixarisi kimi d?st?kl?nir. Sah? s?kill?ri vizual sübut / ?lav? s?n?d kimi yükl?n? bil?r.',
      faqQ3:'Dashboard nec? yaradilir?',
      faqA3:'Yükl?nmis layih? m?lumatlari plan üzr? icra, faktiki icra s?viyy?si, gecikm? v?ziyy?ti, x?rc f?rqi, isçi göst?ricil?ri v? risk s?viyy?l?ri kimi ?sas layih? n?zar?ti göst?ricil?rin? çevrilir.',
      faqQ4:'Öd?nis nec? edilir?',
      faqA4:'Ilk kommersiya modeli h?r yaradilan analiz üçün bird?f?lik öd?nis kimi isl?yir. Müst?ri layih? fayllarini yükl?yir, n?tic?y? önbaxis edir, bir d?f? öd?nis edir v? yaradilmis dashboard + hesabat paketini açir.',
      faqQ5:'Hesabat hansi formatlarda olacaq?',
      faqA5:'Hesabat paketin? dashboard görünüsü, PDF idar?etm? hesabati v? Excel ?sasli analiz n?tic?si daxildir. Bu formatlar sifarisçil?r, tikinti menecerl?ri v? texniki n?zar?t komandalari üçün n?z?rd? tutulur.',
      faqQ6:'Layih? m?lumatlarim t?hlük?siz saxlanilirmi?',
      faqA6:'Layih? m?lumatlarinin t?hlük?sizliyi platformanin ?sas t?l?bl?rind?n biridir. Yükl?nmis fayllar giris n?zar?ti, t?hlük?siz autentifikasiya v? idar? olunan saxlanma qaydalari il? qorunur.'
    }
  };
  Object.assign(faqText.az, {
    faqQ4:'Öd?nis nec? edilir?',
    faqA4:'DevBareun h?m bird?f?lik, h?m d? abun?lik modeli t?klif edir. Single Project ($29) bir analiz üçün bird?f?lik öd?nisdir. Plus ($49/ay) v? Pro ($89/ay) paketl?ri davamli layih? ehtiyaci olan komandalar üçün ayliq analiz kreditl?ri verir. Bütün hallarda fayllari yükl?yir, önbaxisi yoxlayir v? öd?nis t?sdiql?ndikd?n sonra dashboardu açirsiniz.',
    faqQ6:'Layih? m?lumatlarim t?hlük?siz saxlanilirmi?',
    faqA6:'Layih? m?lumatlarinin t?hlük?sizliyi platformanin ?sas t?l?bl?rind?n biridir. Yükl?nmis fayllar giris n?zar?ti, t?hlük?siz autentifikasiya v? idar? olunan saxlanma qaydalari il? qorunur.',
    faqQ7:'Hansi öd?nis seçiml?ri mövcuddur?',
    faqA7:'Single Project $29 bird?f?lik checkout-dur. Plus $49/ay üçün 5 analiz krediti, Pro is? $89/ay üçün 20 analiz krediti verir.',
    faqQ8:'Az?rbaycan tikinti fayl formatlari d?st?kl?nirmi?',
    faqA8:'B?li. DevBareun smeta (BOQ), F-2 / Forma-2 icra aktlari v? isçi qüvv?si c?dv?ll?ri daxil olmaqla Az?rbaycan tikinti is axinlarini d?st?kl?yir. Platforma yükl?m? zamani ümumi Az?rbaycan sütun basliqlarini tanimaq üçün hazirlanib.',
    faqQ9:'Yükl?n?n layih? m?lumatlari nec? qorunur?',
    faqA9:'Yükl?nmis fayllar t?hlük?siz baglantilarla ötürülür v? hesab s?viyy?li giris n?zar?ti arxasinda saxlanilir. Giris yalniz workspace il? m?hdudlasir; fayllar sorgu ?sasinda v? ya hesab baglandiqda silin? bil?r.',
    faqQ10:'Öd?nissiz önbaxis var?',
    faqA10:'B?li. Fayl yükl?m? önbaxisi v? mapping yoxlamasi öd?nisd?n ?vv?l mümkündür. Tam dashboard v? hesabat paketini açmaq üçün öd?nis t?l?b olunur.'
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
