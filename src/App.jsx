import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { useApp } from './context/AppContext'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import UploadModal from './components/UploadModal'
import Toast from './components/Toast'

import Home from './pages/Home'
import KnowledgeSpace from './pages/KnowledgeSpace'
import Chat from './pages/Chat'
import Explore from './pages/Explore'
import KnowledgeGraphPage from './pages/KnowledgeGraphPage'
import Insights from './pages/Insights'
import Settings from './pages/Settings'
import DocumentViewerPage from './pages/DocumentViewerPage'
import ImageViewerPage from './pages/ImageViewerPage'
import AuthPage from './pages/AuthPage'
import './styles/identity.css'

function ProtectedWorkspace() {
  const { user, loading, authError, refreshSession } = useAuth()
  const { workspaceDataReady } = useApp()
  const location = useLocation()

  if (loading) return <main className="auth-page"><p>Checking your VISTAAR session…</p></main>
  if (authError) return <main className="auth-page"><p role="alert">{authError}</p><button className="auth-submit" onClick={() => refreshSession().catch(() => {})}>Retry</button></main>
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  if (!workspaceDataReady) return <main className="auth-page"><p>Loading your workspace…</p></main>

  return (
    <>
      <Sidebar />
      <div className="app-main">
        <Topbar />
        <div className="app-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/knowledge" element={<KnowledgeSpace />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/explore/:id" element={<Explore />} />
            <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/viewer/doc/:id" element={<DocumentViewerPage />} />
            <Route path="/viewer/image/:id" element={<ImageViewerPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
      <UploadModal />
      <Toast />
    </>
  )
}

function AppRoutes() {
  const location = useLocation()
  const isAuthPage = ['/login', '/signup', '/forgot-password', '/reset-password'].includes(location.pathname)

  return (
      <div className={`app-layout ${isAuthPage ? 'auth-layout' : ''}`}>
        {isAuthPage ? <Routes>
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/signup" element={<AuthPage mode="signup" />} />
          <Route path="/forgot-password" element={<AuthPage mode="forgot-password" />} />
          <Route path="/reset-password" element={<AuthPage mode="reset-password" />} />
        </Routes> : <>
        <ProtectedWorkspace />
        </>}
      </div>
  )
}

export default function App() {
  return <AppRoutes />
}
