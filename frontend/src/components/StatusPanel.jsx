export function StatusPanel({
  title,
  message,
  tone = "loading",
  action,
}) {
  return (
    <div className={`status-panel status-panel--${tone} fade-up`} role="status">
      <h3>{title}</h3>
      <p>{message}</p>
      {action ? <div className="hero__actions">{action}</div> : null}
    </div>
  );
}
