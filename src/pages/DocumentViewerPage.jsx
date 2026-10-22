import { useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Sparkles,
  ExternalLink, CheckCircle, FileText
} from 'lucide-react'
import { mockDocuments } from '../data/mockData'

export default function DocumentViewerPage() {
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const doc = mockDocuments.find((d) => d.id === id) || mockDocuments[0]
  const initialPage = parseInt(searchParams.get('page') || '4', 10)
  const [currentPage, setCurrentPage] = useState(initialPage)
  const [zoomLevel, setZoomLevel] = useState(100)
  const [activeTab, setActiveTab] = useState('answer') // 'answer' | 'sources'

  // Generate thumbnail pages array
  const totalPages = doc.pages || 42
  const pagesList = Array.from({ length: Math.min(totalPages, 12) }, (_, i) => i + 1)

  return (
    <div className="doc-viewer-layout">
      {/* LEFT: Page Thumbnails */}
      <aside className="doc-thumbnails">
        <button
          className="btn btn-secondary btn-sm"
          style={{ width: '100%', marginBottom: '12px' }}
          onClick={() => navigate('/knowledge')}
        >
          <ArrowLeft size={14} /> Back to Library
        </button>

        <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px' }}>
          Pages ({totalPages})
        </div>

        {pagesList.map((pageNum) => (
          <div
            key={pageNum}
            className={`doc-thumbnail ${currentPage === pageNum ? 'active' : ''}`}
            onClick={() => setCurrentPage(pageNum)}
          >
            <div style={{ fontSize: '0.75rem', opacity: 0.6, textAlign: 'center', padding: '10px' }}>
              <FileText size={20} style={{ margin: '0 auto 4px' }} />
              <div>Section {pageNum}</div>
            </div>
            <span className="doc-thumbnail-label">Pg {pageNum}</span>
          </div>
        ))}
      </aside>

      {/* CENTER: Document Viewer Canvas */}
      <main className="doc-viewer-main">
        {/* Toolbar */}
        <div className="doc-viewer-toolbar">
          <div className="doc-viewer-title">{doc.name}</div>

          <div className="doc-viewer-controls">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              aria-label="Previous Page"
            >
              <ChevronLeft size={18} />
            </button>
            <span>
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              aria-label="Next Page"
            >
              <ChevronRight size={18} />
            </button>

            <div style={{ height: '16px', width: '1px', background: 'var(--border-primary)', margin: '0 4px' }} />

            <button
              onClick={() => setZoomLevel((z) => Math.max(75, z - 15))}
              aria-label="Zoom Out"
            >
              <ZoomOut size={16} />
            </button>
            <span style={{ minWidth: '45px' }}>{zoomLevel}%</span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(150, z + 15))}
              aria-label="Zoom In"
            >
              <ZoomIn size={16} />
            </button>
          </div>
        </div>

        {/* Rendered Document Page with Highlighted Passage */}
        <div className="doc-viewer-content">
          <div
            className="doc-page-render"
            style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-secondary)', paddingBottom: '12px', marginBottom: '24px', fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
              <span>VISTAAR RESEARCH ARCHIVE • CITATION VERIFIED</span>
              <span>PAGE {currentPage}</span>
            </div>

            <h2 className="doc-page-heading">
              4. Retrieval Augmented Generation Architecture
            </h2>

            <p className="doc-page-text">
              Traditional parametric language models are constrained by their training dataset horizons and suffer from hallucination when queried regarding private or domain-specific corpuses.
            </p>

            <p className="doc-page-text">
              To overcome these constraints,{' '}
              <mark className="doc-highlight" title="Retrieved Passage Grounding VISTAAR Answer">
                RAG retrieves relevant documents before generating the final answer.
              </mark>{' '}
              By converting both query inputs and knowledge chunks into high-dimensional dense vector embeddings, modern vector databases compute cosine similarity at scale within sub-millisecond latencies.
            </p>

            <div className="doc-page-figure">
              <div style={{ height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-card)', border: '1px dashed var(--border-primary)', borderRadius: 'var(--radius-sm)', color: 'var(--primary-600)', fontWeight: 600, fontSize: '0.85rem' }}>
                [ Figure 4.1: Dense Vector Retrieval Flow & Attention Fusion ]
              </div>
              <div className="doc-page-figure-caption">
                Figure 4.1 — Interleaving non-parametric retrieval tokens into the multi-head attention context.
              </div>
            </div>

            <p className="doc-page-text">
              The retrieved snippets are synthesized into the model's active reasoning context. Empirical evaluations on multi-hop question answering confirm that factual ground truth increases by up to 64% while maintaining concise conversational fluency.
            </p>
          </div>
        </div>
      </main>

      {/* RIGHT: VISTAAR Answer & Grounded Sources */}
      <aside className="doc-answer-panel">
        <div className="doc-answer-header">
          <div className="doc-answer-title">VISTAAR Synthesis</div>
          <span style={{ fontSize: '0.72rem', padding: '2px 8px', background: 'var(--success-light)', color: 'var(--success)', borderRadius: '999px', fontWeight: 600 }}>
            Ground Truth Verified
          </span>
        </div>

        <div className="doc-answer-tabs">
          <button
            className={`doc-answer-tab ${activeTab === 'answer' ? 'active' : ''}`}
            onClick={() => setActiveTab('answer')}
          >
            Synthesized Answer
          </button>
          <button
            className={`doc-answer-tab ${activeTab === 'sources' ? 'active' : ''}`}
            onClick={() => setActiveTab('sources')}
          >
            Sources Used (2)
          </button>
        </div>

        <div className="doc-answer-content">
          {activeTab === 'answer' ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary-700)', fontWeight: 600, fontSize: '0.85rem', marginBottom: '12px' }}>
                <Sparkles size={16} /> Grounded Summary
              </div>
              <p className="doc-answer-text">
                "Retrieval Augmented Generation combines information retrieval with language generation. Before generating an answer, it retrieves relevant passages directly from indexed documents—preventing factual hallucinations and enabling grounded citations."
              </p>

              <div style={{ padding: '14px', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  Highlighted Passage Anchor:
                </div>
                <em>"RAG retrieves relevant documents before generating the final answer."</em>
                <div style={{ marginTop: '8px', fontSize: '0.72rem', color: 'var(--primary-600)', fontWeight: 600 }}>
                  Page {currentPage} • 85% Semantic Match
                </div>
              </div>

              <button
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '24px' }}
                onClick={() => navigate(`/chat?q=Tell me more about the architecture described on page ${currentPage} of ${doc.name}`)}
              >
                Ask Follow-Up in Chat
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="evidence-card">
                <div className="evidence-card-header">
                  <div className="evidence-card-icon pdf">📄</div>
                  <div>
                    <div className="evidence-card-name">RAG_Research_Paper.pdf</div>
                    <div className="evidence-card-page">Page 4</div>
                  </div>
                  <span className="relevance-badge high">85%</span>
                </div>
                <div className="evidence-card-text">
                  "RAG retrieves relevant documents before generating the final answer."
                </div>
              </div>

              <div className="evidence-card">
                <div className="evidence-card-header">
                  <div className="evidence-card-icon pdf">📄</div>
                  <div>
                    <div className="evidence-card-name">System_Design_Notes.pdf</div>
                    <div className="evidence-card-page">Page 12</div>
                  </div>
                  <span className="relevance-badge medium">72%</span>
                </div>
                <div className="evidence-card-text">
                  "High-availability vector database deployment and caching strategies."
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
