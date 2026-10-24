# VISTAAR — AI Knowledge Workspace

> **Upload. Understand. Retrieve. Connect. Ask.**

VISTAAR is an AI-powered document and image intelligence workspace. It lets you upload PDFs, text files, and images into a FAISS-indexed knowledge base, then ask grounded natural-language questions powered by a FastAPI RAG (Retrieval-Augmented Generation) backend and Gemini Vision for multimodal image analysis.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Document Upload** | Upload PDF, TXT, MD, JSON, CSV files — indexed into FAISS for semantic search |
| 🖼️ **Image Intelligence** | Ask questions about images using multimodal Gemini Vision (`POST /ask-image`) |
| 💬 **RAG Chat** | Ask natural-language questions grounded in your uploaded documents (`POST /ask`) |
| 🌐 **Web Search** | Live web search synthesis via `POST /search/web` |
| 🕸️ **Knowledge Graph** | Interactive visual graph of concepts and relationships across your knowledge base |
| 📊 **Insights** | Auto-generated analytical summaries and key takeaways from your documents |
| 🔍 **Explore** | Browse, search, filter and preview all uploaded documents and images |
| 🌗 **Dark / Light Mode** | Full theme toggle with persisted preference |

---

## 🏗️ Tech Stack

### Frontend
- **React 19** + **React Router v7** — SPA routing
- **Vite 8** — Lightning-fast dev server & build tool
- **TypeScript** (config + counter utility)
- **Lucide React** — Icon library
- **Vanilla CSS** — Custom design system (no Tailwind)
- **Google Fonts** — Inter + Space Grotesk

### Backend (External — FastAPI)
- **FastAPI** running on `http://127.0.0.1:8000`
- **FAISS** — Vector similarity search / document indexing
- **Gemini Vision** — Multimodal image analysis

---

## 📁 Project Structure

```
vistaar/
├── index.html                  # App entry point & meta tags
├── vite.config.js              # Vite config + /api proxy to FastAPI
├── package.json                # Dependencies & scripts
├── tsconfig.json               # TypeScript configuration
├── .env                        # Environment variables (VITE_API_URL)
├── .gitignore
│
└── src/
    ├── main.jsx                # React DOM mount
    ├── App.jsx                 # Root component — BrowserRouter + Routes
    ├── style.css               # Global styles
    │
    ├── components/             # Shared UI components
    │   ├── Sidebar.jsx         # Navigation sidebar
    │   ├── Topbar.jsx          # Top bar with search & actions
    │   ├── UploadModal.jsx     # File upload dialog (drag & drop)
    │   ├── ThemeToggle.jsx     # Dark/Light mode switch
    │   ├── Toast.jsx           # Notification toasts
    │   ├── FileCard.jsx        # Document/image card tile
    │   ├── HeroBookVisual.jsx  # Animated hero illustration
    │   ├── BeyondVistaarCapsule.jsx  # Promo/feature capsule
    │   ├── EmptyState.jsx      # Empty list placeholder
    │   └── LoadingState.jsx    # Loading spinner
    │
    ├── pages/                  # Route-level page components
    │   ├── Home.jsx            # Landing dashboard
    │   ├── KnowledgeSpace.jsx  # Knowledge base overview
    │   ├── Chat.jsx            # RAG chat interface
    │   ├── Explore.jsx         # Browse & filter all files
    │   ├── KnowledgeGraphPage.jsx  # Interactive concept graph
    │   ├── Insights.jsx        # Auto-generated insights
    │   ├── Settings.jsx        # App configuration
    │   ├── DocumentViewerPage.jsx  # Full document viewer
    │   └── ImageViewerPage.jsx     # Image viewer + analysis
    │
    ├── context/                # React Context providers
    │   ├── AppContext.jsx      # Global app state (files, uploads, toasts)
    │   └── ThemeContext.jsx    # Theme (dark/light) state
    │
    ├── services/
    │   └── api.js              # All API calls to FastAPI backend
    │
    ├── data/
    │   └── mockData.js         # Mock data for dev/demo (no live backend)
    │
    └── styles/                 # Additional CSS modules
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** ≥ 18
- **npm** ≥ 9
- The **FastAPI backend** running on `http://127.0.0.1:8000`

