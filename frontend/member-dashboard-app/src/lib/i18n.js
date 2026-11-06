import { useDelayLang } from "../components/DelayDashboard";

// The workspace language is shared by every view (see useDelayLang): it follows
// the public site's choice, sets <html lang> and updates all components at once.
export function useLang() {
  return useDelayLang();
}

/** Returns t(en, az): picks the string for the current workspace language. */
export function useT() {
  const [lang] = useDelayLang();
  return (en, az) => (lang === "az" ? az : en);
}
