import { NavLink } from 'react-router-dom'
import {
  Home, BookOpen, MessageSquare, Compass, GitBranch, BarChart3,
  Settings, BookOpenCheck, X
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import { useTheme } from '../context/ThemeContext'
import ThemeToggle from './ThemeToggle'
import BeyondVistaarCapsule from './BeyondVistaarCapsule'

const navItems = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/knowledge', icon: BookOpen, label: 'My Knowledge' },
  { path: '/chat', icon: MessageSquare, label: 'Chat' },
  { path: '/explore', icon: Compass, label: 'Explore' },
  { path: '/knowledge-graph', icon: GitBranch, label: 'Knowledge Graph' },
  { path: '/insights', icon: BarChart3, label: 'Insights' },
  { path: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const { sidebarOpen, closeSidebar } = useApp()
  const { isEnlighten } = useTheme()

  return (
    <>
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`}
        onClick={closeSidebar}
        aria-hidden="true"
      />
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        {/* Brand Header */}
        <div className="sidebar-logo" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="sidebar-logo-icon">
              <BookOpenCheck />
            </div>
            <div>
              <div style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.18rem',
                fontWeight: 800,
                letterSpacing: '-0.02em',
                color: isEnlighten ? '#6d28d9' : '#c4b5fd',
              }}>
                VISTAAR
              </div>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-tertiary)', letterSpacing: '0.06em', fontWeight: 600 }}>
                KNOWLEDGE WORKSPACE
              </div>
            </div>
          </div>

          {/* Close button — visible on mobile */}
          {sidebarOpen && (
            <button
              onClick={closeSidebar}
              className="btn btn-ghost btn-sm"
              style={{ padding: '6px', color: 'var(--text-tertiary)' }}
              aria-label="Close navigation"
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Navigation Links */}
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              onClick={closeSidebar}
            >
              <item.icon />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer: BeyondVistaar Capsule + ThemeToggle + User */}
        <div className="sidebar-footer">
          {/* Signature Beyond VISTAAR Capsule */}
          <BeyondVistaarCapsule />

          {/* Beyond VISTAAR theme segmented control */}
          <div style={{ padding: '0 14px 10px' }}>
            <ThemeToggle showLabel={true} />
          </div>

          {/* User profile */}
          <div className="sidebar-user" style={{ cursor: 'pointer' }}>
            <div
              className="sidebar-user-avatar"
              style={{
                background: isEnlighten
                  ? 'linear-gradient(135deg, #7c3aed, #4f46e5)'
                  : 'linear-gradient(135deg, #5b21b6, #3730a3)',
              }}
            >
              EK
            </div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-name">Ekansh</div>
              <div className="sidebar-user-email">ekansh@vistaar.ai</div>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}

