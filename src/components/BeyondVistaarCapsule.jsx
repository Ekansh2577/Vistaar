import React from 'react'
import { useTheme } from '../context/ThemeContext'

/* ============================================================
   BeyondVistaarCapsule
   The signature illustrated capsule shown in the sidebar footer.
   Enlighten Mode  →  warm sunrise mountain scene + open book
   Explore  Mode   →  deep cosmic starfield + crescent moon
   Clicking the capsule toggles the theme.
   ============================================================ */
export default function BeyondVistaarCapsule() {
  const { isEnlighten, toggleTheme } = useTheme()

  return (
    <div
      onClick={toggleTheme}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && toggleTheme()}
      title={isEnlighten ? 'Switch to 🌙 EXPLORE Mode' : 'Switch to ☀️ ENLIGHTEN Mode'}
      style={{
        margin: '0 12px 10px',
        borderRadius: '14px',
        overflow: 'hidden',
        cursor: 'pointer',
        position: 'relative',
        height: '100px',
        flexShrink: 0,
        border: isEnlighten
          ? '1px solid rgba(245, 158, 11, 0.25)'
          : '1px solid rgba(124, 58, 237, 0.3)',
        boxShadow: isEnlighten
          ? '0 4px 20px rgba(245,158,11,0.08), 0 2px 8px rgba(124,58,237,0.06)'
          : '0 4px 20px rgba(124,58,237,0.2), 0 0 30px rgba(59,130,246,0.06)',
        transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        userSelect: 'none',
      }}
    >
      {/* Background scene artwork */}
      {isEnlighten ? <EnlightenScene /> : <ExploreScene />}

      {/* Label overlay at bottom */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          padding: '6px 10px 8px',
          background: isEnlighten
            ? 'linear-gradient(to top, rgba(255,251,235,0.95) 60%, transparent)'
            : 'linear-gradient(to top, rgba(6,9,20,0.97) 60%, transparent)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div style={{
            fontSize: '0.59rem',
            fontWeight: 700,
            letterSpacing: '0.11em',
            textTransform: 'uppercase',
            color: isEnlighten ? '#92400e' : '#7c3aed',
            lineHeight: 1,
            marginBottom: '2px',
          }}>
            BEYOND VISTAAR
          </div>
          <div style={{
            fontSize: '0.7rem',
            fontWeight: 600,
            color: isEnlighten ? '#78350f' : '#c4b5fd',
          }}>
            {isEnlighten ? '☀️ Enlighten Mode' : '🌙 Explore Mode'}
          </div>
        </div>

        {/* Mode indicator dot */}
        <div style={{
          width: '22px',
          height: '22px',
          borderRadius: '50%',
          background: isEnlighten
            ? 'linear-gradient(135deg, #f59e0b, #fbbf24)'
            : 'linear-gradient(135deg, #7c3aed, #4f46e5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '11px',
          flexShrink: 0,
          boxShadow: isEnlighten
            ? '0 0 10px rgba(245,158,11,0.55)'
            : '0 0 10px rgba(124,58,237,0.55)',
        }}>
          {isEnlighten ? '☀' : '🌙'}
        </div>
      </div>
    </div>
  )
}

/* ─── Enlighten Scene: warm sunrise sky, indigo mountains, glowing open book ─── */
function EnlightenScene() {
  return (
    <svg
      viewBox="0 0 236 100"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <linearGradient id="eSky" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fef3c7" />
          <stop offset="40%" stopColor="#fde68a" />
          <stop offset="100%" stopColor="#ddd6fe" />
        </linearGradient>
        <linearGradient id="eMtn1" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#c7d2fe" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#ede9fe" stopOpacity="0.05" />
        </linearGradient>
        <linearGradient id="eMtn2" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#a5b4fc" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#c4b5fd" stopOpacity="0.15" />
        </linearGradient>
        <radialGradient id="eSunGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fef08a" stopOpacity="0.92" />
          <stop offset="60%" stopColor="#fde68a" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#fde68a" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Sky */}
      <rect width="236" height="100" fill="url(#eSky)" />

      {/* Sun glow halo */}
      <ellipse cx="118" cy="26" rx="32" ry="32" fill="url(#eSunGlow)" />
      {/* Sun disk */}
      <circle cx="118" cy="26" r="9" fill="#fbbf24" opacity="0.92" />

      {/* Far mountain range */}
      <path d="M 0 78 Q 40 38 82 53 T 165 38 T 236 58 L 236 100 L 0 100 Z" fill="url(#eMtn1)" />
      {/* Near mountain range */}
      <path d="M 0 84 Q 55 54 92 66 T 182 53 T 236 70 L 236 100 L 0 100 Z" fill="url(#eMtn2)" />

      {/* Open book at center-bottom */}
      <g transform="translate(90, 54)">
        {/* Left page */}
        <path d="M 28 0 Q 12 3 0 10 L 0 28 Q 12 22 28 20 Z" fill="white" opacity="0.88" />
        {/* Right page */}
        <path d="M 28 0 Q 44 3 56 10 L 56 28 Q 44 22 28 20 Z" fill="white" opacity="0.76" />
        {/* Spine */}
        <line x1="28" y1="0" x2="28" y2="20" stroke="#c4b5fd" strokeWidth="1.2" />
        {/* Light rays from book */}
        <ellipse cx="28" cy="2" rx="20" ry="6" fill="#fef08a" opacity="0.4" />
      </g>

      {/* Sparkle dots */}
      <circle cx="58" cy="22" r="1.5" fill="#f59e0b" opacity="0.75" />
      <circle cx="76" cy="14" r="1" fill="#fbbf24" opacity="0.6" />
      <circle cx="163" cy="20" r="1.5" fill="#a78bfa" opacity="0.65" />
      <circle cx="184" cy="12" r="1" fill="#8b5cf6" opacity="0.5" />
      <circle cx="148" cy="30" r="1" fill="#f59e0b" opacity="0.4" />
    </svg>
  )
}

