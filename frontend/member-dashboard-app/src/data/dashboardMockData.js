export const projectOptions = [
  { id: "all", name: "All Projects" },
  { id: "d3", name: "D-3 Residential" },
  { id: "d4", name: "D-4 Residential" },
  { id: "fd10", name: "FD-10" },
  { id: "custom", name: "Custom Project" }
];

export const dateRanges = ["This Month", "Quarter", "Year", "Custom"];

const baseCostSeries = [
  { period: "Jan", budget: 18.5, actualCost: 17.9, forecast: 18.8, committedCost: 16.7 },
  { period: "Feb", budget: 22.4, actualCost: 22.1, forecast: 23.2, committedCost: 20.8 },
  { period: "Mar", budget: 28.2, actualCost: 29.1, forecast: 30.3, committedCost: 26.5 },
  { period: "Apr", budget: 35.8, actualCost: 37.6, forecast: 39.1, committedCost: 34.4 },
  { period: "May", budget: 42.7, actualCost: 45.2, forecast: 47.4, committedCost: 41.9 },
  { period: "Jun", budget: 51.4, actualCost: 54.1, forecast: 57.2, committedCost: 50.6 }
];

const baseScheduleStages = [
  { name: "Foundation", progress: 100, status: "Completed", start: 2, width: 14 },
  { name: "Structure", progress: 86, status: "In Progress", start: 14, width: 18 },
  { name: "Masonry", progress: 58, status: "Delayed", start: 32, width: 15 },
  { name: "MEP", progress: 44, status: "In Progress", start: 47, width: 16 },
  { name: "Facade", progress: 20, status: "Delayed", start: 61, width: 14 },
  { name: "Finishing", progress: 0, status: "Not Started", start: 75, width: 13 },
  { name: "Handover", progress: 0, status: "Not Started", start: 88, width: 10 }
];

const baseRisks = [
  {
    title: "Material delivery delay",
    category: "Material Flow",
    severity: "High",
    impact: "Facade and MEP sequence may slip by 9 days.",
    action: "Confirm delivery slots and assign backup supplier."
  },
  {
    title: "Low manpower on site",
    category: "Schedule",
    severity: "Medium",
    impact: "Structure productivity is below recovery target.",
    action: "Increase crew coverage on critical work fronts."
  },
  {
    title: "Cost overrun risk",
    category: "Cost",
    severity: "Critical",
    impact: "Forecast cost is trending above approved budget.",
    action: "Freeze noncritical spend and review payment package."
  },
  {
    title: "Design approval delay",
    category: "Document Control",
    severity: "High",
    impact: "MEP drawings are delaying procurement release.",
    action: "Escalate approval meeting and close comments."
  },
  {
    title: "Missing document submission",
    category: "Documents",
    severity: "Low",
    impact: "Closeout tracker has incomplete handover records.",
    action: "Request missing files from discipline owners."
  },
  {
    title: "Schedule slippage",
    category: "Project Control",
    severity: "Medium",
    impact: "Planned progress is ahead of actual progress.",
    action: "Revise work sequence and update weekly recovery plan."
  }
];

const baseMilestones = [
  { name: "Structure completion", project: "D-3 Residential", dueDate: "2026-06-05", status: "Due Soon", daysRemaining: 8 },
  { name: "MEP rough-in approval", project: "D-4 Residential", dueDate: "2026-06-12", status: "Upcoming", daysRemaining: 15 },
  { name: "Facade mockup review", project: "FD-10", dueDate: "2026-05-26", status: "Delayed", daysRemaining: -2 },
  { name: "Payment package close", project: "Custom Project", dueDate: "2026-06-01", status: "Due Soon", daysRemaining: 4 },
  { name: "Foundation handover", project: "D-3 Residential", dueDate: "2026-05-20", status: "Completed", daysRemaining: 0 }
];

const baseProjectPortfolio = [
  { name: "D-3 Residential", manager: "N. Aliyev", phase: "Structure", budget: "$38.5M", progress: 73, cpi: 0.98, spi: 0.96, risk: "Low", status: "On Track" },
  { name: "D-4 Residential", manager: "S. Karimov", phase: "Masonry", budget: "$42.2M", progress: 57, cpi: 0.91, spi: 0.88, risk: "High", status: "Delayed" },
  { name: "FD-10", manager: "L. Mammadova", phase: "Facade", budget: "$58.4M", progress: 49, cpi: 0.86, spi: 0.84, risk: "Critical", status: "Critical" },
  { name: "Custom Project", manager: "E. Huseynli", phase: "Tender", budget: "$24.8M", progress: 43, cpi: 1.01, spi: 0.99, risk: "Low", status: "On Track" },
  { name: "Commercial Center", manager: "R. Hasanov", phase: "Finishing", budget: "$31.7M", progress: 82, cpi: 0.95, spi: 0.93, risk: "Medium", status: "Watch" },
  { name: "Logistics Warehouse", manager: "A. Rahimli", phase: "MEP", budget: "$19.4M", progress: 61, cpi: 0.97, spi: 0.92, risk: "Medium", status: "Watch" }
];

