import { useEffect, useMemo, useState } from "react";
import { workspaceApi } from "./api/client";
import { Shell } from "./components/Shell";
import { Overview } from "./pages/Overview";
import { Upload } from "./pages/Upload";
import { Projects } from "./pages/Projects";
import { Reports } from "./pages/Reports";
import { Billing } from "./pages/Billing";
import { Settings } from "./pages/Settings";
import { Team } from "./pages/Team";
import { ProjectAccess } from "./pages/ProjectAccess";
import { ProjectActivity } from "./pages/ProjectActivity";
import { Auth } from "./pages/Auth";
import { PaymentStatus } from "./pages/PaymentStatus";
import { ResultViewer } from "./pages/ResultViewer";
import "./styles.css";

function initialView() {
  const value = new URLSearchParams(location.search).get("view") || location.hash.replace("#", "");
  if (["overview", "upload", "projects", "reports", "billing", "settings", "team", "project-access", "project-activity", "login", "register", "checkout", "payment-success", "payment-failed", "result", "guest-result"].includes(value)) return value;
  const pathView = location.pathname.replace(/^\/+|\/+$/g, "").replace(".html", "");
  const aliases = {
    workspace: "overview",
    dashboard: "overview",
    upload: "upload",
    projects: "projects",
    reports: "reports",
    billing: "billing",
    settings: "settings",
    team: "team",
    "project-access": "project-access",
    "project-activity": "project-activity",
    login: "login",
    register: "register",
    checkout: "checkout",
    "payment-success": "payment-success",
    "payment-failed": "payment-failed",
    "result-dashboard": "result",
    "analysis-view": "result",
    "guest-result": "guest-result",
    profile: "settings",
    "single-project": "upload"
  };
  return aliases[pathView] || "overview";
}

export default function App() {
  const [activeView, setActiveView] = useState(initialView);
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState(null);
  const [projects, setProjects] = useState([]);
  const [reports, setReports] = useState([]);
  const [credits, setCredits] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function refreshWorkspace() {
    setError(null);
    setLoading(true);
    try {
      const [meResult, healthResult, projectResult, creditResult] = await Promise.allSettled([
        workspaceApi.me(),
        workspaceApi.health(),
        workspaceApi.projects(),
        workspaceApi.credits()
      ]);

      if (meResult.status === "fulfilled") setUser(meResult.value?.user || meResult.value?.auth_user || null);
      if (healthResult.status === "fulfilled") setHealth(healthResult.value);
      if (projectResult.status === "fulfilled") {
        const nextProjects = projectResult.value?.projects || [];
        setProjects(nextProjects);
        if (nextProjects.length > 0) {
          const reportResults = await Promise.allSettled(
            nextProjects
              .map((project) => project.project_id || project.id)
              .filter(Boolean)
              .map((projectId) => workspaceApi.reports(projectId))
          );
          setReports(reportResults.flatMap((result) => (
            result.status === "fulfilled" ? result.value?.reports || [] : []
          )));
        } else {
          setReports([]);
        }
      }
      if (creditResult.status === "fulfilled") setCredits(creditResult.value?.credit_summary || null);
      if (meResult.status === "rejected") setError(meResult.reason.message || "Login session could not be verified.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (["login", "register", "checkout", "payment-success", "payment-failed", "guest-result"].includes(activeView)) {
      setLoading(false);
      return;
    }
    refreshWorkspace();
  }, [activeView]);

  function navigate(view) {
    setActiveView(view);
    history.replaceState(null, "", `#${view}`);
  }

  const content = useMemo(() => {
    if (activeView === "upload") return <Upload onUploaded={refreshWorkspace} />;
    if (activeView === "projects") return <Projects projects={projects} onNavigate={navigate} />;
    if (activeView === "reports") return <Reports reports={reports} onNavigate={navigate} />;
    if (activeView === "billing") return <Billing user={user} credits={credits} />;
    if (activeView === "settings") return <Settings user={user} health={health} />;
    if (activeView === "team") return <Team />;
    if (activeView === "project-access") return <ProjectAccess />;
    if (activeView === "project-activity") return <ProjectActivity />;
    if (activeView === "result") return <ResultViewer mode="workspace" />;
    return <Overview projects={projects} reports={reports} credits={credits} onNavigate={navigate} />;
  }, [activeView, projects, reports, credits, user, health]);

  if (activeView === "login") return <Auth mode="login" />;
  if (activeView === "register") return <Auth mode="register" />;
  if (activeView === "checkout") return <PaymentStatus status="checkout" />;
  if (activeView === "payment-success") return <PaymentStatus status="success" />;
  if (activeView === "payment-failed") return <PaymentStatus status="failed" />;
  if (activeView === "guest-result") {
    return <main className="standalone-result-screen"><ResultViewer mode="guest" /></main>;
  }

  return (
    <Shell activeView={activeView} onNavigate={navigate} user={user} credits={credits}>
      {loading && <div className="status-box info">Loading workspace...</div>}
      {error && (
        <div className="status-box warning">
          {error} Open <a href="/workspace/?view=login">login</a> if this workspace is protected.
        </div>
      )}
      {content}
    </Shell>
  );
}
