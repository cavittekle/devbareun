export const DELAY_TEMPLATE_URL = "/templates/devbareun-delay-analysis-template.xlsx";

// DevBareun runs one analysis: construction execution and delay analysis.
export const analysisPackages = [
  {
    id: "delay",
    name: "Execution & Delay Analysis",
    label: "Tikinti layihəsinin icra və gecikmə analizi",
    files: [
      "Baseline schedule (plan start / finish per activity)",
      "Actual progress (actual dates and % complete)",
      "Delay events with responsible party (optional)",
      "Or one Primavera XER / MS Project XML export"
    ],
    outputs: [
      "Planned vs actual S-curve and SPI",
      "Delay in days and forecast completion",
      "Critical path and most delayed activities",
      "Employer / contractor / neutral delay split",
      "PDF and Excel execution report (AZ / EN)"
    ]
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
