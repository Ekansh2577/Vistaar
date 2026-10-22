import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText, Image as ImageIcon, Sparkles, HelpCircle, ArrowRight,
  ChevronRight, Bookmark, CheckCircle2, Eye, Compass
} from 'lucide-react'
import { mockDocuments, mockImages } from '../data/mockData'

export default function Explore() {
  const navigate = useNavigate()
  const allAssets = [...mockDocuments, ...mockImages]
  const [selectedAssetId, setSelectedAssetId] = useState(mockDocuments[0].id)

  const activeAsset = allAssets.find((a) => a.id === selectedAssetId) || allAssets[0]
  const isImage = activeAsset.type === 'image'

  const handleAskQuestion = (question) => {
    navigate(`/chat?q=${encodeURIComponent(question)}`)
  }

  const handleOpenViewer = () => {
    if (isImage) {
      navigate(`/viewer/image/${activeAsset.id}`)
    } else {
      navigate(`/viewer/doc/${activeAsset.id}`)
    }
  }

  return (
    <div className="explore-layout">
      {/* MAIN INTELLIGENCE CONTENT */}
      <div className="explore-main">
        {/* Header with Title and Action buttons */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '28px', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div className={`file-card-icon ${isImage ? 'img' : 'pdf'}`} style={{ width: '48px', height: '48px', fontSize: '1.4rem' }}>
              {isImage ? '🖼' : '📄'}
            </div>
            <div>
              <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {activeAsset.name}
              </h1>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-tertiary)' }}>
                {isImage
                  ? `Image Analysis • ${activeAsset.dimensions} • ${activeAsset.size}`
                  : `${activeAsset.pages} pages • ${activeAsset.chunks} vector chunks • ${activeAsset.size}`}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={handleOpenViewer}>
              <Eye size={16} /> Open {isImage ? 'Intelligence Studio' : 'Document Viewer'}
            </button>
            <button
              className="btn btn-primary"
              onClick={() => handleAskQuestion(`Summarize the key findings from ${activeAsset.name}`)}
            >
              <Sparkles size={16} /> Ask VISTAAR
            </button>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="explore-section">
          <div className="explore-section-title">
            {isImage ? 'Visual Comprehension Summary' : 'Executive Summary'}
          </div>
          <div className="explore-summary">
            {activeAsset.summary}
          </div>
        </div>

        {/* Key Concepts / Detected Text */}
        <div className="explore-section">
          <div className="explore-section-title">
            {isImage ? 'Detected Text & Visual Entities' : 'Key Concepts & Embeddings'}
          </div>
          <div className="explore-concepts">
            {(activeAsset.keyConcepts || activeAsset.detectedText || []).map((concept, idx) => (
              <span
                key={idx}
                className="explore-concept-chip"
                onClick={() => handleAskQuestion(`Explain "${concept}" in the context of ${activeAsset.name}`)}
              >
                {concept}
              </span>
            ))}
          </div>
        </div>

        {/* Key Takeaways / Points */}
        <div className="explore-section">
          <div className="explore-section-title">
            {isImage ? 'Key Visual Takeaways' : 'Essential Takeaways'}
          </div>
          <div className="takeaways-list">
            {(activeAsset.keyTakeaways || activeAsset.keyPoints || []).map((point, idx) => (
              <div key={idx} className="takeaway-item">
                <div className="takeaway-bullet" />
                <div className="takeaway-text">{point}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Suggested Questions */}
        <div className="explore-section">
          <div className="explore-section-title">Suggested Deep-Dive Questions</div>
          <div className="explore-questions">
            {(activeAsset.suggestedQuestions || [
              'What are the core conclusions of this asset?',
              'How does this relate to other indexed knowledge?',
              'What practical implementations are proposed?'
            ]).map((q, idx) => (
              <div
                key={idx}
                className="explore-question"
                onClick={() => handleAskQuestion(q)}
              >
                <HelpCircle />
                <span style={{ flex: 1 }}>{q}</span>
                <ArrowRight size={14} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* EXPLORE SIDEBAR: Asset Switcher & Sections */}
      <aside className="explore-sidebar">
        <div style={{ marginBottom: '24px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
            Knowledge Assets
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {allAssets.map((asset) => {
              const isSelected = asset.id === selectedAssetId
              return (
                <div
                  key={asset.id}
                  onClick={() => setSelectedAssetId(asset.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    background: isSelected ? 'var(--primary-50)' : 'transparent',
                    border: isSelected ? '1px solid var(--border-accent)' : '1px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <span style={{ fontSize: '1rem' }}>{asset.type === 'image' ? '🖼' : '📄'}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: '0.82rem',
                      fontWeight: isSelected ? 600 : 500,
                      color: isSelected ? 'var(--primary-700)' : 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {asset.name}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                      {asset.type === 'image' ? 'Image' : `${asset.pages} pages`}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Important Sections (if document) */}
        {!isImage && activeAsset.sections && (
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
              Document Sections
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {activeAsset.sections.map((sec, idx) => (
                <div
                  key={idx}
                  onClick={() => navigate(`/viewer/doc/${activeAsset.id}?page=${sec.page}`)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-primary)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.78rem',
                    cursor: 'pointer'
                  }}
                >
                  <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{sec.title}</span>
                  <span style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>Pg {sec.page}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>
    </div>
  )
}
