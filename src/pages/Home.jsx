import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search, ArrowRight, FileText, Image as ImageIcon, Sparkles,
  GitBranch, BookOpen, Layers, CheckCircle2, ChevronRight, Upload
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import { mockDocuments, mockImages } from '../data/mockData'
import FileCard from '../components/FileCard'

export default function Home() {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const { setUploadModal } = useApp()

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    navigate(`/chat?q=${encodeURIComponent(query.trim())}`)
  }

  const handleQuickAction = (actionPrompt) => {
    navigate(`/chat?q=${encodeURIComponent(actionPrompt)}`)
  }

  const recentFiles = [...mockDocuments.slice(0, 2), ...mockImages.slice(0, 2)]

  return (
    <div className="page" style={{ padding: '0 0 64px 0', maxWidth: '100%' }}>
      {/* Hero Section */}
      <section className="hero">
        <div
          style={{
            maxWidth: '1280px',
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: '1.15fr 0.85fr',
            gap: '40px',
            alignItems: 'center',
            textAlign: 'left',
          }}
          className="home-hero-grid"
        >
          {/* Left Column: Welcome & Input */}
          <div>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 14px',
                background: 'rgba(124, 58, 237, 0.12)',
                border: '1px solid var(--border-accent)',
                borderRadius: '999px',
                fontSize: '0.8rem',
                fontWeight: 600,
                color: 'var(--text-accent)',
                marginBottom: '18px',
              }}
            >
              <Sparkles size={14} /> AI-Powered Document &amp; Image Intelligence
            </div>

            <h1
              className="hero-brand"
              style={{
                fontSize: '3.5rem',
                fontWeight: 800,
                marginBottom: '8px',
                textAlign: 'left',
                lineHeight: 1.1,
                letterSpacing: '-0.03em',
              }}
            >
              VISTAAR
            </h1>

            <div
              className="hero-tagline"
              style={{
                fontSize: '1.5rem',
                textAlign: 'left',
                fontWeight: 700,
                color: 'var(--text-primary)',
                marginBottom: '4px',
              }}
            >
              Expand your knowledge.
            </div>

            <div
              className="hero-tagline-sub"
              style={{
                fontSize: '1.15rem',
                textAlign: 'left',
                color: 'var(--text-accent)',
                fontWeight: 500,
                marginBottom: '18px',
              }}
            >
              Ask beyond. Discover more.
            </div>

            <p
              className="hero-description"
              style={{
                margin: '0 0 28px 0',
                textAlign: 'left',
                fontSize: '0.95rem',
                color: 'var(--text-secondary)',
                maxWidth: '560px',
                lineHeight: 1.65,
              }}
            >
              An AI-powered document and image intelligence platform that retrieves relevant information across multi-modal assets and delivers grounded answers backed by verified sources.
            </p>

            {/* Central Search / Input */}
            <form
              onSubmit={handleSearchSubmit}
              className="hero-search"
              style={{ margin: '0 0 22px 0', maxWidth: '560px' }}
            >
              <input
                type="text"
                className="hero-search-input"
                placeholder="Ask anything about your documents or images..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button type="submit" className="hero-search-btn" aria-label="Ask VISTAAR">
                <ArrowRight size={20} />
              </button>
            </form>

            {/* Quick Actions */}
            <div className="quick-actions" style={{ justifyContent: 'flex-start', margin: 0 }}>
              <button
                type="button"
                className="quick-action-chip"
                onClick={() => handleQuickAction('Summarize the latest RAG research paper')}
              >
                📄 Summarize this document
              </button>
              <button
                type="button"
                className="quick-action-chip"
                onClick={() => handleQuickAction('Explain the Quick Sort algorithm diagram in DSA notes')}
              >
                🖼 Explain this image
              </button>
              <button
                type="button"
                className="quick-action-chip"
                onClick={() => navigate('/knowledge-graph')}
              >
                🔍 Find key concepts
              </button>
              <button
                type="button"
                className="quick-action-chip"
                onClick={() => handleQuickAction('Compare RAG retrieval vs fine-tuning trade-offs')}
              >
                ⚖ Compare information
              </button>
            </div>
          </div>

          {/* Right Column: ACTIVE WORKSPACE INTELLIGENCE Card */}
          <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
            <div
              style={{
                width: '100%',
                maxWidth: '480px',
                padding: '26px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--radius-xl)',
                boxShadow: 'var(--shadow-xl)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {/* Subtle background glow */}
              <div
                style={{
                  position: 'absolute',
                  top: '-40px',
                  right: '-40px',
                  width: '200px',
                  height: '200px',
                  background: 'radial-gradient(circle, rgba(124, 58, 237, 0.18) 0%, transparent 70%)',
                  borderRadius: '50%',
                  pointerEvents: 'none',
                }}
              />

              {/* Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '18px',
                }}
              >
                <span
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: 'var(--text-tertiary)',
                  }}
                >
                  Active Workspace Intelligence
                </span>
                <span
                  style={{
                    fontSize: '0.74rem',
                    padding: '3px 10px',
                    background: 'var(--success-light)',
                    color: 'var(--success)',
                    borderRadius: '999px',
                    fontWeight: 600,
                  }}
                >
                  Indexed & Live
                </span>
              </div>

              {/* Document & Image Information */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '18px' }}>
                {/* Document info */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px',
                    background: 'var(--bg-input)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-secondary)',
                    cursor: 'pointer',
                  }}
                  onClick={() => navigate('/viewer/doc/doc-1')}
                >
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '8px',
                      background: 'rgba(220, 38, 38, 0.15)',
                      color: '#ef4444',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      flexShrink: 0,
                    }}
                  >
                    PDF
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '0.84rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      RAG_Research_Paper.pdf
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-tertiary)' }}>
                      42 pages • 128 semantic chunks
                    </div>
                  </div>
                  <span style={{ fontSize: '0.74rem', color: 'var(--primary-400)', fontWeight: 600, flexShrink: 0 }}>
                    98% match
                  </span>
                </div>

                {/* Image info */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px',
                    background: 'var(--bg-input)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-secondary)',
                    cursor: 'pointer',
                  }}
                  onClick={() => navigate('/viewer/image/img-2')}
                >
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '8px',
                      background: 'rgba(16, 185, 129, 0.15)',
                      color: '#10b981',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      flexShrink: 0,
                    }}
                  >
                    IMG
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '0.84rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      Architecture_Diagram.png
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-tertiary)' }}>
                      Visual OCR • 7 entities extracted
                    </div>
                  </div>
                  <span style={{ fontSize: '0.74rem', color: 'var(--primary-400)', fontWeight: 600, flexShrink: 0 }}>
                    91% match
                  </span>
                </div>
              </div>

              {/* Grounded Answer Synthesis & Source References */}
              <div
                style={{
                  padding: '16px',
                  background: 'rgba(124, 58, 237, 0.08)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid rgba(139, 92, 246, 0.25)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '8px',
                    color: 'var(--text-accent)',
                    fontWeight: 600,
                    fontSize: '0.84rem',
                  }}
                >
                  <Sparkles size={16} /> Grounded Answer Synthesis
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
                  "Retrieval Augmented Generation combines vector search across your PDF documents and OCR extracted from architecture diagrams to answer questions without hallucination."
                </p>
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                  <span className="relevance-badge high">Source 1: Pg 4</span>
                  <span className="relevance-badge high">Source 2: Pg 12</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Workspace Body */}
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 32px' }}>
        {/* The 5-Step Core UX Principle */}
        <section style={{ margin: '48px 0 56px 0', textAlign: 'center' }}>
          <div
            style={{
              fontSize: '0.8rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-accent)',
              marginBottom: '8px',
            }}
          >
            The VISTAAR Principle
          </div>
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '1.8rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              marginBottom: '32px',
            }}
          >
            Your Knowledge, Intelligently Expanded
          </h2>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '16px',
            }}
            className="home-principle-grid"
          >
            {[
              { step: '1', title: 'Upload', desc: 'Drop documents, research papers, diagrams or image notes' },
              { step: '2', title: 'Understand', desc: 'Semantic chunking, OCR parsing & vector embeddings' },
              { step: '3', title: 'Retrieve', desc: 'Hybrid dense & lexical search finds precise context' },
              { step: '4', title: 'Connect', desc: 'Synthesizes knowledge graphs across all your sources' },
              { step: '5', title: 'Answer', desc: 'Truthful responses backed with clickable evidence' },
            ].map((item, idx) => (
              <div
                key={item.step}
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-primary)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '24px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '50%',
                    background: idx === 4 ? 'var(--gradient-primary)' : 'rgba(124, 58, 237, 0.15)',
                    color: idx === 4 ? '#ffffff' : 'var(--primary-400)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: '0.95rem',
                    marginBottom: '14px',
                  }}
                >
                  {item.step}
                </div>
                <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                  {item.title}
                </h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', lineHeight: 1.5, margin: 0 }}>
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Feature Highlights Grid */}
        <section style={{ marginBottom: '56px' }}>
          <div className="feature-cards" style={{ maxWidth: '100%' }}>
            <div className="feature-card" onClick={() => navigate('/knowledge')}>
              <div className="feature-card-icon purple">
                <FileText />
              </div>
              <div className="feature-card-title">Document Intelligence</div>
              <div className="feature-card-desc">
                PDF, DOCX, and text analysis with exact page citations and highlighted excerpts.
              </div>
            </div>

            <div className="feature-card" onClick={() => navigate('/knowledge')}>
              <div className="feature-card-icon green">
                <ImageIcon />
              </div>
              <div className="feature-card-title">Vision Understanding</div>
              <div className="feature-card-desc">
                Extract text, read handwritten notes, understand architecture diagrams and charts.
              </div>
            </div>

            <div className="feature-card" onClick={() => navigate('/knowledge-graph')}>
              <div className="feature-card-icon blue">
                <GitBranch />
              </div>
              <div className="feature-card-title">Knowledge Graph</div>
              <div className="feature-card-desc">
                Explore interconnected topics, embeddings, and relationship networks interactively.
              </div>
            </div>

            <div className="feature-card" onClick={() => navigate('/explore')}>
              <div className="feature-card-icon amber">
                <Layers />
              </div>
              <div className="feature-card-title">Executive Summaries</div>
              <div className="feature-card-desc">
                Instant high-level overviews, key takeaways, and suggested questions for every asset.
              </div>
            </div>
          </div>
        </section>

        {/* Recent Knowledge Space */}
        <section>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '20px',
            }}
          >
            <div>
              <h3
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: '1.3rem',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                }}
              >
                Recent Knowledge Assets
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                Jump directly into exploration or ask questions
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setUploadModal(true)}>
                <Upload size={14} /> Upload Asset
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => navigate('/knowledge')}>
                View All Assets <ArrowRight size={14} />
              </button>
            </div>
          </div>

          <div className="files-grid">
            {recentFiles.map((file) => (
              <FileCard key={file.id} file={file} />
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
