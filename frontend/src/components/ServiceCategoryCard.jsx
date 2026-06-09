export function ServiceCategoryCard({ category }) {
  return (
    <article
      className="service-card fade-up"
      style={{ backgroundImage: `url('${category.image}')` }}
    >
      <div className="service-card__overlay" />
      <div className="service-card__body">
        <span className="service-card__tag">{category.tag}</span>
        <h3>{category.title}</h3>
        <p>{category.body}</p>
      </div>
    </article>
  );
}
