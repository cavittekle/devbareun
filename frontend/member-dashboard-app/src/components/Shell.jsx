import { useEffect, useState } from "react";
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
  UsersRound
} from "lucide-react";
import { workspaceApi } from "../api/client";
import { classNames } from "../lib/format";

const navItems = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "upload", label: "Upload Project", icon: UploadCloud },
  { id: "projects", label: "My Projects", icon: FolderKanban },
  { id: "reports", label: "Reports", icon: FileBarChart },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "team", label: "Team", icon: UsersRound },
  { id: "project-access", label: "Project Access", icon: FolderKey },
  { id: "project-activity", label: "Project Activity", icon: Activity },
  { id: "settings", label: "Settings", icon: Settings }
];

const SIDEBAR_STORAGE_KEY = "devbareun.workspace.sidebarCollapsed.v1";

function readSidebarCollapsed() {
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function Shell({ activeView, onNavigate, user, credits, children, demoMode = false }) {
  const email = user?.email || "Workspace";
  const initials = email.slice(0, 1).toUpperCase();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsed);

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarCollapsed));
    } catch {
      // Keep the UI toggle working even when localStorage is unavailable.
    }
  }, [sidebarCollapsed]);

  async function logout() {
    if (demoMode) {
      location.href = "/workspace/?view=login";
      return;
    }
    try {
      await workspaceApi.logout();
    } finally {
      location.href = "/workspace/?view=login";
    }
  }

  return (
    <div className={classNames("workspace-shell", sidebarCollapsed && "sidebar-collapsed")}>
      <aside className="workspace-sidebar" aria-label="Workspace sidebar">
        <div className="workspace-sidebar-header">
          <a className="workspace-brand" href="/" aria-label="DevBareun home">
            <img className="workspace-brand-full" src="/assets/devbareun-logo-horizontal-white.svg" alt="DevBareun" />
            <img className="workspace-brand-symbol" src="/assets/devbareun-symbol-white.svg" alt="" aria-hidden="true" />
          </a>
          <button
            className="workspace-sidebar-toggle"
            type="button"
            aria-label={sidebarCollapsed ? "Open sidebar" : "Collapse sidebar"}
            aria-expanded={!sidebarCollapsed}
            title={sidebarCollapsed ? "Open sidebar" : "Collapse sidebar"}
            onClick={() => setSidebarCollapsed((current) => !current)}
          >
            <Menu size={18} />
          </button>
        </div>
        <nav aria-label="Workspace navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={classNames("workspace-nav-item", activeView === item.id && "active")}
                onClick={() => onNavigate(item.id)}
                title={sidebarCollapsed ? item.label : undefined}
              >
                <Icon size={18} />
                <span className="workspace-nav-label">{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="workspace-plan-card">
          <span>{demoMode ? "Preview plan" : "Current plan"}</span>
          <strong>{user?.plan || "No active plan"}</strong>
          <small>{credits?.remaining ?? 0} project credits remaining</small>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div>
            <span className="workspace-eyebrow">{demoMode ? "Sample workspace preview" : "DevBareun Workspace"}</span>
            <strong>{email}</strong>
          </div>
          <button type="button" className="workspace-top-button">
            <Bell size={17} />
            <span>Notifications</span>
          </button>
          <button type="button" className="workspace-top-button" onClick={logout}>
            <LogOut size={17} />
            <span>{demoMode ? "Exit preview" : "Logout"}</span>
          </button>
          <div className="workspace-avatar" aria-label="Account">
            {initials}
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <section className="page-header">
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
