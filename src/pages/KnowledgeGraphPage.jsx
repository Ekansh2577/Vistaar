import { useState, useMemo, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  GitBranch, Search, Sparkles, X, ArrowRight, ZoomIn, ZoomOut,
  Maximize2, RotateCcw, ExternalLink, HelpCircle, Layers, CheckCircle2
} from 'lucide-react'
import { mockKnowledgeGraph } from '../data/mockData'
import { knowledgeGraphService } from '../services/api'

// Deterministic balanced coordinates (1000x700 viewBox) designed for radial clarity
const BALANCED_COORDINATES = {
  rag: { x: 500, y: 350 },
  // Primary concentric anchors
  retrieval: { x: 310, y: 230 },
  generation: { x: 690, y: 230 },
  embeddings: { x: 330, y: 480 },
  vectordb: { x: 670, y: 480 },
  llm: { x: 740, y: 350 },
  // Retrieval cluster satellites
  semantic: { x: 170, y: 150 },
  bm25: { x: 160, y: 270 },
  faiss: { x: 240, y: 340 },
  dense: { x: 160, y: 390 },
  // Embeddings cluster satellites
  similarity: { x: 230, y: 570 },
  textEmbed: { x: 360, y: 610 },
  chunking: { x: 490, y: 580 },
  // Generation & LLM cluster satellites
  prompting: { x: 730, y: 110 },
  finetuning: { x: 840, y: 260 },
}

