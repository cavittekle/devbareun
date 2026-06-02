const money = (value) => {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return "$0";
  if (Math.abs(number) >= 1_000_000) return `$${(number / 1_000_000).toFixed(1)}M`;
  if (Math.abs(number) >= 1_000) return `$${(number / 1_000).toFixed(1)}K`;
  return `$${number.toFixed(0)}`;
};

const numberText = (value, fallback = "0") => {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
};

const statusTone = (value, warningAt = 1) => {
  const number = Number(value || 0);
  if (number >= warningAt * 2) return "critical";
  if (number >= warningAt) return "warning";
  return "good";
};

export function apiProjectsToOptions(projects, fallbackOptions) {
  if (!Array.isArray(projects) || projects.length === 0) return fallbackOptions;
  return [
    { id: "all", name: "All Projects" },
    ...projects.map((project) => ({
      id: project.id || project.project_id,
      name: project.project_name || project.name || "Project"
    }))
  ];
}

export function adaptDashboardApi(apiData, fallbackData) {
  if (!apiData || typeof apiData !== "object") return fallbackData;
  const kpis = apiData.kpis || {};
  const schedule = apiData.schedule_performance || {};
  const documents = apiData.document_control || {};
  const summary = apiData.management_summary || {};
  const statusRows = apiData.project_status || [];
  const costRows = apiData.cost_overview || [];
  const risks = apiData.top_risks || [];
  const milestones = apiData.upcoming_milestones || [];
  const reports = apiData.reports || fallbackData.reports;

  return {
    ...fallbackData,
    kpis: [
      { label: "Active Projects", value: numberText(kpis.active_projects), trend: "+0", comparison: "current workspace", status: "good" },
      { label: "Total Budget", value: money(kpis.total_budget), trend: "+0%", comparison: "approved budget", status: "watch" },
      { label: "Cost Performance Index", value: numberText(kpis.cpi, "N/A"), trend: kpis.cpi && kpis.cpi < 1 ? "-0.01" : "+0.00", comparison: "target 1.00", status: kpis.cpi && kpis.cpi < 0.9 ? "critical" : kpis.cpi && kpis.cpi < 1 ? "warning" : "good" },
      { label: "Schedule Performance Index", value: numberText(kpis.spi, "N/A"), trend: kpis.spi && kpis.spi < 1 ? "-0.01" : "+0.00", comparison: "target 1.00", status: kpis.spi && kpis.spi < 0.9 ? "critical" : kpis.spi && kpis.spi < 1 ? "warning" : "good" },
      { label: "Delayed Activities", value: numberText(kpis.delayed_activities), trend: "+0", comparison: "open activities", status: statusTone(kpis.delayed_activities, 8) },
      { label: "High Risk Items", value: numberText(kpis.high_risk_items), trend: "+0", comparison: "needs action", status: statusTone(kpis.high_risk_items, 3) }
    ],
    costSeries: costRows.length
      ? costRows.map((item) => ({
          period: item.period,
          budget: toMillions(item.budget),
          actualCost: toMillions(item.actual),
          forecast: toMillions(item.forecast),
          committedCost: toMillions(item.committed)
        }))
      : fallbackData.costSeries,
    schedule: {
      planned: Number(schedule.planned_progress || 0),
      actual: Number(schedule.actual_progress || 0),
      variance: Number(schedule.variance || 0),
      delayDays: Number(schedule.delay_days || 0)
    },
    scheduleStages: schedule.stages?.length ? schedule.stages : fallbackData.scheduleStages,
    statusBreakdown: statusRows.length
      ? statusRows.map((item) => ({ name: item.status, value: item.count }))
      : fallbackData.statusBreakdown,
    risks: risks.length
      ? risks.map((risk) => ({
          title: risk.risk_title || risk.title,
          category: risk.category,
          severity: risk.severity,
          impact: risk.impact || risk.description,
          action: risk.recommended_action || risk.action
        }))
      : fallbackData.risks,
    milestones: milestones.length
      ? milestones.map((milestone) => ({
          name: milestone.milestone_name || milestone.name,
          project: milestone.project || "Project",
          dueDate: milestone.due_date || milestone.dueDate || "TBD",
          status: normalizeMilestoneStatus(milestone.status),
          daysRemaining: Number(milestone.days_remaining ?? milestone.daysRemaining ?? 0)
        }))
      : fallbackData.milestones,
    documentsSummary: {
      uploadedFiles: Number(documents.uploaded_files || 0),
      pendingReview: Number(documents.pending_review || 0),
      approvedDocuments: Number(documents.approved_documents || 0),
      missingDocuments: Number(documents.missing_documents || 0)
    },
    managementSummary: {
      overall: summary.overall_status || fallbackData.managementSummary.overall,
      delayReason: summary.main_delay_reason || fallbackData.managementSummary.delayReason,
      costPressure: summary.cost_pressure || fallbackData.managementSummary.costPressure,
      action: summary.immediate_action || fallbackData.managementSummary.action
    },
    reports: reports?.length
      ? reports.map((report) => ({
          name: report.report_name || report.name,
          project: report.project_name || report.project || "Project",
          type: report.report_type || report.type,
          created: report.created_date || report.created || "",
          format: report.format || "PDF",
          status: normalizeReportStatus(report.status)
        }))
      : fallbackData.reports,
    controlHealth: {
      ...fallbackData.controlHealth,
      readinessScore: Number(summary.confidence_score || fallbackData.controlHealth.readinessScore),
      lastSync: apiData.last_updated ? new Date(apiData.last_updated).toLocaleString() : fallbackData.controlHealth.lastSync,
      highPriorityActions: Number(kpis.high_risk_items || fallbackData.controlHealth.highPriorityActions),
      delayedMilestones: milestones.filter((item) => normalizeMilestoneStatus(item.status) === "Delayed").length,
      missingDocuments: Number(documents.missing_documents || 0),
      reviewStatus: apiData.empty_state ? "Watch closely" : Number(kpis.high_risk_items || 0) > 0 ? "Recovery needed" : "Controlled"
    },
    apiMeta: {
      emptyState: Boolean(apiData.empty_state),
      message: apiData.message,
      lastUpdated: apiData.last_updated
    }
  };
}

function toMillions(value) {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return 0;
  return Number((number / 1_000_000).toFixed(1));
}

function normalizeMilestoneStatus(status) {
  if (["Upcoming", "Due Soon", "Delayed", "Completed"].includes(status)) return status;
  if (status === "Planned") return "Upcoming";
  return "Upcoming";
}

function normalizeReportStatus(status) {
  const text = String(status || "Ready").toLowerCase();
  if (text.includes("review")) return "Review";
  return "Ready";
}

