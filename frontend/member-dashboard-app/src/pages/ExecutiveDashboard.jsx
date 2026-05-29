import CostOverviewChart from "../components/CostOverviewChart.jsx";
import CostPackages from "../components/CostPackages.jsx";
import ControlHealthBar from "../components/ControlHealthBar.jsx";
import DocumentsPanel from "../components/DocumentsPanel.jsx";
import DocumentSummary from "../components/DocumentSummary.jsx";
import KpiCard from "../components/KpiCard.jsx";
import ManagementSummary from "../components/ManagementSummary.jsx";
import MilestonesCard from "../components/MilestonesCard.jsx";
import ProjectPortfolio from "../components/ProjectPortfolio.jsx";
import ReportsPanel from "../components/ReportsPanel.jsx";
import RiskTable from "../components/RiskTable.jsx";
import ScheduleTimeline from "../components/ScheduleTimeline.jsx";
import SettingsWorkspace from "../components/SettingsWorkspace.jsx";
import Sidebar from "../components/Sidebar.jsx";
import StatusDonutChart from "../components/StatusDonutChart.jsx";
import Topbar from "../components/Topbar.jsx";
import UploadWorkspace from "../components/UploadWorkspace.jsx";

export default function ExecutiveDashboard({
  activeSection,
  apiState,
  dashboardData,
  dateRange,
  isNotificationsOpen,
  isProfileMenuOpen,
  isProjectMenuOpen,
  isSidebarOpen,
  onDateRangeChange,
  onNotificationsClose,
  onNotificationsToggle,
  onProjectChange,
  onProjectMenuClose,
  onProjectMenuToggle,
  onProfileMenuClose,
  onProfileMenuToggle,
  onSectionChange,
  onSeverityFilterChange,
  onRefreshDashboard,
  onSidebarClose,
  onSidebarToggle,
  onThemeToggle,
  projectOptions,
  selectedProject,
  severityFilter,
  theme
}) {
  return (
    <div className="min-h-screen text-slate-950 dark:text-white">
      <div className="grid min-h-screen lg:grid-cols-[320px_minmax(0,1fr)]">
        <Sidebar
          activeSection={activeSection}
          isOpen={isSidebarOpen}
          onClose={onSidebarClose}
          onSectionChange={onSectionChange}
        />

        <main className="min-w-0 px-4 pb-10 sm:px-6 lg:px-8">
          <Topbar
            activeSection={activeSection}
            dateRange={dateRange}
            isNotificationsOpen={isNotificationsOpen}
            isProfileMenuOpen={isProfileMenuOpen}
            isProjectMenuOpen={isProjectMenuOpen}
            notifications={dashboardData.notifications}
            onDateRangeChange={onDateRangeChange}
            onNotificationsClose={onNotificationsClose}
            onNotificationsToggle={onNotificationsToggle}
            onProjectChange={onProjectChange}
            onProjectMenuClose={onProjectMenuClose}
            onProjectMenuToggle={onProjectMenuToggle}
            onProfileMenuClose={onProfileMenuClose}
            onProfileMenuToggle={onProfileMenuToggle}
            onRefreshDashboard={onRefreshDashboard}
            onSectionChange={onSectionChange}
            onSidebarToggle={onSidebarToggle}
            onThemeToggle={onThemeToggle}
            projectOptions={projectOptions}
            selectedProject={selectedProject}
            theme={theme}
            apiState={apiState}
          />

          <ControlHealthBar actionQueue={dashboardData.actionQueue} controlHealth={dashboardData.controlHealth} />

          <DashboardStateBanner apiState={apiState} dashboardData={dashboardData} />

          {renderSection({
            activeSection,
            dashboardData,
            onSeverityFilterChange,
            severityFilter
          })}
        </main>
      </div>
    </div>
  );
}

