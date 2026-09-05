// Load a published package by slug and present its gallery and trip details.

import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";

import { SectionHeading } from "../components/SectionHeading";
import { StatusPanel } from "../components/StatusPanel";
import { getPackageBySlug } from "../lib/api";
import {
  formatAvailabilityStatus,
  formatCurrency,
  formatDateRange,
} from "../lib/formatters";

const fallbackSlides = [
  "/images/hero/serengeti.jpg",
  "/images/hero/giraffe.jpg",
  "/images/hero/union-buildings.jpg",
];

export function PackageDetailPage() {
  const { slug } = useParams();
  const [packageDetail, setPackageDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [currentHeroSlide, setCurrentHeroSlide] = useState(0);

  useEffect(() => {
    // Ignore a late response after unmounting or switching to a different slug.
    let isMounted = true;

    async function loadPackage() {
      try {
        const payload = await getPackageBySlug(slug);
        if (isMounted) {
          setPackageDetail(payload);
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

    loadPackage();

    return () => {
      isMounted = false;
    };
  }, [slug]);

  const packageSlides = packageDetail
    ? [packageDetail.hero_image_url, ...packageDetail.images.map((image) => image.image_url)].filter(Boolean)
    : [];

  const heroSlides = [...new Set(packageSlides)].length > 0
    ? [...new Set(packageSlides)]
    : fallbackSlides;

  useEffect(() => {
    setCurrentHeroSlide(0);
  }, [slug, packageDetail?.hero_image_url, packageDetail?.images]);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setCurrentHeroSlide((currentIndex) => (currentIndex + 1) % heroSlides.length);
    }, 5000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [heroSlides]);

  if (loading) {
    return (
      <main className="page">
        <div className="container">
          <StatusPanel
            title="Loading package details"
            message="Fetching the itinerary, gallery, and availability for this trip."
          />
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page">
        <div className="container">
          <StatusPanel
            title="Package details unavailable"
            message={error}
            tone="error"
            action={
              <Link className="button" to="/packages">
                Back to packages
              </Link>
            }
          />
        </div>
      </main>
    );
  }

  if (!packageDetail) {
    return null;
  }

  const inclusionItems = packageDetail.inclusions ?? [];
  const includedItems = inclusionItems.filter(
    (item) => item.type === "included"
  );
  const excludedItems = inclusionItems.filter(
    (item) => item.type === "excluded"
  );

  return (
    <main className="page">
      <div className="container">
        <section className="package-detail__header fade-up">
          <div className="package-detail__summary">
            <span className="eyebrow-dark">Package details</span>
            <h1>{packageDetail.title}</h1>
            <div className="package-highlight">
              {packageDetail.location} - {packageDetail.duration_days} days
            </div>
            <p>{packageDetail.short_description || packageDetail.full_description}</p>
            <p>
              From{" "}
              <strong>
                {formatCurrency(packageDetail.price_from, packageDetail.currency)}
              </strong>
            </p>
            <div className="hero__actions">
              <Link className="button" to="/packages">
                View all packages
              </Link>
            </div>
          </div>

          <div className="package-detail__hero">
            <div className="package-detail__media" aria-hidden="true">
              {heroSlides.map((slide, index) => (
                <div
                  key={slide}
                  className={`package-detail__slide${index === currentHeroSlide ? " is-active" : ""}`}
                  style={{
                    backgroundImage: `linear-gradient(180deg, rgba(16, 20, 17, 0.16), rgba(16, 20, 17, 0.68)), url("${slide}")`,
                  }}
                />
              ))}
            </div>

            <div className="package-detail__hero-dots" aria-label="Package images">
              {heroSlides.map((slide, index) => (
                <button
                  key={slide}
                  className={`hero__dot${index === currentHeroSlide ? " is-active" : ""}`}
                  type="button"
                  aria-label={`Show package image ${index + 1}`}
                  aria-pressed={index === currentHeroSlide ? "true" : "false"}
                  onClick={() => setCurrentHeroSlide(index)}
                />
              ))}
            </div>
          </div>
        </section>

        <section className="section">
          <div className="detail-grid">
            <article className="detail-panel fade-up">
              <h3>Overview</h3>
              {packageDetail.full_description
                .split(/\n+/)
                .filter(Boolean)
                .map((paragraph, index) => (
                  <p key={`${index}-${paragraph}`}>{paragraph}</p>
                ))}
            </article>

            <article className="detail-panel fade-up">
              <h3>Trip snapshot</h3>
              <ul>
                <li>Destination: {packageDetail.location}</li>
                <li>Duration: {packageDetail.duration_days} days</li>
                <li>Currency: {packageDetail.currency}</li>
                <li>
                  Featured package: {packageDetail.is_featured ? "Yes" : "No"}
                </li>
              </ul>
            </article>
          </div>
        </section>

        <section className="section">
          <SectionHeading
            eyebrow="Itinerary"
            title="Tour breakdown"
            description="Loaded from `GET /api/packages/{slug}`."
          />

          <div className="package-timeline">
            {packageDetail.itinerary.length > 0 ? (
              packageDetail.itinerary.map((item, index) => (
                <article className="package-timeline__item detail-panel fade-up" key={item.id}>
                  <div className="package-timeline__marker" aria-hidden="true">
                    {index + 1}
                  </div>
                  <div className="package-timeline__content">
                    <span className="eyebrow-dark">Stop {index + 1}</span>
                    <h3>{item.title}</h3>
                    <p>{item.description}</p>
                    {item.duration ? (
                      <div className="package-timeline__duration">{item.duration}</div>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <StatusPanel
                title="No itinerary published"
                message="This package does not have itinerary entries yet."
                tone="empty"
              />
            )}
          </div>
        </section>

        <section className="section">
          <SectionHeading
            eyebrow="Pricing"
            title="Cost Includes And Excludes"
            description="Review what is covered in the package price and what guests should plan for separately."
          />

          {includedItems.length > 0 || excludedItems.length > 0 ? (
            <div className="package-inclusions-grid">
              <article className="detail-panel fade-up">
                <h3>Cost Includes</h3>
                {includedItems.length > 0 ? (
                  <ul className="package-checklist package-checklist--included">
                    {includedItems.map((item) => (
                      <li key={item.id}>{item.name}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No included items have been published yet.</p>
                )}
              </article>

              <article className="detail-panel fade-up">
                <h3>Cost Excludes</h3>
                {excludedItems.length > 0 ? (
                  <ul className="package-checklist package-checklist--excluded">
                    {excludedItems.map((item) => (
                      <li key={item.id}>{item.name}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No excluded items have been published yet.</p>
                )}
              </article>
            </div>
          ) : (
            <StatusPanel
              title="No pricing breakdown published"
              message="This package does not have cost include or exclude items yet."
              tone="empty"
            />
          )}
        </section>

        <section className="section">
          <SectionHeading
            eyebrow="Availability"
            title="Upcoming dates"
            description="Visitors can review current date windows and available spots before enquiring."
          />

          {packageDetail.availability.length > 0 ? (
            <div className="availability-grid">
              {packageDetail.availability.map((availability) => {
                const status = formatAvailabilityStatus(
                  availability.status,
                  availability.spots_available
                );

                return (
                  <article className="availability-card fade-up" key={availability.id}>
                    <span
                      className={`availability-badge availability-badge--${status.tone}`}
                    >
                      {status.label}
                    </span>
                    <h3>{formatDateRange(availability.start_date, availability.end_date)}</h3>
                    <p>
                      {availability.spots_available} spots left out of{" "}
                      {availability.capacity}
                    </p>
                    <div className="availability-card__meta">
                      <span>Starts {availability.start_date}</span>
                      <span>Ends {availability.end_date}</span>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <StatusPanel
              title="No dates published"
              message="Availability windows have not been added for this package yet."
              tone="empty"
            />
          )}
        </section>

        <section className="section">
          <SectionHeading
            eyebrow="Gallery"
            title="Package images"
            description="Cover and supporting images from the backend are surfaced here when available."
          />

          {packageDetail.images.length > 0 ? (
            <div className="gallery-grid">
              {packageDetail.images.map((image) => (
                <div
                  key={image.id}
                  className="gallery-tile fade-up"
                  style={{
                    backgroundImage: `linear-gradient(180deg, rgba(16, 23, 34, 0.1), rgba(16, 23, 34, 0.48)), url("${image.image_url}")`,
                  }}
                  aria-label={image.alt_text || packageDetail.title}
                  role="img"
                />
              ))}
            </div>
          ) : (
            <StatusPanel
              title="No gallery images"
              message="This package currently has no published gallery items."
              tone="empty"
            />
          )}
        </section>
      </div>
    </main>
  );
}
