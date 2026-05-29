import { Bell, Check, ChevronDown, CreditCard, LogOut, Menu, Moon, RefreshCcw, Search, Settings, Sun, UserRound } from "lucide-react";
import { dateRanges } from "../data/dashboardMockData.js";

const notificationStyles = {
  Critical: "border-red-400/45 bg-red-400/10 text-red-300",
  Ready: "border-emerald-400/35 bg-emerald-400/10 text-emerald-400",
  Watch: "border-yellow-300/40 bg-yellow-300/10 text-yellow-300",
  Missing: "border-orange-400/45 bg-orange-400/10 text-orange-300"
};

export default function Topbar({
  activeSection,
  dateRange,
  isNotificationsOpen,
  isProfileMenuOpen,
  isProjectMenuOpen,
  notifications,
  apiState,
  onDateRangeChange,
  onNotificationsClose,
  onNotificationsToggle,
  onProjectChange,
  onProjectMenuClose,
  onProjectMenuToggle,
  onProfileMenuClose,
  onProfileMenuToggle,
  onRefreshDashboard,
  onSectionChange,
  onSidebarToggle,
  onThemeToggle,
  projectOptions,
  selectedProject,
  theme
}) {
  const activeProject = projectOptions.find((project) => project.id === selectedProject) || projectOptions[0];

  return (
    <header className="sticky top-0 z-20 -mx-4 mb-6 border-b border-slate-200/70 bg-slate-50/80 px-4 py-4 backdrop-blur-2xl dark:border-cyan-300/10 dark:bg-[#020713]/75 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-center gap-3">
          <button className="db-button px-3 lg:hidden" type="button" onClick={onSidebarToggle} aria-label="Open sidebar">
            <Menu size={18} />
          </button>
          <div>
            <p className="db-pill mb-2">Construction Analytics</p>
            <h1 className="text-2xl font-black tracking-tight text-slate-950 dark:text-white sm:text-3xl">
              Executive Dashboard
            </h1>
            <p className="mt-1 text-sm font-bold text-slate-500 dark:text-slate-400">
              Current section: <span className="text-cyanAccent">{activeSection}</span>
              <span className="ml-2 text-slate-400">
                {apiState?.source === "api" ? "Live data" : apiState?.source === "empty" ? "Ready for upload" : "Demo fallback"}
              </span>
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <div className="relative min-w-[220px]">
            <button
              aria-expanded={isProjectMenuOpen}
              className="flex h-12 w-full items-center justify-between gap-3 rounded-2xl border border-slate-300/80 bg-white/90 px-3 text-left text-sm font-black text-slate-900 outline-none transition hover:border-cyan-400/70 focus:border-cyan-400 dark:border-white/10 dark:bg-white/[0.055] dark:text-white"
              type="button"
              onClick={onProjectMenuToggle}
            >
              <span className="flex min-w-0 items-center gap-2">
                <Search className="shrink-0 text-cyanAccent" size={17} />
                <span className="truncate">{activeProject.name}</span>
              </span>
              <ChevronDown className={`shrink-0 text-slate-400 transition ${isProjectMenuOpen ? "rotate-180" : ""}`} size={17} />
            </button>
            {isProjectMenuOpen ? (
              <div className="absolute left-0 top-14 z-40 w-full overflow-hidden rounded-3xl border border-slate-200/80 bg-white/95 p-2 shadow-card backdrop-blur-2xl dark:border-cyan-300/20 dark:bg-slate-950/95">
                <div className="mb-1 flex items-center justify-between px-2 py-1">
                  <span className="text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Project selector</span>
                  <button className="text-xs font-black text-cyanAccent" type="button" onClick={onProjectMenuClose}>
                    Close
                  </button>
                </div>
                <div className="grid gap-1">
                  {projectOptions.map((project) => {
                    const isActive = project.id === selectedProject;
                    return (
                      <button
                        className={`flex items-center justify-between rounded-2xl px-3 py-3 text-left text-sm font-black transition ${
                          isActive
                            ? "bg-cyan-300/15 text-slate-950 dark:text-white"
                            : "text-slate-700 hover:bg-cyan-300/10 dark:text-slate-200"
                        }`}
                        key={project.id}
                        type="button"
                        onClick={() => onProjectChange(project.id)}
                      >
                        {project.name}
                        {isActive ? <Check className="text-cyanAccent" size={16} /> : null}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            {dateRanges.map((range) => (
              <button
                className={`rounded-2xl border px-3 py-2 text-xs font-black transition ${
                  dateRange === range
                    ? "border-cyan-300/50 bg-cyan-300/15 text-slate-950 shadow-glow dark:text-white"
                    : "border-slate-300/70 bg-white/60 text-slate-600 hover:border-cyan-300/40 dark:border-white/10 dark:bg-white/[0.055] dark:text-slate-300"
                }`}
                key={range}
                type="button"
                onClick={() => onDateRangeChange(range)}
              >
                {range}
              </button>
            ))}
          </div>

          <div className="relative flex items-center gap-2">
            <button
              className="db-button px-3"
              type="button"
              onClick={onRefreshDashboard}
              aria-label="Refresh dashboard"
              title={apiState?.lastUpdated ? `Last updated ${new Date(apiState.lastUpdated).toLocaleString()}` : "Refresh dashboard"}
            >
              <RefreshCcw className={apiState?.isLoading ? "animate-spin" : ""} size={18} />
            </button>
            <button
              aria-expanded={isNotificationsOpen}
              aria-label="Notifications"
              className="db-button px-3"
              type="button"
              onClick={onNotificationsToggle}
            >
              <Bell size={18} />
              <span className="h-2 w-2 rounded-full bg-red-400 shadow-[0_0_14px_rgba(248,113,113,0.8)]" />
            </button>
            {isNotificationsOpen ? (
              <div className="absolute right-0 top-14 z-30 w-[min(380px,calc(100vw-2rem))] rounded-3xl border border-slate-200/80 bg-white/95 p-3 shadow-card backdrop-blur-2xl dark:border-cyan-300/20 dark:bg-slate-950/95">
                <div className="mb-3 flex items-center justify-between">
                  <strong className="text-slate-950 dark:text-white">Notifications</strong>
                  <button className="text-xs font-black text-cyanAccent" type="button" onClick={onNotificationsClose}>
                    Close
                  </button>
                </div>
                <div className="grid gap-2">
                  {notifications.map((item) => (
                    <article className="rounded-2xl border border-slate-200/80 bg-slate-50/80 p-3 dark:border-white/10 dark:bg-white/[0.045]" key={`${item.title}-${item.time}`}>
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <strong className="text-sm text-slate-950 dark:text-white">{item.title}</strong>
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-black ${notificationStyles[item.tone]}`}>
                          {item.tone}
                        </span>
                      </div>
                      <p className="text-sm leading-5 text-slate-600 dark:text-slate-300">{item.body}</p>
                      <p className="mt-2 text-xs font-bold text-slate-400">{item.time}</p>
                    </article>
                  ))}
                </div>
              </div>
            ) : null}
            <button className="db-button px-3" type="button" onClick={onThemeToggle} aria-label="Toggle theme">
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button
              aria-expanded={isProfileMenuOpen}
              className="db-button px-3"
              type="button"
              aria-label="User profile"
              onClick={onProfileMenuToggle}
            >
              <UserRound size={18} />
              <span className="hidden text-sm md:inline">DB</span>
            </button>
            {isProfileMenuOpen ? (
              <div className="absolute right-0 top-14 z-30 w-[min(320px,calc(100vw-2rem))] rounded-3xl border border-slate-200/80 bg-white/95 p-3 shadow-card backdrop-blur-2xl dark:border-cyan-300/20 dark:bg-slate-950/95">
                <div className="mb-3 flex items-start justify-between gap-3 rounded-2xl bg-slate-50/80 p-3 dark:bg-white/[0.045]">
                  <div>
                    <strong className="block text-slate-950 dark:text-white">DevBareun User</strong>
                    <span className="text-sm text-slate-500 dark:text-slate-400">Project Controls Manager</span>
                  </div>
                  <button className="text-xs font-black text-cyanAccent" type="button" onClick={onProfileMenuClose}>
                    Close
                  </button>
                </div>
                <div className="grid gap-2">
                  <button
                    className="flex items-center justify-between rounded-2xl px-3 py-3 text-left text-sm font-black text-slate-700 transition hover:bg-cyan-300/10 dark:text-slate-200"
                    type="button"
                    onClick={() => onSectionChange("Settings")}
                  >
                    <span className="flex items-center gap-2"><Settings size={16} className="text-cyanAccent" />Settings</span>
                    <ChevronDown className="-rotate-90 text-slate-400" size={15} />
                  </button>
                  <button
                    className="flex items-center justify-between rounded-2xl px-3 py-3 text-left text-sm font-black text-slate-700 transition hover:bg-cyan-300/10 dark:text-slate-200"
                    type="button"
                    onClick={() => onSectionChange("Reports")}
                  >
                    <span className="flex items-center gap-2"><CreditCard size={16} className="text-cyanAccent" />Billing & reports</span>
                    <ChevronDown className="-rotate-90 text-slate-400" size={15} />
                  </button>
                  <button
                    className="flex items-center justify-between rounded-2xl px-3 py-3 text-left text-sm font-black text-red-500 transition hover:bg-red-400/10"
                    type="button"
                    onClick={onProfileMenuClose}
                  >
                    <span className="flex items-center gap-2"><LogOut size={16} />Sign out demo</span>
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
