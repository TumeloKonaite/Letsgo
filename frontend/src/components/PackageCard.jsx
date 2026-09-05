// Render a public package summary with pricing and a link to its detail page.

import { Link } from "react-router-dom";

import { formatCurrency } from "../lib/formatters";

export function PackageCard({ packageItem }) {
  const imageStyle = packageItem.hero_image_url
    ? {
        backgroundImage: `linear-gradient(180deg, rgba(16, 23, 34, 0.02), rgba(16, 23, 34, 0.82)), url("${packageItem.hero_image_url}")`,
      }
    : undefined;

  return (
    <article className="package-card fade-up">
      <div className="package-card__image" style={imageStyle} />

      <div className="package-card__body">
        <span className="package-card__price">
          From {formatCurrency(packageItem.price_from, packageItem.currency)}
        </span>

        <span className="package-card__meta">{packageItem.location}</span>
        <h3>{packageItem.title}</h3>
        <p>{packageItem.short_description || "Curated South African travel experience."}</p>

        <div className="package-card__footer">
          <span>{packageItem.duration_days} days</span>
          <Link className="inline-link" to={`/packages/${packageItem.slug}`}>
            View package
          </Link>
        </div>
      </div>
    </article>
  );
}