const baseCostPackages = [
  { package: "Concrete works", budget: "$28.4M", committed: "$27.1M", actual: "$25.9M", variance: "-$1.2M", status: "Controlled" },
  { package: "Facade systems", budget: "$18.8M", committed: "$20.5M", actual: "$12.4M", variance: "+$1.7M", status: "Pressure" },
  { package: "MEP installation", budget: "$34.2M", committed: "$32.8M", actual: "$24.6M", variance: "-$1.4M", status: "Controlled" },
  { package: "Finishing works", budget: "$21.6M", committed: "$23.1M", actual: "$10.7M", variance: "+$1.5M", status: "Watch" }
];

const baseReports = [
  { name: "Executive Portfolio Report", project: "All Projects", type: "Project Control", created: "2026-05-28", format: "PDF", status: "Ready" },
  { name: "D-4 Schedule Recovery", project: "D-4 Residential", type: "Schedule", created: "2026-05-27", format: "PDF", status: "Ready" },
  { name: "FD-10 Cost Pressure Review", project: "FD-10", type: "Cost", created: "2026-05-26", format: "Excel", status: "Review" },
  { name: "Document Control Register", project: "All Projects", type: "Documents", created: "2026-05-25", format: "PDF + Excel", status: "Ready" }
];

const baseDocumentRegister = [
  { code: "STR-221", title: "Structure weekly report", discipline: "Structure", project: "D-3 Residential", status: "Approved", owner: "Site team" },
  { code: "MEP-104", title: "MEP shop drawing set", discipline: "MEP", project: "D-4 Residential", status: "Pending Review", owner: "Design lead" },
  { code: "FAC-088", title: "Facade mockup approval", discipline: "Facade", project: "FD-10", status: "Missing", owner: "Facade contractor" },
  { code: "COM-312", title: "Payment package backup", discipline: "Commercial", project: "Custom Project", status: "Approved", owner: "Cost control" }
];

const uploadModules = [
  "Full Project Control",
  "Schedule Recovery",
  "Cost & Payment Control",
  "Material Flow",
  "Risk & Decisions",
  "Document Control"
];

const settingsGroups = [
  { title: "Workspace", items: ["Company profile", "Portfolio permissions", "Dashboard language", "Default report format"] },
  { title: "Notifications", items: ["Critical risk alerts", "Milestone reminders", "Report ready messages", "Billing reminders"] },
  { title: "Integrations", items: ["Supabase Auth placeholder", "Storage placeholder", "Stripe portal placeholder", "Railway backend placeholder"] }
];

const baseNotifications = [
  { title: "Critical risk requires owner", body: "FD-10 facade decision is blocking recovery sequence.", tone: "Critical", time: "6 min ago" },
  { title: "Report ready", body: "Executive Portfolio Report is ready for download.", tone: "Ready", time: "28 min ago" },
  { title: "Milestone due soon", body: "Structure completion is due in 8 days.", tone: "Watch", time: "1 hr ago" },
  { title: "Document gap", body: "Facade mockup approval is still missing.", tone: "Missing", time: "2 hrs ago" }
];

const baseActionQueue = [
  { label: "Assign risk owner", detail: "FD-10 cost overrun risk", priority: "Critical" },
  { label: "Close design approval", detail: "D-4 MEP drawing package", priority: "High" },
  { label: "Confirm delivery slot", detail: "Facade systems material flow", priority: "High" },
  { label: "Update recovery baseline", detail: "Portfolio schedule package", priority: "Medium" }
];

