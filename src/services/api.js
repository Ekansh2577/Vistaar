// ============================================
// VISTAAR API Service Layer
// Connects frontend to teammate's FastAPI backend
// Endpoints:
//   - POST /upload (multipart/form-data: file)
//   - POST /ask    (JSON: { question: string })
//   - GET  /       (backend root/health)
// ============================================

import { mockDocuments, mockImages, mockConversations, mockKnowledgeGraph, mockInsights } from '../data/mockData'

// Base URL configured from environment variable or defaults to Vite proxy '/api'
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

/**
 * Check if the FastAPI backend is running and reachable.
 */
export async function checkBackendHealth() {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 4000)
    const res = await fetch(`${API_BASE_URL}/`, {
      method: 'GET',
      credentials: 'include',
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    return { online: res.ok, status: res.status }
  } catch (err) {
    return { online: false, error: err.message }
  }
}

// ============================================
// Document Service
// ============================================
export const documentService = {
  checkHealth: checkBackendHealth,

  /**
   * Upload a document (PDF or text) to the backend FAISS index.
   * Endpoint: POST /upload
   * Rate limit: 5/minute
   */
  async upload(file, onProgress = () => {}) {
    if (!file) {
      throw new Error('Please select a file to upload.')
    }

    // Supported formats check according to backend ingestion capability
    const fileName = file.name.toLowerCase()
    const isPdf = fileName.endsWith('.pdf')
    const isTxt = fileName.endsWith('.txt') || fileName.endsWith('.md') || fileName.endsWith('.json') || fileName.endsWith('.csv')
    const isSupported = isPdf || isTxt

    if (!isSupported && !file.type.includes('image')) {
      throw new Error('The backend currently supports PDF and text files (.pdf, .txt). Please upload a supported format.')
    }

    const formData = new FormData()
    formData.append('file', file)

    let res
    try {
      res = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      })
    } catch (networkErr) {
      throw new Error(
        `Failed to reach VISTAAR backend at "${API_BASE_URL}/upload". Ensure the FastAPI backend is running on http://127.0.0.1:8000.`
      )
    }

    if (res.status === 429) {
      throw new Error('Upload rate limit exceeded (5 uploads per minute). Please wait a moment before trying again.')
    }

    if (!res.ok) {
      let errDetail = `Server error HTTP ${res.status}`
      try {
        const errorJson = await res.json()
        if (errorJson.detail) errDetail = errorJson.detail
      } catch {
        // ignore JSON parse error on non-json error responses
      }
      throw new Error(errDetail)
    }

    const data = await res.json()
    if (!data.job_id) {
      throw new Error(data.detail || 'The backend did not start document processing.')
    }

    const startedAt = Date.now()
    let status
    do {
      await new Promise(resolve => setTimeout(resolve, 700))
      let statusResponse
      try {
        statusResponse = await fetch(`${API_BASE_URL}/upload/${encodeURIComponent(data.job_id)}`, {
          method: 'GET',
          credentials: 'include',
        })
      } catch {
        throw new Error('Lost connection while checking document processing status.')
      }

      if (!statusResponse.ok) {
        let detail = `Could not check document status (HTTP ${statusResponse.status}).`
        try {
          const errorJson = await statusResponse.json()
          if (errorJson.detail) detail = errorJson.detail
        } catch {
          // Keep the HTTP status when the response is not JSON.
        }
        throw new Error(detail)
      }
      status = await statusResponse.json()
      onProgress(status)

      if (Date.now() - startedAt > 15 * 60 * 1000) {
        throw new Error('Document processing took too long. Check backend OCR and embedding configuration.')
      }
      if (status.status === 'failed') {
        throw new Error(status.error || 'Document processing failed.')
      }
    } while (status.status !== 'ready')

    return {
      success: true,
      message: status.message,
      indexedChunks: status.indexed_chunks,
      warnings: status.warnings || [],
      scannedPages: status.scanned_pages || 0,
      document: {
        id: `doc-${Date.now()}`,
        name: file.name,
        type: isPdf ? 'pdf' : file.type.includes('image') ? 'image' : 'text',
        size: `${(file.size / (1024 * 1024)).toFixed(2)} MB`,
        uploadedAt: 'Just now',
        status: 'Ready',
        backendMessage: status.message,
      },
    }
  },

  async getAll() {
    return [...mockDocuments, ...mockImages]
  },

  async getDocuments() {
    return mockDocuments
  },

  async getImages() {
    return mockImages
  },

  async getById(id) {
    const allFiles = [...mockDocuments, ...mockImages]
    return allFiles.find(f => f.id === id) || null
  },

  async delete(id) {
    return { success: true }
  },

  async getAnalysis(id) {
    const doc = [...mockDocuments, ...mockImages].find(f => f.id === id)
    return doc ? {
      summary: doc.summary,
      keyConcepts: doc.keyConcepts || doc.detectedText || [],
      sections: doc.sections || [],
      suggestedQuestions: doc.suggestedQuestions || [],
      keyTakeaways: doc.keyTakeaways || doc.keyPoints || [],
    } : null
  },
}

