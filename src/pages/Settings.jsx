import { useState } from 'react'
import {
  Sliders, User, Moon, Shield, Sparkles, Check, Database, Eye, Save
} from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { useApp } from '../context/AppContext'
import ThemeToggle from '../components/ThemeToggle'

export default function Settings() {
  const { theme, setTheme } = useTheme()
  const { addToast } = useApp()

  const [activeTab, setActiveTab] = useState('appearance')
  const [streamChat, setStreamChat] = useState(true)
  const [showConfidence, setShowConfidence] = useState(true)
  const [multimodalOcr, setMultimodalOcr] = useState(true)
  const [hybridSearch, setHybridSearch] = useState(true)
  const [userName, setUserName] = useState('Ekansh')
  const [userEmail, setUserEmail] = useState('ekansh@vistaar.ai')

  const handleSave = () => {
    addToast('Preferences saved successfully', 'success')
  }

  return (
    <div className="page">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Settings & Preferences</h1>
          <p className="page-subtitle">Configure theme appearance, vector indexing, and research workspace behavior.</p>
        </div>
        <button className="btn btn-primary" onClick={handleSave}>
          <Save size={16} /> Save Changes
        </button>
      </div>

      <div className="settings-layout">
        {/* Navigation Sidebar */}
        <div className="settings-nav">
          <div
            className={`settings-nav-item ${activeTab === 'appearance' ? 'active' : ''}`}
            onClick={() => setActiveTab('appearance')}
          >
            <Moon />
            <span>Appearance & Theme</span>
          </div>

          <div
            className={`settings-nav-item ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            <User />
            <span>Profile & Account</span>
          </div>

          <div
            className={`settings-nav-item ${activeTab === 'knowledge' ? 'active' : ''}`}
            onClick={() => setActiveTab('knowledge')}
          >
            <Database />
            <span>RAG & Knowledge</span>
          </div>

          <div
            className={`settings-nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <Sliders />
            <span>Chat & Evidence</span>
          </div>
        </div>

        {/* Content Panel */}
        <div>
          {/* Appearance Section */}
          {activeTab === 'appearance' && (
            <div className="settings-section">
              <div className="settings-section-title">Visual Appearance</div>
              <div className="settings-section-desc">
                VISTAAR's "Beyond VISTAAR" theme is not a simple light/dark switch — it's two distinct visual philosophies.
              </div>

              {/* Beyond VISTAAR Experience Cards */}
              <div style={{ marginTop: '20px', marginBottom: '24px' }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '14px',
                }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-accent)' }}>
                    ✦ BEYOND VISTAAR
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>— Choose your experience</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  {/* Enlighten Mode Card */}
                  <div
                    onClick={() => setTheme('enlighten')}
                    style={{
                      padding: '18px 16px',
                      borderRadius: '14px',
                      border: theme === 'enlighten'
                        ? '2px solid #f59e0b'
                        : '1.5px solid var(--border-primary)',
                      background: theme === 'enlighten'
                        ? 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 50%, #f5f3ff 100%)'
                        : 'var(--bg-card)',
                      cursor: 'pointer',
                      transition: 'all 250ms ease',
                      boxShadow: theme === 'enlighten'
                        ? '0 4px 20px rgba(245,158,11,0.15), 0 2px 8px rgba(124,58,237,0.06)'
                        : 'var(--shadow-sm)',
                      position: 'relative',
                      overflow: 'hidden',
                    }}
                  >
                    {/* Preview strip */}
                    <div style={{
                      height: '48px',
                      borderRadius: '8px',
                      background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 40%, #ddd6fe 100%)',
                      marginBottom: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '22px',
                    }}>
                      ☀️
                    </div>
                    <div style={{ fontWeight: 700, fontSize: '0.92rem', color: theme === 'enlighten' ? '#78350f' : 'var(--text-primary)', marginBottom: '4px' }}>
                      ENLIGHTEN
                    </div>
                    <div style={{ fontSize: '0.78rem', color: theme === 'enlighten' ? '#92400e' : 'var(--text-tertiary)', lineHeight: 1.45 }}>
                      Clear, bright and expansive.
                    </div>
                    {theme === 'enlighten' && (
                      <div style={{
                        position: 'absolute',
                        top: '10px',
                        right: '10px',
                        width: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        background: '#f59e0b',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '11px',
                        color: 'white',
                        fontWeight: 700,
                      }}>
                        ✓
                      </div>
                    )}
                  </div>

                  {/* Explore Mode Card */}
                  <div
                    onClick={() => setTheme('explore')}
                    style={{
                      padding: '18px 16px',
                      borderRadius: '14px',
                      border: theme === 'explore'
                        ? '2px solid #7c3aed'
                        : '1.5px solid var(--border-primary)',
                      background: theme === 'explore'
                        ? 'linear-gradient(135deg, #080c18 0%, #11082e 50%, #070d1f 100%)'
                        : 'var(--bg-card)',
                      cursor: 'pointer',
                      transition: 'all 250ms ease',
                      boxShadow: theme === 'explore'
                        ? '0 4px 20px rgba(124,58,237,0.3), 0 0 30px rgba(59,130,246,0.08)'
                        : 'var(--shadow-sm)',
                      position: 'relative',
                      overflow: 'hidden',
                    }}
                  >
                    {/* Preview strip */}
                    <div style={{
                      height: '48px',
                      borderRadius: '8px',
                      background: 'linear-gradient(135deg, #060912 0%, #11082e 50%, #05091c 100%)',
                      marginBottom: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '22px',
                      border: '1px solid rgba(124,58,237,0.3)',
                    }}>
                      🌙
                    </div>
                    <div style={{ fontWeight: 700, fontSize: '0.92rem', color: theme === 'explore' ? '#c4b5fd' : 'var(--text-primary)', marginBottom: '4px' }}>
                      EXPLORE
                    </div>
                    <div style={{ fontSize: '0.78rem', color: theme === 'explore' ? '#a78bfa' : 'var(--text-tertiary)', lineHeight: 1.45 }}>
                      Deep, immersive and curious.
                    </div>
                    {theme === 'explore' && (
                      <div style={{
                        position: 'absolute',
                        top: '10px',
                        right: '10px',
                        width: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        background: '#7c3aed',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '11px',
                        color: 'white',
                        fontWeight: 700,
                      }}>
                        ✓
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="settings-group">
                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Interface Theme</div>
                    <div className="settings-item-desc">Quick toggle between Enlighten and Explore modes</div>
                  </div>
                  <ThemeToggle />
                </div>

                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Fluid Animations</div>
                    <div className="settings-item-desc">Enable smooth micro-interactions and node transitions</div>
                  </div>
                  <div className="toggle-switch active" />
                </div>
              </div>
            </div>
          )}


          {/* Profile Section */}
          {activeTab === 'profile' && (
            <div className="settings-section">
              <div className="settings-section-title">Researcher Profile</div>
              <div className="settings-section-desc">Manage your workspace identity and credentials.</div>

              <div className="settings-group">
                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Full Name</div>
                    <div className="settings-item-desc">Displayed on conversations and exports</div>
                  </div>
                  <input
                    type="text"
                    value={userName}
                    onChange={(e) => setUserName(e.target.value)}
                    style={{
                      padding: '8px 12px',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>

                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Email Address</div>
                    <div className="settings-item-desc">Used for workspace notifications</div>
                  </div>
                  <input
                    type="email"
                    value={userEmail}
                    onChange={(e) => setUserEmail(e.target.value)}
                    style={{
                      padding: '8px 12px',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>

                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Role & Permissions</div>
                    <div className="settings-item-desc">Current workspace privileges</div>
                  </div>
                  <span style={{ fontSize: '0.8rem', padding: '4px 12px', background: 'var(--primary-50)', color: 'var(--primary-700)', borderRadius: '999px', fontWeight: 600 }}>
                    Workspace Administrator
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Knowledge & RAG Indexing Section */}
          {activeTab === 'knowledge' && (
            <div className="settings-section">
              <div className="settings-section-title">Knowledge & Vector Indexing</div>
              <div className="settings-section-desc">Fine-tune chunking, embeddings, and multi-modal OCR ingestion parameters.</div>

              <div className="settings-group">
                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Multi-modal Visual OCR</div>
                    <div className="settings-item-desc">Automatically detect handwritten text, algorithms, and diagram structures in uploaded images</div>
                  </div>
                  <div
                    className={`toggle-switch ${multimodalOcr ? 'active' : ''}`}
                    onClick={() => setMultimodalOcr(!multimodalOcr)}
                  />
                </div>

                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Hybrid Dense + Sparse Search</div>
                    <div className="settings-item-desc">Combine FAISS dense vector cosine distance with BM25 keyword matching for optimal recall</div>
                  </div>
                  <div
                    className={`toggle-switch ${hybridSearch ? 'active' : ''}`}
                    onClick={() => setHybridSearch(!hybridSearch)}
                  />
                </div>

                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Semantic Chunk Size</div>
                    <div className="settings-item-desc">Default window size per vector representation</div>
                  </div>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--primary-600)' }}>
                    512 tokens (overlapping 64)
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Chat & Evidence Preferences */}
          {activeTab === 'chat' && (
            <div className="settings-section">
              <div className="settings-section-title">Research Workspace Behavior</div>
              <div className="settings-section-desc">Configure how responses and grounding citations are surfaced in the chat environment.</div>

              <div className="settings-group">
                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Show Grounding Confidence Scores</div>
                    <div className="settings-item-desc">Display similarity percentage (e.g., 85% relevant) next to cited evidence</div>
                  </div>
                  <div
                    className={`toggle-switch ${showConfidence ? 'active' : ''}`}
                    onClick={() => setShowConfidence(!showConfidence)}
                  />
                </div>

                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Simulated Fast Streaming</div>
                    <div className="settings-item-desc">Generate completion tokens with progressive typing cadence</div>
                  </div>
                  <div
                    className={`toggle-switch ${streamChat ? 'active' : ''}`}
                    onClick={() => setStreamChat(!streamChat)}
                  />
                </div>

                <div className="settings-item">
                  <div>
                    <div className="settings-item-label">Evidence Verification Panel</div>
                    <div className="settings-item-desc">Default visibility of the right-hand evidence drawer on desktop viewports</div>
                  </div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Expanded by Default
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
