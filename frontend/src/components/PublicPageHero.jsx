// Provide a consistent hero layout with optional actions for public pages.

import { useEffect, useState } from "react";

const defaultSlides = [
  "/images/hero/serengeti.jpg",
  "/images/hero/giraffe.jpg",
  "/images/hero/union-buildings.jpg",
];

export function PublicPageHero({
  eyebrow,
  title,
  description,
  actions = null,
  slides = defaultSlides,
  variant = "",
}) {
  const [currentSlide, setCurrentSlide] = useState(0);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setCurrentSlide((currentIndex) => (currentIndex + 1) % slides.length);
    }, 5000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [slides]);

  useEffect(() => {
    setCurrentSlide(0);
  }, [slides]);

  return (
    <section className={`page-hero page-hero--image${variant ? ` ${variant}` : ""}`}>
      <div className="container">
        <div className="page-hero__panel page-hero__panel--image fade-up">
          <div className="page-hero__media" aria-hidden="true">
            {slides.map((slide, index) => (
              <div
                key={slide}
                className={`page-hero__slide${index === currentSlide ? " is-active" : ""}`}
                style={{ backgroundImage: `url('${slide}')` }}
              />
            ))}
          </div>

          <div className="page-hero__content">
            <span className="eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            {description ? <p>{description}</p> : null}
            {actions}
          </div>

          <div className="page-hero__dots" aria-label={`${eyebrow} images`}>
            {slides.map((slide, index) => (
              <button
                key={slide}
                className={`hero__dot${index === currentSlide ? " is-active" : ""}`}
                type="button"
                aria-label={`Show slide ${index + 1}`}
                aria-pressed={index === currentSlide ? "true" : "false"}
                onClick={() => setCurrentSlide(index)}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
