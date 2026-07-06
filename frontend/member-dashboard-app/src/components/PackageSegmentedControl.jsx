import { BarChart3, ClipboardList, Gauge, ShieldAlert } from "lucide-react";
import { analysisPackages } from "../data/packages";
import { demoWorkspace } from "../data/demoWorkspace";

function packageIcon(packageId) {
  if (packageId === "cost-control") return Gauge;
  if (packageId === "material-continuity") return ClipboardList;
  if (packageId === "risk-decisions") return ShieldAlert;
  return BarChart3;
}

export function PackageSegmentedControl({
  activePackage = "schedule-recovery",
  onPackageChange,
  onPackageOpen,
  showMetric = false,
  ariaLabel = "Switch package"
}) {
  return (
    <div className="package-segmented-control" role="group" aria-label={ariaLabel}>
      {analysisPackages.map((item) => {
        const Icon = packageIcon(item.id);
        const insight = demoWorkspace.packageInsights?.[item.id];
        const active = item.id === activePackage;
        return (
          <button
            key={item.id}
            type="button"
            className={active ? "active" : ""}
            aria-label={showMetric && insight ? `${item.name}, ${insight.metric} ${insight.metricLabel}` : item.name}
            aria-pressed={active}
            onClick={() => {
              onPackageChange?.(item.id);
              onPackageOpen?.(item.id);
            }}
          >
            <Icon size={16} />
            <span>
              <strong>{item.name}</strong>
              {showMetric ? <small>{insight?.metric} - {insight?.metricLabel}</small> : null}
            </span>
          </button>
        );
      })}
    </div>
  );
}
