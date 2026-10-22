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
  async upload(file) {
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

    // Backend returns: {"message": "PDF text not readable. Try another file."}
    if (data.message && data.message.toLowerCase().includes('not readable')) {
      throw new Error(data.message)
    }

    // Successfully scheduled for background ingestion
    return {
      success: true,
      message: data.message,
      document: {
        id: `doc-${Date.now()}`,
        name: file.name,
        type: isPdf ? 'pdf' : file.type.includes('image') ? 'image' : 'text',
        size: `${(file.size / (1024 * 1024)).toFixed(2)} MB`,
        uploadedAt: 'Just now',
        status: 'Indexed in FAISS',
        backendMessage: data.message,
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
