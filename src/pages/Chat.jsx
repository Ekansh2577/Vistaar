import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  MessageSquare, Plus, Send, Paperclip, FileText, Image as ImageIcon,
  CheckCircle, Sparkles, ExternalLink, ArrowRight, CornerDownLeft, ShieldCheck,
  AlertCircle, RefreshCw, Upload
} from 'lucide-react'
import { mockConversations, mockDocuments, mockImages } from '../data/mockData'
import { useApp } from '../context/AppContext'
import { chatService } from '../services/api'

export default function Chat() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setUploadModal, uploadedDocuments, backendOnline, checkBackendStatus } = useApp()

  const [conversations, setConversations] = useState(mockConversations)
  const [activeConvId, setActiveConvId] = useState('conv-1')
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  
  // Mixed sources filter
  const [selectedSourceIds, setSelectedSourceIds] = useState(['doc-1', 'doc-2'])
  const [evidencePanelOpen, setEvidencePanelOpen] = useState(true)

  const messagesEndRef = useRef(null)

  // Current conversation
  const currentConv = conversations.find((c) => c.id === activeConvId) || conversations[0]

  // Available sources pool (includes uploaded session documents)
  const allAvailableSources = [
    ...(uploadedDocuments || []).map(d => ({
      ...d,
      tags: ['Uploaded', 'FAISS Indexed'],
      summary: d.backendMessage || 'Indexed into FAISS vector database.',
    })),
    ...mockDocuments,
    ...mockImages
  ]

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

  const handleSendMessage = async (messageText) => {
    const text = (messageText || inputMessage).trim()
    if (!text || isTyping) return

    const userMsg = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      sources: [],
    }

    // Add user message to active conversation
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

    try {
      // Call actual FastAPI backend endpoint: POST /ask
      const response = await chatService.askQuestion(text)

      // Check if backend returned empty retrieval notice
      const isUnindexed = response.answer?.includes('Please upload a document first') ||
                          response.answer?.includes('No relevant information found')

      const assistantMsg = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: response.answer,
        isUnindexedNotice: isUnindexed,
        sources: (uploadedDocuments && uploadedDocuments.length > 0)
          ? uploadedDocuments.map(d => ({
              docId: d.id,
              name: d.name,
              page: 1,
              relevance: 90,
              type: d.type === 'pdf' ? 'pdf' : 'text',
              textSnippet: 'Indexed into backend FAISS vector index (Top-8 retrieval).',
            }))
          : [],
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
    } catch (err) {
      // Graceful error state directly in conversation
      const errorMsg = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        isError: true,
        content: `⚠️ Error contacting VISTAAR backend:\n\n${err.message}\n\nPlease verify that the FastAPI backend server is running on http://127.0.0.1:8000 and has GEMINI_API_KEY configured.`,
        sources: [],
      }

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeConvId) {
            return {
              ...c,
              messages: [...c.messages, errorMsg],
            }
          }
          return c
        })
      )
    } finally {
      setIsTyping(false)
    }
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
              Knowledge Base Context
            </div>
            
            {uploadedDocuments && uploadedDocuments.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {uploadedDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '6px 8px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid rgba(16, 185, 129, 0.25)',
                      fontSize: '0.78rem',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <CheckCircle size={14} style={{ color: '#10b981', flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {doc.name}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', lineHeight: 1.4 }}>
                No custom files uploaded yet. Backend FAISS vector store is empty.
              </div>
            )}

            <button
              className="btn btn-secondary btn-sm"
              style={{ width: '100%', marginTop: '12px', fontSize: '0.75rem' }}
              onClick={() => setUploadModal(true)}
            >
              <Upload size={13} /> Upload Document
            </button>
          </div>
        </div>
      </aside>

      {/* CENTER PANEL: Main Conversation Area */}
      <main className="chat-main">
        <div className="chat-main-header">
          <div>
            <div className="chat-main-title">{currentConv?.title || 'Chat Workspace'}</div>
            <div className="chat-main-subtitle">
              FastAPI RAG Pipeline • FAISS Dense Retrieval (Top-8) • Gemini Context Grounding
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Backend Connectivity Status Pill */}
            <div
              onClick={checkBackendStatus}
              title="Click to check backend status"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '999px',
                fontSize: '0.72rem',
                fontWeight: 600,
                cursor: 'pointer',
                background:
                  backendOnline === true
                    ? 'rgba(16, 185, 129, 0.12)'
                    : backendOnline === false
                    ? 'rgba(239, 68, 68, 0.12)'
                    : 'rgba(245, 158, 11, 0.12)',
                color:
                  backendOnline === true
                    ? '#10b981'
                    : backendOnline === false
                    ? '#ef4444'
                    : '#f59e0b',
                border: `1px solid ${
                  backendOnline === true
                    ? 'rgba(16, 185, 129, 0.3)'
                    : backendOnline === false
                    ? 'rgba(239, 68, 68, 0.3)'
                    : 'rgba(245, 158, 11, 0.3)'
                }`,
              }}
            >
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background:
                    backendOnline === true
                      ? '#10b981'
                      : backendOnline === false
                      ? '#ef4444'
                      : '#f59e0b',
                }}
              />
              <span>
                {backendOnline === true
                  ? 'Backend Connected'
                  : backendOnline === false
                  ? 'Backend Offline'
                  : 'Checking Backend'}
              </span>
            </div>

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
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-tertiary)' }}>Indexed Target:</span>
          {uploadedDocuments && uploadedDocuments.length > 0 ? (
            uploadedDocuments.map(s => (
              <span key={s.id} className="source-chip" style={{ fontSize: '0.72rem', padding: '2px 10px', background: 'rgba(16, 185, 129, 0.15)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
                <span className="source-chip-icon">📄</span>
                <span>{s.name} (Active in FAISS)</span>
              </span>
            ))
          ) : (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
              No document uploaded yet. Click "Upload Knowledge" to index a PDF or TXT file into FAISS.
            </span>
          )}
        </div>

        {/* Messages Scroll Container */}
        <div className="chat-messages">
          {currentConv?.messages.length === 0 ? (
            <div className="empty-state" style={{ margin: 'auto' }}>
              <div className="empty-state-icon">
                <Sparkles size={32} style={{ color: 'var(--primary-600)' }} />
              </div>
              <h3 className="empty-state-title">Ask anything about your documents</h3>
              <p className="empty-state-desc">
                Submit natural language questions to the VISTAAR FastAPI backend. The system will retrieve relevant chunks via FAISS vector similarity search and generate grounded answers using Gemini.
              </p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                <button
                  className="quick-action-chip"
                  onClick={() => handleSendMessage('What is the main topic of the uploaded document?')}
                >
                  What is the document about?
                </button>
                <button
                  className="quick-action-chip"
                  onClick={() => handleSendMessage('Summarize the key findings.')}
                >
                  Summarize key findings
                </button>
                <button
                  className="quick-action-chip"
                  onClick={() => setUploadModal(true)}
                >
                  <Upload size={13} style={{ display: 'inline', marginRight: '4px' }} />
                  Upload new PDF/TXT
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
                  <div
                    className="chat-message-bubble"
                    style={
                      msg.isError
                        ? { background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: 'var(--text-primary)' }
                        : undefined
                    }
                  >
                    {msg.content.split('\n').map((paragraph, idx) => (
                      <p key={idx} style={{ marginBottom: idx === msg.content.split('\n').length - 1 ? 0 : '8px' }}>
                        {paragraph}
                      </p>
                    ))}

                    {msg.isUnindexedNotice && (
                      <div style={{ marginTop: '12px' }}>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => setUploadModal(true)}
                        >
                          <Upload size={14} /> Upload a Document Now
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Inline Source Chips when backend provides references */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="chat-message-sources">
                      <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-tertiary)', alignSelf: 'center' }}>
                        Target Document:
                      </span>
                      {msg.sources.map((src, idx) => (
                        <div
                          key={idx}
                          className="chat-source-card"
                          onClick={() => {}}
                        >
                          <div className={`chat-source-icon ${src.type === 'image' ? 'img' : 'pdf'}`}>
                            📄
                          </div>
                          <div>
                            <div className="chat-source-name">{src.name}</div>
                            <div className="chat-source-page">
                              FAISS In-Memory Index • Top-8 Chunks
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
                    Searching FAISS vector index & querying Gemini...
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
              placeholder="Ask a question about your uploaded documents (Press Enter to send)..."
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
            <div className="chat-sources-title">Backend Evidence & Context</div>
            <div className="chat-sources-subtitle">
              Ground truth retrieved by FAISS vector index
            </div>
          </div>

          <div className="chat-sources-list">
            {uploadedDocuments && uploadedDocuments.length > 0 ? (
              uploadedDocuments.map((doc, i) => (
                <div key={i} className="evidence-card">
                  <div className="evidence-card-header">
                    <div className="evidence-card-icon pdf">
                      📄
                    </div>
                    <div>
                      <div className="evidence-card-name">{doc.name}</div>
                      <div className="evidence-card-page">
                        {doc.size} • Ingestion Status: Indexed
                      </div>
                    </div>
                    <div className="evidence-card-relevance">
                      <span className="relevance-badge high">
                        Active
                      </span>
                    </div>
                  </div>

                  <div className="evidence-card-text">
                    "Chunks stored in FAISS IndexFlatL2 (384-dim all-MiniLM-L6-v2 embeddings). The backend retrieves top-8 chunks for each query and logs preview matches to the server console."
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: '20px 16px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
                <div style={{ marginBottom: '10px', fontSize: '1.5rem' }}>📂</div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>No Documents Indexed Yet</div>
                <p style={{ lineHeight: 1.5, fontSize: '0.8rem', margin: '0 0 16px 0' }}>
                  Upload a PDF or TXT file to populate the backend FAISS index and observe retrieved context.
                </p>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => setUploadModal(true)}
                  style={{ width: '100%' }}
                >
                  <Upload size={14} /> Upload Knowledge
                </button>
              </div>
            )}

            <div style={{ marginTop: '16px', padding: '12px 14px', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>Backend RAG Architecture:</div>
              <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <li>Chunk size: 1000 chars (200 char overlap)</li>
                <li>Embedding model: all-MiniLM-L6-v2</li>
                <li>Search: Exact FAISS L2 Euclidean distance</li>
                <li>Retrieval: Top K = 8 chunks</li>
                <li>Generation: Gemini with strict context prompt</li>
              </ul>
            </div>
          </div>
        </aside>
      )}
    </div>
  )
}
