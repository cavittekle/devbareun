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

export function Shell({ activeView, onNavigate, user, credits, children }) {
  const email = user?.email || "Workspace";
  const initials = email.slice(0, 1).toUpperCase();

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
        <a className="workspace-brand" href="/">
          <img src="/assets/devbareun-logo-horizontal-white.svg" alt="DevBareun" />
        </a>
        <nav aria-label="Workspace navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={classNames("workspace-nav-item", activeView === item.id && "active")}
                onClick={() => onNavigate(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="workspace-plan-card">
          <span>Current plan</span>
          <strong>{user?.plan || "No active plan"}</strong>
          <small>{credits?.remaining ?? 0} project credits remaining</small>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div>
            <span className="workspace-eyebrow">DevBareun Workspace</span>
            <strong>{email}</strong>
          </div>
          <button type="button" className="workspace-top-button">
            <Bell size={17} />
            <span>Notifications</span>
          </button>
          <button type="button" className="workspace-top-button" onClick={logout}>
            <LogOut size={17} />
            <span>Logout</span>
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
