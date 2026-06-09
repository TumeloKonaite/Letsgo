import { useEffect, useState } from "react";

import { PackageCard } from "../components/PackageCard";
import { PublicPageHero } from "../components/PublicPageHero";
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
      <PublicPageHero
        eyebrow="Packages"
        title="Browse published trips"
        description="Explore current LetsGoSouth packages, compare destinations, and move into the existing enquiry flow when you are ready."
      />

      <div className="container">
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
