import React from 'react'
import { Sun, Moon, Sparkles } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

export default function ThemeToggle({ showLabel = true, compact = false }) {
  const { theme, setEnlighten, setExplore, isEnlighten, isExplore } = useTheme()

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '6px',
        width: '100%',
      }}
      className="beyond-vistaar-control"
    >
      {showLabel && (
        <div
          style={{
            fontSize: '0.66rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-tertiary)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <Sparkles size={10} style={{ color: 'var(--text-accent)' }} />
          <span>BEYOND VISTAAR</span>
        </div>
      )}

      {/* Segmented Control Pill */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          background: 'var(--bg-input)',
          border: '1px solid var(--border-primary)',
          borderRadius: '999px',
          padding: '3px',
          width: compact ? 'auto' : '100%',
          boxShadow: 'var(--shadow-xs)',
          position: 'relative',
          transition: 'all 300ms ease',
        }}
      >
        {/* Enlighten Button */}
        <button
          type="button"
          onClick={setEnlighten}
          style={{
            flex: compact ? 'none' : 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: compact ? '6px 10px' : '6px 12px',
            borderRadius: '999px',
            border: 'none',
            fontSize: '0.74rem',
            fontWeight: isEnlighten ? 700 : 500,
            color: isEnlighten ? '#6d28d9' : 'var(--text-tertiary)',
            background: isEnlighten
              ? 'linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%)'
              : 'transparent',
            boxShadow: isEnlighten
              ? '0 2px 8px rgba(124, 58, 237, 0.18), 0 1px 2px rgba(0, 0, 0, 0.05)'
              : 'none',
            cursor: 'pointer',
            transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
            whiteSpace: 'nowrap',
          }}
          title="☀️ Enlighten Mode — Knowledge expanding into clarity and light"
          aria-label="Enlighten Mode"
        >
          <Sun
            size={13}
            style={{
              color: isEnlighten ? '#f59e0b' : 'inherit',
              transition: 'transform 300ms ease',
              transform: isEnlighten ? 'rotate(90deg)' : 'none',
            }}
          />
          <span>ENLIGHTEN</span>
        </button>

        {/* Explore Button */}
        <button
          type="button"
          onClick={setExplore}
          style={{
            flex: compact ? 'none' : 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: compact ? '6px 10px' : '6px 12px',
            borderRadius: '999px',
            border: 'none',
            fontSize: '0.74rem',
            fontWeight: isExplore ? 700 : 500,
            color: isExplore ? '#ffffff' : 'var(--text-tertiary)',
            background: isExplore
              ? 'linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)'
              : 'transparent',
            boxShadow: isExplore
              ? '0 2px 10px rgba(124, 58, 237, 0.35), 0 0 12px rgba(99, 102, 241, 0.25)'
              : 'none',
            cursor: 'pointer',
            transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
            whiteSpace: 'nowrap',
          }}
          title="🌙 Explore Mode — Knowledge expanding into depth, curiosity and discovery"
          aria-label="Explore Mode"
        >
          <Moon
            size={13}
            style={{
              color: isExplore ? '#c4b5fd' : 'inherit',
              transition: 'transform 300ms ease',
              transform: isExplore ? 'rotate(-15deg)' : 'none',
            }}
          />
          <span>EXPLORE</span>
        </button>
      </div>
    </div>
  )
}
