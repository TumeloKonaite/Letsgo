import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getAdminPackages } from "../../api/adminPackagesApi";
import { useAuth } from "../../auth/AuthProvider";
import { SectionHeading } from "../../components/SectionHeading";
import { StatusPanel } from "../../components/StatusPanel";
import { getCurrentAdmin } from "../../lib/adminApi";
import { formatCurrency } from "../../lib/formatters";

function formatStatusLabel(status) {
  // Convert API status identifiers into readable labels.
  return status
    .toLowerCase()
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function Dashboard() {
  // Load protected profile and package data for the admin overview.
  const { user, isAdmin, adminClaimName, logout } = useAuth();
  const [packages, setPackages] = useState([]);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadAdminData() {
      // Fetch independent dashboard resources together to reduce load time.
      try {
        const [profilePayload, packagesPayload] = await Promise.all([
          getCurrentAdmin(),
          getAdminPackages(),
        ]);

        if (!isMounted) {
          return;
        }

        setProfile(profilePayload);
        setPackages(packagesPayload);
        setError("");
      } catch (requestError) {
        if (!isMounted) {
          return;
        }

        setError(requestError.message);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadAdminData();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main className="page">
      <div className="container">
        <section className="page-hero fade-up">
          <div className="page-hero__panel admin-dashboard__hero">
            <div className="admin-toolbar">
              <div>
                <span className="eyebrow-dark">Protected admin</span>
                <h1>Package management</h1>
              </div>

              <div className="hero__actions admin-toolbar__actions">
                <Link className="button" to="/admin/packages">
                  Open package dashboard
                </Link>
                <button className="button-secondary" type="button" onClick={() => logout("/")}>
                  Log out
                </button>
              </div>
            </div>

            <p>
              This page validates the Clerk session, refreshes the token
              when needed, and calls protected admin endpoints with
              <code> Authorization: Bearer &lt;Clerk session token&gt;</code>.
            </p>

            <div className="admin-summary-grid">
              <article className="detail-panel">
                <span className="eyebrow-dark">Signed in as</span>
                <h3>{profile?.username || user?.username || "Admin"}</h3>
                <p>{profile?.email || user?.email || "No email returned from Clerk."}</p>
              </article>

              <article className="detail-panel">
                <span className="eyebrow-dark">Admin claim</span>
                <h3>{isAdmin ? "Granted" : "Missing"}</h3>
                <p>
                  The backend only serves admin data when the Clerk session claim
                  <code> {adminClaimName}: true</code> is present.
                </p>
              </article>

              <article className="detail-panel">
                <span className="eyebrow-dark">Packages</span>
                <h3>{packages.length}</h3>
                <p>Loaded from the protected <code>GET /api/admin/packages</code> endpoint.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="section">
          <SectionHeading
            eyebrow="Admin packages"
            title="Protected package list"
            description="Only authenticated admins can reach this route and fetch this data."
          />

          {loading ? (
            <StatusPanel
              title="Loading admin packages"
              message="Fetching your admin profile and package inventory from protected API routes."
            />
          ) : null}

          {!loading && error ? (
            <StatusPanel
              title="Admin data unavailable"
              message={error}
              tone="error"
            />
          ) : null}

          {!loading && !error && packages.length === 0 ? (
            <StatusPanel
              title="No packages yet"
              message="The admin API returned an empty package list."
              tone="empty"
            />
          ) : null}

          {!loading && !error && packages.length > 0 ? (
            <div className="admin-package-grid">
              {packages.map((packageItem) => (
                <article className="detail-panel fade-up" key={packageItem.id}>
                  <div className="admin-package-card__header">
                    <div>
                      <span className="eyebrow-dark">{packageItem.slug}</span>
                      <h3>{packageItem.title}</h3>
                    </div>
                    <span className={`admin-status admin-status--${packageItem.is_published ? "published" : "draft"}`}>
                      {formatStatusLabel(packageItem.status)}
                    </span>
                  </div>

                  <p>{packageItem.short_description || packageItem.description}</p>

                  <div className="admin-package-card__meta">
                    <span>{packageItem.destination}</span>
                    <span>
                      {packageItem.duration_days} days / {packageItem.duration_nights} nights
                    </span>
                    <span>{formatCurrency(packageItem.price_from, packageItem.currency)}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
