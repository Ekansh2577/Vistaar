import { useNavigate } from 'react-router-dom'
import {
  BarChart3, FileText, Image as ImageIcon, MessageSquare, Search,
  TrendingUp, Clock, CheckCircle2, ArrowRight
} from 'lucide-react'
import { mockInsights } from '../data/mockData'

export default function Insights() {
  const navigate = useNavigate()

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Workspace Insights & Analytics</h1>
        <p className="page-subtitle">Telemetry on retrieval accuracy, knowledge coverage, and inquiry patterns.</p>
      </div>

      {/* Top Stats Cards */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon purple">
            <FileText />
          </div>
          <div>
            <div className="stat-value">{mockInsights.totalDocuments}</div>
            <div className="stat-label">Indexed Documents</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">
            <ImageIcon />
          </div>
          <div>
            <div className="stat-value">{mockInsights.totalImages}</div>
            <div className="stat-label">Visual Knowledge Assets</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon blue">
            <MessageSquare />
          </div>
          <div>
            <div className="stat-value">{mockInsights.totalQuestions}</div>
            <div className="stat-label">Questions Answered</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon amber">
            <TrendingUp />
          </div>
          <div>
            <div className="stat-value">{mockInsights.keyTopics}</div>
            <div className="stat-label">Semantic Chunks Mapped</div>
          </div>
        </div>
      </div>

      {/* 2x2 Grid of Detailed Insights */}
      <div className="insights-grid">
        {/* Most Used Topics */}
        <div className="insight-card">
          <div className="insight-card-header">
            <div className="insight-card-title">Top Knowledge Domains</div>
            <span className="insight-card-badge">Query Frequency</span>
          </div>

          <div className="topic-bars">
            {mockInsights.mostUsedTopics.map((topic, i) => {
              const maxCount = mockInsights.mostUsedTopics[0].count
              const percentage = Math.round((topic.count / maxCount) * 100)
              return (
                <div key={i} className="topic-bar">
                  <span className="topic-bar-label">{topic.name}</span>
                  <div className="topic-bar-track">
                    <div className="topic-bar-fill" style={{ width: `${percentage}%` }} />
                  </div>
                  <span className="topic-bar-value">{topic.count}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Frequently Retrieved Sources */}
        <div className="insight-card">
          <div className="insight-card-header">
            <div className="insight-card-title">Frequently Grounded Sources</div>
            <span className="insight-card-badge">High Confidence</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {mockInsights.frequentSources.map((source, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px',
                  background: 'var(--bg-input)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-secondary)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FileText size={18} style={{ color: 'var(--primary-600)' }} />
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {source.name}
                  </span>
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary-700)', background: 'var(--primary-50)', padding: '2px 10px', borderRadius: '999px' }}>
                  {source.count} citations
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Search Queries */}
        <div className="insight-card">
          <div className="insight-card-header">
            <div className="insight-card-title">Recent Inquiries</div>
            <span className="insight-card-badge">History</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {mockInsights.recentSearches.map((s, idx) => (
              <div
                key={idx}
                onClick={() => navigate(`/chat?q=${encodeURIComponent(s.query)}`)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Search size={14} style={{ color: 'var(--text-tertiary)' }} />
                  <span style={{ fontSize: '0.84rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                    "{s.query}"
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                  <Clock size={12} /> {s.time}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Activity Feed */}
        <div className="insight-card">
          <div className="insight-card-header">
            <div className="insight-card-title">Knowledge Space Activity</div>
            <span className="insight-card-badge">Live Stream</span>
          </div>

          <div className="activity-list">
            {mockInsights.recentActivity.map((act, idx) => (
              <div key={idx} className="activity-item">
                <div className="activity-icon" style={{ background: 'var(--primary-50)' }}>
                  {act.icon}
                </div>
                <div className="activity-text">
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{act.action}</span>{' '}
                  <span style={{ color: 'var(--text-secondary)' }}>"{act.target}"</span>
                </div>
                <div className="activity-time">{act.time}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
