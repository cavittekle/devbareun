import {
  BarChart3,
  CalendarClock,
  FileBarChart,
  FileText,
  FolderKanban,
  Gauge,
  Settings,
  ShieldAlert,
  UploadCloud,
  WalletCards,
  X
} from "lucide-react";

const navigation = [
  { label: "Overview", icon: Gauge },
  { label: "Projects", icon: FolderKanban },
  { label: "Schedule", icon: CalendarClock },
  { label: "Cost", icon: WalletCards },
  { label: "Risk", icon: ShieldAlert },
  { label: "Reports", icon: FileBarChart },
  { label: "Documents", icon: FileText },
  { label: "Upload", icon: UploadCloud },
  { label: "Settings", icon: Settings }
];

export default function Sidebar({ activeSection, isOpen, onClose, onSectionChange }) {
  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-slate-950/70 backdrop-blur-sm transition lg:hidden ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-80 max-w-[86vw] flex-col border-r border-slate-200/70 bg-white/90 p-5 shadow-2xl backdrop-blur-2xl transition duration-300 dark:border-cyan-300/15 dark:bg-slate-950/90 lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-center justify-between">
          <a className="flex items-center gap-3" href="/index.html" aria-label="DevBareun landing">
            <img className="h-10 w-10 rounded-2xl object-contain" src="/assets/devbareun-symbol-white.svg" alt="DevBareun" />
            <div>
              <div className="text-lg font-black tracking-tight text-slate-950 dark:text-white">
                Dev<span className="text-cyanAccent">Bareun</span>
              </div>
              <div className="text-[10px] font-black uppercase tracking-[0.24em] text-slate-500 dark:text-cyan-200/70">
                Project Control
              </div>
            </div>
          </a>
          <button className="db-button px-3 lg:hidden" type="button" onClick={onClose} aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>

        <div className="mb-3 flex items-center justify-between text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
          <span>Main Workspace</span>
          <span className="rounded-full bg-cyan-300/10 px-2 py-1 text-cyanAccent">Live</span>
        </div>

        <nav className="grid flex-1 content-start gap-2 overflow-y-auto pr-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.label;
            return (
              <button
                aria-current={isActive ? "page" : undefined}
                className={`group flex items-center gap-3 rounded-2xl border px-3 py-3 text-left text-sm font-black transition ${
                  isActive
                    ? "border-cyan-300/50 bg-cyan-300/12 text-slate-950 shadow-glow dark:text-white"
                    : "border-transparent text-slate-600 hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white"
                }`}
                key={item.label}
                type="button"
                onClick={() => {
                  onSectionChange(item.label);
                  onClose();
                }}
              >
                <span
                  className={`grid h-10 w-10 place-items-center rounded-2xl ${
                    isActive
                      ? "bg-cyan-300/20 text-cyanAccent"
                      : "bg-slate-100 text-slate-500 group-hover:text-cyanAccent dark:bg-white/[0.06]"
                  }`}
                >
                  <Icon size={18} />
                </span>
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="mt-5 grid gap-3">
          <div className="rounded-3xl border border-cyan-300/25 bg-cyan-300/10 p-4">
            <div className="mb-2 flex items-center justify-between text-sm font-black text-slate-950 dark:text-white">
              <span>Plus workspace</span>
              <span className="text-cyanAccent">3/5</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
              <div className="h-full w-3/5 rounded-full bg-gradient-to-r from-cyanAccent to-purpleAccent" />
            </div>
            <p className="mt-2 text-xs font-bold text-slate-500 dark:text-slate-400">Monthly project review usage</p>
          </div>

          <div className="rounded-3xl border border-purple-400/25 bg-purple-400/10 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-black text-slate-950 dark:text-white">
            <BarChart3 size={17} className="text-purpleAccent" />
            Executive view
          </div>
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
            Portfolio status, cost pressure and risk signals are grouped for leadership review.
          </p>
          </div>
        </div>
      </aside>
    </>
  );
}
