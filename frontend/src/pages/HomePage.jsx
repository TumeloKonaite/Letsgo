import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

import {
  aboutHighlights,
  contactDetails,
  serviceCategories,
} from "../data/about";
import { getPackages } from "../lib/api";
import { PackageCard } from "../components/PackageCard";
import { SectionHeading } from "../components/SectionHeading";
import { StatusPanel } from "../components/StatusPanel";

export function HomePage() {
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

  const featuredPackages = packages.filter((packageItem) => packageItem.is_featured);
  const packagesToShow = (featuredPackages.length ? featuredPackages : packages).slice(0, 3);

  return (
    <>
      <main className="page">
        <div className="container">
          <section className="hero fade-up">
            <div className="hero__grid">
              <div>
                <span className="eyebrow">South African travel, thoughtfully planned</span>
                <h1>Dream bigger. Discover more. Explore South Africa.</h1>
                <p>
                  LetsGoSouth brings together curated packages, trusted local
                  guidance, and meaningful travel experiences for visitors who
                  want more than a generic itinerary.
                </p>

                <div className="hero__actions">
                  <Link className="button" to="/packages">
                    Browse packages
                  </Link>
                  <a className="button-secondary" href="#about">
                    About LetsGoSouth
                  </a>
                </div>
              </div>

              <div className="hero__stats">
                <div className="stat-card">
                  <span className="stat-card__label">Focus</span>
                  <strong>Guided tours, safari escapes, cultural experiences</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-card__label">Approach</span>
                  <strong>Local knowledge, reliable partners, clear booking flow</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-card__label">Ideal for</span>
                  <strong>Local and international travelers exploring South Africa</strong>
                </div>
              </div>
            </div>
          </section>

          <section className="section">
            <SectionHeading
              eyebrow="Packages"
              title="Published travel packages from the backend"
              description="The homepage highlights live package data from the API so visitors can immediately start exploring active trips."
            />

            {loading ? (
              <StatusPanel
                title="Loading packages"
                message="Fetching the latest published LetsGoSouth itineraries."
              />
            ) : null}

            {!loading && error ? (
              <StatusPanel
                title="Packages could not be loaded"
                message={error}
                tone="error"
                action={
                  <Link className="button" to="/packages">
                    Open packages page
                  </Link>
                }
              />
            ) : null}

            {!loading && !error && packagesToShow.length === 0 ? (
              <StatusPanel
                title="No published packages yet"
                message="Packages will appear here once they are published from the backend."
                tone="empty"
              />
            ) : null}

            {!loading && !error && packagesToShow.length > 0 ? (
              <div className="package-grid">
                {packagesToShow.map((packageItem) => (
                  <PackageCard key={packageItem.slug} packageItem={packageItem} />
                ))}
              </div>
            ) : null}
          </section>

          <section className="section" id="about">
            <div className="about-grid">
              <div className="about-grid__intro fade-up">
                <span className="eyebrow-dark">About us</span>
                <h2>Dream. Discover. Explore.</h2>
                <p>
                  We are a South African-driven tourism brand with a passion for
                  travel, culture, and meaningful experiences. Our platform is
                  designed for both local and international travelers looking for
                  reliable information, trusted services, and genuine
                  connections to destinations.
                </p>
                <p>We believe travel should be simple, safe, and rewarding.</p>

                <div className="about-grid__actions">
                  <Link className="button" to="/packages">
                    Check availability
                  </Link>
                  <a className="button-secondary" href="#contact">
                    Get in touch
                  </a>
                </div>
              </div>

              <div className="about-grid__content">
                {aboutHighlights.map((highlight) => (
                  <article className="about-card fade-up" key={highlight.title}>
                    <h3>{highlight.title}</h3>
                    {highlight.body ? <p>{highlight.body}</p> : null}
                    {highlight.items ? (
                      <ul>
                        {highlight.items.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : null}
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section className="section">
            <SectionHeading
              eyebrow="Experiences"
              title="Plan your South African adventure with the right mix of guidance and freedom"
              description="The old LetsGoSouth about and landing pages focused on safari travel, local partnerships, and destination support. Those themes now live directly in the new public frontend."
            />

            <div className="service-grid">
              {serviceCategories.map((category) => (
                <article className="service-card fade-up" key={category.title}>
                  <span className="service-card__tag">{category.tag}</span>
                  <h3>{category.title}</h3>
                  <p>{category.body}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="section">
            <div className="cta-banner fade-up">
              <span className="eyebrow">Ready to go</span>
              <h2>Ready to adventure and enjoy the best of South Africa?</h2>
              <p>
                Browse available packages, compare itineraries, and contact the
                LetsGoSouth team when you are ready to lock in the right trip.
              </p>
              <div className="cta-banner__actions">
                <Link className="button" to="/packages">
                  Book a tour
                </Link>
                <a className="button-secondary" href={`mailto:${contactDetails.email}`}>
                  Contact us
                </a>
              </div>
            </div>
          </section>
        </div>
      </main>

      <footer className="footer" id="contact">
        <div className="container footer-grid">
          <div className="fade-up">
            <h3>LET'S GO SOUTH AFRICA</h3>
            <p className="footer-copy">
              We are your trusted travel and tourism platform for exploring
              South Africa. From iconic landmarks and wildlife safaris to
              vibrant cities and hidden gems, we help travelers discover the
              best experiences this country has to offer.
            </p>
          </div>

          <div className="fade-up">
            <h4>Useful links</h4>
            <div className="footer-links">
              <Link to="/">Home</Link>
              <a href="/#about">About us</a>
              <Link to="/packages">Packages</Link>
              <a href={`mailto:${contactDetails.email}`}>Contact us</a>
            </div>
          </div>

          <div className="fade-up">
            <h4>Find us</h4>
            <div className="footer-links">
              <span>{contactDetails.address}</span>
              <a href={`tel:${contactDetails.phone.replace(/\s+/g, "")}`}>
                {contactDetails.phone}
              </a>
              <a href={`mailto:${contactDetails.email}`}>{contactDetails.email}</a>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
