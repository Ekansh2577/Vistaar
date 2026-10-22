export default function LoadingState({ message = 'Analyzing knowledge...' }) {
  return (
    <div className="empty-state" style={{ minHeight: '300px' }}>
      <div className="loading-pulse">
        <div className="loading-pulse-dot" />
        <div className="loading-pulse-dot" />
        <div className="loading-pulse-dot" />
      </div>
      <p style={{ marginTop: '16px', color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>
        {message}
      </p>
    </div>
  )
}
