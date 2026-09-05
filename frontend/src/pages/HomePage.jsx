// Combine the rotating hero, service categories, and fetched package highlights.

import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

import { serviceCategories } from "../data/about";
import { getPackages } from "../lib/api";
import { PackageCard } from "../components/PackageCard";
import { SectionHeading } from "../components/SectionHeading";
import { ServiceCategoryCard } from "../components/ServiceCategoryCard";
import { StatusPanel } from "../components/StatusPanel";

const heroSlides = [
  {
    image: "/images/hero/serengeti.jpg",
    eyebrow: "Safari lodges and game drives",
  },
  {
    image: "/images/hero/giraffe.jpg",
    eyebrow: "Scenic routes and ocean escapes",
  },
  {
    image: "/images/hero/union-buildings.jpg",
    eyebrow: "Culture, heritage, and local discovery",
  },
];

const heroHighlights = [
  "Curated tours built for real travelers",
  "Local support from arrival to departure",
  "Safari, culture, scenery, and easy planning",
];

const heroFacts = [
  {
    label: "Experiences",
    value: "Safari, culture, coast, and heritage",
  },
  {
    label: "Support",
    value: "Packages, transfers, and destination guidance",
  },
  {
    label: "Next Step",
    value: "Browse packages or send an enquiry",
  },
];

const trustIndicators = [
  "Guided Tours",
  "Safari Adventures",
  "Airport Transfers",
  "Local Travel Support",
];

export function HomePage() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [currentSlide, setCurrentSlide] = useState(0);

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

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setCurrentSlide((currentIndex) => (currentIndex + 1) % heroSlides.length);
    }, 5000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  const featuredPackages = packages.filter((packageItem) => packageItem.is_featured);
  const packagesToShow = (featuredPackages.length ? featuredPackages : packages).slice(0, 3);

  return (
    <main className="page page--home">
      <section className="hero hero--immersive">
        <div className="hero__media" aria-hidden="true">
          {heroSlides.map((slide, index) => (
            <div
              key={slide.image}
              className={`hero__slide${index === currentSlide ? " is-active" : ""}`}
              style={{ backgroundImage: `url('${slide.image}')` }}
            />
          ))}
        </div>
        <div className="hero__overlay" />

        <div className="container hero__content">
          <div className="hero__copy fade-up">
            <span className="eyebrow">{heroSlides[currentSlide].eyebrow}</span>
            <h1>
              Dream.
              <br />
              Discover.
              <br />
              Explore.
            </h1>
            <p>
              Plan your South African adventure with a warmer, simpler travel
              experience built around visual inspiration, curated packages, and
              practical local support.
            </p>

            <div className="hero__actions">
              <Link className="button" to="/packages">
                Browse Packages
              </Link>
              <Link className="button-secondary button-secondary--light" to="/packages">
                Check Availability
              </Link>
            </div>
          </div>

          <aside className="hero__spotlight fade-up">
            <span className="hero__spotlight-label">Why travelers choose LetsGoSouth</span>
            <ul className="hero__list">
              {heroHighlights.map((highlight) => (
                <li key={highlight}>{highlight}</li>
              ))}
            </ul>
            <Link className="hero__spotlight-link" to="/contact">
              Need help planning? Send an enquiry.
            </Link>
          </aside>
        </div>

        <div className="container hero__bottom fade-up">
          <div className="hero__dots" aria-label="Hero images">
            {heroSlides.map((slide, index) => (
              <button
                key={slide.image}
                className={`hero__dot${index === currentSlide ? " is-active" : ""}`}
                type="button"
                aria-label={`Show slide ${index + 1}`}
                aria-pressed={index === currentSlide ? "true" : "false"}
                onClick={() => setCurrentSlide(index)}
              />
            ))}
          </div>
        </div>
      </section>

      <div className="container">
        <section className="section home-assurance">
          <div className="home-assurance__intro fade-up">
            <span className="eyebrow-dark">Why Travel With Us</span>
            <h2>Trusted South African travel experiences, planned with local support.</h2>
            <p>
              A calmer way to explore safari, scenery, transfers, and destination
              guidance before you start comparing packages.
            </p>
            <div className="home-assurance__list" role="list" aria-label="Travel support">
              {trustIndicators.map((item) => (
                <span className="home-assurance__item" key={item} role="listitem">
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="home-assurance__facts">
            {heroFacts.map((fact) => (
              <article className="home-assurance__card fade-up" key={fact.label}>
                <span>{fact.label}</span>
                <strong>{fact.value}</strong>
              </article>
            ))}
          </div>
        </section>

        <section className="section">
          <SectionHeading
            eyebrow="Featured Packages"
            title="Start with live package listings already available on the site"
            description="Browse current trips straight from the backend and compare published options before you enquire."
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
              action={(
                <Link className="button" to="/packages">
                  Open packages page
                </Link>
              )}
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

        <section className="section">
          <SectionHeading
            eyebrow="Services"
            title="Six tourism-focused categories travelers can understand at a glance"
            description="The homepage now emphasizes practical visitor needs such as safari planning, transfers, culture, heritage, and destination support."
          />

          <div className="service-grid">
            {serviceCategories.map((category) => (
              <ServiceCategoryCard key={category.title} category={category} />
            ))}
          </div>
        </section>

        <section className="section section--tight">
          <div className="cta-banner fade-up">
            <span className="eyebrow">Plan Your Trip</span>
            <h2>Start Planning Your Adventure</h2>
            <p>
              Browse existing packages, check availability through the current
              package flow, or contact the team for guidance on your next
              itinerary.
            </p>
            <div className="cta-banner__actions">
              <Link className="button" to="/packages">
                Book a Tour
              </Link>
              <Link className="button-secondary button-secondary--light" to="/contact">
                Contact Us
              </Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
