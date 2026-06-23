export const analysisPackages = [
  {
    id: "schedule-recovery",
    name: "Schedule Recovery",
    label: "Delay and workforce logic",
    files: ["Baseline Schedule", "Actual Progress", "Workforce Data (optional)"],
    outputs: ["Delay Dashboard", "Critical Path", "Workforce Gap", "Recovery Plan"]
  },
  {
    id: "cost-control",
    name: "Cost Control",
    label: "Estimate and payment tracking",
    files: ["Cost Estimate / BOQ", "Actual Cost", "Progress Payment / F-2"],
    outputs: ["Cost Dashboard", "Payment Tracking", "Budget Variance", "Remaining Value"]
  },
  {
    id: "material-continuity",
    name: "Material Continuity",
    label: "Stock and consumption logic",
    files: ["Material List / BOQ", "Stock Records", "Consumption or Procurement Updates"],
    outputs: ["Material Dashboard", "Shortage Alerts", "Consumption Trend", "Procurement Actions"]
  },
  {
    id: "risk-decisions",
    name: "Risk & Decisions",
    label: "Risk register and decision tracking",
    files: ["Risk Register", "Site Notes", "Decision Records", "Cost or Schedule Signals"],
    outputs: ["Risk Dashboard", "Priority Register", "Decision Prompts", "Management Actions"]
  }
];

export const planCatalog = {
  single: {
    name: "Single Project",
    price: "$29",
    cadence: "one-time",
    credits: "1 project"
  },
  plus: {
    name: "Plus",
    price: "$49",
    cadence: "month",
    credits: "5 / month"
  },
  pro: {
    name: "Pro",
    price: "$89",
    cadence: "month",
    credits: "20 / month"
  }
};