export default function KnowledgeGraphPage() {
  const navigate = useNavigate()
  const [graphData, setGraphData] = useState(mockKnowledgeGraph)
  const [selectedNodeId, setSelectedNodeId] = useState('rag')
  const [hoveredNodeId, setHoveredNodeId] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Pan and Zoom transform state
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  const canvasRef = useRef(null)

  // Fetch graph from service if available, fallback to mockData
  useEffect(() => {
    let isMounted = true
    knowledgeGraphService
      .getGraph()
      .then((data) => {
        if (isMounted && data) setGraphData(data)
      })
      .catch((err) => {
        console.error('Failed to fetch knowledge graph:', err)
      })
    return () => {
      isMounted = false
    }
  }, [])

  // Currently selected node data
  const selectedNode =
    graphData.nodes.find((n) => n.id === selectedNodeId) || graphData.nodes[0]

  // Calculate directly connected neighbor IDs
  const connectedNodeIds = useMemo(() => {
    const ids = new Set()
    graphData.edges.forEach((edge) => {
      if (edge.from === selectedNodeId) ids.add(edge.to)
      if (edge.to === selectedNodeId) ids.add(edge.from)
    })
    return ids
  }, [selectedNodeId, graphData.edges])

  // Related node objects
  const relatedNodes = useMemo(() => {
    return graphData.nodes.filter((n) => connectedNodeIds.has(n.id))
  }, [connectedNodeIds, graphData.nodes])

  // Filtered matching nodes by search
  const matchingNodeIds = useMemo(() => {
    if (!searchQuery.trim()) return null
    const q = searchQuery.toLowerCase()
    return new Set(
      graphData.nodes
        .filter(
          (n) =>
            n.label.toLowerCase().includes(q) ||
            n.description?.toLowerCase().includes(q)
        )
        .map((n) => n.id)
    )
  }, [searchQuery, graphData.nodes])

  // Auto-select first search result if not already matched
  useEffect(() => {
    if (matchingNodeIds && matchingNodeIds.size > 0) {
      if (!matchingNodeIds.has(selectedNodeId)) {
        const firstMatch = Array.from(matchingNodeIds)[0]
        setSelectedNodeId(firstMatch)
      }
    }
  }, [matchingNodeIds])

  // Pan controls
  const handleMouseDown = (e) => {
    if (e.target.closest('.kg-interactive-node')) return
    setIsDragging(true)
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }

  const handleMouseMove = (e) => {
    if (!isDragging) return
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const handleWheel = (e) => {
    e.preventDefault()
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92
    setZoom((prev) => Math.min(2.0, Math.max(0.65, prev * zoomFactor)))
  }

  // Zoom controls
  const handleZoomIn = () => setZoom((z) => Math.min(2.0, +(z + 0.15).toFixed(2)))
  const handleZoomOut = () => setZoom((z) => Math.max(0.65, +(z - 0.15).toFixed(2)))
  const handleResetView = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }
  const handleFitToView = () => {
    setZoom(0.92)
    setPan({ x: 0, y: 0 })
  }

  const handleAskInChat = (conceptName) => {
    navigate(
      `/chat?q=${encodeURIComponent(
        `Explain how ${conceptName} operates within our RAG knowledge architecture`
      )}`
    )
  }

  // Node position helper with balanced coordinates
  const getNodePos = (node) => {
    return (
      BALANCED_COORDINATES[node.id] || {
        x: (node.x / 100) * 1000,
        y: (node.y / 100) * 700,
      }
    )
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1fr) 340px',
        height: 'calc(100vh - var(--topbar-height))',
        overflow: 'hidden',
        background: 'var(--bg-primary)',
      }}
      className="kg-workspace-layout"
    >
      {/* LEFT / CENTER: Dedicated Graph Canvas Area */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          background: 'var(--bg-secondary)',
          position: 'relative',
        }}
        className="kg-canvas-wrapper"
      >
        {/* Graph Header Toolbar */}
        <div
          style={{
            padding: '14px 24px',
            borderBottom: '1px solid var(--border-primary)',
            background: 'var(--bg-card)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            zIndex: 15,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(124, 58, 237, 0.15)',
                color: 'var(--primary-400)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <GitBranch size={20} />
            </div>
            <div>
              <h1
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: '1.1rem',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  margin: 0,
                }}
              >
                Semantic Concept Graph
              </h1>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', margin: 0 }}>
                Synthesized concept relationships across indexed documents & images
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Real Search Input */}
            <div className="search-input-group" style={{ minWidth: '220px', padding: '6px 14px' }}>
              <Search size={14} />
              <input
                type="text"
                placeholder="Search concepts (e.g. FAISS, BM25)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  style={{ color: 'var(--text-tertiary)', padding: '2px', cursor: 'pointer' }}
                >
                  <X size={12} />
                </button>
              )}
            </div>

            {/* Viewport Zoom & Pan Controls */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--radius-md)',
                padding: '2px',
              }}
            >
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleZoomIn}
                title="Zoom In"
                style={{ padding: '6px 8px' }}
              >
                <ZoomIn size={15} />
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleZoomOut}
                title="Zoom Out"
                style={{ padding: '6px 8px' }}
              >
                <ZoomOut size={15} />
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleFitToView}
                title="Fit to View"
                style={{ padding: '6px 8px' }}
              >
                <Maximize2 size={15} />
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleResetView}
                title="Reset View"
                style={{ padding: '6px 8px' }}
              >
                <RotateCcw size={15} />
              </button>
            </div>
          </div>
        </div>

        {/* Dedicated Canvas Viewport */}
        <div
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
          style={{
            flex: 1,
            position: 'relative',
            overflow: 'hidden',
            cursor: isDragging ? 'grabbing' : 'grab',
            userSelect: 'none',
          }}
        >
          {/* Subtle Canvas Dot Grid Background */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundImage: 'radial-gradient(var(--border-primary) 1px, transparent 1px)',
              backgroundSize: '24px 24px',
              opacity: 0.5,
              pointerEvents: 'none',
            }}
          />

          {/* Hierarchy Legend */}
          <div
            className="kg-legend"
            style={{
              position: 'absolute',
              bottom: '20px',
              left: '20px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
              boxShadow: 'var(--shadow-md)',
              zIndex: 10,
              pointerEvents: 'auto',
            }}
          >
            <div
              style={{
                fontSize: '0.7rem',
                fontWeight: 600,
                color: 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '8px',
              }}
            >
              Graph Hierarchy
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--gradient-primary)' }} />
                <span>Core Anchor (RAG)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary-400)' }} />
                <span>Primary Concept</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--indigo-400)' }} />
                <span>Secondary Technique</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--gray-400)' }} />
                <span>Tertiary Component</span>
              </div>
            </div>
          </div>

          {/* SVG & Node Scene Scaled and Panned */}
          <div
            style={{
              position: 'absolute',
              width: '1000px',
              height: '700px',
              left: '50%',
              top: '50%',
              marginLeft: '-500px',
              marginTop: '-350px',
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: '500px 350px',
              transition: isDragging ? 'none' : 'transform 0.15s ease-out',
            }}
          >
            {/* SVG Edges Layer */}
            <svg
              viewBox="0 0 1000 700"
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
              }}
            >
              <defs>
                <linearGradient id="edgeGlowPrimary" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity="0.9" />
                </linearGradient>
              </defs>

              {graphData.edges.map((edge, idx) => {
                const fromNode = graphData.nodes.find((n) => n.id === edge.from)
                const toNode = graphData.nodes.find((n) => n.id === edge.to)
                if (!fromNode || !toNode) return null

                const fromPos = getNodePos(fromNode)
                const toPos = getNodePos(toNode)

                const isConnectedToSelected =
                  fromNode.id === selectedNodeId || toNode.id === selectedNodeId
                const isHoveredEdge =
                  hoveredNodeId &&
                  (fromNode.id === hoveredNodeId || toNode.id === hoveredNodeId)

                const isPrimaryEdge =
                  fromNode.id === 'rag' || toNode.id === 'rag'

                let strokeColor = isPrimaryEdge
                  ? 'var(--primary-400)'
                  : 'var(--border-primary)'
                let strokeWidth = isPrimaryEdge ? 2 : 1.3
                let opacity = 0.45

                if (isConnectedToSelected || isHoveredEdge) {
                  strokeColor = 'url(#edgeGlowPrimary)'
                  strokeWidth = 2.8
                  opacity = 0.95
                } else if (selectedNodeId) {
                  opacity = 0.15
                }

                return (
                  <line
                    key={idx}
                    x1={fromPos.x}
                    y1={fromPos.y}
                    x2={toPos.x}
                    y2={toPos.y}
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    opacity={opacity}
                    strokeDasharray={isConnectedToSelected ? 'none' : isPrimaryEdge ? 'none' : '4,4'}
                    style={{ transition: 'stroke 0.25s ease, opacity 0.25s ease' }}
                  />
                )
              })}
            </svg>

            {/* Interactive Nodes Layer */}
            {graphData.nodes.map((node) => {
              const pos = getNodePos(node)
              const isSelected = node.id === selectedNodeId
              const isConnected = connectedNodeIds.has(node.id)
              const isHovered = hoveredNodeId === node.id
              const isMatch = matchingNodeIds ? matchingNodeIds.has(node.id) : true

              // Node size based on hierarchy
              const baseSize =
                node.type === 'core'
                  ? 94
                  : node.type === 'primary'
                  ? 76
                  : node.type === 'secondary'
                  ? 62
                  : 52

              // Determine opacity based on selection state
              let opacity = 1
              if (selectedNodeId) {
                if (isSelected || isConnected) {
                  opacity = 1
                } else {
                  opacity = isMatch ? 0.35 : 0.18
                }
              }

              return (
                <div
                  key={node.id}
                  className={`kg-interactive-node kg-node ${node.type}`}
                  onClick={() => setSelectedNodeId(node.id)}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  style={{
                    position: 'absolute',
                    left: `${pos.x}px`,
                    top: `${pos.y}px`,
                    width: `${baseSize}px`,
                    height: `${baseSize}px`,
                    transform: `translate(-50%, -50%) scale(${
                      isSelected ? 1.08 : isHovered ? 1.05 : 1
                    })`,
                    zIndex: isSelected ? 30 : isConnected ? 20 : isHovered ? 25 : 10,
                    opacity,
                    cursor: 'pointer',
                    transition:
                      'transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.25s ease',
                  }}
                >
                  <div
                    className="kg-node-circle"
                    style={{
                      border: isSelected
                        ? '3px solid #c4b5fd'
                        : isConnected
                        ? '2px solid var(--primary-400)'
                        : isMatch && searchQuery
                        ? '2px solid var(--success)'
                        : undefined,
                      boxShadow: isSelected
                        ? '0 0 24px rgba(139, 92, 246, 0.55), 0 0 8px rgba(124, 58, 237, 0.4)'
                        : isConnected
                        ? '0 0 14px rgba(139, 92, 246, 0.25)'
                        : undefined,
                      fontSize:
                        node.type === 'core'
                          ? '1.05rem'
                          : node.type === 'primary'
                          ? '0.8rem'
                          : '0.72rem',
                    }}
                  >
                    <span style={{ whiteSpace: 'pre-line', pointerEvents: 'none' }}>
                      {node.label}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* RIGHT: Dedicated Entity Details Sidebar Column (NO OVERLAP) */}
      <aside
        style={{
          width: '340px',
          background: 'var(--bg-card)',
          borderLeft: '1px solid var(--border-primary)',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
          zIndex: 15,
        }}
        className="kg-details-sidebar"
      >
        {/* Panel Header */}
        <div
          style={{
            padding: '20px',
            borderBottom: '1px solid var(--border-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                color: 'var(--text-accent)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              Entity Details
            </span>
            <span
              style={{
                fontSize: '0.7rem',
                padding: '2px 8px',
                background: 'var(--primary-50)',
                color: 'var(--primary-700)',
                borderRadius: '999px',
                fontWeight: 600,
              }}
            >
              {selectedNode?.docs || 1} Documents
            </span>
          </div>

          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '1.35rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              margin: '0 0 4px',
            }}
          >
            {selectedNode?.label.replace('\n', ' ')}
          </h2>

          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background:
                  selectedNode?.type === 'core'
                    ? 'var(--primary-500)'
                    : selectedNode?.type === 'primary'
                    ? 'var(--indigo-500)'
                    : 'var(--gray-400)',
              }}
            />
            {selectedNode?.type === 'core'
              ? 'Core Architectural Anchor'
              : selectedNode?.type === 'primary'
              ? 'Primary Component'
              : selectedNode?.type === 'secondary'
              ? 'Retrieval & Indexing Technique'
              : 'Sub-component Element'}
          </div>
        </div>

        {/* Panel Body */}
        <div style={{ padding: '20px', flex: 1, display: 'flex', flexDirection: 'column', gap: '22px' }}>
          {/* Description */}
          <div>
            <div
              style={{
                fontSize: '0.74rem',
                fontWeight: 600,
                color: 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '8px',
              }}
            >
              Description
            </div>
            <p
              style={{
                fontSize: '0.86rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.65,
                background: 'var(--bg-input)',
                padding: '12px 14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-secondary)',
                margin: 0,
              }}
            >
              {selectedNode?.description ||
                'Semantic concept mapped across vector database indices and retrieval chunks.'}
            </p>
          </div>

          {/* Related Concepts */}
          <div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '10px',
              }}
            >
              <div
                style={{
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Directly Related Concepts ({relatedNodes.length})
              </div>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {relatedNodes.map((rel) => (
                <button
                  key={rel.id}
                  onClick={() => setSelectedNodeId(rel.id)}
                  className="kg-info-tag"
                  style={{
                    border: '1px solid var(--border-primary)',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                  }}
                  title={`Focus on ${rel.label.replace('\n', ' ')}`}
                >
                  {rel.label.replace('\n', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Grounding Context */}
          <div
            style={{
              padding: '14px',
              background: 'rgba(124, 58, 237, 0.08)',
              border: '1px solid rgba(139, 92, 246, 0.25)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-accent)', marginBottom: '4px' }}>
              <CheckCircle2 size={14} /> Grounded Association
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
              This entity is cross-indexed across RAG research documentation and architecture diagrams.
            </p>
          </div>

          {/* Action Buttons */}
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              className="btn btn-primary"
              style={{ width: '100%' }}
              onClick={() => handleAskInChat(selectedNode?.label.replace('\n', ' '))}
            >
              <Sparkles size={15} /> Ask in Research Chat
            </button>

            <button
              className="btn btn-secondary btn-sm"
              style={{ width: '100%' }}
              onClick={() => navigate('/knowledge')}
            >
              <Layers size={14} /> View Related Documents
            </button>
          </div>
        </div>
      </aside>
    </div>
  )
}