const projectSnapshots = {
  all: {
    multiplier: 1,
    kpis: [
      { label: "Active Projects", value: "18", trend: "+3", comparison: "vs previous period", status: "good" },
      { label: "Total Budget", value: "$245.6M", trend: "+4.8%", comparison: "approved portfolio", status: "watch" },
      { label: "Cost Performance Index", value: "0.94", trend: "-0.03", comparison: "target 1.00", status: "warning" },
      { label: "Schedule Performance Index", value: "0.91", trend: "-0.06", comparison: "target 1.00", status: "critical" },
      { label: "Delayed Activities", value: "47", trend: "+9", comparison: "open activities", status: "critical" },
      { label: "High Risk Items", value: "14", trend: "+4", comparison: "needs action", status: "critical" }
    ],
    schedule: { planned: 72, actual: 64, variance: -8, delayDays: 18 },
    statuses: [
      { name: "On Track", value: 7 },
      { name: "Watch", value: 5 },
      { name: "Delayed", value: 3 },
      { name: "Critical", value: 2 },
      { name: "No Data", value: 1 }
    ],
    documentsSummary: { uploadedFiles: 1284, pendingReview: 87, approvedDocuments: 1026, missingDocuments: 31 },
    managementSummary: {
      overall: "Portfolio performance is stable but below target on schedule recovery.",
      delayReason: "Main delay reason is material delivery alignment and late design approvals.",
      costPressure: "Cost pressure is visible in committed packages and forecast variance.",
      action: "Prioritize delayed facade, payment package review and recovery crew allocation."
    }
  },
  d3: {
    multiplier: 0.82,
    kpis: [
      { label: "Active Projects", value: "1", trend: "0", comparison: "single project", status: "good" },
      { label: "Total Budget", value: "$38.5M", trend: "+1.1%", comparison: "approved budget", status: "good" },
      { label: "Cost Performance Index", value: "0.98", trend: "+0.01", comparison: "target 1.00", status: "good" },
      { label: "Schedule Performance Index", value: "0.96", trend: "-0.02", comparison: "target 1.00", status: "watch" },
      { label: "Delayed Activities", value: "8", trend: "+2", comparison: "open activities", status: "watch" },
      { label: "High Risk Items", value: "2", trend: "-1", comparison: "needs action", status: "good" }
    ],
    schedule: { planned: 76, actual: 73, variance: -3, delayDays: 6 },
    statuses: [
      { name: "On Track", value: 1 },
      { name: "Watch", value: 0 },
      { name: "Delayed", value: 0 },
      { name: "Critical", value: 0 },
      { name: "No Data", value: 0 }
    ],
    documentsSummary: { uploadedFiles: 214, pendingReview: 13, approvedDocuments: 181, missingDocuments: 4 },
    managementSummary: {
      overall: "D-3 Residential is close to target with manageable schedule variance.",
      delayReason: "Minor manpower allocation gap is affecting masonry follow-up works.",
      costPressure: "Cost pressure is limited and payment status remains under control.",
      action: "Keep weekly production checks and close remaining drawing submissions."
    }
  },
  d4: {
    multiplier: 0.96,
    kpis: [
      { label: "Active Projects", value: "1", trend: "0", comparison: "single project", status: "watch" },
      { label: "Total Budget", value: "$42.2M", trend: "+3.4%", comparison: "approved budget", status: "watch" },
      { label: "Cost Performance Index", value: "0.91", trend: "-0.04", comparison: "target 1.00", status: "warning" },
      { label: "Schedule Performance Index", value: "0.88", trend: "-0.07", comparison: "target 1.00", status: "critical" },
      { label: "Delayed Activities", value: "16", trend: "+5", comparison: "open activities", status: "critical" },
      { label: "High Risk Items", value: "5", trend: "+2", comparison: "needs action", status: "critical" }
    ],
    schedule: { planned: 69, actual: 57, variance: -12, delayDays: 22 },
    statuses: [
      { name: "On Track", value: 0 },
      { name: "Watch", value: 0 },
      { name: "Delayed", value: 1 },
      { name: "Critical", value: 0 },
      { name: "No Data", value: 0 }
    ],
    documentsSummary: { uploadedFiles: 198, pendingReview: 31, approvedDocuments: 144, missingDocuments: 12 },
    managementSummary: {
      overall: "D-4 Residential needs schedule recovery and tighter cost control.",
      delayReason: "Design approval delay and low manpower are driving the current variance.",
      costPressure: "Forecast is above budget and committed cost needs commercial review.",
      action: "Escalate approvals, increase workforce and rebaseline affected work packages."
    }
  },
  fd10: {
    multiplier: 1.08,
    kpis: [
      { label: "Active Projects", value: "1", trend: "0", comparison: "single project", status: "critical" },
      { label: "Total Budget", value: "$58.4M", trend: "+6.2%", comparison: "approved budget", status: "warning" },
      { label: "Cost Performance Index", value: "0.86", trend: "-0.08", comparison: "target 1.00", status: "critical" },
      { label: "Schedule Performance Index", value: "0.84", trend: "-0.10", comparison: "target 1.00", status: "critical" },
      { label: "Delayed Activities", value: "21", trend: "+7", comparison: "open activities", status: "critical" },
      { label: "High Risk Items", value: "7", trend: "+3", comparison: "needs action", status: "critical" }
    ],
    schedule: { planned: 63, actual: 49, variance: -14, delayDays: 29 },
    statuses: [
      { name: "On Track", value: 0 },
      { name: "Watch", value: 0 },
      { name: "Delayed", value: 0 },
      { name: "Critical", value: 1 },
      { name: "No Data", value: 0 }
    ],
    documentsSummary: { uploadedFiles: 266, pendingReview: 42, approvedDocuments: 198, missingDocuments: 18 },
    managementSummary: {
      overall: "FD-10 is the highest priority project in the current portfolio view.",
      delayReason: "Facade delivery and unresolved design decisions are driving slippage.",
      costPressure: "Cost trend is above tolerance and payment approvals are slowing closure.",
      action: "Hold recovery review, confirm material delivery and assign decision owners."
    }
  },
  custom: {
    multiplier: 0.74,
    kpis: [
      { label: "Active Projects", value: "1", trend: "+1", comparison: "new workspace", status: "good" },
      { label: "Total Budget", value: "$24.8M", trend: "+0.8%", comparison: "approved budget", status: "good" },
      { label: "Cost Performance Index", value: "1.01", trend: "+0.02", comparison: "target 1.00", status: "good" },
      { label: "Schedule Performance Index", value: "0.99", trend: "+0.01", comparison: "target 1.00", status: "good" },
      { label: "Delayed Activities", value: "3", trend: "-2", comparison: "open activities", status: "good" },
      { label: "High Risk Items", value: "1", trend: "-1", comparison: "needs action", status: "good" }
    ],
    schedule: { planned: 44, actual: 43, variance: -1, delayDays: 2 },
    statuses: [
      { name: "On Track", value: 1 },
      { name: "Watch", value: 0 },
      { name: "Delayed", value: 0 },
      { name: "Critical", value: 0 },
      { name: "No Data", value: 0 }
    ],
    documentsSummary: { uploadedFiles: 86, pendingReview: 7, approvedDocuments: 63, missingDocuments: 2 },
    managementSummary: {
      overall: "Custom Project is performing within the target control range.",
      delayReason: "No major delay driver is visible in the current review.",
      costPressure: "Cost pressure is low and forecast remains inside tolerance.",
      action: "Continue baseline monitoring and keep document submissions current."
    }
  }
};

