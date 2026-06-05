import { Link, useParams } from "react-router-dom";

import { StatusPanel } from "../../components/StatusPanel";

export function AdminPackageEditorPage() {
  const { packageId } = useParams();
  const isCreateMode = !packageId;

  return (
    <main className="page">
      <div className="container">
        <section className="page-hero fade-up">
          <div className="page-hero__panel admin-dashboard__hero">
            <span className="eyebrow-dark">Protected admin</span>
            <h1>{isCreateMode ? "Create package" : "Edit package"}</h1>
            <p>
              This protected route is ready for the package form workflow. The admin
              packages dashboard now links here directly instead of landing on a 404.
            </p>

            <div className="hero__actions">
              <Link className="button-secondary" to="/admin/packages">
                Back to packages
              </Link>
            </div>
          </div>
        </section>

        <section className="section">
          <StatusPanel
            title={isCreateMode ? "Package creation page placeholder" : `Package editor placeholder for #${packageId}`}
            message="The dashboard route is wired up and protected. The package form itself can now be added on top of this route without changing navigation again."
            tone="empty"
          />
        </section>
      </div>
    </main>
  );
}
