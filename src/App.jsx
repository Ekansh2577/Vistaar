import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
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
      </div>
    </BrowserRouter>
  )
}