export function getDashboardData(projectId = "all", dateRange = "This Month") {
  const snapshot = projectSnapshots[projectId] || projectSnapshots.all;
  const rangeFactor = dateRange === "Quarter" ? 1.08 : dateRange === "Year" ? 1.18 : dateRange === "Custom" ? 0.92 : 1;
  const factor = snapshot.multiplier * rangeFactor;

  return {
    projects: projectOptions,
    kpis: snapshot.kpis,
    costSeries: baseCostSeries.map((item) => ({
      ...item,
      budget: Number((item.budget * factor).toFixed(1)),
      actualCost: Number((item.actualCost * factor).toFixed(1)),
      forecast: Number((item.forecast * factor).toFixed(1)),
      committedCost: Number((item.committedCost * factor).toFixed(1))
    })),
    schedule: snapshot.schedule,
    scheduleStages: baseScheduleStages,
    statusBreakdown: snapshot.statuses,
    risks: baseRisks,
    milestones: baseMilestones,
    projectPortfolio: projectId === "all" ? baseProjectPortfolio : baseProjectPortfolio.filter((project) => project.name === (projectOptions.find((item) => item.id === projectId)?.name || "")),
    costPackages: baseCostPackages,
    reports: baseReports,
    documentRegister: baseDocumentRegister,
    uploadModules,
    settingsGroups,
    notifications: baseNotifications,
    actionQueue: baseActionQueue,
    controlHealth: {
      readinessScore: snapshot.schedule.actual > 70 ? 88 : snapshot.schedule.actual > 55 ? 76 : 62,
      lastSync: "29 May 2026, 09:40",
      highPriorityActions: baseActionQueue.filter((item) => item.priority === "Critical" || item.priority === "High").length,
      delayedMilestones: baseMilestones.filter((item) => item.status === "Delayed").length,
      missingDocuments: snapshot.documentsSummary.missingDocuments,
      reviewStatus: snapshot.schedule.delayDays > 20 ? "Recovery needed" : snapshot.schedule.delayDays > 8 ? "Watch closely" : "Controlled"
    },
    documentsSummary: snapshot.documentsSummary,
    managementSummary: snapshot.managementSummary
  };
}
