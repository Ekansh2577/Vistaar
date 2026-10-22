import { createContext, useContext, useState } from 'react'

const AppContext = createContext()

export function AppProvider({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [toasts, setToasts] = useState([])
  const [uploadModal, setUploadModal] = useState(false)

  const toggleSidebar = () => setSidebarOpen(prev => !prev)
  const closeSidebar = () => setSidebarOpen(false)

  const addToast = (message, type = 'info') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4000)
  }

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  return (
    <AppContext.Provider value={{
      sidebarOpen, toggleSidebar, closeSidebar,
      toasts, addToast, removeToast,
      uploadModal, setUploadModal,
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
