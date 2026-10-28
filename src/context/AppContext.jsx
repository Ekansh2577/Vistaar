import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { checkBackendHealth } from '../services/api'
import { useAuth } from './AuthContext'

const AppContext = createContext()

export function AppProvider({ children }) {
  const { user } = useAuth()
  const ownerKey = user ? String(user.id) : 'guest'
  const [dataOwnerKey, setDataOwnerKey] = useState(ownerKey)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [toasts, setToasts] = useState([])
  const [uploadModal, setUploadModal] = useState(false)
  const [uploadedDocuments, setUploadedDocuments] = useState(() => {
    try {
      const saved = localStorage.getItem(`vistaar_session_docs_${ownerKey}`)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [uploadedImages, setUploadedImages] = useState(() => {
    try {
      const saved = localStorage.getItem(`vistaar_session_images_${ownerKey}`)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [activeImage, setActiveImage] = useState(null)
  const [backendOnline, setBackendOnline] = useState(null) // null = checking, true = online, false = offline

  useEffect(() => {
    try {
      const docs = localStorage.getItem(`vistaar_session_docs_${ownerKey}`)
      const images = localStorage.getItem(`vistaar_session_images_${ownerKey}`)
      setUploadedDocuments(docs ? JSON.parse(docs) : [])
      setUploadedImages(images ? JSON.parse(images) : [])
    } catch {
      setUploadedDocuments([])
      setUploadedImages([])
    }
    setActiveImage(null)
    setDataOwnerKey(ownerKey)
  }, [ownerKey])

  const toggleSidebar = () => setSidebarOpen(prev => !prev)
  const closeSidebar = () => setSidebarOpen(false)

  const addToast = (message, type = 'info') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4500)
  }

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  const addUploadedDocument = (doc) => {
    setUploadedDocuments(prev => {
      const updated = [doc, ...prev]
      try {
        localStorage.setItem(`vistaar_session_docs_${ownerKey}`, JSON.stringify(updated))
      } catch {
        // ignore
      }
      return updated
    })
  }

  const addUploadedImage = (img) => {
    setUploadedImages(prev => {
      const updated = [img, ...prev]
      try {
        localStorage.setItem(`vistaar_session_images_${ownerKey}`, JSON.stringify(updated))
      } catch {
        // ignore
      }
      return updated
    })
    setActiveImage(img)
  }

  const checkStatus = useCallback(async () => {
    const res = await checkBackendHealth()
    setBackendOnline(res.online)
    return res.online
  }, [])

  useEffect(() => {
    checkStatus()
    const interval = setInterval(checkStatus, 15000)
    return () => clearInterval(interval)
  }, [checkStatus])

  return (
    <AppContext.Provider value={{
      sidebarOpen, toggleSidebar, closeSidebar,
      toasts, addToast, removeToast,
      uploadModal, setUploadModal,
      uploadedDocuments, addUploadedDocument,
      uploadedImages, addUploadedImage,
      activeImage, setActiveImage,
      workspaceDataReady: dataOwnerKey === ownerKey,
      backendOnline, checkBackendStatus: checkStatus,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
