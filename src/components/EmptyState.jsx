export default function EmptyState({ icon, title, description, action, onAction }) {
  return (
    <div className="empty-state" id="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-desc">{description}</p>
      {action && (
        <button className="btn btn-primary" onClick={onAction}>
          {action}
        </button>
      )}
    </div>
  )
}
