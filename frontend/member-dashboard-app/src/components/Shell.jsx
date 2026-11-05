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

const navItems = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "upload", label: "New delay analysis", icon: UploadCloud },
  { id: "projects", label: "My projects", icon: FolderKanban },
  { id: "reports", label: "Reports", icon: FileBarChart },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "settings", label: "Settings", icon: Settings }
];

// Team sharing stays available for companies, below the main menu.
const teamNavItems = [
  { id: "team", label: "Team", icon: UsersRound },
  { id: "project-access", label: "Project access", icon: FolderKey },
  { id: "project-activity", label: "Project activity", icon: Activity }
];

const allNavItems = [...navItems, ...teamNavItems];

export function Shell({ activeView, onNavigate, user, credits, children }) {
  const email = user?.email || "Workspace";
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
  const activeLabel = allNavItems.find((item) => item.id === activeView)?.label || "Menu";

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
            aria-label={menuOpen ? "Close workspace menu" : "Open workspace menu"}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span>{activeLabel}</span>
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
        <div id="workspace-sidebar-panel" className={classNames("workspace-sidebar-panel", menuOpen && "open")}>
          <nav aria-label="Workspace navigation">
            {navItems.map((item) => (
              <NavButton key={item.id} item={item} active={activeView === item.id} onSelect={selectView} />
            ))}
          </nav>
          <nav className="workspace-nav-secondary" aria-label="Team and sharing">
            <span className="workspace-nav-heading">Team and sharing</span>
            {teamNavItems.map((item) => (
              <NavButton key={item.id} item={item} active={activeView === item.id} onSelect={selectView} />
            ))}
          </nav>
          <div className="workspace-plan-card">
            <span>Current plan</span>
            <strong>{user?.plan || "No active plan"}</strong>
            <small>{credits?.remaining ?? 0} project credits remaining</small>
          </div>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div>
            <span className="workspace-eyebrow">DevBareun Workspace</span>
            <strong>{email}</strong>
          </div>
          <button type="button" className="workspace-top-button icon-only" aria-label="Notifications" title="Notifications">
            <Bell size={17} />
          </button>
          <div className="workspace-account" ref={accountRef}>
            <button
              type="button"
              className="workspace-avatar"
              aria-label="Account menu"
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
                  <Settings size={16} /> Settings
                </button>
                <button type="button" role="menuitem" onClick={logout}>
                  <LogOut size={16} /> Logout
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

function NavButton({ item, active, onSelect }) {
  const Icon = item.icon;
  return (
    <button
      type="button"
      className={classNames("workspace-nav-item", active && "active")}
      onClick={() => onSelect(item.id)}
    >
      <Icon size={18} />
      <span>{item.label}</span>
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

export function EmptyState({ title, description, action }) {
  return (
    <section className="empty-state">
      <BarChart3 size={34} />
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </section>
  );
}
