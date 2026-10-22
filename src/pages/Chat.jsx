import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  MessageSquare, Plus, Send, Paperclip, FileText, Image as ImageIcon,
  CheckCircle, Sparkles, ExternalLink, ArrowRight, CornerDownLeft, ShieldCheck
} from 'lucide-react'
import { mockConversations, mockDocuments, mockImages } from '../data/mockData'
import { useApp } from '../context/AppContext'

export default function Chat() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setUploadModal } = useApp()

  const [conversations, setConversations] = useState(mockConversations)
  const [activeConvId, setActiveConvId] = useState('conv-1')
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  
  // Mixed sources filter (PDFs and Images selected for chat context)
  const [selectedSourceIds, setSelectedSourceIds] = useState(['doc-1', 'doc-2', 'img-2'])
  const [evidencePanelOpen, setEvidencePanelOpen] = useState(true)

  const messagesEndRef = useRef(null)

  // Current conversation
  const currentConv = conversations.find((c) => c.id === activeConvId) || conversations[0]

  // Available sources pool
  const allAvailableSources = [...mockDocuments, ...mockImages]

  // Handle incoming query param ?q=
  useEffect(() => {
    const query = searchParams.get('q')
    if (query) {
      handleSendMessage(query)
    }
  }, [searchParams])

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentConv?.messages, isTyping])

  const handleSendMessage = (messageText) => {
    const text = (messageText || inputMessage).trim()
    if (!text) return

    const userMsg = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      sources: [],
    }

    // Add user message
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === activeConvId) {
          return {
            ...c,
            title: c.messages.length === 0 ? (text.length > 28 ? text.slice(0, 28) + '...' : text) : c.title,
            messages: [...c.messages, userMsg],
          }
        }
        return c
      })
    )

    if (!messageText) setInputMessage('')
    setIsTyping(true)

    // Simulate RAG retrieval & generation delay
    setTimeout(() => {
      // Build dynamic context-aware answer
      let answerContent = ''
      let sources = []

      if (text.toLowerCase().includes('sort') || text.toLowerCase().includes('dsa') || text.toLowerCase().includes('image')) {
        answerContent = `Based on your uploaded image **DSA_Notes.jpg** and **Architecture_Diagram.png**:\n\n- **Algorithm Structure:** The handwritten notes define Quick Sort using a divide-and-conquer strategy with recursive partitioning.\n- **Pivot Selection:** Crucial for avoiding O(n²) worst-case degradation. Choosing median-of-three yields average O(n log n) runtime.\n- **Visual Trace:** The partitioned arrays in the diagram show elements smaller than the pivot shifted left, and larger elements shifted right.`
        sources = [
          { docId: 'img-1', name: 'DSA_Notes.jpg', page: 1, relevance: 94, type: 'image', textSnippet: 'Quick Sort algorithm step-by-step pivot selection and partition logic.' },
          { docId: 'img-2', name: 'Architecture_Diagram.png', page: 1, relevance: 78, type: 'image', textSnippet: 'Vector search flow into LLM context augmentation.' }
        ]
      } else {
        answerContent = `According to your indexed knowledge base:\n\n1. **Core Concept:** Retrieval Augmented Generation (RAG) grounds language models in external authoritative documents before generating completions, eliminating hallucinations.\n2. **Retrieval Mechanism:** Documents are partitioned into dense chunks, embedded using transformer models, and queried through vector similarity indices like FAISS.\n3. **Multi-Source Synthesis:** Both structured documentation and diagrammatic visuals are retrieved concurrently to form an evidence-backed synthesized response.`
        sources = [
          { docId: 'doc-1', name: 'RAG_Research_Paper.pdf', page: 4, relevance: 88, type: 'pdf', textSnippet: 'RAG combines pre-trained parametric memory with non-parametric dense vector index representations.' },
          { docId: 'doc-2', name: 'System_Design_Notes.pdf', page: 12, relevance: 76, type: 'pdf', textSnippet: 'High-availability vector database deployment and caching strategies.' },
          { docId: 'doc-6', name: 'Data_Science_Handbook.pdf', page: 27, relevance: 64, type: 'pdf', textSnippet: 'Statistical evaluation of retrieval accuracy and precision-recall trade-offs.' }
        ]
      }

      const assistantMsg = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: answerContent,
        sources,
      }

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeConvId) {
            return {
              ...c,
              messages: [...c.messages, assistantMsg],
            }
          }
          return c
        })
      )
      setIsTyping(false)
    }, 1200)
  }

  const handleNewChat = () => {
    const newId = `conv-${Date.now()}`
    const newConv = {
      id: newId,
      title: 'New Research Chat',
      date: 'Today',
      messages: [],
    }
    setConversations([newConv, ...conversations])
    setActiveConvId(newId)
  }

  const toggleSourceSelection = (id) => {
    setSelectedSourceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  // Active sources list from latest assistant message
  const latestAssistantMessage = [...(currentConv?.messages || [])].reverse().find((m) => m.role === 'assistant')
  const activeEvidenceSources = latestAssistantMessage?.sources || [
    { docId: 'doc-1', name: 'RAG_Research_Paper.pdf', page: 4, relevance: 85, type: 'pdf', textSnippet: 'RAG combines retrieval with language generation to reduce factual hallucinations.' },
    { docId: 'doc-2', name: 'System_Design_Notes.pdf', page: 12, relevance: 72, type: 'pdf', textSnippet: 'Microservices architecture for decoupled vector indexing.' },
    { docId: 'doc-6', name: 'Data_Science_Handbook.pdf', page: 27, relevance: 61, type: 'pdf', textSnippet: 'Evaluation metrics for dense retrieval models.' },
  ]

  const handleOpenSource = (source) => {
    if (source.type === 'image') {
      navigate(`/viewer/image/${source.docId}`)
    } else {
      navigate(`/viewer/doc/${source.docId}?page=${source.page || 1}`)
    }
  }

  return (
    <div className="chat-layout">
      {/* LEFT PANEL: Conversation History */}
      <aside className="chat-sidebar">
        <div className="chat-sidebar-header">
          <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleNewChat}>
            <Plus size={16} /> New Chat
          </button>
        </div>

        <div className="chat-sidebar-list">
          <div className="chat-sidebar-section-title">Active Conversations</div>
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`chat-history-item ${conv.id === activeConvId ? 'active' : ''}`}
              onClick={() => setActiveConvId(conv.id)}
            >
              <MessageSquare />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{conv.title}</span>
            </div>
          ))}

          <div style={{ marginTop: '24px', padding: '12px', borderTop: '1px solid var(--border-secondary)' }}>
            <div className="chat-sidebar-section-title" style={{ padding: '0 0 8px 0' }}>
              Selected Sources ({selectedSourceIds.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {allAvailableSources.slice(0, 4).map((src) => {
                const isChecked = selectedSourceIds.includes(src.id)
                return (
                  <div
                    key={src.id}
                    onClick={() => toggleSourceSelection(src.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '6px 8px',
                      borderRadius: 'var(--radius-sm)',
                      background: isChecked ? 'var(--primary-50)' : 'transparent',
                      cursor: 'pointer',
                      fontSize: '0.78rem',
                      color: isChecked ? 'var(--primary-700)' : 'var(--text-secondary)',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      style={{ cursor: 'pointer' }}
                    />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {src.name}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </aside>

      {/* CENTER PANEL: Main Conversation Area */}
      <main className="chat-main">
        <div className="chat-main-header">
          <div>
            <div className="chat-main-title">{currentConv?.title || 'Chat Workspace'}</div>
            <div className="chat-main-subtitle">
              Grounding queries across {selectedSourceIds.length} active documents & images
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setEvidencePanelOpen(!evidencePanelOpen)}
            >
              <ShieldCheck size={14} /> {evidencePanelOpen ? 'Hide Evidence' : 'Show Evidence'}
            </button>
          </div>
        </div>

        {/* Selected Sources Context Pills */}
        <div style={{ padding: '8px 28px', borderBottom: '1px solid var(--border-secondary)', background: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-tertiary)' }}>Context Pool:</span>
          {allAvailableSources.filter(s => selectedSourceIds.includes(s.id)).map(s => (
            <span key={s.id} className="source-chip" style={{ fontSize: '0.72rem', padding: '2px 10px' }}>
              <span className="source-chip-icon">{s.type === 'image' ? '🖼' : '📄'}</span>
              <span>{s.name}</span>
            </span>
          ))}
        </div>

        {/* Messages Scroll Container */}
        <div className="chat-messages">
          {currentConv?.messages.length === 0 ? (
            <div className="empty-state" style={{ margin: 'auto' }}>
              <div className="empty-state-icon">
                <Sparkles size={32} style={{ color: 'var(--primary-600)' }} />
              </div>
              <h3 className="empty-state-title">Ask anything about your knowledge</h3>
              <p className="empty-state-desc">
                Ask questions across documents and images. VISTAAR will cross-reference text, code, charts, and diagrams to deliver verified answers.
              </p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                <button
                  className="quick-action-chip"
                  onClick={() => handleSendMessage('What is Retrieval Augmented Generation (RAG)?')}
                >
                  What is RAG?
                </button>
                <button
                  className="quick-action-chip"
                  onClick={() => handleSendMessage('Explain the Quick Sort algorithm in DSA_Notes.jpg')}
                >
                  Explain Quick Sort notes
                </button>
                <button
                  className="quick-action-chip"
                  onClick={() => handleSendMessage('How does the RAG architecture diagram connect to embeddings?')}
                >
                  Analyze architecture diagram
                </button>
              </div>
            </div>
          ) : (
            currentConv?.messages.map((msg) => (
              <div key={msg.id} className={`chat-message ${msg.role}`}>
                <div className="chat-message-avatar">
                  {msg.role === 'user' ? 'EK' : <Sparkles size={16} />}
                </div>
                <div className="chat-message-content">
                  <div className="chat-message-bubble">
                    {msg.content.split('\n').map((paragraph, idx) => (
                      <p key={idx} style={{ marginBottom: idx === msg.content.split('\n').length - 1 ? 0 : '8px' }}>
                        {paragraph}
                      </p>
                    ))}
                  </div>

                  {/* Inline Source Chips */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="chat-message-sources">
                      <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-tertiary)', alignSelf: 'center' }}>
                        Grounding Sources:
                      </span>
                      {msg.sources.map((src, idx) => (
                        <div
                          key={idx}
                          className="chat-source-card"
                          onClick={() => handleOpenSource(src)}
                        >
                          <div className={`chat-source-icon ${src.type === 'image' ? 'img' : 'pdf'}`}>
                            {src.type === 'image' ? '🖼' : '📄'}
                          </div>
                          <div>
                            <div className="chat-source-name">{src.name}</div>
                            <div className="chat-source-page">
                              {src.type === 'image' ? 'Visual OCR' : `Page ${src.page}`} • {src.relevance}% relevant
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {isTyping && (
            <div className="chat-message assistant">
              <div className="chat-message-avatar">
                <Sparkles size={16} />
              </div>
              <div className="chat-message-content">
                <div className="chat-message-bubble" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                  <div className="loading-pulse">
                    <div className="loading-pulse-dot" />
                    <div className="loading-pulse-dot" />
                    <div className="loading-pulse-dot" />
                  </div>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-tertiary)' }}>
                    Searching vector embeddings & verifying evidence...
                  </span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="chat-input-container">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSendMessage()
            }}
            className="chat-input-wrapper"
          >
            <textarea
              placeholder="Ask a question about your documents, notes or images (Press Enter to send)..."
              value={inputMessage}
              rows={1}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage()
                }
              }}
            />

            <div className="chat-input-actions">
              <button
                type="button"
                className="chat-input-action-btn"
                title="Add to knowledge"
                onClick={() => setUploadModal(true)}
              >
                <Paperclip size={18} />
              </button>
              <button
                type="submit"
                className="chat-send-btn"
                disabled={!inputMessage.trim() || isTyping}
                aria-label="Send query"
              >
                <Send size={18} />
              </button>
            </div>
          </form>
        </div>
      </main>

      {/* RIGHT PANEL: Sources / Evidence Workspace */}
      {evidencePanelOpen && (
        <aside className="chat-sources-panel">
          <div className="chat-sources-header">
            <div className="chat-sources-title">Verified Evidence</div>
            <div className="chat-sources-subtitle">
              Ground truth extracted from selected knowledge assets
            </div>
          </div>

          <div className="chat-sources-list">
            {activeEvidenceSources.map((ev, i) => (
              <div
                key={i}
                className="evidence-card"
                onClick={() => handleOpenSource(ev)}
              >
                <div className="evidence-card-header">
                  <div className={`evidence-card-icon ${ev.type === 'image' ? 'img' : 'pdf'}`}>
                    {ev.type === 'image' ? '🖼' : '📄'}
                  </div>
                  <div>
                    <div className="evidence-card-name">{ev.name}</div>
                    <div className="evidence-card-page">
                      {ev.type === 'image' ? 'Visual Region #1' : `Page ${ev.page || 1}`}
                    </div>
                  </div>
                  <div className="evidence-card-relevance">
                    <span className={`relevance-badge ${ev.relevance >= 80 ? 'high' : 'medium'}`}>
                      {ev.relevance}%
                    </span>
                  </div>
                </div>

                <div className="evidence-card-text">
                  "{ev.textSnippet || 'Retrieved semantic segment matched high-dimensional cosine similarity score above relevance threshold.'}"
                </div>

                <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px', fontSize: '0.75rem', color: 'var(--primary-600)', fontWeight: 500 }}>
                  View passage <ExternalLink size={12} />
                </div>
              </div>
            ))}
          </div>
        </aside>
      )}
    </div>
  )
}
