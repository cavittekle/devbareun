// Upload picker reliability fix
(function(){
  function bindUploadPickerFix(){
    const input = document.querySelector('#fileInput') || document.querySelector('input[type="file"]');
    const drop = document.querySelector('#dropZone');
    const chooseBtn = document.querySelector('[data-i18n="uploadBtn"]');
    if(!input) return;

    if(chooseBtn && !chooseBtn.dataset.pickerFix){
      chooseBtn.dataset.pickerFix = "true";
      chooseBtn.addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        input.click();
      });
    }

    if(drop && !drop.dataset.pickerFix){
      drop.dataset.pickerFix = "true";
      drop.addEventListener('keydown', function(e){
        if(e.key === "Enter" || e.key === " "){
          e.preventDefault();
          input.click();
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', bindUploadPickerFix);
  bindUploadPickerFix();
})();
