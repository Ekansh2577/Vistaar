import { useState, useRef } from 'react'
import { X, Upload, FileText, Image as ImageIcon, CheckCircle2, AlertCircle } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { documentService } from '../services/api'

export default function UploadModal() {
  const { uploadModal, setUploadModal, addToast, addUploadedDocument, addUploadedImage, backendOnline } = useApp()
  const [activeTab, setActiveTab] = useState('all') // 'all', 'document', 'image'
  const [selectedFile, setSelectedFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadStageText, setUploadStageText] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef(null)

  if (!uploadModal) return null

  const handleClose = () => {
    if (isUploading) return
    setSelectedFile(null)
    setUploadProgress(0)
    setUploadStageText('')
    setErrorMessage('')
    setUploadModal(false)
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setErrorMessage('')
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      setSelectedFile(file)
      setErrorMessage('')
    }
  }

  const handleUploadSubmit = async () => {
    if (!selectedFile) return
    setIsUploading(true)
    setErrorMessage('')
    setUploadProgress(25)

    const isImage = selectedFile.type.startsWith('image/') || 
      selectedFile.name.match(/\.(png|jpe?g|webp|gif)$/i)

    if (isImage) {
      setUploadStageText('Preparing visual asset for Gemini vision analysis...')
      try {
        const previewUrl = URL.createObjectURL(selectedFile)
        const imgAsset = {
          id: `img-${Date.now()}`,
          name: selectedFile.name,
          type: 'image',
          size: `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB`,
          rawFile: selectedFile,
          previewUrl: previewUrl,
          uploadedAt: 'Just now',
          status: 'Ready for Vision Analysis',
          summary: 'Uploaded image ready for visual question answering, OCR reading, and diagram analysis.'
        }
        setUploadProgress(100)
        addUploadedImage(imgAsset)
        addToast(`Image "${selectedFile.name}" added to VISTAAR! Ask questions about it in Chat.`, 'success')
        setTimeout(() => {
          setIsUploading(false)
          handleClose()
        }, 500)
      } catch (err) {
        setIsUploading(false)
        setErrorMessage('Failed to load image.')
      }
      return
    }

    setUploadStageText('Transmitting file to backend ingestion endpoint...')

    try {
      setUploadProgress(50)
      setUploadStageText('Extracting text and triggering FAISS indexing task...')

      const result = await documentService.upload(selectedFile)

      setUploadProgress(100)
      setUploadStageText('Document accepted! Chunks and embeddings are being generated in the background.')

      addUploadedDocument(result.document)
      addToast(result.message || `Successfully uploaded "${selectedFile.name}"`, 'success')

      setTimeout(() => {
        setIsUploading(false)
        handleClose()
      }, 700)
    } catch (err) {
      setIsUploading(false)
      setUploadProgress(0)
      setErrorMessage(err.message || 'Upload failed. Please check the backend connection.')
      addToast(err.message || 'Upload failed', 'error')
    }
  }

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3 className="modal-title">Add to Knowledge Space</h3>
            {backendOnline === false && (
              <span style={{ fontSize: '0.72rem', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                <AlertCircle size={12} /> Backend server offline (FastAPI port 8000)
              </span>
            )}
          </div>
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
              Documents (PDF, TXT)
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
                ? '.pdf,.txt,.md'
                : '.pdf,.txt,.md,image/*'
            }
          />

          <div
            className="upload-area"
            style={{
              borderColor: errorMessage ? '#ef4444' : dragOver ? 'var(--primary-500)' : undefined,
              cursor: isUploading ? 'not-allowed' : 'pointer'
            }}
            onDragOver={(e) => {
              e.preventDefault()
              if (!isUploading) setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={isUploading ? undefined : handleDrop}
            onClick={() => !isUploading && fileInputRef.current?.click()}
          >
            <div className="upload-area-icon">
              <Upload />
            </div>
            <div className="upload-area-title">
              {selectedFile ? selectedFile.name : 'Click to select or drag & drop file'}
            </div>
            <div className="upload-area-desc">
              {selectedFile
                ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for backend vector indexing`
                : 'Upload PDFs, research papers, lecture notes, or TXT documents'}
            </div>
            <div className="upload-area-formats">
              Backend Supported: PDF, TXT, Plain Text (Extracted via PyPDF2 & indexed in FAISS)
            </div>
          </div>

          {errorMessage && (
            <div style={{
              marginTop: '12px',
              padding: '10px 14px',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              color: '#ef4444',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{errorMessage}</span>
            </div>
          )}

          {isUploading && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{uploadStageText}</span>
                <span style={{ fontWeight: 600, color: 'var(--primary-600)' }}>{uploadProgress}%</span>
              </div>
              <div style={{ height: '6px', background: 'var(--bg-input)', borderRadius: '999px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${uploadProgress}%`,
                    background: 'var(--gradient-primary)',
                    transition: 'width 0.25s ease',
                  }}
                />
              </div>
            </div>
          )}

          <div style={{ marginTop: '20px', padding: '12px 14px', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <CheckCircle2 size={16} style={{ color: 'var(--primary-600)', flexShrink: 0 }} />
            <span>Uploaded files are parsed by the backend, split into overlapping 1000-char chunks, embedded with all-MiniLM-L6-v2, and indexed into FAISS.</span>
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
            {isUploading ? 'Ingesting into FAISS...' : 'Upload & Index'}
          </button>
        </div>
      </div>
    </div>
  )
}
