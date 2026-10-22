import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Bell, Menu } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { useTheme } from '../context/ThemeContext'

export default function Topbar({ title }) {
  const { toggleSidebar, addToast } = useApp()
  const { isEnlighten } = useTheme()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)
  const searchInputRef = useRef(null)
  const navigate = useNavigate()

  /* ⌘K / Ctrl+K keyboard shortcut */
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        searchInputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    navigate(`/chat?q=${encodeURIComponent(searchQuery.trim())}`)
    setSearchQuery('')
  }

  const handleNotificationClick = () => {
    addToast('3 documents recently updated with new semantic chunks', 'info')
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="topbar-hamburger" onClick={toggleSidebar} aria-label="Toggle navigation menu">
          <Menu />
        </button>
        {title && <h1 className="topbar-title">{title}</h1>}

        {/* Search with ⌘K badge */}
        <form onSubmit={handleSearchSubmit} className="topbar-search" style={{ position: 'relative' }}>
          <Search style={{ color: searchFocused ? 'var(--text-accent)' : 'var(--text-tertiary)', transition: 'color 200ms' }} />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search across your knowledge base..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            style={{ paddingRight: '52px' }}
          />
          {/* ⌘K shortcut badge */}
          {!searchFocused && !searchQuery && (
            <kbd
              style={{
                position: 'absolute',
                right: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
                padding: '2px 6px',
                borderRadius: '5px',
                fontSize: '0.68rem',
                fontWeight: 600,
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-tertiary)',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                lineHeight: 1.4,
                pointerEvents: 'none',
                userSelect: 'none',
                letterSpacing: '-0.01em',
              }}
            >
              ⌘K
            </kbd>
          )}
        </form>
      </div>

      <div className="topbar-right">
        <button
          className="topbar-icon-btn"
          id="notification-btn"
          aria-label="Notifications"
          onClick={handleNotificationClick}
        >
          <Bell />
          <span className="topbar-notification-dot" />
        </button>
        <div
          className="topbar-avatar"
          id="profile-avatar"
          onClick={() => navigate('/settings')}
          title="Account Settings"
          style={{
            background: isEnlighten
              ? 'linear-gradient(135deg, #7c3aed, #4f46e5)'
              : 'linear-gradient(135deg, #5b21b6, #3730a3)',
          }}
        >
          EK
        </div>
      </div>
    </header>
  )
}

