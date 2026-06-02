import { ChevronRight } from "lucide-react";
import SectionHeader from "./SectionHeader.jsx";

export default function SettingsWorkspace({ groups }) {
  return (
    <article className="db-card-light p-5">
      <SectionHeader
        eyebrow="Settings"
        title="Workspace Settings"
        description="Profile, notification and integration placeholders are prepared for future backend connection."
        action={<button className="db-button db-button-primary" type="button">Save settings</button>}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        {groups.map((group) => (
          <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={group.title}>
            <h3 className="mb-4 text-lg font-black text-slate-950 dark:text-white">{group.title}</h3>
            <div className="grid gap-2">
              {group.items.map((item) => (
                <button className="flex items-center justify-between rounded-2xl bg-slate-100/80 px-3 py-3 text-left text-sm font-bold text-slate-700 transition hover:bg-cyan-300/10 dark:bg-white/[0.045] dark:text-slate-200" key={item} type="button">
                  {item}
                  <ChevronRight size={16} className="text-cyanAccent" />
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
