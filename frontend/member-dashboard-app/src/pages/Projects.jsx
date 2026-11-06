import { EmptyState, PageHeader } from "../components/Shell";
import { useT } from "../lib/i18n";

export function Projects({ projects, onNavigate }) {
  const t = useT();
  return (
    <>
      <PageHeader
        eyebrow={t("Projects", "Layihələr")}
        title={t("My projects", "Layihələrim")}
        description={t("Every project you upload for a delay analysis is listed here.", "Gecikmə analizi üçün yüklədiyiniz hər layihə burada görünür.")}
        action={<button type="button" className="primary-button" onClick={() => onNavigate("upload")}>{t("New delay analysis", "Yeni gecikmə analizi")}</button>}
      />
      {projects.length === 0 ? (
        <EmptyState
          title={t("No projects yet.", "Hələ layihə yoxdur.")}
          description={t("A project is created when you upload its planning, F2 and F3 certificates and contract.", "Layihə onun planlaması, F2 və F3 aktları və müqaviləsi yükləndikdə yaranır.")}
        />
      ) : (
        <section className="card-grid">
          {projects.map((project) => (
            <article className="panel" key={project.project_id || project.id}>
              <span className="workspace-eyebrow">{project.current_status || project.status || t("Project", "Layihə")}</span>
              <h2>{project.project_name || project.name || t("Untitled project", "Adsız layihə")}</h2>
              <p>{project.location || project.client_name || t("Details appear after the files are read.", "Məlumat fayllar oxunduqdan sonra görünür.")}</p>
            </article>
          ))}
        </section>
      )}
    </>
  );
}