### 1. Clone & Install

```bash
git clone https://github.com/Ekansh2577/Vistaar.git
cd vistaar
npm install
```

### 2. Configure Environment

The default `.env` file proxies all `/api` requests to the FastAPI backend:

```env
VITE_API_URL=/api
```

> To point directly at a remote backend, change it to:
> ```env
> VITE_API_URL=https://your-backend-url.com
> ```

### 3. Start the Dev Server

```bash
npm run dev
```

App will be available at **http://localhost:5173**

### 4. Build for Production

```bash
npm run build
```

Output goes to the `dist/` directory.

---

## 🔌 Backend API

Vistaar expects a **FastAPI** backend running at `http://127.0.0.1:8000` with the following endpoints:

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| `GET` | `/` | Health check | — |
| `POST` | `/upload` | Upload a file (multipart/form-data: `file`) | 5/min |
| `POST` | `/ask` | Ask a question `{ question: string }` | 10/min |
| `POST` | `/ask-image` | Analyze an image (multipart: `file` + optional `question`) | 10/min |
| `POST` | `/search/web` | Live web search `{ query: string }` | 10/min |

### Supported Upload Formats

| Type | Extensions |
|------|------------|
| Documents | `.pdf`, `.txt`, `.md`, `.json`, `.csv` |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` |

### Response Shapes

```json
// POST /upload
{ "message": "File ingested successfully." }

// POST /ask
{ "answer": "Your grounded answer here." }

// POST /ask-image
{ "answer": "Visual analysis result." }

