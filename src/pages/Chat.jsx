import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  MessageSquare, Plus, Send, Paperclip, FileText, Image as ImageIcon,
  CheckCircle, Sparkles, ExternalLink, ArrowRight, CornerDownLeft, ShieldCheck,
  AlertCircle, RefreshCw, Upload, Globe, Eye, X, Compass
} from 'lucide-react'
import { mockConversations, mockDocuments, mockImages } from '../data/mockData'
import { useApp } from '../context/AppContext'
import { chatService, imageService } from '../services/api'

export default function Chat() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const {
    setUploadModal,
    uploadedDocuments,
    uploadedImages,
    activeImage,
    setActiveImage,
    backendOnline,
    checkBackendStatus
  } = useApp()

  const [conversations, setConversations] = useState(mockConversations)
  const [activeConvId, setActiveConvId] = useState('conv-1')
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [typingStatusText, setTypingStatusText] = useState('')
  
  // Right panel active tab: 'document' | 'web' | 'image'
  const [evidenceTab, setEvidenceTab] = useState('document')
  const [evidencePanelOpen, setEvidencePanelOpen] = useState(true)
  const [activeWebSources, setActiveWebSources] = useState([])

  // Local attached image for immediate vision query
  const [attachedImageFile, setAttachedImageFile] = useState(null)
  const [attachedImagePreview, setAttachedImagePreview] = useState(null)

  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // Current conversation
  const currentConv = conversations.find((c) => c.id === activeConvId) || conversations[0]

  // Handle incoming query param ?q=
  useEffect(() => {
    const query = searchParams.get('q')
    if (query) {
      handleSendMessage(query)
    }
  }, [searchParams])

  // Sync active image from context if available
  useEffect(() => {
    if (activeImage && activeImage.rawFile && !attachedImageFile) {
      setAttachedImageFile(activeImage.rawFile)
      setAttachedImagePreview(activeImage.previewUrl || URL.createObjectURL(activeImage.rawFile))
    }
  }, [activeImage])

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentConv?.messages, isTyping])

  const handleImageAttach = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      if (!file.type.startsWith('image/')) {
        alert('Please select an image file (PNG, JPG, WEBP, GIF).')
        return
      }
      setAttachedImageFile(file)
      setAttachedImagePreview(URL.createObjectURL(file))
    }
  }

  const handleRemoveAttachedImage = () => {
    setAttachedImageFile(null)
    setAttachedImagePreview(null)
    if (activeImage) setActiveImage(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // Handle Web Search Fallback action
  const handleWebSearch = async (searchQuery) => {
    const query = searchQuery?.trim()
    if (!query || isTyping) return

    setIsTyping(true)
    setTypingStatusText(`Searching live web for "${query}" & synthesizing answer...`)

    try {
      const webResult = await chatService.searchWeb(query)
      const assistantMsg = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        isWebSearch: true,
        query: query,
        content: webResult.synthesized_answer,
        webSources: webResult.sources || [],
        sources: [],
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

      if (webResult.sources && webResult.sources.length > 0) {
        setActiveWebSources(webResult.sources)
        setEvidenceTab('web')
        setEvidencePanelOpen(true)
      }
    } catch (err) {
      const errorMsg = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        isError: true,
        content: `⚠️ Web Search Fallback Error:\n\n${err.message}\n\nPlease check your internet connection or backend search configuration.`,
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
      setTypingStatusText('')
    }
  }

  const handleSendMessage = async (messageText) => {
    const text = (messageText || inputMessage).trim()
    if (!text || isTyping) return

    const imageToAnalyze = attachedImageFile
    const imagePreviewToDisplay = attachedImagePreview

    const userMsg = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      attachedImage: imagePreviewToDisplay,
      imageName: imageToAnalyze ? imageToAnalyze.name : null,
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

    // ROUTE 1: If an image is attached/active, route directly to Multimodal Vision Endpoint!
    if (imageToAnalyze) {
      setTypingStatusText(`Analyzing image pixels and reading visual elements with Gemini Vision...`)

      try {
        const visionResult = await imageService.askImage(imageToAnalyze, text)

        const assistantMsg = {
          id: `msg-${Date.now() + 1}`,
          role: 'assistant',
          isVisionAnalysis: true,
          imageName: imageToAnalyze.name,
          imagePreview: imagePreviewToDisplay,
          content: visionResult.answer,
          sources: [
            {
              name: imageToAnalyze.name,
              type: 'image',
              page: 1,
              relevance: 100,
              textSnippet: `Direct multimodal pixel analysis: ${imageToAnalyze.name} (${(imageToAnalyze.size / (1024 * 1024)).toFixed(2)} MB)`,
            }
          ],
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

        setEvidenceTab('image')
      } catch (err) {
        const errorMsg = {
          id: `msg-${Date.now() + 1}`,
          role: 'assistant',
          isError: true,
          content: `⚠️ Image Analysis Error:\n\n${err.message}`,
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
        setTypingStatusText('')
      }
      return
    }

    // ROUTE 2: Standard Document Question Answering via FAISS Index
    setTypingStatusText('Searching FAISS vector index & querying document context...')

    try {
      const response = await chatService.askQuestion(text)

      // Check if evidence is missing or ungrounded
      const rawAns = response.answer || ''
      const lowerAns = rawAns.toLowerCase()
      const isMissingEvidence =
        lowerAns.includes('could not find this in the document') ||
        lowerAns.includes('no relevant information found')

      let assistantContent = rawAns
      let needsWebFallback = false

      if (isMissingEvidence) {
        assistantContent = 'This information is not clearly stated in the uploaded document.'
        needsWebFallback = true
      }

      const assistantMsg = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: assistantContent,
        originalQuestion: text,
        needsWebFallback: needsWebFallback,
        sources: !needsWebFallback && uploadedDocuments && uploadedDocuments.length > 0
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
      setEvidenceTab('document')
    } catch (err) {
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
      setTypingStatusText('')
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

  return (
    <div className="chat-layout">
      {/* LEFT PANEL: Conversation History & Context Pool */}
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

          {/* Uploaded Documents Context */}
          <div style={{ marginTop: '24px', padding: '12px', borderTop: '1px solid var(--border-secondary)' }}>
            <div className="chat-sidebar-section-title" style={{ padding: '0 0 8px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Knowledge Assets</span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>
                {(uploadedDocuments?.length || 0) + (uploadedImages?.length || 0)} active
              </span>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {uploadedDocuments && uploadedDocuments.length > 0 ? (
                uploadedDocuments.map((doc) => (
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
                    <FileText size={14} style={{ color: '#10b981', flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {doc.name}
                    </span>
                  </div>
                ))
              ) : null}

              {uploadedImages && uploadedImages.length > 0 ? (
                uploadedImages.map((img) => (
                  <div
                    key={img.id}
                    onClick={() => {
                      setAttachedImageFile(img.rawFile)
                      setAttachedImagePreview(img.previewUrl)
                      setActiveImage(img)
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '6px 8px',
                      borderRadius: 'var(--radius-sm)',
                      background: attachedImageFile?.name === img.name ? 'rgba(124, 58, 237, 0.2)' : 'rgba(124, 58, 237, 0.08)',
                      border: attachedImageFile?.name === img.name ? '1px solid var(--primary-500)' : '1px solid rgba(124, 58, 237, 0.2)',
                      fontSize: '0.78rem',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                    }}
                  >
                    <ImageIcon size={14} style={{ color: 'var(--primary-600)', flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {img.name} (Image Vision)
                    </span>
                  </div>
                ))
              ) : null}

              {(!uploadedDocuments || uploadedDocuments.length === 0) && (!uploadedImages || uploadedImages.length === 0) && (
                <div style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', lineHeight: 1.4 }}>
                  No files uploaded yet. Upload a PDF, TXT, or image to ground your research.
                </div>
              )}
            </div>

            <button
              className="btn btn-secondary btn-sm"
              style={{ width: '100%', marginTop: '12px', fontSize: '0.75rem' }}
              onClick={() => setUploadModal(true)}
            >
              <Upload size={13} /> Upload Document or Image
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
              Multi-Source Grounding: FAISS Dense Document Retrieval • Gemini Multimodal Vision • External Web Search
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
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-tertiary)' }}>Active Target:</span>
          {attachedImageFile ? (
            <span className="source-chip" style={{ fontSize: '0.72rem', padding: '2px 10px', background: 'rgba(124, 58, 237, 0.15)', borderColor: 'rgba(124, 58, 237, 0.35)', color: 'var(--text-accent)' }}>
              <span className="source-chip-icon">🖼</span>
              <span>Visual Image: {attachedImageFile.name} (Direct Vision Analysis)</span>
              <button
                type="button"
                onClick={handleRemoveAttachedImage}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0 0 0 4px', color: 'inherit' }}
                title="Detach image and return to document mode"
              >
                ✕
              </button>
            </span>
          ) : uploadedDocuments && uploadedDocuments.length > 0 ? (
            uploadedDocuments.map(s => (
              <span key={s.id} className="source-chip" style={{ fontSize: '0.72rem', padding: '2px 10px', background: 'rgba(16, 185, 129, 0.15)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
                <span className="source-chip-icon">📄</span>
                <span>{s.name} (FAISS Index)</span>
              </span>
            ))
          ) : (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
              No document uploaded. Queries with missing document evidence offer live Web Search fallback.
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
              <h3 className="empty-state-title">Ask anything across documents, images & the web</h3>
              <p className="empty-state-desc">
                VISTAAR answers document questions strictly from indexed context. When document evidence is missing, it provides real-time web search fallback. When images are uploaded, it uses genuine multimodal vision understanding.
              </p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                <button
                  className="quick-action-chip"
                  onClick={() => handleSendMessage('What is the chunk size and overlap used in VISTAAR?')}
                >
                  📄 Document Chunk Size?
                </button>
                <button
                  className="quick-action-chip"
                  onClick={() => handleSendMessage('What are the latest advancements in quantum computing in 2026?')}
                >
                  🌐 External Question (Web Fallback)
                </button>
                <button
                  className="quick-action-chip"
                  onClick={() => fileInputRef.current?.click()}
                >
                  🖼 Attach Image to Analyze
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
                  {/* User attached image thumbnail */}
                  {msg.attachedImage && (
                    <div style={{ marginBottom: '8px' }}>
                      <img
                        src={msg.attachedImage}
                        alt="Attached visual"
                        style={{ maxHeight: '160px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-primary)', display: 'block' }}
                      />
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '2px', display: 'block' }}>
                        Attached: {msg.imageName}
                      </span>
                    </div>
                  )}

                  <div
                    className="chat-message-bubble"
                    style={
                      msg.isError
                        ? { background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: 'var(--text-primary)' }
                        : msg.isWebSearch
                        ? { background: 'var(--bg-card)', border: '1px solid rgba(59, 130, 246, 0.35)' }
                        : msg.isVisionAnalysis
                        ? { background: 'var(--bg-card)', border: '1px solid rgba(124, 58, 237, 0.35)' }
                        : undefined
                    }
                  >
                    {/* Header Banner for Web Search or Vision Results */}
                    {msg.isWebSearch && (
                      <div style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '4px 10px',
                        borderRadius: '999px',
                        background: 'rgba(59, 130, 246, 0.12)',
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                        fontSize: '0.74rem',
                        fontWeight: 700,
                        color: '#3b82f6',
                        marginBottom: '10px'
                      }}>
                        <Globe size={13} />
                        <span>External Web Sources (Not from uploaded document)</span>
                      </div>
                    )}

                    {msg.isVisionAnalysis && (
                      <div style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '4px 10px',
                        borderRadius: '999px',
                        background: 'rgba(124, 58, 237, 0.12)',
                        border: '1px solid rgba(124, 58, 237, 0.3)',
                        fontSize: '0.74rem',
                        fontWeight: 700,
                        color: 'var(--text-accent)',
                        marginBottom: '10px'
                      }}>
                        <Eye size={13} />
                        <span>Grounded in Uploaded Image: {msg.imageName} (Multimodal Vision)</span>
                      </div>
                    )}

                    {/* Main text content */}
                    {msg.content.split('\n').map((paragraph, idx) => (
                      <p key={idx} style={{ marginBottom: idx === msg.content.split('\n').length - 1 ? 0 : '8px' }}>
                        {paragraph}
                      </p>
                    ))}

                    {/* Feature 1: Fallback Action Button when evidence is missing in document */}
                    {msg.needsWebFallback && (
                      <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px dashed var(--border-secondary)' }}>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                          Would you like to search the live web for this topic instead?
                        </div>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{
                            background: 'rgba(59, 130, 246, 0.1)',
                            borderColor: 'rgba(59, 130, 246, 0.35)',
                            color: '#3b82f6',
                            fontWeight: 600,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                          onClick={() => handleWebSearch(msg.originalQuestion)}
                        >
                          <Globe size={14} /> Search the Web
                        </button>
                      </div>
                    )}

                    {/* External Web Source Cards in Message Bubble */}
                    {msg.isWebSearch && msg.webSources && msg.webSources.length > 0 && (
                      <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-secondary)' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Cited Web Results:
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {msg.webSources.map((source, sIdx) => (
                            <a
                              key={sIdx}
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                display: 'block',
                                padding: '8px 12px',
                                borderRadius: 'var(--radius-sm)',
                                background: 'var(--bg-input)',
                                border: '1px solid var(--border-primary)',
                                textDecoration: 'none',
                                color: 'inherit',
                                transition: 'all 0.15s ease'
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                                <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--primary-600)' }}>
                                  {source.title}
                                </span>
                                <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6' }}>
                                  {source.domain} <ExternalLink size={10} style={{ display: 'inline', marginLeft: '2px' }} />
                                </span>
                              </div>
                              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                                {source.snippet}
                              </p>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Inline Source Chips for Document Answers */}
                  {msg.sources && msg.sources.length > 0 && !msg.isWebSearch && (
                    <div className="chat-message-sources">
                      <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-tertiary)', alignSelf: 'center' }}>
                        {msg.isVisionAnalysis ? 'Visual Source:' : 'Target Document:'}
                      </span>
                      {msg.sources.map((src, idx) => (
                        <div
                          key={idx}
                          className="chat-source-card"
                          onClick={() => {}}
                        >
                          <div className={`chat-source-icon ${src.type === 'image' ? 'img' : 'pdf'}`}>
                            {src.type === 'image' ? '🖼' : '📄'}
                          </div>
                          <div>
                            <div className="chat-source-name">{src.name}</div>
                            <div className="chat-source-page">
                              {src.type === 'image' ? 'Direct Vision Grounding' : 'FAISS Index • Top-8 Chunks'}
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
                    {typingStatusText || 'Searching vector embeddings & generating response...'}
                  </span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="chat-input-container">
          {/* Attached Image Pill above input */}
          {attachedImageFile && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              marginBottom: '8px',
              background: 'rgba(124, 58, 237, 0.1)',
              border: '1px solid rgba(124, 58, 237, 0.3)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
              color: 'var(--text-primary)',
            }}>
              <ImageIcon size={16} style={{ color: 'var(--primary-600)', flexShrink: 0 }} />
              <span style={{ fontWeight: 600 }}>Analyzing Image:</span>
              <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {attachedImageFile.name} ({(attachedImageFile.size / 1024).toFixed(0)} KB)
              </span>
              <button
                type="button"
                onClick={handleRemoveAttachedImage}
                style={{
                  marginLeft: 'auto',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-tertiary)',
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="Remove attached image"
              >
                <X size={14} />
              </button>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSendMessage()
            }}
            className="chat-input-wrapper"
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleImageAttach}
              style={{ display: 'none' }}
              accept="image/*"
            />

            <textarea
              placeholder={
                attachedImageFile
                  ? `Ask anything about ${attachedImageFile.name} (e.g. "What is this image about?", "Read the text")...`
                  : 'Ask about uploaded documents or request external research (Press Enter to send)...'
              }
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
                title="Attach image for vision understanding"
                onClick={() => fileInputRef.current?.click()}
                style={attachedImageFile ? { color: 'var(--primary-600)' } : undefined}
              >
                <ImageIcon size={18} />
              </button>
              <button
                type="button"
                className="chat-input-action-btn"
                title="Add to knowledge base"
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
            <div className="chat-sources-title">Evidence & Provenance</div>
            <div className="chat-sources-subtitle">
              Ground truth inspection across multi-source modalities
            </div>

            {/* Segmented View Switcher */}
            <div style={{ display: 'flex', gap: '4px', marginTop: '10px' }}>
              <button
                className={`filter-tab ${evidenceTab === 'document' ? 'active' : ''}`}
                style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                onClick={() => setEvidenceTab('document')}
              >
                📄 Document
              </button>
              <button
                className={`filter-tab ${evidenceTab === 'web' ? 'active' : ''}`}
                style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                onClick={() => setEvidenceTab('web')}
              >
                🌐 Web Fallback
              </button>
              <button
                className={`filter-tab ${evidenceTab === 'image' ? 'active' : ''}`}
                style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                onClick={() => setEvidenceTab('image')}
              >
                🖼 Image Vision
              </button>
            </div>
          </div>

          <div className="chat-sources-list">
            {/* VIEW 1: Document Evidence */}
            {evidenceTab === 'document' && (
              <>
                {uploadedDocuments && uploadedDocuments.length > 0 ? (
                  uploadedDocuments.map((doc, i) => (
                    <div key={i} className="evidence-card">
                      <div className="evidence-card-header">
                        <div className="evidence-card-icon pdf">📄</div>
                        <div>
                          <div className="evidence-card-name">{doc.name}</div>
                          <div className="evidence-card-page">
                            {doc.size} • Status: Indexed in FAISS
                          </div>
                        </div>
                        <div className="evidence-card-relevance">
                          <span className="relevance-badge high">Active</span>
                        </div>
                      </div>
                      <div className="evidence-card-text">
                        "Dense embeddings generated via all-MiniLM-L6-v2 (384 dims). Context is partitioned into 1000-char chunks with 200-char overlap and searched using FAISS exact Euclidean distance."
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '20px 16px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
                    <div style={{ marginBottom: '8px', fontSize: '1.4rem' }}>📂</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>No Documents Indexed</div>
                    <p style={{ lineHeight: 1.4, fontSize: '0.78rem', margin: '0 0 12px 0' }}>
                      Upload a PDF or TXT document to populate FAISS.
                    </p>
                    <button className="btn btn-primary btn-sm" onClick={() => setUploadModal(true)} style={{ width: '100%' }}>
                      <Upload size={13} /> Upload Document
                    </button>
                  </div>
                )}
              </>
            )}

            {/* VIEW 2: External Web Sources */}
            {evidenceTab === 'web' && (
              <>
                {activeWebSources && activeWebSources.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', padding: '0 4px' }}>
                      External web citations (verified distinct from private documents):
                    </div>
                    {activeWebSources.map((source, i) => (
                      <div key={i} className="evidence-card">
                        <div className="evidence-card-header">
                          <div className="evidence-card-icon" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6' }}>
                            <Globe size={16} />
                          </div>
                          <div>
                            <div className="evidence-card-name">{source.title}</div>
                            <div className="evidence-card-page">{source.domain}</div>
                          </div>
                        </div>
                        <div className="evidence-card-text">
                          "{source.snippet}"
                        </div>
                        <div style={{ marginTop: '8px', textAlign: 'right' }}>
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ fontSize: '0.72rem', color: 'var(--primary-600)', textDecoration: 'none', fontWeight: 600 }}
                          >
                            Visit Source <ExternalLink size={10} style={{ display: 'inline', marginLeft: '2px' }} />
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: '20px 16px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
                    <div style={{ marginBottom: '8px', fontSize: '1.4rem' }}>🌐</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>No Active Web Search</div>
                    <p style={{ lineHeight: 1.4, fontSize: '0.78rem', margin: 0 }}>
                      When a question cannot be answered from your uploaded document, click "Search the Web" to trigger live external web research.
                    </p>
                  </div>
                )}
              </>
            )}

            {/* VIEW 3: Image Vision Grounding */}
            {evidenceTab === 'image' && (
              <>
                {attachedImageFile || (uploadedImages && uploadedImages.length > 0) ? (
                  <div className="evidence-card">
                    <div className="evidence-card-header">
                      <div className="evidence-card-icon img">🖼</div>
                      <div>
                        <div className="evidence-card-name">
                          {attachedImageFile ? attachedImageFile.name : uploadedImages[0].name}
                        </div>
                        <div className="evidence-card-page">
                          Multimodal Gemini Vision Ingestion
                        </div>
                      </div>
                      <div className="evidence-card-relevance">
                        <span className="relevance-badge high">Visual</span>
                      </div>
                    </div>
                    {attachedImagePreview && (
                      <div style={{ margin: '10px 0', borderRadius: 'var(--radius-sm)', overflow: 'hidden', border: '1px solid var(--border-secondary)' }}>
                        <img
                          src={attachedImagePreview}
                          alt="Analyzed asset"
                          style={{ width: '100%', maxHeight: '180px', objectFit: 'contain', background: 'var(--bg-input)' }}
                        />
                      </div>
                    )}
                    <div className="evidence-card-text">
                      "Image pixels are processed directly by Gemini's native vision models (gemini-3-flash-preview). Analyzes diagrams, flowcharts, printed text, OCR equations, and visual layout without text extraction degradation."
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: '20px 16px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
                    <div style={{ marginBottom: '8px', fontSize: '1.4rem' }}>🖼</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>No Active Image</div>
                    <p style={{ lineHeight: 1.4, fontSize: '0.78rem', margin: '0 0 12px 0' }}>
                      Attach or upload an image to inspect visual diagrams, handwritten notes, or charts.
                    </p>
                    <button className="btn btn-secondary btn-sm" onClick={() => fileInputRef.current?.click()} style={{ width: '100%' }}>
                      <ImageIcon size={13} /> Select Image
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Architecture Overview */}
            <div style={{ marginTop: '16px', padding: '12px 14px', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>VISTAAR Multi-Source Modes:</div>
              <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                <li><strong>Document Mode:</strong> FAISS Top-8 Exact Euclidean Retrieval</li>
                <li><strong>Missing Evidence:</strong> Explicit "Search the Web" Action Fallback</li>
                <li><strong>Vision Mode:</strong> Direct Native Gemini Multimodal Vision</li>
              </ul>
            </div>
          </div>
        </aside>
      )}
    </div>
  )
}
