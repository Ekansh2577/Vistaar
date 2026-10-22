import { useState, useRef } from 'react'
import { X, Upload, FileText, Image as ImageIcon, CheckCircle2 } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function UploadModal() {
  const { uploadModal, setUploadModal, addToast } = useApp()
  const [activeTab, setActiveTab] = useState('all') // 'all', 'document', 'image'
  const [selectedFile, setSelectedFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef(null)

  if (!uploadModal) return null

  const handleClose = () => {
    if (isUploading) return
    setSelectedFile(null)
    setUploadProgress(0)
    setUploadModal(false)
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleUploadSubmit = () => {
    if (!selectedFile) return
    setIsUploading(true)
    setUploadProgress(15)

    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval)
          setTimeout(() => {
            setIsUploading(false)
            addToast(`Successfully processed "${selectedFile.name}" into knowledge space`, 'success')
            handleClose()
          }, 400)
          return 100
        }
        return prev + 25
      })
    }, 250)
  }

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Add to Knowledge Space</h3>
          <button className="modal-close" onClick={handleClose} disabled={isUploading}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <button
              className={`filter-tab ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
              type="button"
            >
              All Types
            </button>
            <button
              className={`filter-tab ${activeTab === 'document' ? 'active' : ''}`}
              onClick={() => setActiveTab('document')}
              type="button"
            >
              <FileText size={14} style={{ display: 'inline', marginRight: '4px' }} />
              Documents
            </button>
            <button
              className={`filter-tab ${activeTab === 'image' ? 'active' : ''}`}
              onClick={() => setActiveTab('image')}
              type="button"
            >
              <ImageIcon size={14} style={{ display: 'inline', marginRight: '4px' }} />
              Images
            </button>
          </div>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            style={{ display: 'none' }}
            accept={
              activeTab === 'image'
                ? 'image/*'
                : activeTab === 'document'
                ? '.pdf,.docx,.txt,.pptx'
                : '.pdf,.docx,.txt,.pptx,image/*'
            }
          />

          <div
            className="upload-area"
            style={{ borderColor: dragOver ? 'var(--primary-500)' : undefined }}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="upload-area-icon">
              <Upload />
            </div>
            <div className="upload-area-title">
              {selectedFile ? selectedFile.name : 'Click to upload or drag & drop'}
            </div>
            <div className="upload-area-desc">
              {selectedFile
                ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for vector indexing`
                : 'Upload PDFs, research papers, diagrams, handwritten notes or screenshots'}
            </div>
            <div className="upload-area-formats">
              Supported: PDF, DOCX, PPTX, TXT, PNG, JPG, WEBP (up to 50MB)
            </div>
          </div>

          {isUploading && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Extracting chunks & embeddings...</span>
                <span style={{ fontWeight: 600, color: 'var(--primary-600)' }}>{uploadProgress}%</span>
              </div>
              <div style={{ height: '6px', background: 'var(--bg-input)', borderRadius: '999px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${uploadProgress}%`,
                    background: 'var(--gradient-primary)',
                    transition: 'width 0.2s ease',
                  }}
                />
              </div>
            </div>
          )}

          <div style={{ marginTop: '20px', padding: '12px 14px', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <CheckCircle2 size={16} style={{ color: 'var(--primary-600)', flexShrink: 0 }} />
            <span>Files are encrypted, chunked semantically, and indexed for high-precision retrieval.</span>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={handleClose} disabled={isUploading}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleUploadSubmit}
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? 'Processing Knowledge...' : 'Upload & Index'}
          </button>
        </div>
      </div>
    </div>
  )
}
