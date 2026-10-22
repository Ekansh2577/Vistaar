import React from 'react'

export default function HeroBookVisual() {
  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: '560px',
        height: '460px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      className="hero-book-visual-container"
    >
      {/* Background Soft Misty Mountain & Environment Layer */}
      <svg
        viewBox="0 0 560 460"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          overflow: 'visible',
        }}
      >
        <defs>
          {/* Sky / Ambient Glow Gradient */}
          <linearGradient id="skyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f3f4fd" stopOpacity="0.8" />
            <stop offset="60%" stopColor="#ede9fe" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#fdf4ff" stopOpacity="0.2" />
          </linearGradient>

          {/* Mountains Gradient 1 */}
          <linearGradient id="mountainGrad1" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#c7d2fe" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#e0e7ff" stopOpacity="0.1" />
          </linearGradient>

          {/* Mountains Gradient 2 (closer) */}
          <linearGradient id="mountainGrad2" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#a5b4fc" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#eef2ff" stopOpacity="0.2" />
          </linearGradient>

          {/* Foothills Gradient */}
          <linearGradient id="foothillsGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#818cf8" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#f8fafc" stopOpacity="0.05" />
          </linearGradient>

          {/* Connection Arc Gradients */}
          <linearGradient id="arcGradPurple" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.3" />
          </linearGradient>
          <linearGradient id="arcGradBlue" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#a855f7" stopOpacity="0.3" />
          </linearGradient>

          {/* Book Page Gradients */}
          <linearGradient id="leftPageGrad" x1="0%" y1="50%" x2="100%" y2="50%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="85%" stopColor="#f8fafc" />
            <stop offset="100%" stopColor="#e2e8f0" />
          </linearGradient>
          <linearGradient id="rightPageGrad" x1="0%" y1="50%" x2="100%" y2="50%">
            <stop offset="0%" stopColor="#e2e8f0" />
            <stop offset="15%" stopColor="#f8fafc" />
            <stop offset="100%" stopColor="#ffffff" />
          </linearGradient>

          {/* Book Edge Thickness */}
          <linearGradient id="bookEdgeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#cbd5e1" />
            <stop offset="100%" stopColor="#94a3b8" />
          </linearGradient>

          {/* Glow filter */}
          <filter id="glowLight" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Ambient Sky Backdrop */}
        <circle cx="280" cy="220" r="220" fill="url(#skyGradient)" />

        {/* Far Distant Mountain Ridges */}
        <path
          d="M 20 280 Q 90 200 160 220 T 300 190 T 420 210 T 540 260 L 540 380 L 20 380 Z"
          fill="url(#mountainGrad1)"
        />

        {/* Closer Mountain Peaks */}
        <path
          d="M 60 290 Q 140 170 210 200 T 350 170 T 480 230 L 540 380 L 60 380 Z"
          fill="url(#mountainGrad2)"
        />

        {/* Foothills & Forest Ridge */}
        <path
          d="M 80 320 Q 170 240 260 270 T 440 260 T 540 310 L 540 390 L 80 390 Z"
          fill="url(#foothillsGrad)"
        />

        {/* Pine Tree Silhouettes on Ridge */}
        <g fill="#6366f1" opacity="0.3">
          <polygon points="140,285 137,295 143,295" />
          <polygon points="148,280 145,292 151,292" />
          <polygon points="156,283 153,294 159,294" />
          <polygon points="210,270 207,282 213,282" />
          <polygon points="218,266 215,280 221,280" />
          <polygon points="226,272 223,283 229,283" />
          <polygon points="400,280 397,293 403,293" />
          <polygon points="410,275 407,290 413,290" />
        </g>

        {/* Dotted Curved Connecting Arcs */}
        {/* Arc to 'Explore' */}
        <path
          d="M 280 340 C 240 270, 160 230, 135 155"
          fill="none"
          stroke="url(#arcGradPurple)"
          strokeWidth="1.8"
          strokeDasharray="4 4"
        />
        {/* Arc to 'Understand' */}
        <path
          d="M 310 340 C 340 250, 410 180, 435 110"
          fill="none"
          stroke="url(#arcGradBlue)"
          strokeWidth="1.8"
          strokeDasharray="4 4"
        />
        {/* Arc to 'Discover' */}
        <path
          d="M 320 350 C 370 300, 440 280, 480 210"
          fill="none"
          stroke="url(#arcGradPurple)"
          strokeWidth="1.8"
          strokeDasharray="4 4"
        />
        {/* Cross connection between nodes */}
        <path
          d="M 160 170 C 240 140, 340 130, 400 130"
          fill="none"
          stroke="#a78bfa"
          strokeWidth="1.2"
          strokeDasharray="3 3"
          opacity="0.6"
        />

        {/* Sparkles / Knowledge Particles */}
        <g fill="#8b5cf6" opacity="0.75">
          <circle cx="190" cy="180" r="2.5" />
          <circle cx="270" cy="150" r="3" />
          <circle cx="360" cy="170" r="2.5" />
          <circle cx="430" cy="240" r="3.5" />
          <circle cx="230" cy="260" r="2" />
          <circle cx="330" cy="280" r="2.5" />
        </g>
        {/* 4-point Diamond Sparkles */}
        <path
          d="M 270 140 Q 270 148 278 148 Q 270 148 270 156 Q 270 148 262 148 Q 270 148 270 140 Z"
          fill="#7c3aed"
          opacity="0.8"
        />
        <path
          d="M 440 180 Q 440 186 446 186 Q 440 186 440 192 Q 440 186 434 186 Q 440 186 440 180 Z"
          fill="#3b82f6"
          opacity="0.8"
        />

        {/* ================================================= */}
        {/* THE LARGE OPEN BOOK (Lower Right Foreground)     */}
        {/* ================================================= */}
        <g transform="translate(180, 270)" filter="url(#glowLight)">
          {/* Subtle Ambient Book Glow */}
          <ellipse cx="140" cy="95" rx="150" ry="30" fill="rgba(124, 58, 237, 0.15)" />

          {/* Book Bottom Pages Block / Thickness */}
          {/* Left Block */}
          <path
            d="M 140 102 C 90 98, 40 110, 0 120 L 0 112 C 40 102, 90 90, 140 94 Z"
            fill="url(#bookEdgeGrad)"
          />
          {/* Right Block */}
          <path
            d="M 140 94 C 190 90, 240 102, 280 112 L 280 120 C 240 110, 190 98, 140 102 Z"
            fill="url(#bookEdgeGrad)"
          />

          {/* Curved Left Open Page */}
          <path
            d="M 140 94 C 95 86, 45 98, 5 110 C 25 72, 75 58, 140 76 Z"
            fill="url(#leftPageGrad)"
            stroke="#cbd5e1"
            strokeWidth="0.8"
          />

          {/* Curved Right Open Page */}
          <path
            d="M 140 76 C 205 58, 255 72, 275 110 C 235 98, 185 86, 140 94 Z"
            fill="url(#rightPageGrad)"
            stroke="#cbd5e1"
            strokeWidth="0.8"
          />

          {/* Book Center Binding / Spine shadow */}
          <path
            d="M 140 76 C 139 82, 139 88, 140 94 C 141 88, 141 82, 140 76 Z"
            fill="#94a3b8"
          />

          {/* Subtle Text Lines on Left Page */}
          <g stroke="#94a3b8" strokeWidth="1.2" strokeLinecap="round" opacity="0.45">
            <line x1="45" y1="88" x2="115" y2="80" />
            <line x1="48" y1="94" x2="118" y2="86" />
            <line x1="52" y1="100" x2="120" y2="92" />
          </g>

          {/* Subtle Text Lines on Right Page */}
          <g stroke="#94a3b8" strokeWidth="1.2" strokeLinecap="round" opacity="0.45">
            <line x1="162" y1="80" x2="235" y2="88" />
            <line x1="160" y1="86" x2="232" y2="94" />
            <line x1="158" y1="92" x2="228" y2="100" />
          </g>
        </g>
      </svg>

      {/* ================================================= */}
      {/* FLOATING TRANSLUCENT DOCUMENT CARDS               */}
      {/* ================================================= */}

      {/* Floating Card 1: Center-Left Research Card */}
      <div
        style={{
          position: 'absolute',
          left: '160px',
          top: '90px',
          width: '135px',
          padding: '12px 14px',
          background: 'rgba(255, 255, 255, 0.92)',
          backdropFilter: 'blur(8px)',
          borderRadius: '12px',
          border: '1px solid rgba(221, 214, 254, 0.9)',
          boxShadow: '0 12px 28px rgba(124, 58, 237, 0.12), 0 2px 6px rgba(0, 0, 0, 0.04)',
          transform: 'rotate(-4deg)',
          transition: 'transform 0.3s ease',
          zIndex: 5,
        }}
        className="hero-floating-card-1"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#8b5cf6' }} />
          <div style={{ width: '45px', height: '4px', background: '#ddd6fe', borderRadius: '4px' }} />
        </div>
        <div style={{ width: '100%', height: '3px', background: '#e2e8f0', borderRadius: '3px', marginBottom: '5px' }} />
        <div style={{ width: '85%', height: '3px', background: '#e2e8f0', borderRadius: '3px', marginBottom: '5px' }} />
        <div style={{ width: '65%', height: '3px', background: '#e2e8f0', borderRadius: '3px', marginBottom: '8px' }} />
        {/* Mini Graph indicator */}
        <div style={{ display: 'flex', gap: '4px', alignItems: 'flex-end', height: '18px', paddingTop: '4px' }}>
          <div style={{ width: '6px', height: '8px', background: '#c4b5fd', borderRadius: '2px' }} />
          <div style={{ width: '6px', height: '14px', background: '#8b5cf6', borderRadius: '2px' }} />
          <div style={{ width: '6px', height: '10px', background: '#a78bfa', borderRadius: '2px' }} />
          <div style={{ width: '6px', height: '16px', background: '#6d28d9', borderRadius: '2px' }} />
        </div>
      </div>

      {/* Floating Card 2: Center-Right Knowledge Card */}
      <div
        style={{
          position: 'absolute',
          right: '150px',
          top: '120px',
          width: '115px',
          padding: '10px 12px',
          background: 'rgba(255, 255, 255, 0.94)',
          backdropFilter: 'blur(8px)',
          borderRadius: '10px',
          border: '1px solid rgba(199, 210, 254, 0.9)',
          boxShadow: '0 10px 24px rgba(99, 102, 241, 0.12), 0 2px 6px rgba(0, 0, 0, 0.04)',
          transform: 'rotate(5deg)',
          transition: 'transform 0.3s ease',
          zIndex: 6,
        }}
        className="hero-floating-card-2"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
          <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#3b82f6' }} />
          <div style={{ width: '40px', height: '4px', background: '#bfdbfe', borderRadius: '4px' }} />
        </div>
        <div style={{ width: '90%', height: '3px', background: '#e2e8f0', borderRadius: '3px', marginBottom: '4px' }} />
        <div style={{ width: '70%', height: '3px', background: '#e2e8f0', borderRadius: '3px', marginBottom: '6px' }} />
        <div style={{ display: 'inline-block', padding: '2px 6px', background: '#eff6ff', borderRadius: '4px', fontSize: '0.62rem', color: '#2563eb', fontWeight: 600 }}>
          RAG Verified
        </div>
      </div>

      {/* Floating Card 3: Small Note Card (Upper Center) */}
      <div
        style={{
          position: 'absolute',
          left: '260px',
          top: '50px',
          width: '80px',
          padding: '8px 10px',
          background: 'rgba(255, 255, 255, 0.88)',
          backdropFilter: 'blur(6px)',
          borderRadius: '8px',
          border: '1px solid rgba(221, 214, 254, 0.8)',
          boxShadow: '0 8px 20px rgba(139, 92, 246, 0.1)',
          transform: 'rotate(-2deg)',
          zIndex: 4,
        }}
      >
        <div style={{ width: '100%', height: '3px', background: '#ddd6fe', borderRadius: '3px', marginBottom: '4px' }} />
        <div style={{ width: '75%', height: '3px', background: '#f1f5f9', borderRadius: '3px', marginBottom: '4px' }} />
        <div style={{ width: '60%', height: '3px', background: '#f1f5f9', borderRadius: '3px' }} />
      </div>

      {/* ================================================= */}
      {/* FLOATING ACTION BADGES WITH LABELS                */}
      {/* ================================================= */}

      {/* Badge 1: 'Explore' */}
      <div
        style={{
          position: 'absolute',
          left: '90px',
          top: '125px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 12px',
          background: '#ffffff',
          borderRadius: '999px',
          border: '1px solid #e0e7ff',
          boxShadow: '0 6px 18px rgba(124, 58, 237, 0.1)',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: '#6d28d9',
          zIndex: 8,
        }}
      >
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: '#8b5cf6',
            boxShadow: '0 0 6px #8b5cf6',
          }}
        />
        <span>Explore</span>
      </div>

      {/* Badge 2: 'Understand' */}
      <div
        style={{
          position: 'absolute',
          right: '110px',
          top: '85px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 12px',
          background: '#ffffff',
          borderRadius: '999px',
          border: '1px solid #dbeafe',
          boxShadow: '0 6px 18px rgba(59, 130, 246, 0.1)',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: '#2563eb',
          zIndex: 8,
        }}
      >
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: '#3b82f6',
            boxShadow: '0 0 6px #3b82f6',
          }}
        />
        <span>Understand</span>
      </div>

      {/* Badge 3: 'Discover' */}
      <div
        style={{
          position: 'absolute',
          right: '55px',
          top: '200px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 12px',
          background: '#ffffff',
          borderRadius: '999px',
          border: '1px solid #f3e8ff',
          boxShadow: '0 6px 18px rgba(168, 85, 247, 0.1)',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: '#7c3aed',
          zIndex: 8,
        }}
      >
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: '#a855f7',
            boxShadow: '0 0 6px #a855f7',
          }}
        />
        <span>Discover</span>
      </div>
    </div>
  )
}
