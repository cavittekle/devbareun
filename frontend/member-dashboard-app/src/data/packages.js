// DevBareun runs one analysis: construction execution and delay analysis.
export const analysisPackages = [
  {
    id: "delay",
    name: "Execution & Delay Analysis",
    label: "Tikinti layihəsinin icra və gecikmə analizi",
    files: [
      "Planning: baseline schedule and actual progress (Excel, Primavera XER, MS Project)",
      "F2 certificates: payment for completed work (Excel or Word)",
      "Contract (PDF, Word, JPEG or PNG)",
      "Delay events with responsible party (optional)"
    ],
    outputs: [
      "Planned vs actual S-curve and SPI",
      "Delay in days and forecast completion",
      "Critical path and most delayed activities",
      "Employer / contractor / neutral delay split",
      "F2 certified value against physical progress",
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
