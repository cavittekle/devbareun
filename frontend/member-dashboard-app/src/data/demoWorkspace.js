// Prototype-only payload for /workspace/?demo=1. Keep this out of production data paths.
export const demoWorkspace = {
  enabledLabel: "Sample workspace preview",
  user: {
    email: "demo.owner@devbareun.example",
    name: "Demo Workspace Owner",
    plan: "Plus",
    company_name: "Sample Builder Studio"
  },
  health: {
    status: "ok",
    database: "connected",
    storage: "configured"
  },
  credits: {
    plan_code: "plus",
    plan_name: "Plus",
    remaining: 4,
    used: 1,
    monthly_allowance: 5,
    renews_at: "2026-07-01T00:00:00+04:00"
  },
  demoWorkflow: [
    {
      step: "01",
      title: "Upload evidence",
      description: "Schedule, cost, material or risk files are screened and mapped.",
      status: "Mapped"
    },
    {
      step: "02",
      title: "Review package logic",
      description: "Only the selected control package is shown in the management dashboard.",
      status: "Ready"
    },
    {
      step: "03",
      title: "Export decision pack",
      description: "Executive PDF and Excel evidence packages are prepared from the snapshot.",
      status: "Preview"
    }
  ],
  packageInsights: {
    "schedule-recovery": {
      name: "Schedule Recovery",
      status: "Recovery watch",
      metric: "18 days",
      metricLabel: "largest active delay",
      nextStep: "Lock a two-week recovery schedule and close facade delivery dates.",
      signal: "Critical path and workforce logic"
    },
    "cost-control": {
      name: "Cost Control",
      status: "Cost pressure",
      metric: "AZN 620K",
      metricLabel: "forecast variance",
      nextStep: "Separate rework, acceleration and normal production costs before certification.",
      signal: "BOQ, actual cost and F-2 payment logic"
    },
    "material-continuity": {
      name: "Material Continuity",
      status: "Supply watch",
      metric: "3",
      metricLabel: "critical shortages",
      nextStep: "Confirm facade panels, LV switchgear and fire-stopping delivery windows.",
      signal: "Stock, inbound delivery and coverage logic"
    },
    "risk-decisions": {
      name: "Risk & Decisions",
      status: "Decision required",
      metric: "2",
      metricLabel: "overdue decisions",
      nextStep: "Escalate owner decisions blocking facade shipment and temporary power.",
      signal: "Risk register and decision-log logic"
    }
  },
  projects: [
    {
      project_id: "demo-sample-harbor-logistics",
      project_name: "Sample Harbor Logistics Center",
      name: "Sample Harbor Logistics Center",
      client_name: "Sample Client Group",
      location: "Baku, Azerbaijan",
      current_status: "Recovery watch",
      status: "Recovery watch",
      contract_value: 12800000,
      currency: "AZN",
      planned_progress: 54,
      actual_progress: 47,
      delay_days: 18,
      risk_score: 72,
      updated_at: "2026-06-24T09:30:00+04:00"
    }
  ],
  reports: [
    {
      report_id: "demo-report-executive-june",
      id: "demo-report-executive-june",
      report_name: "Executive Control Report - June 2026",
      name: "Executive Control Report - June 2026",
      project_name: "Sample Harbor Logistics Center",
      format: "PDF",
      snapshot_available: true,
      download_count: 2,
      package_name: "Schedule Recovery",
      status: "Ready",
      summary: "Owner-facing schedule recovery board with delay drivers and next actions.",
      sections: ["Executive summary", "Delay analysis", "Recovery actions", "Source traceability"],
      generated_at: "2026-06-24T09:25:00+04:00"
    },
    {
      report_id: "demo-report-cost-schedule-export",
      id: "demo-report-cost-schedule-export",
      report_name: "Cost and Schedule Data Package",
      name: "Cost and Schedule Data Package",
      project_name: "Sample Harbor Logistics Center",
      format: "Excel",
      snapshot_available: true,
      download_count: 1,
      package_name: "Cost Control",
      status: "Ready",
      summary: "Workbook-style evidence export with cost package, payment and schedule tabs.",
      sections: ["Cost package grid", "Payment trend", "Schedule variance", "Data warnings"],
      generated_at: "2026-06-24T09:31:00+04:00"
    },
    {
      report_id: "demo-report-material-continuity",
      id: "demo-report-material-continuity",
      report_name: "Material Continuity Action Pack",
      name: "Material Continuity Action Pack",
      project_name: "Sample Harbor Logistics Center",
      format: "Excel",
      snapshot_available: true,
      download_count: 1,
      package_name: "Material Continuity",
      status: "Ready",
      summary: "Procurement and stock continuity workbook covering shortage windows, suppliers and action owners.",
      sections: ["Material shortage grid", "Supplier lanes", "Coverage days", "Procurement actions"],
      generated_at: "2026-06-24T10:18:00+04:00"
    },
    {
      report_id: "demo-report-risk-decisions",
      id: "demo-report-risk-decisions",
      report_name: "Risk Decision Register Snapshot",
      name: "Risk Decision Register Snapshot",
      project_name: "Sample Harbor Logistics Center",
      format: "PDF",
      snapshot_available: true,
      download_count: 0,
      package_name: "Risk & Decisions",
      status: "Review",
      summary: "Decision board snapshot for overdue owner actions and mitigation owners.",
      sections: ["Risk matrix", "Decision board", "Owner actions", "Audit trace"],
      generated_at: "2026-06-24T10:32:00+04:00"
    }
  ],
  team: {
    workspace: {
      company_name: "Sample Builder Studio",
      plan: "Plus"
    },
    membership: {
      company_role: "owner",
      status: "active"
    },
    members: [
      {
        membership_id: "demo-member-owner",
        member_email: "demo.owner@devbareun.example",
        company_role: "owner",
        status: "active",
        joined_at: "2026-06-01T10:00:00+04:00"
      },
      {
        membership_id: "demo-member-planner",
        member_email: "demo.planner@devbareun.example",
        company_role: "manager",
        status: "active",
        joined_at: "2026-06-08T14:15:00+04:00"
      }
    ],
    invitations: [
      {
        invitation_id: "demo-invite-finance",
        invitee_email: "demo.finance@devbareun.example",
        company_role: "viewer",
        status: "pending",
        expires_at: "2026-06-27T18:00:00+04:00"
      }
    ]
  },
  projectAccess: {
    grants: [
      {
        grant_id: "demo-grant-manager",
        member_email: "demo.planner@devbareun.example",
        project_role: "manager",
        status: "active"
      },
      {
        grant_id: "demo-grant-owner",
        member_email: "demo.owner@devbareun.example",
        project_role: "manager",
        status: "active"
      }
    ]
  },
  activity: [
    {
      event_id: "demo-event-upload",
      action: "upload.completed",
      occurred_at: "2026-06-24T09:00:00+04:00",
      actor: { email: "demo.planner@devbareun.example" },
      metadata: { format: "XER + XLSX" }
    },
    {
      event_id: "demo-event-analysis",
      action: "analysis.completed",
      occurred_at: "2026-06-24T09:18:00+04:00",
      actor: { type: "system" },
      metadata: { risk_count: 4 }
    },
    {
      event_id: "demo-event-report",
      action: "report.generated",
      occurred_at: "2026-06-24T09:25:00+04:00",
      actor: { type: "system" },
      metadata: { format: "PDF" }
    }
  ],
  resultPayload: {
      project: {
        name: "Sample Harbor Logistics Center",
        project_name: "Sample Harbor Logistics Center",
        status: "Recovery watch",
        currency: "AZN",
        client_name: "Sample Client Group",
        contractor_name: "Sample Builder Studio",
        location: "Baku, Azerbaijan",
        total_area_m2: 48200,
        workforce: "186 site staff",
        start_date: "2025-09-15",
        contract_end: "2027-01-20",
        duration_label: "16 months"
      },
    dashboard: {
      project: {
        name: "Sample Harbor Logistics Center",
        status: "Recovery watch",
        currency: "AZN"
      },
      kpis: {
        total_budget: 12800000,
        actual_cost: 6350000,
        forecast_cost: 13420000,
        risk_score: 72,
        risk_level: "High watch"
      },
      schedule_performance: {
        planned_progress: 54,
        actual_progress: 47,
        variance: -7,
        delay_days: 18
      },
      schedule_buildings: [
        {
          id: "b01",
          name: "Building 1",
          current_stage: "Structural frame complete, facade brackets in progress",
          planned_stage: "Facade installation",
          planned_progress: 58,
          actual_progress: 51,
          delay_days: 14,
          deadline: "2026-10-15",
          risk_level: "High",
          issue: "Facade bracket inspection is late.",
          next_action: "Close inspection comments and release facade crew."
        },
        {
          id: "b02",
          name: "Building 2",
          current_stage: "MEP rough-in continues on levels 2-4",
          planned_stage: "MEP rough-in completion",
          planned_progress: 55,
          actual_progress: 48,
          delay_days: 16,
          deadline: "2026-10-22",
          risk_level: "High",
          issue: "MEP coordination drawings have unresolved comments.",
          next_action: "Run 48-hour clash closure cycle."
        },
        {
          id: "b03",
          name: "Building 3",
          current_stage: "Interior partition works started",
          planned_stage: "Partition works",
          planned_progress: 50,
          actual_progress: 45,
          delay_days: 9,
          deadline: "2026-11-04",
          risk_level: "Medium",
          issue: "Drywall material delivery is partial.",
          next_action: "Prioritize delivery to critical floors."
        },
        {
          id: "b04",
          name: "Building 4",
          current_stage: "Envelope works waiting for panel shipment",
          planned_stage: "Envelope closure",
          planned_progress: 62,
          actual_progress: 42,
          delay_days: 31,
          deadline: "2026-09-30",
          risk_level: "Critical",
          issue: "Panel shipment confirmation is missing.",
          next_action: "Escalate supplier decision and prepare alternate shipment plan."
        },
        {
          id: "b05",
          name: "Building 5",
          current_stage: "Roof waterproofing approved",
          planned_stage: "Roof and facade",
          planned_progress: 49,
          actual_progress: 52,
          delay_days: -4,
          deadline: "2026-11-18",
          risk_level: "Watch",
          issue: "Ahead of plan; monitor crew transfer risk.",
          next_action: "Keep planned crew allocation unchanged."
        },
        {
          id: "b06",
          name: "Building 6",
          current_stage: "Steel erection zone B in progress",
          planned_stage: "Steel completion",
          planned_progress: 43,
          actual_progress: 40,
          delay_days: 5,
          deadline: "2026-12-05",
          risk_level: "Medium",
          issue: "Crane availability is tight.",
          next_action: "Lock crane windows for night shifts."
        },
        {
          id: "b07",
          name: "Building 7",
          current_stage: "Concrete works tracking baseline",
          planned_stage: "Frame cycle",
          planned_progress: 41,
          actual_progress: 41,
          delay_days: 0,
          deadline: "2026-12-12",
          risk_level: "Watch",
          issue: "On plan.",
          next_action: "Continue weekly monitoring."
        },
        {
          id: "b08",
          name: "Building 8",
          current_stage: "Substructure handover pending",
          planned_stage: "Superstructure start",
          planned_progress: 37,
          actual_progress: 30,
          delay_days: 12,
          deadline: "2026-12-20",
          risk_level: "Medium",
          issue: "Drainage inspection is delayed.",
          next_action: "Book inspection slot and recover with double shift."
        },
        {
          id: "b09",
          name: "Building 9",
          current_stage: "Fit-out mockup approved",
          planned_stage: "Fit-out start",
          planned_progress: 57,
          actual_progress: 59,
          delay_days: -3,
          deadline: "2026-10-30",
          risk_level: "Watch",
          issue: "Ahead of plan.",
          next_action: "Use mockup approval to support other buildings."
        },
        {
          id: "b10",
          name: "Building 10",
          current_stage: "Fire-stopping works behind",
          planned_stage: "MEP closure",
          planned_progress: 53,
          actual_progress: 44,
          delay_days: 18,
          deadline: "2026-11-02",
          risk_level: "High",
          issue: "Fire-stopping subcontractor progress is below target.",
          next_action: "Approve additional team and daily quantity tracking."
        },
        {
          id: "b11",
          name: "Building 11",
          current_stage: "External works started",
          planned_stage: "External works",
          planned_progress: 46,
          actual_progress: 43,
          delay_days: 6,
          deadline: "2026-12-08",
          risk_level: "Medium",
          issue: "Paving sequence overlaps with material staging.",
          next_action: "Separate staging area before paving start."
        },
        {
          id: "b12",
          name: "Building 12",
          current_stage: "Testing and commissioning blocked by power room handover",
          planned_stage: "Commissioning",
          planned_progress: 68,
          actual_progress: 49,
          delay_days: 29,
          deadline: "2026-09-25",
          risk_level: "Critical",
          issue: "Power room handover is blocking commissioning path.",
          next_action: "Owner decision needed on temporary power and access."
        }
      ],
      management_summary: {
        overall_status: "Project is active but needs schedule recovery.",
        main_delay_reason: "Facade procurement and MEP coordination are behind the baseline.",
        cost_pressure: "Forecast cost is above contract value because of overtime and expedited material orders.",
        immediate_action: "Approve a two-week recovery plan and lock supplier delivery dates."
      },
      top_risks: [
        {
          risk: "Facade delivery delay",
          level: "High",
          reason: "Supplier confirmation is missing for two shipment lots.",
          action: "Confirm delivery slots and prepare alternate supplier option."
        },
        {
          risk: "MEP coordination clash",
          level: "Medium",
          reason: "Level 3 ceiling coordination has unresolved service routes.",
          action: "Run a focused coordination meeting with site, design and subcontractor leads."
        },
        {
          risk: "Cost overrun pressure",
          level: "Medium",
          reason: "Overtime and crane standby costs are trending above baseline.",
          action: "Approve recovery work only for critical activities and track weekly cost impact."
        }
      ],
      recommended_actions: [
        "Freeze the next two-week recovery schedule by trade package.",
        "Confirm facade delivery dates before approving interior acceleration.",
        "Review MEP clash list every 48 hours until Level 3 is cleared.",
        "Export the executive report for the weekly owner meeting."
      ],
      document_control: {
        uploaded_files: 5,
        missing_documents: 1
      },
      data_quality: {
        confidence: 88,
        warnings: [
          "One material delivery date is missing.",
          "Progress payment file has two rows without cost codes."
        ],
        sheet_profiles: [
          { name: "Baseline schedule", rows: 1240 },
          { name: "Actual progress", rows: 1186 },
          { name: "Cost control", rows: 342 }
        ]
      },
      analysis_provenance: {
        file_count: 5,
        source_fingerprint: "demo-8cf2b8b71f4c9a24",
        analysis_engine_version: "demo-v1.0",
        files: [
          {
            file_id: "demo-file-xer",
            filename: "baseline_schedule_demo.xer",
            extension: "XER",
            size_bytes: 1843200,
            checksum_status: "verified",
            security_scan_status: "clean",
            content_hash_source: "sha256"
          },
          {
            file_id: "demo-file-progress",
            filename: "actual_progress_june_demo.xlsx",
            extension: "XLSX",
            size_bytes: 624000,
            checksum_status: "verified",
            security_scan_status: "clean",
            content_hash_source: "sha256"
          },
          {
            file_id: "demo-file-cost",
            filename: "cost_control_demo.xlsx",
            extension: "XLSX",
            size_bytes: 512400,
            checksum_status: "verified",
            security_scan_status: "clean",
            content_hash_source: "sha256"
          }
        ]
      },
      reports: [
        {
          id: "demo-report-executive-june",
          report_id: "demo-report-executive-june",
          report_name: "Executive Control Report - June 2026"
        }
      ],
      last_updated: "2026-06-24T09:30:00+04:00"
    }
  },
  packageResults: {
    "cost-control": {
      project: {
        name: "Sample Harbor Logistics Center",
        project_name: "Sample Harbor Logistics Center",
        status: "Cost pressure",
        currency: "AZN",
        client_name: "Sample Client Group",
        contractor_name: "Sample Builder Studio",
        location: "Baku, Azerbaijan",
        start_date: "2025-09-15",
        contract_end: "2027-01-20",
        duration_label: "16 months"
      },
      dashboard: {
        package_id: "cost-control",
        project: {
          name: "Sample Harbor Logistics Center",
          status: "Cost pressure",
          currency: "AZN"
        },
        kpis: {
          total_budget: 12800000,
          actual_cost: 6350000,
          committed_cost: 9820000,
          forecast_cost: 13420000,
          payment_certified: 5480000,
          cost_variance: 620000,
          variance_percent: 4.8,
          risk_score: 68,
          risk_level: "High watch"
        },
        cost_control: {
          summary: "Forecast cost is above contract value because facade acceleration, crane standby and MEP rework are trending above baseline.",
          packages: [
            { code: "C-01", name: "Structural concrete", budget: 2450000, actual: 2380000, forecast: 2520000, variance: 70000, progress: 72, status: "Watch", issue: "Concrete wastage is above plan on two pour zones.", action: "Approve quantity reconciliation before next payment." },
            { code: "C-02", name: "Facade and envelope", budget: 2180000, actual: 1360000, forecast: 2510000, variance: 330000, progress: 46, status: "Critical", issue: "Expedited panel shipment and bracket rework are not in the baseline.", action: "Freeze alternate supplier pricing by Friday." },
            { code: "C-03", name: "MEP rough-in", budget: 1960000, actual: 1120000, forecast: 2120000, variance: 160000, progress: 48, status: "High", issue: "Coordination clashes are creating rework hours.", action: "Track rework labor separately from production labor." },
            { code: "C-04", name: "Interior fit-out", budget: 1620000, actual: 620000, forecast: 1580000, variance: -40000, progress: 32, status: "On track", issue: "Fit-out remains inside allowance.", action: "Protect contingency and avoid early overtime release." },
            { code: "C-05", name: "External works", budget: 980000, actual: 410000, forecast: 1040000, variance: 60000, progress: 39, status: "Watch", issue: "Paving sequence overlaps with temporary storage.", action: "Separate staging cost before next procurement order." },
            { code: "C-06", name: "Site preliminaries", budget: 1210000, actual: 820000, forecast: 1450000, variance: 240000, progress: 61, status: "High", issue: "Crane standby and night-shift supervision are rising.", action: "Approve recovery shifts only for critical packages." }
          ],
          payment_trend: [
            { period: "Jan", planned: 620000, actual: 580000 },
            { period: "Feb", planned: 760000, actual: 710000 },
            { period: "Mar", planned: 940000, actual: 880000 },
            { period: "Apr", planned: 1110000, actual: 980000 },
            { period: "May", planned: 1260000, actual: 1190000 },
            { period: "Jun", planned: 1420000, actual: 1360000 }
          ],
          change_orders: [
            { id: "CO-014", title: "Facade bracket redesign", value: 145000, status: "Pending approval", owner: "Client QS", due_date: "2026-06-28" },
            { id: "CO-018", title: "Night shift acceleration", value: 98000, status: "Under review", owner: "Project director", due_date: "2026-06-27" },
            { id: "CO-021", title: "Temporary power for commissioning", value: 74000, status: "Decision needed", owner: "Owner rep", due_date: "2026-06-26" }
          ],
          decisions: [
            "Approve only critical-path acceleration costs for the next two weeks.",
            "Separate rework cost codes from normal production before payment certification.",
            "Negotiate facade shipment premium before confirming the recovery schedule."
          ]
        },
        document_control: { uploaded_files: 4, missing_documents: 1 },
        data_quality: {
          confidence: 86,
          warnings: ["Two cost rows are missing cost-code ownership.", "One change order does not have approval status."],
          sheet_profiles: [{ name: "BOQ", rows: 612 }, { name: "Actual cost", rows: 424 }, { name: "Payment certificates", rows: 88 }]
        },
        analysis_provenance: {
          file_count: 4,
          source_fingerprint: "demo-cost-b2d91f84",
          analysis_engine_version: "demo-v1.0",
          files: [
            { file_id: "demo-cost-boq", filename: "boq_cost_plan_demo.xlsx", extension: "XLSX", size_bytes: 734000, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" },
            { file_id: "demo-cost-actual", filename: "actual_cost_june_demo.xlsx", extension: "XLSX", size_bytes: 512400, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" },
            { file_id: "demo-cost-payment", filename: "f2_payment_certificate_demo.pdf", extension: "PDF", size_bytes: 392000, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" }
          ]
        },
        recommended_actions: [
          "Freeze facade acceleration spend until shipment premium is approved.",
          "Reconcile structural concrete quantities before the next payment cycle.",
          "Move night-shift approval into a weekly cost-impact log."
        ],
        last_updated: "2026-06-24T10:05:00+04:00"
      }
    },
    "material-continuity": {
      project: {
        name: "Sample Harbor Logistics Center",
        project_name: "Sample Harbor Logistics Center",
        status: "Supply watch",
        currency: "AZN",
        client_name: "Sample Client Group",
        contractor_name: "Sample Builder Studio",
        location: "Baku, Azerbaijan",
        start_date: "2025-09-15",
        contract_end: "2027-01-20",
        duration_label: "16 months"
      },
      dashboard: {
        package_id: "material-continuity",
        project: {
          name: "Sample Harbor Logistics Center",
          status: "Supply watch",
          currency: "AZN"
        },
        kpis: {
          material_risk_score: 74,
          critical_shortages: 3,
          average_coverage_days: 13,
          open_purchase_orders: 11,
          delayed_deliveries: 4,
          risk_level: "High watch"
        },
        material_continuity: {
          summary: "Facade panels, switchgear and fire-stopping stock are the main continuity constraints for the next two-week work plan.",
          inventory: [
            { code: "M-101", name: "Facade aluminum panels", category: "Envelope", required_qty: 5400, stock_qty: 1800, inbound_qty: 900, unit: "m2", coverage_days: 9, status: "Critical", supplier: "Baku Panel Supply", issue: "Shipment lot 2 is not confirmed.", action: "Confirm vessel slot and reserve alternate local batch." },
            { code: "M-118", name: "MEP cable trays", category: "MEP", required_qty: 12800, stock_qty: 6100, inbound_qty: 2500, unit: "m", coverage_days: 18, status: "Watch", supplier: "Sample Electro Supply", issue: "Stock is enough for current rough-in only.", action: "Release next PO after level 3 clash closure." },
            { code: "M-133", name: "Fire-stopping sealant", category: "Life safety", required_qty: 980, stock_qty: 210, inbound_qty: 120, unit: "box", coverage_days: 7, status: "Critical", supplier: "SafeJoint Trading", issue: "Consumption rate doubled after rework.", action: "Approve emergency top-up for Buildings 10 and 12." },
            { code: "M-146", name: "Roof waterproofing membrane", category: "Roof", required_qty: 7800, stock_qty: 5200, inbound_qty: 0, unit: "m2", coverage_days: 31, status: "Healthy", supplier: "BlueRoof", issue: "No immediate shortage.", action: "Keep stock transfer blocked from non-critical zones." },
            { code: "M-159", name: "LV switchgear", category: "Electrical", required_qty: 24, stock_qty: 6, inbound_qty: 8, unit: "set", coverage_days: 11, status: "Critical", supplier: "GridLine Systems", issue: "Factory test certificate is missing.", action: "Escalate certificate release and align commissioning access." },
            { code: "M-172", name: "Drywall boards", category: "Interior", required_qty: 14600, stock_qty: 7800, inbound_qty: 2200, unit: "sheet", coverage_days: 22, status: "Watch", supplier: "BuildBoard", issue: "Delivery split is not matched to floor sequence.", action: "Retag delivery by building and floor." }
          ],
          supplier_lanes: [
            { supplier: "Baku Panel Supply", lane: "Facade", reliability: 62, next_delivery: "2026-06-29", status: "Critical" },
            { supplier: "GridLine Systems", lane: "Electrical", reliability: 68, next_delivery: "2026-07-02", status: "High" },
            { supplier: "SafeJoint Trading", lane: "Life safety", reliability: 74, next_delivery: "2026-06-27", status: "Watch" },
            { supplier: "BlueRoof", lane: "Roof", reliability: 91, next_delivery: "Stocked", status: "Healthy" }
          ],
          consumption_trend: [
            { period: "W21", planned: 82, actual: 76 },
            { period: "W22", planned: 86, actual: 91 },
            { period: "W23", planned: 88, actual: 97 },
            { period: "W24", planned: 92, actual: 105 }
          ],
          procurement_actions: [
            "Confirm facade shipment lot 2 before moving facade crews.",
            "Approve fire-stopping emergency top-up for Buildings 10 and 12.",
            "Release LV switchgear only after factory certificate is received.",
            "Retag drywall delivery by floor sequence to avoid double handling."
          ]
        },
        document_control: { uploaded_files: 4, missing_documents: 1 },
        data_quality: {
          confidence: 84,
          warnings: ["One supplier lane has no confirmed delivery time.", "Two material rows are missing storage zone."],
          sheet_profiles: [{ name: "Material BOQ", rows: 520 }, { name: "Stock ledger", rows: 386 }, { name: "Procurement tracker", rows: 128 }]
        },
        analysis_provenance: {
          file_count: 4,
          source_fingerprint: "demo-material-91af2c64",
          analysis_engine_version: "demo-v1.0",
          files: [
            { file_id: "demo-material-boq", filename: "material_boq_demo.xlsx", extension: "XLSX", size_bytes: 684000, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" },
            { file_id: "demo-material-stock", filename: "stock_records_demo.xlsx", extension: "XLSX", size_bytes: 348000, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" },
            { file_id: "demo-material-procurement", filename: "procurement_updates_demo.csv", extension: "CSV", size_bytes: 126000, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" }
          ]
        },
        recommended_actions: [
          "Lock material delivery dates against the two-week workface plan.",
          "Escalate missing certificates before commissioning blockers spread.",
          "Protect healthy roof stock from transfer to non-critical zones."
        ],
        last_updated: "2026-06-24T10:18:00+04:00"
      }
    },
    "risk-decisions": {
      project: {
        name: "Sample Harbor Logistics Center",
        project_name: "Sample Harbor Logistics Center",
        status: "Decision required",
        currency: "AZN",
        client_name: "Sample Client Group",
        contractor_name: "Sample Builder Studio",
        location: "Baku, Azerbaijan",
        start_date: "2025-09-15",
        contract_end: "2027-01-20",
        duration_label: "16 months"
      },
      dashboard: {
        package_id: "risk-decisions",
        project: {
          name: "Sample Harbor Logistics Center",
          status: "Decision required",
          currency: "AZN"
        },
        kpis: {
          risk_score: 78,
          open_risks: 9,
          critical_risks: 3,
          overdue_decisions: 2,
          decision_cycle_days: 5.4,
          risk_level: "Critical watch"
        },
        risk_decisions: {
          summary: "Three decisions are now blocking schedule recovery: facade shipment approval, temporary power access and MEP clash closure ownership.",
          risks: [
            { id: "R-01", title: "Facade shipment approval delay", category: "Procurement", severity: "Critical", probability: 78, impact: 88, owner: "Owner rep", due_date: "2026-06-26", status: "Decision needed", decision_needed: "Approve shipment premium or alternate supplier.", action: "Prepare cost/time comparison for steering meeting." },
            { id: "R-02", title: "Temporary power blocks commissioning", category: "Access", severity: "Critical", probability: 72, impact: 84, owner: "Client utilities", due_date: "2026-06-27", status: "Decision needed", decision_needed: "Confirm temporary power access route.", action: "Issue one-page access decision request." },
            { id: "R-03", title: "MEP clash closure slows rough-in", category: "Design", severity: "High", probability: 69, impact: 72, owner: "Design manager", due_date: "2026-06-28", status: "Open", decision_needed: "Assign final routing authority.", action: "Run 48-hour closure room with site and design." },
            { id: "R-04", title: "Crane standby cost pressure", category: "Cost", severity: "High", probability: 61, impact: 67, owner: "Construction manager", due_date: "2026-06-29", status: "Open", decision_needed: "Limit night shift crane use.", action: "Approve crane windows only for critical picks." },
            { id: "R-05", title: "Fire-stopping stock shortage", category: "Material", severity: "Medium", probability: 64, impact: 58, owner: "Procurement lead", due_date: "2026-06-27", status: "Mitigation active", decision_needed: "Approve emergency top-up.", action: "Release emergency PO for Buildings 10 and 12." },
            { id: "R-06", title: "Payment certificate evidence gaps", category: "Commercial", severity: "Medium", probability: 52, impact: 55, owner: "QS lead", due_date: "2026-07-01", status: "Open", decision_needed: "Agree evidence pack format.", action: "Align cost-code evidence with client QS." }
          ],
          decisions: [
            { id: "D-14", title: "Facade shipment premium", owner: "Owner representative", status: "Overdue", due_date: "2026-06-23", impact: "31-day delay risk on Building 4", next_step: "Approve premium or alternate supplier today." },
            { id: "D-17", title: "Temporary power access", owner: "Client utilities", status: "Due now", due_date: "2026-06-26", impact: "Commissioning blocked on Building 12", next_step: "Confirm access route and temporary connection responsibility." },
            { id: "D-21", title: "MEP routing authority", owner: "Design manager", status: "Open", due_date: "2026-06-28", impact: "Rework risk across levels 2-4", next_step: "Nominate final routing approver." },
            { id: "D-24", title: "Night shift cost limit", owner: "Project director", status: "Open", due_date: "2026-06-29", impact: "Controls recovery cost exposure", next_step: "Approve cost cap for critical activities only." }
          ],
          matrix: [
            { level: "Critical", count: 3, color: "#EF4444" },
            { level: "High", count: 2, color: "#F08A1E" },
            { level: "Medium", count: 3, color: "#D4A24C" },
            { level: "Low", count: 1, color: "#22C55E" }
          ],
          actions: [
            "Move overdue decisions into a daily owner-action list.",
            "Attach schedule-day impact to every critical decision request.",
            "Close MEP routing authority before releasing rough-in recovery crews.",
            "Keep cost decisions tied to approved recovery activities only."
          ]
        },
        top_risks: [
          { risk: "Facade shipment approval delay", level: "Critical", reason: "Decision is blocking Building 4 envelope closure.", action: "Approve premium or alternate supplier." },
          { risk: "Temporary power blocks commissioning", level: "Critical", reason: "Building 12 commissioning cannot proceed without access.", action: "Confirm temporary connection route." },
          { risk: "MEP clash closure slows rough-in", level: "High", reason: "Routing decision remains open.", action: "Assign final routing authority." }
        ],
        document_control: { uploaded_files: 4, missing_documents: 0 },
        data_quality: {
          confidence: 87,
          warnings: ["One decision item has no named approver.", "Two risk rows need updated due dates."],
          sheet_profiles: [{ name: "Risk register", rows: 96 }, { name: "Decision log", rows: 42 }, { name: "Site notes", rows: 118 }]
        },
        analysis_provenance: {
          file_count: 4,
          source_fingerprint: "demo-risk-67c8af31",
          analysis_engine_version: "demo-v1.0",
          files: [
            { file_id: "demo-risk-register", filename: "risk_register_demo.xlsx", extension: "XLSX", size_bytes: 244000, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" },
            { file_id: "demo-risk-decisions", filename: "decision_log_demo.xlsx", extension: "XLSX", size_bytes: 188000, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" },
            { file_id: "demo-risk-notes", filename: "site_notes_demo.pdf", extension: "PDF", size_bytes: 418000, checksum_status: "verified", security_scan_status: "clean", content_hash_source: "sha256" }
          ]
        },
        recommended_actions: [
          "Resolve facade shipment decision before the next recovery update.",
          "Escalate temporary power access to the owner decision meeting.",
          "Attach due dates and owners to every high-severity risk."
        ],
        last_updated: "2026-06-24T10:32:00+04:00"
      }
    }
  }
};