function DashboardStateBanner({ apiState, dashboardData }) {
  if (!apiState?.isLoading && !apiState?.error && !dashboardData?.apiMeta?.emptyState) {
    return null;
  }

  const message = apiState?.isLoading
    ? "Loading latest project control data..."
    : apiState?.error
      ? apiState.error
      : dashboardData?.apiMeta?.message || "Upload project files and run analysis to generate dashboard.";

  return (
    <div className="mb-6 rounded-3xl border border-cyan-300/25 bg-cyan-300/10 p-4 text-sm font-bold text-slate-700 dark:text-slate-200">
      {message}
    </div>
  );
}

function renderSection({ activeSection, dashboardData, onSeverityFilterChange, severityFilter }) {
  if (activeSection === "Projects") {
    return (
      <div className="grid gap-4">
        <ProjectPortfolio projects={dashboardData.projectPortfolio} />
        <div className="grid gap-4 xl:grid-cols-3">
          <ManagementSummary summary={dashboardData.managementSummary} />
          <StatusDonutChart data={dashboardData.statusBreakdown} />
        </div>
      </div>
    );
  }

  if (activeSection === "Schedule") {
    return (
      <div className="grid gap-4 xl:grid-cols-3">
        <ScheduleTimeline schedule={dashboardData.schedule} stages={dashboardData.scheduleStages} />
        <MilestonesCard milestones={dashboardData.milestones} />
      </div>
    );
  }

  if (activeSection === "Cost") {
    return (
      <div className="grid gap-4">
        <section className="grid gap-4 xl:grid-cols-3">
          <CostOverviewChart data={dashboardData.costSeries} />
          <DocumentSummary summary={dashboardData.documentsSummary} />
        </section>
        <CostPackages packages={dashboardData.costPackages} />
      </div>
    );
  }

  if (activeSection === "Risk") {
    return (
      <div className="grid gap-4 xl:grid-cols-3">
        <RiskTable
          onSeverityFilterChange={onSeverityFilterChange}
          risks={dashboardData.risks}
          severityFilter={severityFilter}
        />
        <StatusDonutChart data={dashboardData.statusBreakdown} />
      </div>
    );
  }

  if (activeSection === "Reports") {
    return (
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <ReportsPanel reports={dashboardData.reports} />
        </div>
        <ManagementSummary summary={dashboardData.managementSummary} />
      </div>
    );
  }

  if (activeSection === "Documents") {
    return (
      <div className="grid gap-4">
        <section className="grid gap-4 xl:grid-cols-3">
          <DocumentSummary summary={dashboardData.documentsSummary} />
          <div className="xl:col-span-2">
            <DocumentsPanel documents={dashboardData.documentRegister} />
          </div>
        </section>
      </div>
    );
  }

  if (activeSection === "Upload") {
    return <UploadWorkspace modules={dashboardData.uploadModules} />;
  }

  if (activeSection === "Settings") {
    return <SettingsWorkspace groups={dashboardData.settingsGroups} />;
  }

  return (
    <>
      <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {dashboardData.kpis.map((kpi) => (
          <KpiCard key={kpi.label} kpi={kpi} />
        ))}
      </section>

      <section className="mb-6 grid gap-4 xl:grid-cols-3">
        <ManagementSummary summary={dashboardData.managementSummary} />
        <StatusDonutChart data={dashboardData.statusBreakdown} />
      </section>

      <section className="mb-6 grid gap-4 xl:grid-cols-3">
        <CostOverviewChart data={dashboardData.costSeries} />
        <DocumentSummary summary={dashboardData.documentsSummary} />
      </section>

      <section className="mb-6 grid gap-4 xl:grid-cols-3">
        <ScheduleTimeline schedule={dashboardData.schedule} stages={dashboardData.scheduleStages} />
        <MilestonesCard milestones={dashboardData.milestones} />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <RiskTable
          onSeverityFilterChange={onSeverityFilterChange}
          risks={dashboardData.risks}
          severityFilter={severityFilter}
        />
      </section>
    </>
  );
}
