import { useEffect, useMemo, useState } from "react";
import ExecutiveDashboard from "./pages/ExecutiveDashboard.jsx";
import { getDashboardData, projectOptions } from "./data/dashboardMockData.js";
import { getExecutiveDashboard, getPortfolioDashboard, getProjects } from "./api/devbareunApi.js";
import { adaptDashboardApi, apiProjectsToOptions } from "./api/dashboardAdapter.js";

export default function App() {
  const [selectedProject, setSelectedProject] = useState("all");
  const [dateRange, setDateRange] = useState("This Month");
  const [activeSection, setActiveSection] = useState("Overview");
  const [severityFilter, setSeverityFilter] = useState("All");
  const [theme, setTheme] = useState("dark");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isProjectMenuOpen, setIsProjectMenuOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [apiState, setApiState] = useState({
    isLoading: false,
    error: null,
    source: "demo",
    lastUpdated: null,
    refreshKey: 0
  });
  const [liveDashboardData, setLiveDashboardData] = useState(null);
  const [liveProjectOptions, setLiveProjectOptions] = useState(projectOptions);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const fallbackDashboardData = useMemo(
    () => getDashboardData(selectedProject, dateRange),
    [selectedProject, dateRange]
  );
  const dashboardData = liveDashboardData || fallbackDashboardData;

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setApiState((state) => ({ ...state, isLoading: true, error: null }));
      try {
        const [projects, dashboard] = await Promise.all([
          getProjects().catch(() => []),
          selectedProject === "all" ? getPortfolioDashboard() : getExecutiveDashboard(selectedProject)
        ]);
        if (cancelled) return;
        const nextProjectOptions = apiProjectsToOptions(projects, projectOptions);
        setLiveProjectOptions(nextProjectOptions);
        setLiveDashboardData(adaptDashboardApi(dashboard, fallbackDashboardData));
        setApiState({
          isLoading: false,
          error: null,
          source: dashboard?.empty_state ? "empty" : "api",
          lastUpdated: dashboard?.last_updated || new Date().toISOString(),
          refreshKey: apiState.refreshKey
        });
      } catch (error) {
        if (cancelled) return;
        setLiveDashboardData(null);
        setLiveProjectOptions(projectOptions);
        setApiState((state) => ({
          ...state,
          isLoading: false,
          error: error?.message || "Backend is not reachable. Demo dashboard data is shown.",
          source: "demo",
          lastUpdated: null
        }));
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [selectedProject, dateRange, apiState.refreshKey, fallbackDashboardData]);

  return (
    <ExecutiveDashboard
      activeSection={activeSection}
      dashboardData={dashboardData}
      dateRange={dateRange}
      isSidebarOpen={isSidebarOpen}
      isNotificationsOpen={isNotificationsOpen}
      isProfileMenuOpen={isProfileMenuOpen}
      isProjectMenuOpen={isProjectMenuOpen}
      apiState={apiState}
      projectOptions={liveProjectOptions}
      selectedProject={selectedProject}
      severityFilter={severityFilter}
      theme={theme}
      onDateRangeChange={setDateRange}
      onProjectChange={(projectId) => {
        setSelectedProject(projectId);
        setIsProjectMenuOpen(false);
      }}
      onProjectMenuToggle={() => {
        setIsProjectMenuOpen((value) => !value);
        setIsNotificationsOpen(false);
        setIsProfileMenuOpen(false);
      }}
      onProjectMenuClose={() => setIsProjectMenuOpen(false)}
      onProfileMenuToggle={() => {
        setIsProfileMenuOpen((value) => !value);
        setIsNotificationsOpen(false);
        setIsProjectMenuOpen(false);
      }}
      onProfileMenuClose={() => setIsProfileMenuOpen(false)}
      onSectionChange={(section) => {
        setActiveSection(section);
        setIsProfileMenuOpen(false);
      }}
      onSeverityFilterChange={setSeverityFilter}
      onSidebarToggle={() => setIsSidebarOpen((value) => !value)}
      onSidebarClose={() => setIsSidebarOpen(false)}
      onThemeToggle={() => setTheme((value) => (value === "dark" ? "light" : "dark"))}
      onNotificationsToggle={() => {
        setIsNotificationsOpen((value) => !value);
        setIsProjectMenuOpen(false);
        setIsProfileMenuOpen(false);
      }}
      onNotificationsClose={() => setIsNotificationsOpen(false)}
      onRefreshDashboard={() => setApiState((state) => ({ ...state, refreshKey: state.refreshKey + 1 }))}
    />
  );
}