// POST /search/web
{ "answer": "Synthesized web result.", "sources": [] }
```

---

## 🗺️ App Routes

| Path | Page | Description |
|------|------|-------------|
| `/` | Home | Dashboard with overview & quick actions |
| `/knowledge` | Knowledge Space | Manage your uploaded knowledge base |
| `/chat` | Chat | RAG-powered Q&A chat interface |
| `/explore` | Explore | Browse, search & filter all files |
| `/explore/:id` | Explore (Detail) | Focused view for a specific file |
| `/knowledge-graph` | Knowledge Graph | Interactive concept relationship graph |
| `/insights` | Insights | AI-generated analytical summaries |
| `/settings` | Settings | App preferences & configuration |
| `/viewer/doc/:id` | Document Viewer | Full document reading view |
| `/viewer/image/:id` | Image Viewer | Image detail + multimodal analysis |

---

## ⚙️ Vite Proxy Configuration

The dev server proxies `/api/*` → `http://127.0.0.1:8000/*`, stripping the `/api` prefix:

```js
// vite.config.js
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}
```

This means all `fetch('/api/upload')` calls reach `POST http://127.0.0.1:8000/upload` on the backend — no CORS issues in development.

---

## 🧩 State Management

Global state is managed through two React contexts:

- **`AppContext`** — Holds uploaded files list, active upload state, toast notifications, and backend connection status.
- **`ThemeContext`** — Manages dark/light theme preference, persisted in `localStorage`.

---

## 🛠️ Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server on port 5173 |
| `npm run build` | Type-check + build production bundle to `dist/` |
| `npm run preview` | Serve the production build locally |

---

## 📄 License

This project is private. All rights reserved © Ekansh.

---

## 🔄 How the Backend Works

Vistaar's backend is a **FastAPI** Python server responsible for:

1. **Document Ingestion** — Receiving uploaded files, chunking them into text segments, generating vector embeddings, and storing them in a FAISS in-memory index.
2. **RAG Query Pipeline** — On each `/ask` request, it performs a nearest-neighbour FAISS search to retrieve the Top-8 most relevant chunks, then feeds them as context to a Gemini LLM to produce a grounded answer.
3. **Multimodal Vision** — On each `/ask-image` request, it sends the raw image bytes + the user's question directly to Gemini Vision for pixel-level understanding.
4. **Web Search** — On each `/search/web` request, it queries the live web, aggregates result snippets, and synthesizes a coherent answer using the LLM.

### Backend Processing Pipeline (per request type)

```
┌─────────────────────────────────────────────────────────────────┐
│                      UPLOAD FLOW                                │
│                                                                 │
│  User uploads file                                              │
│       │                                                         │
│       ▼                                                         │
│  FastAPI  POST /upload                                          │
│       │                                                         │
│       ▼                                                         │
│  File chunker  ──► Text chunks (e.g. 512 tokens / 50 overlap)  │
│       │                                                         │
│       ▼                                                         │
│  Gemini Embeddings API  ──► float[] vector per chunk            │
│       │                                                         │
│       ▼                                                         │
│  FAISS Index  (in-memory vector store)                          │
│       │                                                         │
│       ▼                                                         │
│  { "message": "File ingested successfully." }                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  RAG QUESTION-ANSWER FLOW                       │
│                                                                 │
│  User sends question                                            │
│       │                                                         │
│       ▼                                                         │
│  FastAPI  POST /ask  { question: "..." }                        │
│       │                                                         │
│       ▼                                                         │
│  Embed question  ──► query vector                               │
│       │                                                         │
│       ▼                                                         │
│  FAISS nearest-neighbour search  ──► Top-8 chunk matches        │
│       │                                                         │
│       ▼                                                         │
│  Build context prompt:                                          │
│    "Answer based ONLY on these chunks: [chunk1, chunk2, ...]"   │
│       │                                                         │
│       ▼                                                         │
│  Gemini LLM  ──► grounded answer string                        │
│       │                                                         │
│       ▼                                                         │
│  { "answer": "The chunk size used is..." }                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│               MULTIMODAL IMAGE VISION FLOW                      │
│                                                                 │
│  User attaches image + question                                 │
│       │                                                         │
│       ▼                                                         │
│  FastAPI  POST /ask-image  (multipart: file + question)         │
│       │                                                         │
│       ▼                                                         │
│  Raw image bytes + question  ──►  Gemini Vision (multimodal)   │
│       │                                                         │
│       ▼                                                         │
│  Pixel-level understanding, OCR, object detection              │
│       │                                                         │
│       ▼                                                         │
│  { "answer": "The image shows..." }                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    WEB SEARCH FLOW                              │
│                                                                 │
│  User triggers web search fallback                              │
│       │                                                         │
│       ▼                                                         │
│  FastAPI  POST /search/web  { query: "..." }                    │
│       │                                                         │
│       ▼                                                         │
│  Live web search API  ──►  top result snippets + URLs           │
│       │                                                         │
│       ▼                                                         │
│  Gemini LLM synthesizes answer from snippets                    │
│       │                                                         │
│       ▼                                                         │
│  { "answer": "...", "sources": [{ title, url, snippet }] }      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ How the Frontend Talks to the Backend

### The Proxy Bridge

In development, the Vite dev server proxies every `/api/*` request to the FastAPI backend running at `http://127.0.0.1:8000`, stripping the `/api` prefix. This means **no CORS configuration** is needed:

```
Browser ──► fetch('/api/ask') ──► Vite Proxy ──► http://127.0.0.1:8000/ask
```

In production, set `VITE_API_URL` to your deployed backend URL directly.

---

### Service Layer (`src/services/api.js`)

All backend communication is centralised in the **API service layer**. No page or component makes raw `fetch()` calls — everything goes through named service objects:

| Service | Exported Object | Key Methods |
|---|---|---|
| **Document Service** | `documentService` | `upload(file)`, `getAll()`, `getById(id)` |
| **Chat / RAG Service** | `chatService` | `askQuestion(question)`, `searchWeb(query)` |
| **Image Service** | `imageService` | `askImage(file, question)` |
| **Knowledge Graph Service** | `knowledgeGraphService` | `getGraph()`, `getNodeDetails(nodeId)` |
| **Insights Service** | `insightsService` | `getInsights()` |
| **Health Check** | `checkBackendHealth()` | Polls `GET /` with 4 s timeout |

---

### Request / Response Flow (step by step)

#### 1. File Upload (`UploadModal.jsx` → `documentService.upload`)

```
User selects file in UploadModal
       │
       ▼
documentService.upload(file)          ← src/services/api.js
       │
       ├─ Validates extension (.pdf, .txt, .md, .json, .csv, images)
       ├─ Builds FormData { file }
       ├─ POST /api/upload
       │
       ▼
Backend indexes file into FAISS
       │
       ▼
{ "message": "File ingested successfully." }
       │
       ▼
AppContext.addUploadedDocument(doc)   ← persisted to localStorage
       │
       ▼
Toast notification: "✅ Uploaded & indexed"
```

#### 2. Document Q&A (`Chat.jsx` → `chatService.askQuestion`)

```
User types question + presses Send
       │
       ▼
chatService.askQuestion(text)         ← src/services/api.js
       │
       ├─ POST /api/ask  { question: text }
       │
       ▼
Backend: FAISS retrieval + Gemini LLM
       │
       ▼
{ "answer": "..." }
       │
       ▼
Chat.jsx checks answer for "no relevant info" phrases
       │
       ├─ Found → sets needsWebFallback = true → shows "Search Web" button
       └─ Not found → renders answer with FAISS source chips
```

#### 3. Image Vision Query (`Chat.jsx` → `imageService.askImage`)

```
User attaches image file + types question
       │
       ▼
imageService.askImage(file, question) ← src/services/api.js
       │
       ├─ Builds FormData { file, question }
       ├─ POST /api/ask-image
       │
       ▼
Backend: Gemini Vision (multimodal)
       │
       ▼
{ "answer": "The image shows..." }
       │
       ▼
Chat.jsx renders response with purple 👁 "Vision Analysis" badge
```

#### 4. Web Search Fallback (`Chat.jsx` → `chatService.searchWeb`)

```
User clicks "Search the Web" on an ungrounded answer
       │
       ▼
chatService.searchWeb(query)          ← src/services/api.js
       │
       ├─ POST /api/search/web  { query }
       │
       ▼
Backend: Web search + Gemini synthesis
       │
       ▼
{ "answer": "...", "sources": [...] }
       │
       ▼
Chat.jsx renders answer with 🌐 "External Web Sources" badge
+ clickable source cards with title, domain, snippet
```

---

### Global State & Backend Health (`AppContext.jsx`)

`AppContext` is the central React context that wires everything together:

```
AppContext
├── backendOnline        → polls GET /api/ every 15 seconds
│                          null = checking | true = online | false = offline
│                          Shown as colour-coded pill in Chat topbar
│
├── uploadedDocuments    → persisted to localStorage (vistaar_session_docs)
│                          shown as "FAISS Index" source chips in Chat
│
├── uploadedImages       → persisted to localStorage (vistaar_session_images)
│                          click any image → auto-attaches to Vision mode in Chat
│
├── activeImage          → the currently "active" image for Vision analysis
│
├── toasts               → auto-dismissing notifications (4.5 s)
│
└── uploadModal          → controls UploadModal visibility
```

---

### Rate Limits & Error Handling

The service layer catches all network and HTTP errors and throws user-readable messages:

| Scenario | Error Shown |
|---|---|
| Backend unreachable | `"Failed to reach VISTAAR backend at '/api/...'. Ensure FastAPI is running on http://127.0.0.1:8000."` |
| Upload rate limit hit | `"Upload rate limit exceeded (5 uploads per minute). Please wait."` |
| Question rate limit hit | `"Question rate limit exceeded (10 questions per minute). Please wait."` |
| PDF not readable | `"PDF text not readable. Try another file."` |
| Ungrounded answer | Shows inline **"Search the Web"** fallback button |
| Vision / Web search error | Red error bubble in chat with full error message |

---

## 🔁 Full Data Flow Diagram

```
┌──────────────┐     upload / ask       ┌─────────────────────────┐
│              │ ──────────────────────► │   FastAPI Backend       │
│   Browser    │                        │   :8000                 │
│   (Vite      │ ◄────────────────────── │                         │
│   :5173)     │     JSON response       │  ┌──────────────────┐  │
│              │                        │  │  FAISS Index     │  │
│  React SPA   │                        │  │  (in-memory)     │  │
│  ├ AppContext │      /api/* proxy      │  └──────────────────┘  │
│  ├ api.js    │ ◄───────────────────── │                         │
│  └ pages/    │   Vite strips /api     │  ┌──────────────────┐  │
│              │                        │  │  Gemini LLM /    │  │
└──────────────┘                        │  │  Vision API      │  │
                                        │  └──────────────────┘  │
       ▲                                └─────────────────────────┘
       │
  localStorage
  (session docs
   & images)
```
