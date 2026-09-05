// Offer navigation back to public pages when no route matches.

import { Link } from "react-router-dom";

import { PublicPageHero } from "../components/PublicPageHero";

export function NotFoundPage() {
  return (
    <main className="page">
      <PublicPageHero
        eyebrow="404"
        title="That page has moved off the route map."
        description="Head back to the homepage or browse the published LetsGoSouth packages."
        actions={(
          <div className="hero__actions">
            <Link className="button" to="/">
              Home
            </Link>
            <Link className="button-secondary button-secondary--light" to="/packages">
              Packages
            </Link>
          </div>
        )}
      />
    </main>
  );
}