/* ─── Explore Scene: deep space, nebula, milky way river, crescent moon ─── */
function ExploreScene() {
  const stars = [
    [10,8,0],[25,15,1],[45,5,0],[68,12,1],[88,7,0],[110,4,1],[135,10,0],[158,6,1],[178,13,0],[200,8,1],[218,4,0],[230,12,1],
    [18,28,0],[38,32,1],[72,26,0],[95,30,1],[130,25,0],[162,32,1],[192,27,0],[215,22,1],
    [8,48,0],[52,55,1],[85,50,0],[145,52,1],[198,48,0],[226,55,1],
    [30,70,0],[75,72,1],[120,68,0],[168,73,1],[210,70,0],
    [15,88,0],[60,85,1],[118,90,0],[175,86,1],[220,88,0],
  ]

  return (
    <svg
      viewBox="0 0 236 100"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <linearGradient id="xSky" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#060912" />
          <stop offset="55%" stopColor="#11082e" />
          <stop offset="100%" stopColor="#05091c" />
        </linearGradient>
        <radialGradient id="xMoonGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#c4b5fd" stopOpacity="0.45" />
          <stop offset="100%" stopColor="#7c3aed" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="xNebula" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#1d4ed8" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#7c3aed" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="xRiver" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#312e81" stopOpacity="0" />
          <stop offset="50%" stopColor="#4338ca" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#312e81" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Deep space background */}
      <rect width="236" height="100" fill="url(#xSky)" />

      {/* Nebula cloud (left) */}
      <ellipse cx="55" cy="42" rx="58" ry="34" fill="url(#xNebula)" />

      {/* Milky way river */}
      <ellipse cx="118" cy="65" rx="112" ry="14" fill="url(#xRiver)" />

      {/* Stars */}
      {stars.map(([x, y, t], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i % 5 === 0 ? 1.3 : i % 3 === 0 ? 0.9 : 0.5}
          fill="white"
          opacity={i % 4 === 0 ? 0.9 : i % 3 === 0 ? 0.6 : 0.38}
        />
      ))}

      {/* Moon glow halo */}
      <ellipse cx="174" cy="25" rx="24" ry="24" fill="url(#xMoonGlow)" />
      {/* Moon disc */}
      <circle cx="174" cy="25" r="14" fill="#e0e7ff" opacity="0.93" />
      {/* Shadow bite for crescent */}
      <circle cx="180" cy="21" r="12" fill="#0d1428" />

      {/* Constellation lines */}
      <line x1="25" y1="15" x2="45" y2="5" stroke="#7c3aed" strokeWidth="0.65" opacity="0.52" />
      <line x1="45" y1="5" x2="68" y2="12" stroke="#7c3aed" strokeWidth="0.65" opacity="0.52" />
      <line x1="68" y1="12" x2="88" y2="7" stroke="#4f46e5" strokeWidth="0.65" opacity="0.45" />
      <line x1="8" y1="48" x2="52" y2="55" stroke="#3b82f6" strokeWidth="0.5" opacity="0.38" />

      {/* Glowing accent stars */}
      <circle cx="45" cy="5" r="2.2" fill="#a78bfa" opacity="0.92" />
      <circle cx="68" cy="12" r="1.6" fill="#60a5fa" opacity="0.85" />
      <circle cx="52" cy="55" r="2" fill="#818cf8" opacity="0.72" />
    </svg>
  )
}