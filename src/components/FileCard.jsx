import { FileText, Image, FileSpreadsheet, FileType, MoreVertical, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const typeIcons = {
  pdf: { icon: '📄', className: 'pdf' },
  doc: { icon: '📝', className: 'doc' },
  docx: { icon: '📝', className: 'doc' },
  ppt: { icon: '📊', className: 'ppt' },
  pptx: { icon: '📊', className: 'ppt' },
  txt: { icon: '📃', className: 'txt' },
  image: { icon: '🖼', className: 'img' },
  jpg: { icon: '🖼', className: 'img' },
  jpeg: { icon: '🖼', className: 'img' },
  png: { icon: '🖼', className: 'img' },
  webp: { icon: '🖼', className: 'img' },
}

export default function FileCard({ file }) {
  const navigate = useNavigate()
  const typeInfo = typeIcons[file.type] || typeIcons[file.format] || typeIcons.txt
  const isImage = file.type === 'image' || ['jpg', 'jpeg', 'png', 'webp'].includes(file.format)

  const handleClick = () => {
    if (isImage) {
      navigate(`/image/${file.id}`)
    } else {
      navigate(`/document/${file.id}`)
    }
  }

  return (
    <div className="file-card" onClick={handleClick} id={`file-card-${file.id}`}>
      <div className="file-card-header">
        <div className={`file-card-icon ${typeInfo.className}`}>
          {typeInfo.icon}
        </div>
        <div className="file-card-info">
          <div className="file-card-name" title={file.name}>{file.name}</div>
          <div className="file-card-meta">
            {isImage ? (
              <>{file.format?.toUpperCase() || 'Image'} • {file.size}</>
            ) : (
              <>{file.pages} pages • {file.chunks} chunks</>
            )}
          </div>
        </div>
        <button className="file-card-more" onClick={e => e.stopPropagation()} aria-label="More options">
          <MoreVertical size={16} />
        </button>
      </div>

      {file.tags && file.tags.length > 0 && (
        <div className="file-card-tags">
          {file.tags.map(tag => (
            <span className="file-tag" key={tag}>{tag}</span>
          ))}
        </div>
      )}

      <div className="file-card-footer">
        <Clock size={12} />
        <span>Uploaded {file.uploadedAt}</span>
      </div>
    </div>
  )
}
