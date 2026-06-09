import { Link } from "react-router-dom";

import { PublicPageHero } from "../components/PublicPageHero";
import { SectionHeading } from "../components/SectionHeading";
import { aboutHighlights } from "../data/about";

const trustReasons = [
  "Local Knowledge",
  "Trusted Partners",
  "Practical Travel Support",
  "Curated Experiences",
  "Flexible Itineraries",
  "Responsive Communication",
];

const planningSteps = [
  "Browse packages and discover destinations that match your travel style.",
  "Send an enquiry so we can guide you toward the right experience.",
  "Refine the details with practical support, timing, and local insight.",
  "Travel with confidence knowing the journey has been clearly planned.",
];

export function AboutPage() {
  return (
    <main className="page">
      <PublicPageHero
        eyebrow="About Us"
        title="Travel support shaped by South African experience."
        description="LetsGoSouth is built around practical planning, trusted local knowledge, and the kind of travel experiences people actually remember when they come to South Africa."
      />

      <div className="container">
        <section className="section">
          <SectionHeading
            eyebrow="Who We Are"
            title="Helping travelers experience South Africa with confidence."
            description="We help local and international visitors move from curiosity to a clear trip plan with destination guidance, curated packages, and responsive local support."
          />

          <div className="about-grid">
            <div className="about-grid__intro fade-up">
              <span className="eyebrow-dark">Our Story</span>
              <h2>Warm hospitality. Clear planning. Memorable experiences.</h2>
              <p>
                Our goal is to make South Africa feel accessible, exciting, and
                well-organized for every traveler, whether they are chasing a
                first safari, a cultural city experience, or a multi-stop
                holiday.
              </p>
              <p>
                We keep the public experience simple: browse the routes, compare
                packages, and send an enquiry when you are ready to move.
              </p>
              <div className="about-grid__actions">
                <Link className="button" to="/packages">
                  Browse Packages
                </Link>
                <Link className="button-secondary" to="/contact">
                  Contact Us
                </Link>
              </div>
            </div>

            <div className="about-grid__content">
              {aboutHighlights.map((highlight) => (
                <article className="about-card fade-up" key={highlight.title}>
                  {highlight.accent ? (
                    <span className="about-card__accent">{highlight.accent}</span>
                  ) : null}
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
          <div className="about-story-grid">
            <div className="about-story-panel fade-up">
              <span className="eyebrow-dark">Why Travel With LetsGoSouth</span>
              <h2>Trusted guidance, practical support, and a clearer path from enquiry to departure.</h2>
              <p>
                The About page is where we explain how we work, why travelers
                trust us, and what kind of planning experience you can expect
                before you even choose a package.
              </p>

              <div className="about-story-panel__list" role="list" aria-label="Trust reasons">
                {trustReasons.map((reason) => (
                  <span className="about-story-panel__item" key={reason} role="listitem">
                    {reason}
                  </span>
                ))}
              </div>
            </div>

            <div className="about-steps">
              {planningSteps.map((step, index) => (
                <article className="about-step-card fade-up" key={step}>
                  <span className="about-step-card__number">0{index + 1}</span>
                  <p>{step}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
