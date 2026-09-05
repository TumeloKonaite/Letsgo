// Manage the package list, publication actions, and per-package request feedback.

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  deletePackage,
  getAdminPackages,
  publishPackage,
  unpublishPackage,
} from "../../api/adminPackagesApi";
import { useAuth } from "../../auth/AuthProvider";
import { SectionHeading } from "../../components/SectionHeading";
import { StatusPanel } from "../../components/StatusPanel";
import { formatCurrency } from "../../lib/formatters";

function formatStatusLabel(status) {
  return String(status || "")
    .toLowerCase()
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function getStatusTone(status) {
  const normalizedStatus = String(status || "").trim().toLowerCase();

  if (normalizedStatus === "published") {
    return "published";
  }

  if (normalizedStatus === "archived") {
    return "archived";
  }

  return "draft";
}

function formatFlagLabel(value) {
  return value ? "Yes" : "No";
}

export function AdminPackagesPage() {
  const { logout } = useAuth();
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [activePackageId, setActivePackageId] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadPackages() {
      try {
        const packagesPayload = await getAdminPackages();

        if (!isMounted) {
          return;
        }

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

    loadPackages();

    return () => {
      isMounted = false;
    };
  }, []);

  async function handlePublishToggle(packageItem) {
    setActionError("");
    setActivePackageId(packageItem.id);

    try {
      const updatedPackage = packageItem.is_published
        ? await unpublishPackage(packageItem.id)
        : await publishPackage(packageItem.id);

      setPackages((currentPackages) =>
        currentPackages.map((currentPackage) =>
          currentPackage.id === updatedPackage.id ? updatedPackage : currentPackage
        )
      );
    } catch (requestError) {
      setActionError(requestError.message);
    } finally {
      setActivePackageId(null);
    }
  }

  async function handleDelete(packageItem) {
    const confirmed = window.confirm(
      `Delete "${packageItem.title}"? This action cannot be undone.`
    );

    if (!confirmed) {
      return;
    }

    setActionError("");
    setActivePackageId(packageItem.id);

    try {
      await deletePackage(packageItem.id);
      setPackages((currentPackages) =>
        currentPackages.filter((currentPackage) => currentPackage.id !== packageItem.id)
      );
    } catch (requestError) {
      setActionError(requestError.message);
    } finally {
      setActivePackageId(null);
    }
  }

  const packageCounts = {
    total: packages.length,
    active: packages.filter((packageItem) => packageItem.is_active).length,
    published: packages.filter((packageItem) => packageItem.is_published).length,
    featured: packages.filter((packageItem) => packageItem.is_featured).length,
  };

  return (
    <main className="page">
      <div className="container">
        <section className="page-hero fade-up">
          <div className="page-hero__panel admin-dashboard__hero">
            <div className="admin-toolbar">
              <div>
                <span className="eyebrow-dark">Admin packages</span>
                <h1>Manage tourism packages</h1>
              </div>

              <div className="hero__actions admin-toolbar__actions">
                <Link className="button" to="/admin/packages/new">
                  Create package
                </Link>
                <Link className="button-secondary" to="/admin/dashboard">
                  Back to dashboard
                </Link>
                <button className="button-secondary" type="button" onClick={() => logout("/")}>
                  Log out
                </button>
              </div>
            </div>

            <p>
              Review draft, published, and archived packages, then publish, unpublish,
              edit, or remove them from one protected admin route.
            </p>

            <div className="admin-summary-grid">
              <article className="detail-panel">
                <span className="eyebrow-dark">Total packages</span>
                <h3>{packageCounts.total}</h3>
                <p>All packages returned from the protected admin inventory endpoint.</p>
              </article>

              <article className="detail-panel">
                <span className="eyebrow-dark">Active</span>
                <h3>{packageCounts.active}</h3>
                <p>Packages currently marked active in the admin catalog.</p>
              </article>

              <article className="detail-panel">
                <span className="eyebrow-dark">Published</span>
                <h3>{packageCounts.published}</h3>
                <p>Packages currently visible through the published package flow.</p>
              </article>

              <article className="detail-panel">
                <span className="eyebrow-dark">Featured</span>
                <h3>{packageCounts.featured}</h3>
                <p>Packages highlighted for the public storefront experience.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="section">
          <SectionHeading
            eyebrow="Inventory"
            title="Package dashboard"
            description="Every request on this page is sent with the current Clerk session token."
          />

          {actionError ? (
            <StatusPanel title="Could not complete package action." message={actionError} tone="error" />
          ) : null}

          {loading ? (
            <StatusPanel
              title="Loading packages..."
              message="Fetching package inventory from the protected admin API."
            />
          ) : null}

          {!loading && error ? (
            <StatusPanel
              title="Could not load packages."
              message={error}
              tone="error"
            />
          ) : null}

          {!loading && !error && packages.length === 0 ? (
            <StatusPanel
              title="No packages found. Create your first package."
              message="Start by creating a package, then return here to publish and manage it."
              tone="empty"
              action={(
                <Link className="button" to="/admin/packages/new">
                  Create package
                </Link>
              )}
            />
          ) : null}

          {!loading && !error && packages.length > 0 ? (
            <div className="admin-table-shell fade-up">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th scope="col">Title</th>
                    <th scope="col">Destination</th>
                    <th scope="col">Price From</th>
                    <th scope="col">Status</th>
                    <th scope="col">Active</th>
                    <th scope="col">Published</th>
                    <th scope="col">Featured</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {packages.map((packageItem) => {
                    const isBusy = activePackageId === packageItem.id;

                    return (
                      <tr key={packageItem.id}>
                        <td>
                          <div className="admin-table__title">
                            <strong>{packageItem.title}</strong>
                            <span>{packageItem.slug}</span>
                          </div>
                        </td>
                        <td>{packageItem.destination}</td>
                        <td>{formatCurrency(packageItem.price_from, packageItem.currency)}</td>
                        <td>
                          <span
                            className={`admin-status admin-status--${getStatusTone(packageItem.status)}`}
                          >
                            {formatStatusLabel(packageItem.status)}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`admin-flag admin-flag--${packageItem.is_active ? "positive" : "muted"}`}
                          >
                            {formatFlagLabel(packageItem.is_active)}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`admin-flag admin-flag--${packageItem.is_published ? "positive" : "muted"}`}
                          >
                            {formatFlagLabel(packageItem.is_published)}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`admin-flag admin-flag--${packageItem.is_featured ? "accent" : "muted"}`}
                          >
                            {formatFlagLabel(packageItem.is_featured)}
                          </span>
                        </td>
                        <td>
                          <div className="admin-table__actions">
                            <Link className="button-secondary admin-action" to={`/admin/packages/${packageItem.id}/edit`}>
                              Edit
                            </Link>
                            <button
                              className="button-secondary admin-action"
                              type="button"
                              onClick={() => handlePublishToggle(packageItem)}
                              disabled={isBusy}
                            >
                              {packageItem.is_published ? "Unpublish" : "Publish"}
                            </button>
                            <button
                              className="button-secondary admin-action admin-action--danger"
                              type="button"
                              onClick={() => handleDelete(packageItem)}
                              disabled={isBusy}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
