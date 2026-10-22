// ============================================
// VISTAAR API Service Abstraction Layer
// Replace mock implementations with real API calls
// when connecting to Spring Boot / FastAPI backend
// ============================================

import { mockDocuments, mockImages, mockConversations, mockKnowledgeGraph, mockInsights } from '../data/mockData'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api'

// Simulated network delay
const delay = (ms = 500) => new Promise(resolve => setTimeout(resolve, ms))

// ============================================
// Document Service
// ============================================
export const documentService = {
  async getAll() {
    await delay(300)
    return [...mockDocuments, ...mockImages]
  },

  async getDocuments() {
    await delay(300)
    return mockDocuments
  },

  async getImages() {
    await delay(300)
    return mockImages
  },

  async getById(id) {
    await delay(200)
    const allFiles = [...mockDocuments, ...mockImages]
    return allFiles.find(f => f.id === id) || null
  },

  async upload(file) {
    await delay(1500)
    // In production: POST to ${API_BASE_URL}/documents/upload
    return {
      id: `doc-${Date.now()}`,
      name: file.name,
      type: file.type.includes('image') ? 'image' : 'pdf',
      size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
      uploadedAt: 'Just now',
      tags: [],
      chunks: 0,
      pages: 0,
    }
  },

  async delete(id) {
    await delay(300)
    // In production: DELETE ${API_BASE_URL}/documents/${id}
    return { success: true }
  },

  async getAnalysis(id) {
    await delay(800)
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
  async getConversations() {
    await delay(300)
    return mockConversations
  },

  async getConversation(id) {
    await delay(200)
    return mockConversations.find(c => c.id === id) || null
  },

  async sendMessage(conversationId, message, sourceIds = []) {
    await delay(1500)
    // In production: POST ${API_BASE_URL}/chat/ask
    // Body: { conversationId, message, sourceIds }
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: `Based on your uploaded documents, here's what I found:\n\n${message.length > 50 ? 'This is a detailed analysis based on the retrieved context from your documents. The information has been synthesized from multiple sources to provide a comprehensive answer.' : 'I analyzed your documents and found relevant information related to your query. Let me provide a grounded response based on the retrieved evidence.'}`,
      sources: [
        { docId: 'doc-1', name: 'RAG_Research_Paper.pdf', page: 4, relevance: 85, type: 'pdf' },
        { docId: 'doc-2', name: 'System_Design_Notes.pdf', page: 12, relevance: 72, type: 'pdf' },
      ],
    }
  },

  async createConversation() {
    await delay(200)
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
    await delay(500)
    return mockKnowledgeGraph
  },

  async getNodeDetails(nodeId) {
    await delay(300)
    const node = mockKnowledgeGraph.nodes.find(n => n.id === nodeId)
    return node || null
  },
}

// ============================================
// Insights Service
// ============================================
export const insightsService = {
  async getInsights() {
    await delay(400)
    return mockInsights
  },
}

// ============================================
// Image Intelligence Service
// ============================================
export const imageService = {
  async analyzeImage(imageId) {
    await delay(1000)
    const img = mockImages.find(i => i.id === imageId)
    return img ? {
      detectedText: img.detectedText,
      keyPoints: img.keyPoints,
      summary: img.summary,
    } : null
  },

  async askAboutImage(imageId, question) {
    await delay(1200)
    return {
      answer: 'Based on my analysis of the image, I can see the following relevant information...',
      confidence: 0.82,
    }
  },
}
