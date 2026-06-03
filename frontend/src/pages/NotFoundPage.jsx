import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="page">
      <div className="container">
        <section className="page-hero fade-up">
          <div className="page-hero__panel">
            <span className="eyebrow-dark">404</span>
            <h1>That page has moved off the route map.</h1>
            <p>
              Head back to the homepage or browse the published LetsGoSouth
              packages.
            </p>
            <div className="hero__actions">
              <Link className="button" to="/">
                Home
              </Link>
              <Link className="button-secondary" to="/packages">
                Packages
              </Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
