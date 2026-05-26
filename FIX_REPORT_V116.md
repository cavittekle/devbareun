# DevBareun v1.1.6 - AZ result-dashboard language and print-theme fix

## Scope
This patch fixes two issues reported from the generated Project Result Dashboard PDF:

1. Azerbaijani mode still displayed English backend-generated terms/sentences in the result dashboard and exported/printed report.
2. Browser print/PDF output was forced to a white page instead of preserving the dark dashboard theme.

## User-observed evidence
The uploaded PDF showed mixed AZ/EN terms such as:

- `Faktiki icra was detected... planned Baza progress...`
- `Dashboard Etibarlılıq`
- `F-2 sheets detected`, `Progress calculation`, `Planned progress`, `Progress gap`, `Detected sheets`, `Cost sheets`, `Progress sheets`
- `Review cost variance by work package...`
- `The uploaded files did not provide enough mapped KPI evidence...`
- `Upload a plan/fact, cost or workforce file with clear headers.`

It also showed that printed pages were rendered on a white page instead of matching the dashboard appearance.

## Changed files

```text
frontend/js/az-glossary.js
frontend/js/result-dynamic.js
frontend/js/result-schedule-progress.js
frontend/css/result-dashboard.css
```

## Fixes

### 1. Stronger AZ translation layer
`frontend/js/az-glossary.js` now includes additional exact terms, phrase rules and mixed-language cleanup rules for backend-generated dashboard text.

Examples now translated:

```text
Actual execution was detected at 99.05%, but planned baseline progress was not clearly mapped.
→ Faktiki icra 99.05% olaraq aşkar edildi, lakin plan baza icrası aydın uyğunlaşdırılmadı.

F-2 sheets detected
→ F-2 vərəqləri aşkarlandı

Progress calculation
→ İcra hesablaması

Dashboard confidence
→ Panel etibarlılığı

The uploaded files did not provide enough mapped KPI evidence for a full risk register.
→ Yüklənmiş fayllar tam risk reyestri üçün kifayət qədər uyğunlaşdırılmış KPI sübutu təqdim etmədi.
```

### 2. Dynamic dashboard translation after render
`frontend/js/result-dynamic.js` now runs the AZ translation pass after dynamic dashboard rendering. This captures text generated after initial page load.

### 3. Report/export language alignment
`frontend/js/result-dynamic.js` now aligns the report export language with the visible UI language. If the UI is Azerbaijani, PDF/Excel export requests use `lang=az` instead of stale `devbareun_report_lang=en` from localStorage.

### 4. Schedule/progress dashboard row translation
`frontend/js/result-schedule-progress.js` now translates dynamic activity labels, status chips and table status values.

### 5. Print theme preservation
`frontend/css/result-dashboard.css` now overrides print styles so browser print/PDF keeps the dark dashboard styling and uses exact print-color adjustment.

## Browser cache note
After deployment, clear stale localStorage/cache on `devbareun.com` if old language/API behavior remains:

```js
localStorage.removeItem("devbareun_report_lang");
localStorage.removeItem("devbareun_api_base");
location.reload();
```

Then press `Ctrl + F5`.
