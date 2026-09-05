// Share section title, eyebrow, and description markup across pages.

export function SectionHeading({ eyebrow, title, description }) {
  return (
    <div className="section-heading fade-up">
      {eyebrow ? <span className="eyebrow-dark">{eyebrow}</span> : null}
      <h2>{title}</h2>
      {description ? <p>{description}</p> : null}
    </div>
  );
}
