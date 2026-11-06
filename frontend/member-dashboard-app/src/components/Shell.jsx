import {
  BarChart3,
  Bell,
  CreditCard,
  FileBarChart,
  FolderKanban,
  FolderKey,
  Activity,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  UploadCloud,
  UsersRound,
  X
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { workspaceApi } from "../api/client";
import { classNames } from "../lib/format";
import { useDelayLang } from "./DelayDashboard";

const navItems = [
  { id: "overview", icon: LayoutDashboard },
  { id: "upload", icon: UploadCloud },
  { id: "projects", icon: FolderKanban },
  { id: "reports", icon: FileBarChart },
  { id: "billing", icon: CreditCard },
  { id: "settings", icon: Settings }
];

// Team sharing stays available for companies, below the main menu.
const teamNavItems = [
  { id: "team", icon: UsersRound },
  { id: "project-access", icon: FolderKey },
  { id: "project-activity", icon: Activity }
];

export const SHELL_COPY = {
  en: {
    nav: { overview: "Overview", upload: "New delay analysis", projects: "My projects", reports: "Reports", billing: "Billing", settings: "Settings", team: "Team", "project-access": "Project access", "project-activity": "Project activity" },
    skip: "Skip to content",
    menu: "Menu",
    openMenu: "Open workspace menu",
    closeMenu: "Close workspace menu",
    mainNav: "Workspace navigation",
    teamNav: "Team and sharing",
    plan: "Current plan",
    noPlan: "No active plan",
    credits: (count) => `${count} project credit${Number(count) === 1 ? "" : "s"} remaining`,
    eyebrow: "DevBareun workspace",
    notifications: "Notifications",
    account: "Account menu",
    logout: "Log out",
    loading: "Loading workspace...",
    offline: "We can't reach the DevBareun server right now. Try again in a minute.",
    retry: "Try again",
    sessionError: "We couldn't confirm your session.",
    loginHint: "Log in",
    loginHintTail: "to open this workspace."
  },
  az: {
    nav: { overview: "Ümumi baxış", upload: "Yeni gecikmə analizi", projects: "Layihələrim", reports: "Hesabatlar", billing: "Ödəniş", settings: "Ayarlar", team: "Komanda", "project-access": "Layihəyə giriş", "project-activity": "Layihə fəaliyyəti" },
    skip: "Məzmuna keç",
    menu: "Menyu",
    openMenu: "Menyunu aç",
    closeMenu: "Menyunu bağla",
    mainNav: "İş sahəsi menyusu",
    teamNav: "Komanda və paylaşım",
    plan: "Cari plan",
    noPlan: "Aktiv plan yoxdur",
    credits: (count) => `${count} layihə krediti qalıb`,
    eyebrow: "DevBareun iş sahəsi",
    notifications: "Bildirişlər",
    account: "Hesab menyusu",
    logout: "Çıxış",
    loading: "İş sahəsi yüklənir...",
    offline: "DevBareun serverinə indi qoşula bilmirik. Bir dəqiqə sonra yenidən cəhd edin.",
    retry: "Yenidən cəhd et",
    sessionError: "Sessiyanızı təsdiqləyə bilmədik.",
    loginHint: "Daxil olun",
    loginHintTail: "və iş sahəsini açın."
  }
};

const allNavItems = [...navItems, ...teamNavItems];

export function Shell({ activeView, onNavigate, user, credits, children }) {
  const [lang] = useDelayLang();
  const t = SHELL_COPY[lang];
  const email = user?.email || (lang === "az" ? "İş sahəsi" : "Workspace");
  const initials = email.slice(0, 1).toUpperCase();
  const [menuOpen, setMenuOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const accountRef = useRef(null);

  useEffect(() => {
    if (!accountOpen) return undefined;
    function close(event) {
      if (event.type === "keydown" ? event.key === "Escape" : !accountRef.current?.contains(event.target)) {
        setAccountOpen(false);
      }
    }
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", close);
    };
  }, [accountOpen]);
  const activeLabel = allNavItems.some((item) => item.id === activeView) ? t.nav[activeView] : t.menu;

  function selectView(view) {
    setMenuOpen(false);
    onNavigate(view);
  }

  async function logout() {
    try {
      await workspaceApi.logout();
    } finally {
      location.href = "/workspace/?view=login";
    }
  }

  return (
    <div className="workspace-shell">
      <a className="skip-link" href="#workspace-main">{t.skip}</a>
      <aside className="workspace-sidebar">
        <div className="workspace-sidebar-head">
          <a className="workspace-brand" href="/">
            <img src="/assets/devbareun-logo-horizontal-white.svg" alt="DevBareun" />
          </a>
          <button
            type="button"
            className="workspace-menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="workspace-sidebar-panel"
            aria-label={menuOpen ? t.closeMenu : t.openMenu}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span>{activeLabel}</span>
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
        <div id="workspace-sidebar-panel" className={classNames("workspace-sidebar-panel", menuOpen && "open")}>
          <nav aria-label={t.mainNav}>
            {navItems.map((item) => (
              <NavButton key={item.id} item={item} label={t.nav[item.id]} active={activeView === item.id} onSelect={selectView} />
            ))}
          </nav>
          <nav className="workspace-nav-secondary" aria-label={t.teamNav}>
            <span className="workspace-nav-heading">{t.teamNav}</span>
            {teamNavItems.map((item) => (
              <NavButton key={item.id} item={item} label={t.nav[item.id]} active={activeView === item.id} onSelect={selectView} />
            ))}
          </nav>
          <div className="workspace-plan-card">
            <span>{t.plan}</span>
            <strong>{user?.plan || t.noPlan}</strong>
            <small>{t.credits(credits?.remaining ?? 0)}</small>
          </div>
        </div>
      </aside>

      <main className="workspace-main" id="workspace-main" tabIndex={-1}>
        <header className="workspace-topbar">
          <div>
            <span className="workspace-eyebrow">{t.eyebrow}</span>
            <strong>{email}</strong>
          </div>
          <button type="button" className="workspace-top-button icon-only" aria-label={t.notifications} title={t.notifications}>
            <Bell size={17} />
          </button>
          <div className="workspace-account" ref={accountRef}>
            <button
              type="button"
              className="workspace-avatar"
              aria-label={t.account}
              aria-haspopup="menu"
              aria-expanded={accountOpen}
              onClick={() => setAccountOpen((open) => !open)}
            >
              {initials}
            </button>
            {accountOpen && (
              <div className="workspace-account-menu" role="menu">
                <span className="workspace-account-email">{email}</span>
                <button type="button" role="menuitem" onClick={() => { setAccountOpen(false); selectView("settings"); }}>
                  <Settings size={16} /> {t.nav.settings}
                </button>
                <button type="button" role="menuitem" onClick={logout}>
                  <LogOut size={16} /> {t.logout}
                </button>
              </div>
            )}
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

function NavButton({ item, label, active, onSelect }) {
  const Icon = item.icon;
  return (
    <button
      type="button"
      className={classNames("workspace-nav-item", active && "active")}
      onClick={() => onSelect(item.id)}
    >
      <Icon size={18} />
      <span>{label}</span>
    </button>
  );
}

// Workspace pages are tools, not landing pages: the compact header is the default.
export function PageHeader({ eyebrow, title, description, action, compact = true }) {
  return (
    <section className={compact ? "page-header compact" : "page-header"}>
      <div>
        {eyebrow && <span className="workspace-eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="page-actions">{action}</div>}
    </section>
  );
}

export function EmptyState({ title, description, action, headingLevel = 2 }) {
  const Heading = headingLevel === 1 ? "h1" : "h2";
  return (
    <section className="empty-state">
      <BarChart3 size={34} aria-hidden="true" />
      <Heading>{title}</Heading>
      <p>{description}</p>
      {action}
    </section>
  );
}
