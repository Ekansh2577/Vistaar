import { X, CheckCircle, AlertTriangle, Info, AlertCircle } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function Toast() {
  const { toasts, removeToast } = useApp()

  if (!toasts || toasts.length === 0) return null

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return <CheckCircle size={18} style={{ color: 'var(--success)' }} />
      case 'error':
        return <AlertCircle size={18} style={{ color: 'var(--error)' }} />
      case 'warning':
        return <AlertTriangle size={18} style={{ color: 'var(--warning)' }} />
      default:
        return <Info size={18} style={{ color: 'var(--info)' }} />
    }
  }

  return (
    <div className="toast-container" id="toast-container">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.type || 'info'}`}>
          {getIcon(toast.type)}
          <span className="toast-message">{toast.message}</span>
          <button
            className="toast-close"
            onClick={() => removeToast(toast.id)}
            aria-label="Close notification"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
