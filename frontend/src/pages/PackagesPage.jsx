import { useEffect, useState } from "react";

import { PackageCard } from "../components/PackageCard";
import { StatusPanel } from "../components/StatusPanel";
import { getPackages } from "../lib/api";

export function PackagesPage() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadPackages() {
      try {
        const payload = await getPackages();
        if (isMounted) {
          setPackages(payload);
          setError("");
        }
      } catch (requestError) {
        if (isMounted) {
          setError(requestError.message);
        }
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

  return (
    <main className="page">
      <div className="container">
        <section className="page-hero fade-up">
          <div className="page-hero__panel">
            <span className="eyebrow-dark">Packages</span>
            <h1>Browse published trips</h1>
            <p>
              This page is powered by `GET /api/packages` and shows loading,
              empty, and error states for the public frontend.
            </p>
          </div>
        </section>

        <section className="section">
          {loading ? (
            <StatusPanel
              title="Loading packages"
              message="Collecting published packages from the LetsGoSouth API."
            />
          ) : null}

          {!loading && error ? (
            <StatusPanel
              title="Package list unavailable"
              message={error}
              tone="error"
            />
          ) : null}

          {!loading && !error && packages.length === 0 ? (
            <StatusPanel
              title="Nothing published yet"
              message="There are no public travel packages to display right now."
              tone="empty"
            />
          ) : null}

          {!loading && !error && packages.length > 0 ? (
            <div className="package-grid">
              {packages.map((packageItem) => (
                <PackageCard key={packageItem.slug} packageItem={packageItem} />
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
