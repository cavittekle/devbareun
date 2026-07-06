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
import { demoWorkspace } from "./data/demoWorkspace";
import "./styles.css";

function demoModeEnabled() {
  const value = new URLSearchParams(location.search).get("demo");
  return ["1", "true", "yes"].includes(String(value || "").toLowerCase());
}

function initialView() {
  const demoMode = demoModeEnabled();
  const value = new URLSearchParams(location.search).get("view") || location.hash.replace("#", "");
  if (demoMode && ["login", "register", "checkout", "payment-success", "payment-failed", "guest-result"].includes(value)) return "overview";
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

function initialDemoPackage() {
  const value = new URLSearchParams(location.search).get("package");
  if (["schedule-recovery", "cost-control", "material-continuity", "risk-decisions"].includes(value)) return value;
  return "schedule-recovery";
}

export default function App() {
  const demoMode = useMemo(() => demoModeEnabled(), []);
  const [activeDemoPackage, setActiveDemoPackage] = useState(initialDemoPackage);
  const [activeView, setActiveView] = useState(initialView);
  const [user, setUser] = useState(demoMode ? demoWorkspace.user : null);
  const [health, setHealth] = useState(demoMode ? demoWorkspace.health : null);
  const [projects, setProjects] = useState(demoMode ? demoWorkspace.projects : []);
  const [reports, setReports] = useState(demoMode ? demoWorkspace.reports : []);
  const [credits, setCredits] = useState(demoMode ? demoWorkspace.credits : null);
  const [loading, setLoading] = useState(!demoMode);
  const [error, setError] = useState(null);

  async function refreshWorkspace() {
    if (demoMode) {
      setUser(demoWorkspace.user);
      setHealth(demoWorkspace.health);
      setProjects(demoWorkspace.projects);
      setReports(demoWorkspace.reports);
      setCredits(demoWorkspace.credits);
      setError(null);
      setLoading(false);
      return;
    }
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
    if (demoMode) {
      refreshWorkspace();
      return;
    }
    if (["login", "register", "checkout", "payment-success", "payment-failed", "guest-result"].includes(activeView)) {
      setLoading(false);
      return;
    }
    refreshWorkspace();
  }, [activeView]);

  useEffect(() => {
    function syncRouteFromLocation() {
      setActiveView(initialView());
      if (demoMode) setActiveDemoPackage(initialDemoPackage());
    }

    window.addEventListener("hashchange", syncRouteFromLocation);
    window.addEventListener("popstate", syncRouteFromLocation);
    return () => {
      window.removeEventListener("hashchange", syncRouteFromLocation);
      window.removeEventListener("popstate", syncRouteFromLocation);
    };
  }, [demoMode]);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [activeView, activeDemoPackage]);

  function navigate(view) {
    setActiveView(view);
    history.replaceState(null, "", `#${view}`);
  }

  function changeDemoPackage(packageId) {
    if (!demoMode) return;
    setActiveDemoPackage(packageId);
    const params = new URLSearchParams(location.search);
    const currentView = location.hash.replace("#", "") || activeView;
    params.set("demo", "1");
    params.set("package", packageId);
    history.replaceState(null, "", `/workspace/?${params.toString()}#${currentView}`);
  }

  async function handleUploaded(project, packageId) {
    if (demoMode) {
      const nextPackage = packageId || activeDemoPackage;
      setActiveDemoPackage(nextPackage);
      setActiveView("result");
      history.replaceState(null, "", `/workspace/?demo=1&package=${encodeURIComponent(nextPackage)}#result`);
      await refreshWorkspace();
      return;
    }
    await refreshWorkspace(project);
  }

  const content = useMemo(() => {
    const demoPayload = activeDemoPackage === "schedule-recovery"
      ? demoWorkspace.resultPayload
      : demoWorkspace.packageResults?.[activeDemoPackage] || demoWorkspace.resultPayload;
    if (activeView === "upload") return <Upload onUploaded={handleUploaded} demoMode={demoMode} initialPackage={activeDemoPackage} />;
    if (activeView === "projects") {
      return (
        <Projects
          projects={projects}
          onNavigate={navigate}
          demoMode={demoMode}
          activeDemoPackage={activeDemoPackage}
          onDemoPackageChange={changeDemoPackage}
        />
      );
    }
    if (activeView === "reports") {
      return (
        <Reports
          reports={reports}
          onNavigate={navigate}
          demoMode={demoMode}
          activeDemoPackage={activeDemoPackage}
          onDemoPackageChange={changeDemoPackage}
        />
      );
    }
    if (activeView === "billing") return <Billing user={user} credits={credits} demoMode={demoMode} activeDemoPackage={activeDemoPackage} />;
    if (activeView === "settings") return <Settings user={user} health={health} demoMode={demoMode} activeDemoPackage={activeDemoPackage} onDemoPackageChange={changeDemoPackage} />;
    if (activeView === "team") return <Team demoMode={demoMode} />;
    if (activeView === "project-access") return <ProjectAccess demoMode={demoMode} />;
    if (activeView === "project-activity") return <ProjectActivity demoMode={demoMode} />;
    if (activeView === "result") {
      return (
        <ResultViewer
          mode="workspace"
          demoPayload={demoMode ? demoPayload : null}
          demoMode={demoMode}
          activeDemoPackage={activeDemoPackage}
          onDemoPackageChange={changeDemoPackage}
        />
      );
    }
    return (
      <Overview
        projects={projects}
        reports={reports}
        credits={credits}
        onNavigate={navigate}
        demoMode={demoMode}
        activeDemoPackage={activeDemoPackage}
        onDemoPackageChange={changeDemoPackage}
      />
    );
  }, [activeView, projects, reports, credits, user, health, demoMode, activeDemoPackage]);

  if (activeView === "login") return <Auth mode="login" />;
  if (activeView === "register") return <Auth mode="register" />;
  if (activeView === "checkout") return <PaymentStatus status="checkout" />;
  if (activeView === "payment-success") return <PaymentStatus status="success" />;
  if (activeView === "payment-failed") return <PaymentStatus status="failed" />;
  if (activeView === "guest-result") {
    return <main className="standalone-result-screen"><ResultViewer mode="guest" /></main>;
  }

  return (
    <Shell activeView={activeView} onNavigate={navigate} user={user} credits={credits} demoMode={demoMode}>
      {demoMode && (
        <div className="status-box info">
          Preview workspace: sample project data is local to this view.
        </div>
      )}
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
