import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Sparkles, FileText, CheckCircle, HelpCircle, Code,
  Eye, Zap, Layers, Share2, Copy
} from 'lucide-react'
import { mockImages } from '../data/mockData'
import { useApp } from '../context/AppContext'

export default function ImageViewerPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { addToast } = useApp()

  const image = mockImages.find((img) => img.id === id) || mockImages[0]
  const [copiedText, setCopiedText] = useState(false)

  const handleAction = (actionTitle, prompt) => {
    navigate(`/chat?q=${encodeURIComponent(prompt || `${actionTitle} for ${image.name}`)}`)
  }

  const handleCopyExtractedText = () => {
    const text = image.detectedText?.join('\n') || ''
    navigator.clipboard?.writeText(text)
    setCopiedText(true)
    addToast('Extracted OCR text copied to clipboard', 'success')
    setTimeout(() => setCopiedText(false), 2000)
  }

  return (
    <div className="image-intelligence-layout">
      {/* LEFT: Image Viewer Canvas */}
      <div className="image-viewer" style={{ position: 'relative' }}>
        <button
          className="btn btn-secondary btn-sm"
          style={{ position: 'absolute', top: '20px', left: '20px', zIndex: 10 }}
          onClick={() => navigate('/knowledge')}
        >
          <ArrowLeft size={14} /> Back to Library
        </button>

        {/* Visual simulated image preview with rich diagram design */}
        <div
          style={{
            maxWidth: '680px',
            width: '100%',
            aspectRatio: '16/10',
            background: 'var(--bg-card)',
            border: '2px solid var(--border-primary)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-xl)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            position: 'relative'
          }}
        >
          {/* Header Bar */}
          <div style={{ padding: '12px 18px', background: 'var(--bg-input)', borderBottom: '1px solid var(--border-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {image.name}
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
              {image.dimensions} • {image.size}
            </span>
          </div>

          {/* Simulated diagram/handwritten note content */}
          <div style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', background: 'radial-gradient(ellipse at center, rgba(139, 92, 246, 0.04) 0%, transparent 80%)' }}>
            <div style={{ width: '90%', border: '1.5px dashed var(--primary-300)', borderRadius: 'var(--radius-md)', padding: '20px', background: 'var(--bg-surface)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary-700)' }}>
                  QUICK_SORT_PARTITION_ALGORITHM
                </span>
                <span style={{ fontSize: '0.7rem', padding: '2px 8px', background: 'var(--success-light)', color: 'var(--success)', borderRadius: '999px', fontWeight: 600 }}>
                  OCR Confidence: 96.4%
                </span>
              </div>

              {/* Array boxes mockup */}
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', margin: '16px 0' }}>
                {['[ 42 ]', '[ 12 ]', '[ 88 ]', '[ 24* ]', '[ 65 ]', '[ 19 ]'].map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '10px 14px',
                      background: idx === 3 ? 'var(--primary-100)' : 'var(--bg-input)',
                      border: idx === 3 ? '2px solid var(--primary-600)' : '1px solid var(--border-primary)',
                      borderRadius: 'var(--radius-sm)',
                      fontWeight: 600,
                      fontSize: '0.85rem',
                      color: idx === 3 ? 'var(--primary-800)' : 'var(--text-primary)',
                    }}
                  >
                    {item}
                  </div>
                ))}
              </div>

              <div style={{ textAlign: 'center', fontSize: '0.78rem', color: 'var(--text-tertiary)', marginTop: '8px' }}>
                *Pivot element selected at index 3. Partitioning sub-arrays recursively: O(n log n).
              </div>
            </div>
          </div>

          {/* Visual Scan line effect badge */}
          <div style={{ position: 'absolute', bottom: '16px', right: '16px', display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-overlay)', color: 'white', padding: '4px 12px', borderRadius: '999px', fontSize: '0.72rem' }}>
            <Zap size={12} style={{ color: '#fbbf24' }} /> Visual Intelligence Active
          </div>
        </div>
      </div>

      {/* RIGHT: VISTAAR Vision Analysis */}
      <aside className="image-analysis-panel">
        <div className="image-analysis-header">
          <div className="image-analysis-title">Understanding This Image</div>
          <div className="image-analysis-subtitle">
            Multimodal OCR & semantic structure extraction
          </div>
        </div>

        <div className="image-analysis-content">
          {/* Summary */}
          <div>
            <div className="image-analysis-section-title">Visual Interpretation</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              {image.summary}
            </p>
          </div>

          {/* Detected Text Tags */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div className="image-analysis-section-title" style={{ margin: 0 }}>
                Detected Text & Formulas
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleCopyExtractedText}
                style={{ padding: '2px 8px', fontSize: '0.72rem' }}
              >
                <Copy size={12} /> {copiedText ? 'Copied' : 'Copy All'}
              </button>
            </div>
            <div className="detected-text-list">
              {image.detectedText?.map((txt, idx) => (
                <span key={idx} className="detected-text-tag">
                  {txt}
                </span>
              ))}
            </div>
          </div>

          {/* Key Points */}
          <div>
            <div className="image-analysis-section-title">Structured Analysis</div>
            <div className="key-points-list">
              {image.keyPoints?.map((pt, idx) => (
                <div key={idx} className="key-point">
                  <div className="key-point-dot" />
                  <span>{pt}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Possible Actions */}
          <div>
            <div className="image-analysis-section-title">Intelligence Actions</div>
            <div className="image-actions">
              <button
                className="image-action-btn"
                onClick={() => handleAction('Explain this image', `Please explain the algorithm, steps, and formulas detected in ${image.name}`)}
              >
                <Sparkles />
                <span>Explain this image in depth</span>
              </button>

              <button
                className="image-action-btn"
                onClick={handleCopyExtractedText}
              >
                <FileText />
                <span>Extract full OCR text</span>
              </button>

              <button
                className="image-action-btn"
                onClick={() => handleAction('Summarize', `Provide an executive summary of ${image.name}`)}
              >
                <Layers />
                <span>Generate concise summary</span>
              </button>

              <button
                className="image-action-btn"
                onClick={() => handleAction('Solve this', `Solve or write executable code for the algorithm shown in ${image.name}`)}
              >
                <Code />
                <span>Write code / Solve problem</span>
              </button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  )
}
