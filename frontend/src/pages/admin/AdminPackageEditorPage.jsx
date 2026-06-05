import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  createPackage,
  getAdminPackage,
  updatePackage,
} from "../../api/adminPackagesApi";
import { useAuth } from "../../auth/AuthProvider";
import {
  createDefaultPackageValues,
  normalizePackageFormValues,
  PackageForm,
} from "../../components/admin/PackageForm";
import { StatusPanel } from "../../components/StatusPanel";

export function AdminPackageEditorPage() {
  const { getAccessToken } = useAuth();
  const navigate = useNavigate();
  const { packageId } = useParams();
  const isCreateMode = !packageId;
  const [initialValues, setInitialValues] = useState(() => createDefaultPackageValues());
  const [loading, setLoading] = useState(!isCreateMode);
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isCreateMode) {
      setInitialValues(createDefaultPackageValues());
      setLoading(false);
      setLoadError("");
      return;
    }

    let isMounted = true;

    async function loadPackage() {
      setLoading(true);
      setLoadError("");
      setSaveError("");
      setFieldErrors({});

      try {
        const packagePayload = await getAdminPackage(packageId, getAccessToken);

        if (!isMounted) {
          return;
        }

        setInitialValues(normalizePackageFormValues(packagePayload));
      } catch (requestError) {
        if (!isMounted) {
          return;
        }

        setLoadError(requestError.message || "Could not load package.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadPackage();

    return () => {
      isMounted = false;
    };
  }, [getAccessToken, isCreateMode, packageId]);

  async function handleSubmit(payload) {
    if (isSaving) {
      return;
    }

    setIsSaving(true);
    setSaveError("");
    setFieldErrors({});

    try {
      if (isCreateMode) {
        await createPackage(payload, getAccessToken);
      } else {
        await updatePackage(packageId, payload, getAccessToken);
      }

      navigate("/admin/packages", { replace: true });
    } catch (requestError) {
      setSaveError(requestError.message || "Could not save package.");
      setFieldErrors(requestError.fieldErrors || {});
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="page">
      <div className="container">
        <section className="page-hero fade-up">
          <div className="page-hero__panel admin-dashboard__hero">
            <span className="eyebrow-dark">Protected admin</span>
            <h1>{isCreateMode ? "Create package" : "Edit package"}</h1>
            <p>
              {isCreateMode
                ? "Create a new tourism package from the protected admin dashboard."
                : "Update an existing tourism package and save changes back to the protected admin API."}
            </p>

            <div className="hero__actions">
              <Link className="button-secondary" to="/admin/packages">
                Back to packages
              </Link>
            </div>
          </div>
        </section>

        <section className="section">
          {loading ? (
            <StatusPanel
              title="Loading existing package..."
              message="Fetching package details from the protected admin API."
            />
          ) : null}

          {!loading && loadError ? (
            <StatusPanel
              title="Could not load package."
              message={loadError}
              tone="error"
              action={(
                <Link className="button-secondary" to="/admin/packages">
                  Back to packages
                </Link>
              )}
            />
          ) : null}

          {!loading && !loadError ? (
            <PackageForm
              initialValues={initialValues}
              onSubmit={handleSubmit}
              submitLabel={isCreateMode ? "Create package" : "Save changes"}
              isSaving={isSaving}
              submitError={saveError}
              externalFieldErrors={fieldErrors}
            />
          ) : null}
        </section>
      </div>
    </main>
  );
}
