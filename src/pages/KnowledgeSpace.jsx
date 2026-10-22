import { useState, useMemo } from 'react'
import { Search, Plus, Filter, FileText, Image as ImageIcon, BookOpen } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { mockDocuments, mockImages } from '../data/mockData'
import FileCard from '../components/FileCard'
import EmptyState from '../components/EmptyState'

export default function KnowledgeSpace() {
  const [filter, setFilter] = useState('all') // 'all' | 'documents' | 'images'
  const [searchQuery, setSearchQuery] = useState('')
  const { setUploadModal } = useApp()

  const allFiles = useMemo(() => {
    return [...mockDocuments, ...mockImages]
  }, [])

  const filteredFiles = useMemo(() => {
    return allFiles.filter((file) => {
      // Type filter
      if (filter === 'documents' && file.type === 'image') return false
      if (filter === 'images' && file.type !== 'image') return false

      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        const matchesName = file.name.toLowerCase().includes(q)
        const matchesTags = file.tags?.some((t) => t.toLowerCase().includes(q))
        const matchesSummary = file.summary?.toLowerCase().includes(q)
        return matchesName || matchesTags || matchesSummary
      }
      return true
    })
  }, [allFiles, filter, searchQuery])

  const docCount = mockDocuments.length
  const imgCount = mockImages.length

  return (
    <div className="page">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="page-title">My Knowledge Space</h1>
          <p className="page-subtitle">Your documents and images, organized, indexed and ready to explore.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setUploadModal(true)}>
          <Plus size={18} /> Upload Knowledge
        </button>
      </div>

      {/* Controls Bar */}
      <div className="controls-bar">
        <div className="controls-left">
          <div className="filter-tabs">
            <button
              className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All Files ({allFiles.length})
            </button>
            <button
              className={`filter-tab ${filter === 'documents' ? 'active' : ''}`}
              onClick={() => setFilter('documents')}
            >
              <FileText size={14} style={{ display: 'inline', marginRight: '5px' }} />
              Documents ({docCount})
            </button>
            <button
              className={`filter-tab ${filter === 'images' ? 'active' : ''}`}
              onClick={() => setFilter('images')}
            >
              <ImageIcon size={14} style={{ display: 'inline', marginRight: '5px' }} />
              Images ({imgCount})
            </button>
          </div>
        </div>

        <div className="controls-right">
          <div className="search-input-group">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search by title, tag, or topic..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Files Grid or Empty State */}
      {filteredFiles.length > 0 ? (
        <div className="files-grid">
          {filteredFiles.map((file) => (
            <FileCard key={file.id} file={file} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={filter === 'images' ? '🖼' : '📄'}
          title={searchQuery ? 'No matching knowledge found' : filter === 'images' ? 'No images yet' : 'No documents yet'}
          description={
            searchQuery
              ? `No documents or images matched "${searchQuery}". Try different keywords.`
              : filter === 'images'
              ? 'Give VISTAAR something visual to understand — upload diagrams, notes or charts.'
              : 'Your knowledge space is waiting. Upload PDFs, research papers, or docs.'
          }
          action={searchQuery ? 'Clear Search' : 'Upload File'}
          onAction={searchQuery ? () => setSearchQuery('') : () => setUploadModal(true)}
        />
      )}
    </div>
  )
}