// ============================================
// Chat / RAG Service
// ============================================
export const chatService = {
  /**
   * Submit a question to the backend RAG pipeline.
   * Endpoint: POST /ask
   * Rate limit: 10/minute
   * Body: { question: string }
   * Response: { answer: string }
   */
  async askQuestion(question) {
    const trimmed = question?.trim()
    if (!trimmed) {
      throw new Error('Please enter a question.')
    }

    let res
    try {
      res = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: trimmed }),
      })
    } catch (networkErr) {
      throw new Error(
        `Failed to reach VISTAAR backend at "${API_BASE_URL}/ask". Ensure the FastAPI backend is running on http://127.0.0.1:8000.`
      )
    }

    if (res.status === 429) {
      throw new Error('Question rate limit exceeded (10 questions per minute). Please wait a moment before asking again.')
    }

    if (!res.ok) {
      let errDetail = `Server error HTTP ${res.status}`
      try {
        const errorJson = await res.json()
        if (errorJson.detail) errDetail = errorJson.detail
      } catch {
        // ignore
      }
      throw new Error(errDetail)
    }

    const data = await res.json()
    return {
      answer: data.answer,
      sources: data.sources || [],
      timestamp: new Date().toISOString(),
    }
  },

  /**
   * Search the live web and synthesize an external answer.
   * Endpoint: POST /search/web
   * Rate limit: 10/minute
   */
  async searchWeb(query) {
    const trimmed = query?.trim()
    if (!trimmed) {
      throw new Error('Please enter a search query.')
    }

    let res
    try {
      res = await fetch(`${API_BASE_URL}/search/web`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: trimmed }),
      })
    } catch (networkErr) {
      throw new Error(
        `Failed to reach web search endpoint at "${API_BASE_URL}/search/web". Ensure the backend is running.`
      )
    }

    if (res.status === 429) {
      throw new Error('Web search rate limit exceeded (10 queries per minute). Please wait a moment.')
    }

    if (!res.ok) {
      let errDetail = `Server error HTTP ${res.status}`
      try {
        const errorJson = await res.json()
        if (errorJson.detail) errDetail = errorJson.detail
      } catch {
        // ignore
      }
      throw new Error(errDetail)
    }

    return await res.json()
  },

  async getConversations() {
    return mockConversations
  },

  async getConversation(id) {
    return mockConversations.find(c => c.id === id) || null
  },

  async createConversation() {
    return {
      id: `conv-${Date.now()}`,
      title: 'New Conversation',
      date: 'Today',
      messages: [],
    }
  },
}

// ============================================
// Knowledge Graph Service
// ============================================
export const knowledgeGraphService = {
  async getGraph() {
    return mockKnowledgeGraph
  },

  async getNodeDetails(nodeId) {
    const node = mockKnowledgeGraph.nodes.find(n => n.id === nodeId)
    return node || null
  },
}

// ============================================
// Insights Service
// ============================================
export const insightsService = {
  async getInsights() {
    return mockInsights
  },
}

// ============================================
// Image Intelligence Service (Gemini Vision)
// ============================================
export const imageService = {
  /**
   * Query an actual image using multimodal Gemini vision.
   * Endpoint: POST /ask-image
   * Rate limit: 10/minute
   */
  async askImage(file, question) {
    if (!file) {
      throw new Error('Please select an image to analyze.')
    }

    const formData = new FormData()
    formData.append('file', file)
    if (question && question.trim()) {
      formData.append('question', question.trim())
    }

    let res
    try {
      res = await fetch(`${API_BASE_URL}/ask-image`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      })
    } catch (networkErr) {
      throw new Error(
        `Failed to reach image analysis endpoint at "${API_BASE_URL}/ask-image". Ensure the backend is running.`
      )
    }

    if (res.status === 429) {
      throw new Error('Image analysis rate limit exceeded. Please wait a moment before trying again.')
    }

    if (!res.ok) {
      let errDetail = `Server error HTTP ${res.status}`
      try {
        const errorJson = await res.json()
        if (errorJson.detail) errDetail = errorJson.detail
      } catch {
        // ignore
      }
      throw new Error(errDetail)
    }

    return await res.json()
  },

  async analyzeImage(imageId) {
    const img = mockImages.find(i => i.id === imageId)
    return img ? {
      detectedText: img.detectedText,
      keyPoints: img.keyPoints,
      summary: img.summary,
    } : null
  },

  async askAboutImage(imageId, question) {
    return {
      answer: 'Visual analysis feature is currently exploring OCR models. For grounded answers, please query uploaded text or PDF documents.',
      confidence: 0.82,
    }
  },
}
