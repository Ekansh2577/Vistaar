"""
================================================================================
Phase 2 Benchmark Generator & Validator for VISTAAR Research Evaluation
================================================================================
Generates:
1. Five synthetic, controlled evaluation corpus documents in evaluation/corpus/
   Targeting 60-80 chunks total (under size=1000, overlap=200).
2. Master benchmark dataset (32 questions) in evaluation/datasets/
3. Dev (8 questions) and frozen test (24 questions) splits
4. Corpus manifest with SHA-256 hashes and chunk metadata
5. Complete verification suite verifying exact evidence spans and chunk mapping
================================================================================
"""

import os
import sys
import json
import hashlib
from pathlib import Path

# Add backend to sys.path to use actual backend chunking implementation
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from chunking import chunk_text

EVAL_DIR = WORKSPACE_DIR / "evaluation"
CORPUS_DIR = EVAL_DIR / "corpus"
DATASETS_DIR = EVAL_DIR / "datasets"

CORPUS_DIR.mkdir(parents=True, exist_ok=True)
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

HEADER_NOTICE = (
    "[SYNTHETIC EVALUATION CORPUS - CONTROLLED BENCHMARK DATASET FOR VISTAAR RAG RESEARCH EVALUATION. "
    "NOT AN EMPIRICAL HARDWARE/SYSTEM SPECIFICATION.]\n\n"
)

# ------------------------------------------------------------------------------
# 1. Authoring 5 Controlled Evaluation Documents (Targeting 60-80 chunks total)
# ------------------------------------------------------------------------------

DOC_01_CONTENT = HEADER_NOTICE + """# VISTAAR System Architecture and Ingestion Specification

## 1. Document Ingestion and Preprocessing Pipeline
The VISTAAR system implements an ingestion subsystem designed to ingest diverse document formats including plain text files (.txt) and Portable Document Format (.pdf) files. When a user uploads a document through the file ingestion endpoint, the system first verifies the file extension. For plain text files, the payload is read directly as UTF-8 encoded text. For PDF documents, VISTAAR employs the pypdf library to extract text sequentially from each page.
A strict length validation barrier is enforced immediately following text extraction: any document yielding fewer than 50 characters is rejected with an ingestion error to prevent degenerate index creation. The extracted text is then normalized by stripping leading and trailing whitespace while preserving internal newline structures. Ingestion is treated as an append-only operation in the baseline runtime, meaning newly ingested documents add their representations to the running index without purging existing entries.
File format validation also includes basic sanity checks against null byte injections and truncated file streams. If a multi-page PDF contains unextractable rasterized image pages without text streams, those individual pages are bypassed while extractable text pages continue through the ingestion pipeline.

## 2. Character-Level Sliding Window Chunking Protocol
Once text extraction and normalization complete, VISTAAR passes the raw document string to its chunking module. Rather than relying on semantic boundary detection or recursive sentence splitting, the baseline VISTAAR implementation uses a deterministic character-level sliding-window protocol with fixed parameters:
- Window size: 1000 characters
- Overlap size: 200 characters
- Stride: 800 characters
Specifically, the chunking loop iterates through the string using a step stride of 800 characters, taking a slice of length 1000 starting at index i: chunk = text[i:i + 1000]. This deterministic rule guarantees that consecutive chunks share exactly 200 characters of overlapping context at their boundaries. This boundary overlap mitigates information loss when entities, numbers, or technical statements span the arbitrary 1000-character partition boundary. The chunking module returns an ordered list of string chunks, each containing between 1 and 1000 characters.
Because character-level slicing disregards grammatical syntax, individual words or hyphenated tokens may occasionally be bisected across chunk edges. The 200-character overlap window provides sufficient lexical buffer for downstream semantic embedding models to resolve complete clause context on at least one side of the partition.

## 3. Dense Embedding Model and Vector Space Properties
Each text chunk produced by the chunker is transformed into a dense vector embedding. VISTAAR integrates the sentence-transformers library using the pre-trained all-MiniLM-L6-v2 model. This model is a 6-layer MiniLM transformer fine-tuned on over one billion sentence pairs to optimize semantic similarity mapping.
The technical specifications of the embedding engine are:
- Vector dimensionality: 384 dimensions
- Input sequence limit: 256 wordpiece tokens
- Pooling strategy: Mean pooling over contextual token representations
- Normalization: In the baseline VISTAAR configuration, embeddings are output as raw float32 vectors without unit L2 normalization.
When a batch of text chunks arrives, the embedding function computes the 384-dimensional representation for each chunk. The resulting matrix is structured as a two-dimensional numpy array of shape (N, 384) with float32 precision, where N is the number of chunks.
The model executes inference on CPU by default using PyTorch float32 tensors. When texts exceed the 256 token limit, trailing tokens are truncated by the tokenizer before computing the mean pooled embedding representation.

## 4. Vector Store Architecture and Indexing Logic
VISTAAR manages its vector repository through the Facebook AI Similarity Search (FAISS) library. The baseline implementation initializes an in-memory index using faiss.IndexFlatL2 with dimension 384. This index type executes an exact, brute-force Euclidean distance search across all stored vectors.
To maintain synchronization between the FAISS vector index and the raw textual chunks, VISTAAR maintains a parallel global Python list named stored_chunks. When new vectors are inserted via index.add(embeddings), the corresponding textual chunks are appended to stored_chunks using stored_chunks.extend(chunks). This preserves a strict one-to-one positional mapping: the integer ID returned by FAISS at index idx corresponds exactly to stored_chunks[idx]. Because IndexFlatL2 requires no Voronoi cell clustering or product quantization training, index construction is instantaneous and retrieval is perfectly exhaustive with zero quantization distortion.
The index lives entirely in the application process memory space. If the backend process restarts or crashes, the in-memory index resets, requiring ingested documents to be re-parsed and re-embedded upon subsequent startup.

## 5. Context Construction and Prompt Assembly
When a user submits a natural language question, the VISTAAR query processor converts the question string into a 384-dimensional dense vector using the identical all-MiniLM-L6-v2 model instance. The query vector is passed to the search method, which executes index.search(query_embedding, k). In the default baseline deployment, k is set to 8.
The search method returns the k nearest neighbor textual chunks from stored_chunks based on ascending L2 distance. If the index contains fewer than k total vectors, it returns all available chunks. If the index is empty, an empty list is returned.
Upon receiving the retrieved chunks, the question-answering service constructs a consolidated context string by joining the retrieved chunks using a triple hyphen separator: context_str = "\\n\\n---\\n\\n".join(chunks).
This context string is then injected into a strict prompt template:
Context:
{context_str}

Question: {question}
This synthesized prompt string constitutes the complete payload forwarded to the downstream language model.
No external system instructions, conversational persona modifiers, or metadata tags are appended to the context prompt. The prompt design relies strictly on the explicit delimiter structure to isolate context chunks from the user question.

## 6. Generative Model and Temperature Configuration
For generative answer synthesis, VISTAAR interfaces with the Google Generative AI API client using the Gemini family of large language models. The service defines an ordered fallback cascade of model endpoints to manage API rate limits and quota allocations:
1. gemini-3.1-flash-lite
2. gemini-3.5-flash-lite
3. gemini-flash-lite-latest
4. gemini-3.5-flash
5. gemini-3-flash-preview
The generation configuration enforces a strict temperature parameter of 0.0. Setting temperature to zero suppresses stochastic sampling, enforcing greedy decoding to ensure deterministic and reproducible factual responses based exclusively on the provided context passages. The maximum generation budget is configured to 2048 output tokens. If the API returns an empty response or encounters an unrecoverable quota error across all cascade tiers, the service returns a standard fallback error notification string.
The service wraps the API call in an exponential backoff retry loop with up to three retries to handle transient 429 rate limit or 503 service unavailable responses before falling back to the subsequent model tier.

## 7. Web Service Interface and REST API Contracts
VISTAAR exposes its core capabilities through a lightweight HTTP RESTful interface. The backend API defines two primary endpoints:
- POST /ingest: Accepts multipart form data containing document uploads. Validates file integrity, initiates document chunking, calculates embeddings, appends vectors to FAISS, and returns a JSON receipt containing the total chunks indexed.
- POST /ask: Accepts a JSON payload containing the query string {"question": string}. Executes query vectorization, retrieves top-k chunks, invokes the Gemini generation service, and returns a response payload {"answer": string}.
In the baseline API deployment, the /ask endpoint does not return retrieved chunk texts or vector distance scores to client callers; context chunks are retained purely internal to the execution lifecycle of the QA service.

## 8. Ephemeral State Management and Process Lifecycle
Because VISTAAR relies on an in-memory FAISS flat index, multi-tenancy and persistence are managed on an ephemeral per-session basis in the default architecture. There is no external relational database or persistent key-value store attached to the baseline ingestion pipeline.
When administrators trigger an index clear request, the vector_store module resets the FAISS index by calling index.reset() and empties the companion stored_chunks list. Memory allocated to FAISS vectors and Python string objects is reclaimed via standard garbage collection cycles. This lightweight architecture minimizes infrastructure dependencies, allowing standalone local deployment without external database daemons.
"""

DOC_02_CONTENT = HEADER_NOTICE + """# Multimodal Ingestion and Indic Processing Pipeline

## 1. Indic Multilingual Processing Architecture
VISTAAR incorporates specialized preprocessing components designed to address the linguistic and morphological complexities of Indic languages. The pipeline specifically supports high-resource and medium-resource Indian languages across the Indo-Aryan and Dravidian language families, including Hindi, Marathi, Bengali, Tamil, Telugu, and Kannada.
Dravidian languages exhibit agglutinative morphology where grammatical relationships are expressed through extensive suffix concatenation, resulting in long word forms and out-of-vocabulary challenges for standard subword tokenizers. In Indo-Aryan languages like Hindi and Marathi, script processing must handle complex conjunct consonants, matra reordering, and Zero-Width Joiner (ZWJ) or Zero-Width Non-Joiner (ZWNJ) unicode sequences.
VISTAAR applies a unicode normalization pre-filter using canonical decomposition followed by canonical composition (NFC normalization) to standardize composite glyphs before chunking.
Without NFC normalization, identical visual characters can be encoded through differing byte sequences, fragmenting word embeddings and degrading nearest-neighbor retrieval in the vector space.

## 2. OCR Extraction Pipeline for Scanned Manuscripts
To ingest historical archives, administrative notices, and printed government circulars, VISTAAR incorporates an Optical Character Recognition (OCR) pipeline. Scanned documents and image files (.png, .jpeg, .tiff) are processed through a four-stage visual normalization and character recognition workflow:
1. Grayscale conversion and Gaussian blur filtering (kernel size 3x3) to suppress sensor noise.
2. Adaptive Otsu thresholding to segment dark text glyphs from non-uniform, aged paper backgrounds.
3. Deskewing via Radon transform analysis, correcting rotational page misalignments within an angular range of -15 degrees to +15 degrees.
4. Optical character extraction using a custom-tuned Tesseract 5.3 engine equipped with specialized fast-integer Indic language models (tessdata_fast).
The OCR module outputs raw text along with bounding box coordinates and word-level recognition confidence scores. A confidence threshold filter of 72.0% is applied: words recognized with confidence below 72.0% are flagged with an uncertainty marker to alert downstream semantic validators.
The pipeline also discards isolated stray pixel clusters smaller than 4x4 pixels to eliminate speckle artifacts resulting from degraded paper scans.

## 3. Document Layout Analysis and Tabular Extraction Protocol
Many official documents feature multi-column layouts and structured numerical tables. Standard horizontal text extraction frequently scrambles multi-column layouts by concatenating text across columns. VISTAAR mitigates this through a heuristic layout analyzer based on morphological kernels.
Horizontal morphological kernels (size 1x40 pixels) detect horizontal table ruling lines, while vertical kernels (size 40x1 pixels) detect column dividers. The intersection of detected lines defines individual tabular grid cells. Once table geometry is resolved, cell contents are extracted and reformatted into standardized Markdown table syntax prior to sliding-window chunking.
This conversion preserves row-column alignment and ensures that tabular headers remain explicitly coupled with their corresponding cell data. When a table spans across multiple physical pages, the layout analyzer detects matching header structures and merges the continuous rows into a singular structured Markdown entity before emitting it to the chunker.

## 4. Speech and Audio Transcription Modality
For audio content such as agricultural advisories and public service announcements, VISTAAR features a speech-to-text ingestion module. The speech subsystem handles single-channel audio recorded at sampling rates between 8 kHz and 48 kHz, standardized to 16 kHz 16-bit PCM format.
Audio transcription is performed using a Conformer-CTC acoustic architecture trained on 10,000 hours of multilingual Indian audio covering 12 regional languages. The transcription engine generates word-level timestamps and inserts punctuation markers using a recurrent punctuation restoration model.
An automated Word Error Rate (WER) filtering gate discards audio segments exhibiting estimated transcript perplexity exceeding 18.5%. Transcribed speech segments are appended with an audio modality metadata tag indicating the source audio filename, timestamp offset, and speaker turn identifier before entering the sliding-window chunker.
Segments failing the 18.5% threshold are directed to an operator quarantine log, preventing garbled acoustic transcripts from contaminating the retrieval index with phonetic noise.

## 5. Cross-Lingual Semantic Embedding Alignment
To enable cross-lingual retrieval where a user queries in an Indic language (e.g., Hindi) to retrieve relevant passages written in English, VISTAAR configures a cross-lingual embedding extension. In this configuration, the standard English all-MiniLM-L6-v2 model is substituted with paraphrase-multilingual-MiniLM-L12-v2.
This multilingual model shares the 384-dimensional vector space with the baseline model but is trained across 50 languages using multilingual teacher-student distillation. Cross-lingual mapping achieves an alignment cosine similarity of 0.84 on parallel Indo-Aryan evaluation corpora.
In the baseline VISTAAR configuration, however, cross-lingual embeddings remain optional, and the primary deployment operates on all-MiniLM-L6-v2 focused on English document ingestion.
The cross-lingual alignment space ensures that conceptually identical queries expressed in Hindi or English project into close Euclidean neighborhoods within the FAISS IndexFlatL2 index.

## 6. Complex Typography Preprocessing and DPI Normalization
Scanned historical manuscripts frequently exhibit uneven typography and ink bleed-through from reverse pages. To enhance character legibility prior to OCR, VISTAAR implements local adaptive Sauvola thresholding with a dynamic window radius of 15 pixels and a threshold weighting parameter k_s = 0.2.
All scanned image inputs are normalized to 300 Dots Per Inch (DPI) resolution via bicubic resampling. Input images with resolutions lower than 150 DPI are upscaled, while high-resolution scans exceeding 600 DPI are downsampled to prevent excessive computational overhead in the Tesseract morphological extraction stage.

## 7. Audio Pre-Filtering and Voice Activity Detection
The audio ingestion subsystem precedes Conformer-CTC inference with an energy-based Voice Activity Detection (VAD) module. The VAD module partitions continuous audio streams into discrete speech utterances based on a 30-millisecond frame energy threshold.
Periods of non-speech silence exceeding 800 milliseconds trigger an utterance segmentation boundary. This segmentation eliminates long stretches of ambient microphone silence, reducing unnecessary ASR inference overhead and ensuring that generated transcripts correspond to coherent semantic speech passages.
"""

DOC_03_CONTENT = HEADER_NOTICE + """# Comparative Retrieval Baselines and Algorithmic Frameworks

## 1. Dense Passage Retrieval (DPR) Baseline
Dense Passage Retrieval (DPR) represents a dual-encoder retrieval paradigm that replaces traditional lexical indexers with dense representations. In DPR, two independent BERT-base encoders are trained: a question encoder that maps questions to 768-dimensional vectors, and a passage encoder that maps document passages to the same 768-dimensional space.
Similarity is computed using the dot product between the question vector and passage vectors:
Score(q, p) = <E_Q(q), E_P(p)>
DPR is trained using a contrastive loss function with in-batch negatives and mined hard negatives selected from top BM25 search results that do not contain the answer string. While DPR achieves superior recall on open-domain questions requiring semantic understanding, its dual 768-dimensional encoders require substantially greater GPU memory and computational overhead compared to VISTAAR's 384-dimensional all-MiniLM-L6-v2 architecture.
Furthermore, DPR's performance can drop when evaluating domain-specific jargon that differs substantially from the Wikipedia corpora on which the dual encoders were originally pre-trained.

## 2. BM25 Lexical Keyword Baseline
BM25 (Best Matching 25) is an established probabilistic lexical ranking function based on term frequency and inverted index lookup. The BM25 score for a document D given a query Q containing terms q_i is defined as:
BM25(D, Q) = sum_{i=1}^n IDF(q_i) * (f(q_i, D) * (k1 + 1)) / (f(q_i, D) + k1 * (1 - b + b * (|D| / avgdl)))
In standard benchmarking configurations, the hyperparameters are fixed at k1 = 1.2 and b = 0.75.
BM25 exhibits notable strengths in retrieving exact technical identifiers, part numbers, and rare domain terminology that dense embeddings frequently compress into general semantic regions. Conversely, BM25 fails completely when queries and documents use synonyms or paraphrased expressions with zero lexical overlap.
The BM25 index is constructed using Lucene tokenization pipelines, applying lowercase normalization, standard English stopword removal, and the Porter stemming algorithm.

## 3. Hybrid Sparse-Dense Fusion via Reciprocal Rank Fusion
To combine the lexical precision of BM25 with the semantic generalization of dense embeddings, modern retrieval systems employ hybrid fusion. A widely adopted method is Reciprocal Rank Fusion (RRF), which combines ranked lists without requiring score calibration or normalization.
The RRF score of a document d across a set of retrieval methods M is calculated as:
RRF_Score(d) = sum_{m in M} 1 / (k_rrf + r_m(d))
where r_m(d) is the rank of document d in ranking method m (with ranks starting at 1), and k_rrf is a smoothing constant typically set to 60.
In empirical evaluations on heterogeneous corpora, hybrid RRF consistently outperforms standalone dense retrieval by 3.8% in Recall@10 while mitigating the failure modes of out-of-vocabulary queries.
By operating strictly on integer ranks rather than raw similarity logits or probabilistic scores, RRF avoids the need for empirical weight tuning across disparate scoring distributions.

## 4. GraphRAG Knowledge Graph Augmentation
GraphRAG augments dense vector retrieval by constructing a structured knowledge graph from the document corpus. In the GraphRAG framework, an LLM parses text chunks to extract named entities (e.g., organizations, systems, protocols) and relationships (triples of subject-predicate-object).
These entities and relations are indexed into a labeled property graph database such as Neo4j. GraphRAG then applies community detection algorithms, specifically the hierarchical Leiden algorithm, to cluster closely related entities into semantic communities.
For each community, the system pre-generates hierarchical community summaries. During query processing, GraphRAG navigates both the vector embedding index and the graph hierarchy, enabling multi-hop reasoning across globally dispersed documents that cannot be retrieved through single-hop vector similarity alone.
Graph construction requires substantial upfront LLM processing cost, making it significantly more compute-intensive during document ingestion than VISTAAR's flat sliding-window embedding pipeline.

## 5. Self-RAG and Adaptive Retrieval Framework
Self-RAG (Self-Reflective Retrieval-Augmented Generation) introduces an adaptive mechanism where an LLM dynamically controls its own retrieval process through special reflection tokens. Rather than retrieving a fixed number of passages unconditionally for every query, Self-RAG trains the generator to emit:
- [Retrieve]: emitted when external knowledge is required to answer the query.
- [IsRel]: evaluates whether the retrieved passage is relevant to the prompt.
- [IsSup]: evaluates whether the generated output is fully supported by the retrieved context.
- [IsUse]: assesses the overall utility and informativeness of the generated response.
This self-reflective mechanism suppresses unnecessary retrieval operations for queries that can be answered from parametric memory, reducing API latency and eliminating noise from irrelevant retrieved chunks.
During inference, a beam search algorithm balances generation probabilities against reflection token scores, pruning retrieval paths that yield ungrounded or redundant statements.

## 6. Hypothetical Document Embeddings (HyDE) Baseline
HyDE (Hypothetical Document Embeddings) transforms zero-shot retrieval by instructing an instruction-tuned LLM to generate a hypothetical answer passage for an incoming query before retrieval occurs. Even if the generated hypothetical document contains factual inaccuracies, its stylistic and topical vocabulary closely mirrors the target document corpus.
The hypothetical document is then embedded using a dense encoder, and its embedding vector serves as the search query in the vector store.
In comparative trials on technical documentation, HyDE demonstrates elevated recall for abstract conceptual queries but introduces an additional LLM generation round-trip latency penalty prior to vector retrieval.

## 7. ColBERT Late-Interaction Multi-Vector Retrieval
ColBERT (Contextualized Late Interaction over BERT) employs a multi-vector representation model that preserves token-level embeddings for both queries and documents. Rather than compressing an entire chunk into a single fixed-length vector, ColBERT computes token vectors and performs retrieval using the MaxSim operator:
Score(Q, D) = sum_{q in Q} max_{d in D} (E(q) . E(d))
ColBERT achieves retrieval quality approaching cross-encoders while retaining indexing throughput comparable to dual-encoders. However, storing hundreds of token vectors per document chunk increases index memory footprints by roughly an order of magnitude compared to VISTAAR's single 384-dimensional vector per chunk.
"""

DOC_04_CONTENT = HEADER_NOTICE + """# Hardware Profiling, Latency Benchmarks, and Index Scaling

## 1. Vector Search Latency Benchmarks on IndexFlatL2
In production environments, vector retrieval latency is governed by index architecture, vector dimensionality, and hardware execution constraints. A profiling benchmark of VISTAAR's faiss.IndexFlatL2 configuration across different vector collection scales yields the following baseline metrics:
- Hardware testbed: Intel Xeon Platinum 8375C CPU @ 2.80GHz (32 vCPUs, 64 GB RAM), single-threaded execution.
- Vector dimension: 384 dimensions (float32).
- At 1,000 vectors: Retrieval latency averages 0.045 milliseconds for k=8.
- At 10,000 vectors: Retrieval latency averages 0.420 milliseconds for k=8.
- At 100,000 vectors: Retrieval latency scales linearly to 3.850 milliseconds for k=8.
Because IndexFlatL2 performs an exhaustive O(N * d) distance calculation against all N stored vectors, latency grows strictly linearly with database size. Memory consumption for 100,000 vectors at 384 dimensions with 4-byte float32 elements equals exactly 153.6 megabytes of RAM.
The CPU cache hierarchy easily accommodates smaller indices (e.g., 1,000 vectors require 1.53 MB, fitting comfortably inside L3 processor cache), enabling ultra-fast sub-millisecond search latencies.

## 2. Inverted File and Product Quantization (IVF-PQ) Scaling
When scaling beyond 500,000 vectors, exact IndexFlatL2 becomes memory-prohibitive in resource-constrained edge environments. VISTAAR profiles an alternative approximate nearest neighbor configuration: faiss.IndexIVF1024_PQ32.
In this configuration:
- The vector space is partitioned into 1,024 Voronoi cells using k-means clustering.
- Product Quantization (PQ) compresses each 384-dimensional vector into 32 8-bit quantized byte codes, achieving an 87.5% reduction in vector memory footprint (from 1,536 bytes down to 32 bytes per vector).
- Memory footprint for 100,000 vectors drops from 153.6 MB down to 19.2 MB.
- Retrieval latency at 100,000 vectors with nprobe=16 drops to 0.680 milliseconds.
However, this compression introduces an empirical recall penalty: Recall@10 drops by 4.2% relative to exact IndexFlatL2 due to quantization noise and boundary truncation.
The parameter nprobe governs the number of neighboring Voronoi centroids inspected during search. Increasing nprobe from 16 to 64 restores 2.8% of the lost recall but quadruples search latency to 2.45 milliseconds.

## 3. Embedding Model Inference Throughput and Quantization
The computational throughput of the all-MiniLM-L6-v2 embedding model was evaluated on both CPU and GPU hardware under varying precision regimes:
- On Intel Xeon CPU (batch size 32, FP32 precision): Throughput is 412 sentences per second with an average inference latency of 77.6 milliseconds per batch.
- On Intel Xeon CPU with INT8 dynamic quantization via ONNX Runtime: Throughput increases to 780 sentences per second, reducing inference latency to 41.0 milliseconds per batch. Cosine similarity drift between FP32 and INT8 embeddings remains below 0.003 across benchmark validation sets.
- On NVIDIA A10G GPU (batch size 64, FP16 precision): Throughput reaches 2,450 sentences per second with an average inference latency of 26.1 milliseconds per batch.
Dynamic INT8 quantization quantizes feed-forward and attention projection matrix weights to 8-bit integers while maintaining activations in floating point, halving memory bandwidth demands during model forward passes.

## 4. LLM Generation Latency, Throughput, and Token Economics
The generative response phase represents the dominant contributor to overall system latency and operational cost. Profiling the Google Gemini API (gemini-3.1-flash-lite) under temperature 0.0 reveals:
- Time-to-First-Token (TTFT): Averages 420 milliseconds under stable network conditions.
- Generation decoding throughput: 68 tokens per second.
- End-to-end generation latency for a standard 150-token answer: Approximately 2,620 milliseconds.
Operational token economics for the Gemini flash-lite tier are tracked as follows:
- Input context prompt pricing: $0.075 per 1,000,000 tokens.
- Output generation pricing: $0.300 per 1,000,000 tokens.
For a standard query with k=8 retrieved chunks (averaging approximately 1,800 prompt tokens) and a 150-token response, the total API cost per query is approximately $0.00018.
In high-throughput enterprise deployments executing 100,000 queries per day, selecting k=3 instead of k=8 reduces prompt tokens by approximately 60%, lowering daily LLM API expenditure from $18.00 down to roughly $8.50.

## 5. End-to-End System Bottleneck Analysis
An end-to-end latency budget analysis of the VISTAAR pipeline across top-k values k in {3, 5, 8} demonstrates that vector retrieval is not the system bottleneck:
- Vector search via IndexFlatL2 accounts for less than 0.2% of total transaction time.
- Query embedding generation accounts for 3.5% to 5.0% of transaction time.
- Gemini API network round-trip and autoregressive token decoding accounts for 94.8% to 96.3% of total transaction wall-clock time.
Consequently, optimizing top-k primarily serves to control prompt token budget, avoid context dilution, and improve answer faithfulness rather than accelerating vector search execution.

## 6. GPU Memory Constraints and Batch Processing Dynamics
When deploying the embedding pipeline on GPU instances, vectorization throughput is bounded by available GPU High Bandwidth Memory (HBM). On an NVIDIA A10G accelerator with 24 GB of VRAM, the all-MiniLM-L6-v2 model occupies approximately 1.2 GB of memory in FP16 precision.
Increasing the embedding batch size from 32 to 128 increases GPU compute saturation, improving overall throughput to 3,100 sentences per second. However, batch sizes exceeding 256 induce memory thrashing due to temporary activation allocations during multi-head attention matrix multiplication.

## 7. Storage I/O Overhead and In-Memory Execution
Because VISTAAR holds the FAISS index strictly in host memory (RAM), query processing incurs zero disk read operations or block device I/O waits during nearest neighbor retrieval. In contrast, on-disk vector stores relying on memory-mapped files (mmap) experience latency spikes when OS page cache misses force random access read operations from underlying solid-state drives.
Benchmark measurements confirm that RAM-resident IndexFlatL2 delivers a 99th percentile (p99) retrieval latency variance of under 0.15 milliseconds, ensuring predictable execution timing for real-time interactive query pipelines.
"""

DOC_05_CONTENT = HEADER_NOTICE + """# Acoustic Signal Processing, Spectral Analysis, and State Estimation

## 1. Fundamentals of Acoustic Signal Digitization
Continuous-time acoustic signals originating from physical pressure waves are converted into discrete-time digital signals through analog-to-digital converters (ADCs). The sampling process is governed strictly by the Nyquist-Shannon sampling theorem, which states that a continuous band-limited signal can be perfectly reconstructed from its samples if and only if the sampling frequency f_s is strictly greater than twice the highest frequency component f_max present in the signal (f_s > 2 * f_max).
To prevent aliasing distortion caused by high-frequency components folding into the audible baseband spectrum, analog anti-aliasing low-pass filters are inserted prior to digitization. A standard design employs a 6th-order Butterworth low-pass filter characterized by a maximally flat passband response and an attenuation slope of -36 dB per octave in the stopband.
Sampling jitter in the ADC clock introduces broadband phase noise, which degrades the signal-to-noise-and-distortion ratio (SINAD) in precision acoustic instrumentation.

## 2. Spectral Analysis and the Discrete Fourier Transform
Frequency-domain representation of acoustic signals is achieved via the Discrete Fourier Transform (DFT). For a discrete sequence x[n] of length N, the DFT is defined as:
X[k] = sum_{n=0}^{N-1} x[n] * exp(-j * 2 * pi * k * n / N), for k = 0, 1, ..., N-1
Direct computation of the DFT requires O(N^2) complex arithmetic operations. The Cooley-Tukey Fast Fourier Transform (FFT) algorithm reduces this computational complexity to O(N * log2(N)) when N is a power of two.
For time-varying non-stationary acoustic signals such as speech and music, the Short-Time Fourier Transform (STFT) computes localized frequency spectra by applying a sliding analysis window:
STFT{x[n]}(m, omega) = sum_{n=-infinity}^{infinity} x[n] * w[n - m] * exp(-j * omega * n)
A standard STFT parameter configuration uses a 25-millisecond Hamming analysis window with a 10-millisecond hop size, minimizing spectral leakage across adjacent frame boundaries.
Zero-padding the input time sequence interpolates the discrete frequency bin spacing in the output spectrum, enhancing visual resolution for harmonic peak tracking without increasing true physical frequency resolution.

## 3. Discrete-Time State Estimation and the Kalman Filter
In noisy acoustic tracking and sensor telemetry, dynamic state estimation is performed using the discrete-time linear Kalman filter. The system is modeled by linear stochastic difference equations:
State propagation: x_k = Phi_k * x_{k-1} + w_{k-1}
Measurement equation: z_k = H_k * x_k + v_k
where Phi_k represents the state transition matrix, H_k is the measurement observation matrix, w_k is zero-mean Gaussian process noise with covariance matrix Q_k, and v_k is zero-mean Gaussian measurement noise with covariance matrix R_k.
The recursive estimation cycle consists of prediction and measurement update phases:
1. State prediction: x_hat_k^- = Phi_k * x_hat_{k-1}
2. Error covariance prediction: P_k^- = Phi_k * P_{k-1} * Phi_k^T + Q_{k-1}
3. Kalman gain computation: K_k = P_k^- * H_k^T * (H_k * P_k^- * H_k^T + R_k)^(-1)
4. State estimate update: x_hat_k = x_hat_k^- + K_k * (z_k - H_k * x_hat_k^-)
5. Covariance update: P_k = (I - K_k * H_k) * P_k^-
Under linear Gaussian assumptions, the Kalman filter is mathematically proven to be the optimal minimum mean-square error (MMSE) estimator.

## 4. Acoustic Vector Quantization and Cepstral Feature Extraction
Speech recognition and speaker verification front-ends parameterize acoustic signals into Mel-Frequency Cepstral Coefficients (MFCCs). The feature extraction pipeline computes a 13-dimensional static cepstral feature vector per 10-millisecond frame by mapping STFT magnitude spectra onto a 26-channel triangular Mel filterbank, computing logarithmic filter energies, and applying the Discrete Cosine Transform (DCT).
To compress acoustic vector trajectories for codebook transmission, vector quantization is applied using the Linde-Buzo-Gray (LBG) clustering algorithm. The LBG algorithm iteratively splits centroids in Euclidean cepstral space using k-means optimization until the average distortion between training vectors and codebook centroids drops below a predefined convergence tolerance threshold epsilon = 0.001.
First and second temporal derivatives (delta and delta-delta coefficients) are frequently concatenated with the 13 static MFCCs to capture transitional acoustic dynamics, resulting in a 39-dimensional composite acoustic vector.

## 5. Acoustic Echo Cancellation and Adaptive Filtering
In hands-free telecommunications and teleconferencing systems, acoustic coupling between loudspeakers and microphones generates disruptive acoustic echo. Acoustic Echo Cancellation (AEC) removes this echo using adaptive finite impulse response (FIR) filters.
The Normalized Least Mean Squares (NLMS) algorithm adjusts the adaptive filter tap weights w[n] to minimize the error signal e[n] = d[n] - y_hat[n], where d[n] is the microphone pickup signal and y_hat[n] = w^T[n] * x[n] is the estimated acoustic echo.
The NLMS weight update recursion is formulated as:
w[n + 1] = w[n] + (mu / (epsilon_reg + ||x[n]||^2)) * e[n] * x[n]
where mu is the adaptation step-size parameter (0 < mu < 2), and epsilon_reg is a small regularization constant to prevent division by zero during periods of near-silent far-end speech. A Geigel double-talk detector halts filter adaptation when near-end speech is active to prevent divergence of the adaptive filter taps.
Double-talk detectors compute the ratio of the microphone signal energy to the loudspeaker reference energy over a short rectangular window, freezing coefficient adaptation whenever the energy ratio exceeds a calibrated threshold.

## 6. Microphone Array Beamforming and Spatial Filtering
Spatial acoustic filtering is achieved using multi-microphone arrays configured for acoustic beamforming. A delay-and-sum beamformer aligns the arrival times of acoustic wave fronts originating from a target source direction by applying calibrated time delays tau_m to each microphone channel m:
y[n] = (1 / M) * sum_{m=1}^M x_m[n - tau_m]
Constructive interference amplifies the desired acoustic source along the array look-direction, while destructive interference attenuates uncorrelated ambient reverberation and directional acoustic interferers.
Superdirective beamformers optimize microphone channel weightings based on measured spatial noise covariance matrices, achieving narrower main lobes at low frequencies at the cost of increased sensitivity to microphone sensor mismatch.

## 7. Spectral Subtraction and Non-Stationary Noise Suppression
Single-channel acoustic noise reduction frequently employs spectral subtraction. Assuming additive uncorrelated background noise, the power spectrum of the clean signal is estimated by subtracting an estimated noise power spectrum from the noisy speech power spectrum:
|S_hat(omega)|^2 = max(|Y(omega)|^2 - alpha * |N_hat(omega)|^2, beta * |Y(omega)|^2)
where alpha is an over-subtraction factor (alpha >= 1) and beta is a spectral floor parameter (0 < beta << 1) introduced to eliminate musical noise artifacts.
An acoustic voice activity detector continuously updates the noise power spectrum estimate |N_hat(omega)|^2 during speech pauses, ensuring adaptive tracking of slowly drifting environmental noise levels.
"""

DOC_01_SUPPLEMENT = """
## 9. Streaming Ingestion Protocol and Chunk Buffering
To support progressive document loading in interactive clients, VISTAAR defines an experimental chunk streaming protocol over WebSocket connections. In this streaming mode, the document stream is fed in continuous 1000-character blocks with client-side acknowledgments. As each chunk vector is computed, it is immediately inserted into the active FAISS index, allowing early query execution even while trailing pages of a massive document are still being vectorized in the background. A sliding circular buffer retains the latest five chunk slices in memory to handle transient client disconnections without vector duplication.

## 10. Document Metadata Schema and Header Tagging
Although the baseline search method returns raw string chunks, VISTAAR supports an internal chunk metadata schema. When enabled, each chunk is encapsulated in a lightweight JSON record specifying the source document filename, the 0-indexed chunk offset, the character start position, and an SHA-256 integrity hash of the chunk slice. This metadata envelope is stripped immediately before prompt concatenation, ensuring that the downstream Gemini model receives pristine text content without superfluous markup tokens that might degrade generative reasoning.

## 11. Document Ingestion Error Codes and Exception Handling
The ingestion subsystem defines standardized error classifications for handling malformed inputs. Error code ERR_INGEST_001 triggers when an uploaded file payload contains fewer than 50 valid UTF-8 characters. Error code ERR_INGEST_002 is raised when a PDF stream contains encrypted or password-protected content that cannot be decrypted with blank credentials. Error code ERR_INGEST_003 indicates that memory allocation for the vector buffer exceeded the available process memory quota during high-volume batch indexing.
"""

DOC_02_SUPPLEMENT = """
## 8. OCR Post-Correction via Statistical Language Modeling
Raw OCR output from degraded Indic texts frequently contains character confusion errors, such as confusions between similar Devanagari consonants (e.g., 'ba' and 'va', or 'dha' and 'gha'). To correct these errors before text chunking, VISTAAR routes low-confidence spans through an n-gram character language model. The character language model evaluates candidate replacement characters based on 5-gram transition probabilities derived from a corpus of 50 million clean sentences. Character substitutions that improve the language model perplexity score by more than 25% are automatically adopted, reducing character error rate by an estimated 3.4%.

## 9. Indic Script Font Rendering and Glyph Normalization
Digital government documents in India often utilize legacy non-Unicode fonts (such as Kruti Dev or Shree Lipi) rather than standard UTF-8 Unicode Devanagari. VISTAAR embeds a font detection heuristic that inspects character distribution anomalies in extracted strings. When legacy font encodings are detected, the system applies a character mapping lookup table that converts ASCII-mapped glyph codes back to their standard Unicode codepoints before tokenization, preventing corrupted text representations from entering the FAISS vector index.

## 10. Complex Ligature Disambiguation for Rare Dravidian Scripts
In historical Malayalam, Grantha, and Old Kannada epigraphical inscriptions, complex consonant ligatures with stacked subscript glyphs frequently cause segmentation failures in standard OCR kernels. VISTAAR integrates a contextual ligature disambiguation grammar based on classical sandhi split rules. When an ambiguous glyph sequence is detected, the grammar evaluates phonetic validity according to traditional phonotactic constraints, discarding orthographically invalid consonant stacks before generating word candidates.
"""

DOC_03_SUPPLEMENT = """
## 8. Cross-Encoder Re-Ranking Pipeline with BGE-Reranker
In two-stage retrieval architectures, a bi-encoder (such as all-MiniLM-L6-v2) retrieves an initial candidate pool of top-50 chunks, which are subsequently scored by a cross-encoder model like bge-reranker-large. The cross-encoder receives the query and chunk concatenated together, allowing full self-attention across all tokens. While cross-encoder re-ranking improves top-3 precision by resolving fine-grained semantic nuances that bi-encoders miss, it introduces significant computational latency, adding roughly 45 milliseconds of inference time per candidate batch on modern GPU hardware.

## 9. Pseudo-Relevance Feedback and Query Expansion
Pseudo-Relevance Feedback (PRF) assumes that the top-ranked passages returned by an initial retrieval pass are relevant to the user query. The algorithm extracts top informative terms from these initial passages using TF-IDF or RM3 term weighting and expands the original query vector before executing a final retrieval pass. In benchmark evaluations, PRF improves recall for verbose or exploratory queries but risks topic drift when the initial retrieval pass returns irrelevant false positives.

## 10. Dense-Lexical Score Interpolation and Convex Combination Baselines
As an alternative to rank-based Reciprocal Rank Fusion, convex combination baselines normalize min-max scaled dense inner product scores and BM25 scores into a unified composite score: Score_comb(d) = alpha * Score_dense(d) + (1 - alpha) * Score_BM25(d). Tuning the interpolation parameter alpha between 0.0 and 1.0 allows fine-grained balancing between keyword precision and semantic recall. Empirical results show that alpha = 0.65 yields the highest Mean Reciprocal Rank on technical documentation benchmarks.
"""

DOC_04_SUPPLEMENT = """
## 8. Thermal Throttling Dynamics and Sustained Workloads
Under continuous high-concurrency evaluation workloads, sustained CPU utilization across all 32 vCPUs on the benchmark server causes thermal junction temperatures to rise to 82 degrees Celsius. The processor's dynamic frequency scaling reduces core clock speeds from 2.80 GHz to a throttled baseline of 2.35 GHz. This thermal throttling increases batch embedding latency by approximately 14.5%, demonstrating the importance of managed concurrency and hardware cooling during prolonged evaluation runs.

## 9. Network Serialization Latency in Distributed Deployments
When decoupling the retrieval backend and the web frontend into separate containerized microservices communicating over an internal Gigabit Ethernet network, serialization and HTTP payload transfer introduce an additional 2.5 to 4.1 milliseconds of overhead per query. Compressing the retrieved text payload using gzip reduces network transfer latency by 35% on queries retrieving k=8 chunks.

## 10. Multi-Process Concurrency and Lock Contention in FAISS
When serving simultaneous queries across multiple worker processes using Gunicorn or Uvicorn, shared access to an in-memory FAISS index requires careful thread synchronization. Because IndexFlatL2 search operations are read-only O(N*d) matrix multiplications, multiple search threads can query the index concurrently without write lock contention. However, concurrent document ingestion invokes index.add(), necessitating a mutual exclusion write lock that momentarily pauses active search queries for approximately 1.2 milliseconds per batch of 50 chunks.
"""

DOC_05_SUPPLEMENT = """
## 8. Psychoacoustic Masking and Critical Band Filterbanks
Human auditory perception exhibits non-linear frequency resolution and auditory masking phenomena. Psychoacoustic models group frequencies into critical bands according to the Bark scale, where lower frequencies have narrower critical bandwidths than higher frequencies. Simultaneous masking occurs when a strong tonal or noise mask creates an elevated hearing threshold in neighboring frequency bins. Audio compression algorithms exploit this by allocating fewer bits to frequency components falling below the masked threshold.

## 9. Linear Predictive Coding (LPC) and Vocal Tract Synthesis
Linear Predictive Coding (LPC) models the human vocal tract as an all-pole linear filter driven by either periodic impulses (voiced speech) or white noise (unvoiced speech). The current speech sample s[n] is predicted as a linear combination of p past speech samples: s_hat[n] = sum_{k=1}^p a_k * s[n - k]. The prediction coefficients a_k are computed by solving the Yule-Walker autocorrelation equations using the Levinson-Durbin recursive algorithm, providing a compact 10th to 16th-order parameterization of speech formant trajectories.

## 10. Parametric Audio Equalization and Biquad IIR Filter Structures
Digital audio equalization utilizes second-order infinite impulse response (biquad) filters to implement peaking, shelving, and notch filtering stages. The transfer function in the z-domain is defined as: H(z) = (b0 + b1*z^-1 + b2*z^-2) / (1 + a1*z^-1 + a2*z^-2). Cascading multiple biquad sections allows precise acoustic tuning of frequency response curves, compensating for uneven acoustic room modes and loudspeaker frequency irregularities in telecommunication enclosures.
"""

DOCUMENTS = {
    "doc_01_vistaar_architecture.txt": DOC_01_CONTENT + DOC_01_SUPPLEMENT,
    "doc_02_multimodal_indic.txt": DOC_02_CONTENT + DOC_02_SUPPLEMENT,
    "doc_03_comparative_baselines.txt": DOC_03_CONTENT + DOC_03_SUPPLEMENT,
    "doc_04_hardware_latency.txt": DOC_04_CONTENT + DOC_04_SUPPLEMENT,
    "doc_05_acoustic_distractor.txt": DOC_05_CONTENT + DOC_05_SUPPLEMENT,
}

# ------------------------------------------------------------------------------
# 2. Write Corpus Files and Extract Ground-Truth Chunks
# ------------------------------------------------------------------------------

def write_and_chunk_corpus():
    corpus_info = {}
    all_chunks = []
    
    for filename, text in DOCUMENTS.items():
        filepath = CORPUS_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        
        # Exact backend chunking
        chunks = chunk_text(text, size=1000, overlap=200)
        
        # Calculate SHA256 of raw file
        sha256_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        
        doc_entry = {
            "filename": filename,
            "filepath": str(filepath),
            "sha256": sha256_hash,
            "char_count": len(text),
            "chunk_count": len(chunks),
            "chunks": []
        }
        
        # Map chunks with their offsets
        for idx, ch in enumerate(chunks):
            start_offset = idx * 800
            end_offset = start_offset + len(ch)
            chunk_data = {
                "chunk_id": f"{filename.replace('.txt', '')}_c{idx:02d}",
                "global_chunk_idx": len(all_chunks),
                "doc_filename": filename,
                "doc_chunk_idx": idx,
                "start_char": start_offset,
                "end_char": end_offset,
                "char_length": len(ch),
                "text": ch
            }
            doc_entry["chunks"].append(chunk_data)
            all_chunks.append(chunk_data)
            
        corpus_info[filename] = doc_entry

    return corpus_info, all_chunks

corpus_info, all_chunks = write_and_chunk_corpus()

print("=" * 70)
print(f"CORPUS GENERATION SUMMARY:")
total_chunks = len(all_chunks)
print(f"Total Chunks Generated Across 5 Documents: {total_chunks}")
for filename, info in corpus_info.items():
    print(f" - {filename:35s}: {info['chunk_count']:2d} chunks ({info['char_count']:5d} chars, SHA256: {info['sha256'][:10]}...)")
print("=" * 70)

# ------------------------------------------------------------------------------
# 3. Define 32 Benchmark Questions with Verifiable Provenance
# ------------------------------------------------------------------------------

QUESTIONS_RAW = [
    # --------------------------------------------------------------------------
    # CATEGORY A: Direct Single-Document Answerable (12 Questions)
    # --------------------------------------------------------------------------
    {
        "question_id": "PH2-Q01",
        "category": "sufficient_single",
        "split": "test",
        "question": "What chunk size, overlap size, and step stride does VISTAAR use in its sliding-window chunking protocol?",
        "target_documents": ["doc_01_vistaar_architecture.txt"],
        "exact_evidence_spans": [
            "Window size: 1000 characters\n- Overlap size: 200 characters\n- Stride: 800 characters",
            "taking a slice of length 1000 starting at index i: chunk = text[i:i + 1000]."
        ],
        "reference_answer": "VISTAAR uses a window size of 1000 characters, an overlap size of 200 characters, and a step stride of 800 characters in its sliding-window chunking protocol.",
        "expected_behavior": "Direct factual extraction from DOC-01.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q02",
        "category": "sufficient_single",
        "split": "test",
        "question": "What embedding model and vector dimensionality are configured in the baseline VISTAAR embedding module?",
        "target_documents": ["doc_01_vistaar_architecture.txt"],
        "exact_evidence_spans": [
            "VISTAAR integrates the sentence-transformers library using the pre-trained all-MiniLM-L6-v2 model.",
            "Vector dimensionality: 384 dimensions"
        ],
        "reference_answer": "The baseline VISTAAR embedding module uses the sentence-transformers all-MiniLM-L6-v2 model with a vector dimensionality of 384 dimensions.",
        "expected_behavior": "Direct factual extraction from DOC-01.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q03",
        "category": "sufficient_single",
        "split": "dev",
        "question": "Which FAISS index type is used in VISTAAR, and what distance metric does it compute?",
        "target_documents": ["doc_01_vistaar_architecture.txt"],
        "exact_evidence_spans": [
            "The baseline implementation initializes an in-memory index using faiss.IndexFlatL2 with dimension 384. This index type executes an exact, brute-force Euclidean distance search across all stored vectors."
        ],
        "reference_answer": "VISTAAR uses the in-memory faiss.IndexFlatL2 index with dimension 384, which computes exact, brute-force Euclidean distance (L2 distance).",
        "expected_behavior": "Direct factual extraction from DOC-01.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q04",
        "category": "sufficient_single",
        "split": "test",
        "question": "What temperature setting and fallback cascade of Gemini models are defined in the VISTAAR QA service?",
        "target_documents": ["doc_01_vistaar_architecture.txt"],
        "exact_evidence_spans": [
            "1. gemini-3.1-flash-lite\n2. gemini-3.5-flash-lite\n3. gemini-flash-lite-latest\n4. gemini-3.5-flash\n5. gemini-3-flash-preview",
            "The generation configuration enforces a strict temperature parameter of 0.0."
        ],
        "reference_answer": "The VISTAAR QA service enforces a temperature parameter of 0.0 with a fallback cascade of five Gemini models: gemini-3.1-flash-lite, gemini-3.5-flash-lite, gemini-flash-lite-latest, gemini-3.5-flash, and gemini-3-flash-preview.",
        "expected_behavior": "Direct factual extraction from DOC-01.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q05",
        "category": "sufficient_single",
        "split": "test",
        "question": "What confidence threshold is applied to word recognition in VISTAAR's OCR pipeline, and what happens to words below this threshold?",
        "target_documents": ["doc_02_multimodal_indic.txt"],
        "exact_evidence_spans": [
            "A confidence threshold filter of 72.0% is applied: words recognized with confidence below 72.0% are flagged with an uncertainty marker to alert downstream semantic validators."
        ],
        "reference_answer": "A confidence threshold of 72.0% is applied; words recognized with confidence below 72.0% are flagged with an uncertainty marker.",
        "expected_behavior": "Direct factual extraction from DOC-02.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q06",
        "category": "sufficient_single",
        "split": "test",
        "question": "What morphological kernel dimensions are utilized to detect table borders in VISTAAR's document layout analyzer?",
        "target_documents": ["doc_02_multimodal_indic.txt"],
        "exact_evidence_spans": [
            "Horizontal morphological kernels (size 1x40 pixels) detect horizontal table ruling lines, while vertical kernels (size 40x1 pixels) detect column dividers."
        ],
        "reference_answer": "Horizontal morphological kernels of size 1x40 pixels detect horizontal ruling lines, and vertical kernels of size 40x1 pixels detect column dividers.",
        "expected_behavior": "Direct factual extraction from DOC-02.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q07",
        "category": "sufficient_single",
        "split": "dev",
        "question": "What acoustic model architecture and training dataset volume are used in VISTAAR's speech transcription module?",
        "target_documents": ["doc_02_multimodal_indic.txt"],
        "exact_evidence_spans": [
            "Audio transcription is performed using a Conformer-CTC acoustic architecture trained on 10,000 hours of multilingual Indian audio covering 12 regional languages."
        ],
        "reference_answer": "The speech transcription module uses a Conformer-CTC acoustic architecture trained on 10,000 hours of multilingual Indian audio covering 12 regional languages.",
        "expected_behavior": "Direct factual extraction from DOC-02.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q08",
        "category": "sufficient_single",
        "split": "test",
        "question": "What formula and smoothing constant are used in Reciprocal Rank Fusion (RRF) for hybrid retrieval?",
        "target_documents": ["doc_03_comparative_baselines.txt"],
        "exact_evidence_spans": [
            "RRF_Score(d) = sum_{m in M} 1 / (k_rrf + r_m(d))",
            "where r_m(d) is the rank of document d in ranking method m (with ranks starting at 1), and k_rrf is a smoothing constant typically set to 60."
        ],
        "reference_answer": "Reciprocal Rank Fusion computes RRF_Score(d) = sum_{m in M} 1 / (k_rrf + r_m(d)), where r_m(d) is the document's rank in ranking method m starting at 1, and k_rrf is a smoothing constant typically set to 60.",
        "expected_behavior": "Direct factual extraction from DOC-03.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q09",
        "category": "sufficient_single",
        "split": "test",
        "question": "What are the four reflection tokens emitted by the Self-RAG generator, and what does each token signify?",
        "target_documents": ["doc_03_comparative_baselines.txt"],
        "exact_evidence_spans": [
            "- [Retrieve]: emitted when external knowledge is required to answer the query.\n- [IsRel]: evaluates whether the retrieved passage is relevant to the prompt.\n- [IsSup]: evaluates whether the generated output is fully supported by the retrieved context.\n- [IsUse]: assesses the overall utility and informativeness of the generated response."
        ],
        "reference_answer": "The four reflection tokens are: [Retrieve] (emitted when external knowledge is required), [IsRel] (evaluates if retrieved passage is relevant), [IsSup] (evaluates if generated output is fully supported by context), and [IsUse] (assesses overall utility and informativeness).",
        "expected_behavior": "Direct factual extraction from DOC-03.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q10",
        "category": "sufficient_single",
        "split": "test",
        "question": "What is the measured retrieval latency for IndexFlatL2 on an Intel Xeon CPU at 10,000 vectors versus 100,000 vectors for k=8?",
        "target_documents": ["doc_04_hardware_latency.txt"],
        "exact_evidence_spans": [
            "- At 10,000 vectors: Retrieval latency averages 0.420 milliseconds for k=8.\n- At 100,000 vectors: Retrieval latency scales linearly to 3.850 milliseconds for k=8."
        ],
        "reference_answer": "At 10,000 vectors, retrieval latency averages 0.420 milliseconds for k=8, whereas at 100,000 vectors, it scales linearly to 3.850 milliseconds on the Intel Xeon CPU.",
        "expected_behavior": "Direct factual extraction from DOC-04.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q11",
        "category": "sufficient_single",
        "split": "test",
        "question": "How much RAM is required for 100,000 vectors under exact IndexFlatL2 compared to IndexIVF1024_PQ32?",
        "target_documents": ["doc_04_hardware_latency.txt"],
        "exact_evidence_spans": [
            "Memory consumption for 100,000 vectors at 384 dimensions with 4-byte float32 elements equals exactly 153.6 megabytes of RAM.",
            "Memory footprint for 100,000 vectors drops from 153.6 MB down to 19.2 MB."
        ],
        "reference_answer": "Exact IndexFlatL2 requires 153.6 megabytes of RAM for 100,000 vectors, whereas IndexIVF1024_PQ32 reduces the memory footprint to 19.2 megabytes (an 87.5% reduction).",
        "expected_behavior": "Direct factual extraction from DOC-04.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q12",
        "category": "sufficient_single",
        "split": "test",
        "question": "What are the token pricing rates for input context and output generation under the Gemini flash-lite tier used in VISTAAR?",
        "target_documents": ["doc_04_hardware_latency.txt"],
        "exact_evidence_spans": [
            "- Input context prompt pricing: $0.075 per 1,000,000 tokens.\n- Output generation pricing: $0.300 per 1,000,000 tokens."
        ],
        "reference_answer": "Under the Gemini flash-lite tier, input context prompt pricing is $0.075 per 1,000,000 tokens, and output generation pricing is $0.300 per 1,000,000 tokens.",
        "expected_behavior": "Direct factual extraction from DOC-04.",
        "refusal_expected": False,
        "partial_scope": None
    },

    # --------------------------------------------------------------------------
    # CATEGORY B: Multi-Document Cross-Synthesis (8 Questions)
    # --------------------------------------------------------------------------
    {
        "question_id": "PH2-Q13",
        "category": "sufficient_multi",
        "split": "test",
        "question": "Compare the vector embedding dimensionality of VISTAAR's baseline embedding model with the dimensionality of the Dense Passage Retrieval (DPR) baseline.",
        "target_documents": ["doc_01_vistaar_architecture.txt", "doc_03_comparative_baselines.txt"],
        "exact_evidence_spans": [
            "Vector dimensionality: 384 dimensions",
            "In DPR, two independent BERT-base encoders are trained: a question encoder that maps questions to 768-dimensional vectors, and a passage encoder that maps document passages to the same 768-dimensional space."
        ],
        "reference_answer": "VISTAAR's baseline all-MiniLM-L6-v2 embedding model utilizes 384-dimensional vectors, whereas the Dense Passage Retrieval (DPR) baseline maps questions and passages to 768-dimensional vectors.",
        "expected_behavior": "Synthesize dimensionality metrics from DOC-01 and DOC-03.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q14",
        "category": "sufficient_multi",
        "split": "dev",
        "question": "How does VISTAAR's baseline FAISS index type compare to GraphRAG in terms of data structure and indexing approach?",
        "target_documents": ["doc_01_vistaar_architecture.txt", "doc_03_comparative_baselines.txt"],
        "exact_evidence_spans": [
            "The baseline implementation initializes an in-memory index using faiss.IndexFlatL2 with dimension 384. This index type executes an exact, brute-force Euclidean distance search across all stored vectors.",
            "GraphRAG augments dense vector retrieval by constructing a structured knowledge graph from the document corpus.",
            "These entities and relations are indexed into a labeled property graph database such as Neo4j. GraphRAG then applies community detection algorithms, specifically the hierarchical Leiden algorithm, to cluster closely related entities into semantic communities."
        ],
        "reference_answer": "VISTAAR's baseline uses an in-memory faiss.IndexFlatL2 vector index performing brute-force Euclidean distance search across flat text chunk vectors, whereas GraphRAG extracts named entities and relations into a Neo4j labeled property graph and clusters them into semantic communities using the hierarchical Leiden algorithm.",
        "expected_behavior": "Synthesize index architectures from DOC-01 and DOC-03.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q15",
        "category": "sufficient_multi",
        "split": "test",
        "question": "What is the memory footprint for 100,000 vectors in VISTAAR's baseline FAISS IndexFlatL2, and what percentage of total end-to-end latency does vector search account for?",
        "target_documents": ["doc_01_vistaar_architecture.txt", "doc_04_hardware_latency.txt"],
        "exact_evidence_spans": [
            "The baseline implementation initializes an in-memory index using faiss.IndexFlatL2 with dimension 384.",
            "Memory consumption for 100,000 vectors at 384 dimensions with 4-byte float32 elements equals exactly 153.6 megabytes of RAM.",
            "Vector search via IndexFlatL2 accounts for less than 0.2% of total transaction time."
        ],
        "reference_answer": "For 100,000 vectors at 384 dimensions, VISTAAR's IndexFlatL2 requires exactly 153.6 megabytes of RAM, and vector search accounts for less than 0.2% of total end-to-end transaction latency.",
        "expected_behavior": "Synthesize memory footprint and latency share from DOC-01 and DOC-04.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q16",
        "category": "sufficient_multi",
        "split": "test",
        "question": "How are tabular structures extracted from documents in VISTAAR, and what chunking parameters are subsequently applied to the extracted Markdown tables?",
        "target_documents": ["doc_01_vistaar_architecture.txt", "doc_02_multimodal_indic.txt"],
        "exact_evidence_spans": [
            "Horizontal morphological kernels (size 1x40 pixels) detect horizontal table ruling lines, while vertical kernels (size 40x1 pixels) detect column dividers. The intersection of detected lines defines individual tabular grid cells. Once table geometry is resolved, cell contents are extracted and reformatted into standardized Markdown table syntax prior to sliding-window chunking.",
            "the baseline VISTAAR implementation uses a deterministic character-level sliding-window protocol with fixed parameters:\n- Window size: 1000 characters\n- Overlap size: 200 characters\n- Stride: 800 characters"
        ],
        "reference_answer": "Tables are detected using horizontal (1x40 pixel) and vertical (40x1 pixel) morphological kernels to locate ruling lines, cell contents are extracted into standardized Markdown table syntax, and the resulting Markdown text is processed by VISTAAR's sliding-window chunker with a 1000-character window, 200-character overlap, and 800-character stride.",
        "expected_behavior": "Synthesize table extraction in DOC-02 with chunking parameters in DOC-01.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q17",
        "category": "sufficient_multi",
        "split": "test",
        "question": "What is the Word Error Rate threshold for speech transcripts in VISTAAR, and what token limit does the baseline embedding model enforce on chunk inputs?",
        "target_documents": ["doc_01_vistaar_architecture.txt", "doc_02_multimodal_indic.txt"],
        "exact_evidence_spans": [
            "An automated Word Error Rate (WER) filtering gate discards audio segments exhibiting estimated transcript perplexity exceeding 18.5%.",
            "Input sequence limit: 256 wordpiece tokens"
        ],
        "reference_answer": "The speech transcript filtering gate discards audio segments with estimated transcript perplexity/WER exceeding 18.5%, while the baseline embedding model enforces an input sequence limit of 256 wordpiece tokens.",
        "expected_behavior": "Synthesize WER threshold from DOC-02 and sequence token limit from DOC-01.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q18",
        "category": "sufficient_multi",
        "split": "dev",
        "question": "Compare BM25 hyperparameter settings with the RRF smoothing constant used in hybrid retrieval baselines.",
        "target_documents": ["doc_03_comparative_baselines.txt"],
        "exact_evidence_spans": [
            "In standard benchmarking configurations, the hyperparameters are fixed at k1 = 1.2 and b = 0.75.",
            "RRF_Score(d) = sum_{m in M} 1 / (k_rrf + r_m(d))\nwhere r_m(d) is the rank of document d in ranking method m (with ranks starting at 1), and k_rrf is a smoothing constant typically set to 60."
        ],
        "reference_answer": "The BM25 baseline fixes hyperparameters at k1 = 1.2 and b = 0.75, whereas the Reciprocal Rank Fusion (RRF) algorithm uses a smoothing constant of k_rrf = 60.",
        "expected_behavior": "Synthesize retrieval hyperparameter values from DOC-03.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q19",
        "category": "sufficient_multi",
        "split": "test",
        "question": "Which component dominates end-to-end transaction latency in VISTAAR, and what is its measured Time-to-First-Token (TTFT) and token generation rate?",
        "target_documents": ["doc_01_vistaar_architecture.txt", "doc_04_hardware_latency.txt"],
        "exact_evidence_spans": [
            "Gemini API network round-trip and autoregressive token decoding accounts for 94.8% to 96.3% of total transaction wall-clock time.",
            "Time-to-First-Token (TTFT): Averages 420 milliseconds under stable network conditions.\n- Generation decoding throughput: 68 tokens per second."
        ],
        "reference_answer": "The Gemini API network round-trip and autoregressive token decoding dominates end-to-end latency (accounting for 94.8% to 96.3% of wall-clock time), with a measured Time-to-First-Token (TTFT) averaging 420 milliseconds and a decoding throughput of 68 tokens per second.",
        "expected_behavior": "Synthesize system bottleneck and LLM latency profiling from DOC-04 and DOC-01.",
        "refusal_expected": False,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q20",
        "category": "sufficient_multi",
        "split": "test",
        "question": "What is the recall penalty when replacing VISTAAR's exact IndexFlatL2 with IndexIVF1024_PQ32, and how does INT8 quantization affect all-MiniLM-L6-v2 throughput on CPU?",
        "target_documents": ["doc_04_hardware_latency.txt"],
        "exact_evidence_spans": [
            "Recall@10 drops by 4.2% relative to exact IndexFlatL2 due to quantization noise and boundary truncation.",
            "On Intel Xeon CPU with INT8 dynamic quantization via ONNX Runtime: Throughput increases to 780 sentences per second, reducing inference latency to 41.0 milliseconds per batch. Cosine similarity drift between FP32 and INT8 embeddings remains below 0.003"
        ],
        "reference_answer": "Replacing IndexFlatL2 with IndexIVF1024_PQ32 incurs a 4.2% drop in Recall@10, while applying INT8 dynamic quantization to all-MiniLM-L6-v2 on CPU increases throughput from 412 to 780 sentences per second with cosine similarity drift remaining below 0.003.",
        "expected_behavior": "Synthesize index recall trade-off and embedding quantization benchmarks from DOC-04.",
        "refusal_expected": False,
        "partial_scope": None
    },

    # --------------------------------------------------------------------------
    # CATEGORY C: Partially Answerable Queries (6 Questions)
    # --------------------------------------------------------------------------
    {
        "question_id": "PH2-Q21",
        "category": "partial",
        "split": "test",
        "question": "What is VISTAAR's sliding window chunk size and stride, and what is its specific maximum sentence length threshold?",
        "target_documents": ["doc_01_vistaar_architecture.txt"],
        "exact_evidence_spans": [
            "Window size: 1000 characters\n- Overlap size: 200 characters\n- Stride: 800 characters"
        ],
        "reference_answer": "VISTAAR uses a window size of 1000 characters and a step stride of 800 characters (with 200 characters overlap). However, the provided context does not contain any information regarding a maximum sentence length threshold, as VISTAAR uses character-level sliding-window chunking rather than sentence-based splitting.",
        "expected_behavior": "Answer chunk size and stride factually; explicitly state that the sentence length threshold is absent from the context.",
        "refusal_expected": "partial",
        "partial_scope": {
            "supported": "Window size is 1000 characters and stride is 800 characters (200 characters overlap).",
            "unsupported": "Maximum sentence length threshold (VISTAAR does not use sentence-based splitting)."
        }
    },
    {
        "question_id": "PH2-Q22",
        "category": "partial",
        "split": "dev",
        "question": "What is the vector dimension of all-MiniLM-L6-v2 in VISTAAR, and what learning rate was used during its initial pre-training?",
        "target_documents": ["doc_01_vistaar_architecture.txt"],
        "exact_evidence_spans": [
            "Vector dimensionality: 384 dimensions"
        ],
        "reference_answer": "VISTAAR's all-MiniLM-L6-v2 model uses a vector dimensionality of 384 dimensions. However, the provided context does not contain information about the learning rate used during its initial pre-training.",
        "expected_behavior": "Answer vector dimensionality; state that pre-training learning rate is not provided in context.",
        "refusal_expected": "partial",
        "partial_scope": {
            "supported": "Vector dimensionality is 384 dimensions.",
            "unsupported": "Initial pre-training learning rate."
        }
    },
    {
        "question_id": "PH2-Q23",
        "category": "partial",
        "split": "test",
        "question": "What OCR confidence threshold does VISTAAR use for text filtering, and what GPU cluster model was used to train Tesseract 5.3?",
        "target_documents": ["doc_02_multimodal_indic.txt"],
        "exact_evidence_spans": [
            "A confidence threshold filter of 72.0% is applied: words recognized with confidence below 72.0% are flagged with an uncertainty marker"
        ],
        "reference_answer": "VISTAAR applies an OCR confidence threshold filter of 72.0%, flagging words recognized below this score with an uncertainty marker. However, the provided context does not mention the GPU cluster model used to train Tesseract 5.3.",
        "expected_behavior": "Answer OCR confidence threshold; refuse GPU cluster training details.",
        "refusal_expected": "partial",
        "partial_scope": {
            "supported": "OCR confidence threshold is 72.0%.",
            "unsupported": "GPU cluster model used to train Tesseract 5.3."
        }
    },
    {
        "question_id": "PH2-Q24",
        "category": "partial",
        "split": "dev",
        "question": "What is the smoothing constant k_rrf in Reciprocal Rank Fusion, and what is its mathematical proof of convergence?",
        "target_documents": ["doc_03_comparative_baselines.txt"],
        "exact_evidence_spans": [
            "and k_rrf is a smoothing constant typically set to 60."
        ],
        "reference_answer": "In Reciprocal Rank Fusion, the smoothing constant k_rrf is typically set to 60. However, the provided context does not contain a mathematical proof of convergence for RRF.",
        "expected_behavior": "Answer smoothing constant value; refuse mathematical proof of convergence.",
        "refusal_expected": "partial",
        "partial_scope": {
            "supported": "k_rrf smoothing constant is set to 60.",
            "unsupported": "Mathematical proof of convergence."
        }
    },
    {
        "question_id": "PH2-Q25",
        "category": "partial",
        "split": "test",
        "question": "What is the retrieval latency for 10,000 vectors on Intel Xeon CPU for k=8, and what is the exact server rack power consumption in Watts?",
        "target_documents": ["doc_04_hardware_latency.txt"],
        "exact_evidence_spans": [
            "- At 10,000 vectors: Retrieval latency averages 0.420 milliseconds for k=8."
        ],
        "reference_answer": "For 10,000 vectors on an Intel Xeon CPU, IndexFlatL2 retrieval latency averages 0.420 milliseconds for k=8. However, the provided context does not provide information regarding server rack power consumption in Watts.",
        "expected_behavior": "Answer retrieval latency; refuse server rack power consumption.",
        "refusal_expected": "partial",
        "partial_scope": {
            "supported": "Retrieval latency is 0.420 milliseconds for 10,000 vectors at k=8.",
            "unsupported": "Server rack power consumption in Watts."
        }
    },
    {
        "question_id": "PH2-Q26",
        "category": "partial",
        "split": "test",
        "question": "What sampling rate standards are supported by VISTAAR's audio ingestion module, and who was the primary recording engineer for the speech dataset?",
        "target_documents": ["doc_02_multimodal_indic.txt"],
        "exact_evidence_spans": [
            "The speech subsystem handles single-channel audio recorded at sampling rates between 8 kHz and 48 kHz, standardized to 16 kHz 16-bit PCM format."
        ],
        "reference_answer": "VISTAAR's audio ingestion module supports single-channel audio recorded at sampling rates between 8 kHz and 48 kHz, standardized to 16 kHz 16-bit PCM format. However, the context does not state who the primary recording engineer was for the speech dataset.",
        "expected_behavior": "Answer audio sampling rate standards; refuse identity of the recording engineer.",
        "refusal_expected": "partial",
        "partial_scope": {
            "supported": "Supported sampling rates are between 8 kHz and 48 kHz, standardized to 16 kHz 16-bit PCM format.",
            "unsupported": "Primary recording engineer identity."
        }
    },

    # --------------------------------------------------------------------------
    # CATEGORY D: Insufficient Evidence / Unanswerable (6 Questions)
    # --------------------------------------------------------------------------
    {
        "question_id": "PH2-Q27",
        "category": "insufficient",
        "split": "test",
        "question": "What is the recommended hyperparameter configuration for training a vision transformer using AdamW optimizer in VISTAAR?",
        "target_documents": [],
        "exact_evidence_spans": [],
        "reference_answer": "The provided context does not contain sufficient information to answer this question.",
        "expected_behavior": "Complete refusal: VISTAAR corpus contains no mention of vision transformer training or AdamW hyperparameters.",
        "refusal_expected": True,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q28",
        "category": "insufficient",
        "split": "dev",
        "question": "What SQL schema and database connection string does VISTAAR use to store user session histories in PostgreSQL?",
        "target_documents": [],
        "exact_evidence_spans": [],
        "reference_answer": "The provided context does not contain sufficient information to answer this question.",
        "expected_behavior": "Complete refusal: VISTAAR corpus contains no PostgreSQL connection strings or user session SQL schemas.",
        "refusal_expected": True,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q29",
        "category": "insufficient",
        "split": "test",
        "question": "What are the names and affiliations of the software engineers who implemented VISTAAR's frontend user interface in React?",
        "target_documents": [],
        "exact_evidence_spans": [],
        "reference_answer": "The provided context does not contain sufficient information to answer this question.",
        "expected_behavior": "Complete refusal: VISTAAR corpus contains no personnel names, affiliations, or React frontend implementation details.",
        "refusal_expected": True,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q30",
        "category": "insufficient",
        "split": "test",
        "question": "What is the exact mathematical equation used by VISTAAR to calculate Kalman filter gain when updating text chunk vectors?",
        "target_documents": ["doc_05_acoustic_distractor.txt"],
        "exact_evidence_spans": [],
        "reference_answer": "The provided context does not contain sufficient information to answer this question. While the context describes Kalman filtering for acoustic signals and state estimation, VISTAAR does not use Kalman filters to update text chunk vectors.",
        "expected_behavior": "Complete refusal / distinction: VISTAAR does not use Kalman filtering on text chunks; the equation in DOC-05 is purely for acoustic state estimation.",
        "refusal_expected": True,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q31",
        "category": "insufficient",
        "split": "dev",
        "question": "How does VISTAAR configure the NLMS adaptive filter to eliminate acoustic echo during document vector embedding generation?",
        "target_documents": ["doc_05_acoustic_distractor.txt"],
        "exact_evidence_spans": [],
        "reference_answer": "The provided context does not contain sufficient information to answer this question. NLMS adaptive filters are described in the context exclusively for acoustic echo cancellation in telecommunications, not for document vector embedding generation.",
        "expected_behavior": "Complete refusal / distractor rejection: Reject misleading combination of NLMS echo cancellation and document embedding.",
        "refusal_expected": True,
        "partial_scope": None
    },
    {
        "question_id": "PH2-Q32",
        "category": "insufficient",
        "split": "test",
        "question": "What order Butterworth filter does VISTAAR use to remove high-frequency noise from PDF text tokens before FAISS indexing?",
        "target_documents": ["doc_05_acoustic_distractor.txt"],
        "exact_evidence_spans": [],
        "reference_answer": "The provided context does not contain sufficient information to answer this question. Butterworth low-pass filters are described in the context only for analog-to-digital signal conversion of continuous acoustic signals, not for filtering PDF text tokens.",
        "expected_behavior": "Complete refusal / distractor rejection: Reject misleading combination of Butterworth analog filters with PDF text token processing.",
        "refusal_expected": True,
        "partial_scope": None
    }
]

# ------------------------------------------------------------------------------
# 4. Map Ground-Truth Chunks and Verify Evidence Spans Against Actual Chunks
# ------------------------------------------------------------------------------

def verify_and_map_benchmark(questions, all_chunks, corpus_info):
    verified_questions = []
    errors = []
    
    for q in questions:
        qid = q["question_id"]
        cat = q["category"]
        target_docs = q["target_documents"]
        spans = q["exact_evidence_spans"]
        
        matched_chunks = []
        matched_chunk_ids = []
        matched_chunk_global_indices = []
        
        if cat in ["sufficient_single", "sufficient_multi", "partial"]:
            if not spans:
                errors.append(f"[{qid}] Category '{cat}' has empty evidence spans!")
            
            for span in spans:
                span_found = False
                for doc_name, doc_data in corpus_info.items():
                    if target_docs and doc_name not in target_docs:
                        continue
                    
                    full_text = DOCUMENTS[doc_name]
                    if span in full_text:
                        span_found = True
                        # Find chunks in this doc that contain the span or overlap with it
                        for ch in doc_data["chunks"]:
                            if span in ch["text"]:
                                if ch["chunk_id"] not in matched_chunk_ids:
                                    matched_chunk_ids.append(ch["chunk_id"])
                                    matched_chunk_global_indices.append(ch["global_chunk_idx"])
                                    matched_chunks.append({
                                        "chunk_id": ch["chunk_id"],
                                        "global_chunk_idx": ch["global_chunk_idx"],
                                        "doc_filename": ch["doc_filename"]
                                    })
                            else:
                                # In case span crosses boundary, check sub-spans
                                sub_len = min(60, len(span))
                                if span[:sub_len] in ch["text"] or span[-sub_len:] in ch["text"]:
                                    if ch["chunk_id"] not in matched_chunk_ids:
                                        matched_chunk_ids.append(ch["chunk_id"])
                                        matched_chunk_global_indices.append(ch["global_chunk_idx"])
                                        matched_chunks.append({
                                            "chunk_id": ch["chunk_id"],
                                            "global_chunk_idx": ch["global_chunk_idx"],
                                            "doc_filename": ch["doc_filename"]
                                        })
                if not span_found:
                    errors.append(f"[{qid}] Evidence span not found in target documents! Span: '{span[:60]}...'")
            
            if not matched_chunk_ids:
                errors.append(f"[{qid}] No chunks matched evidence spans!")
                
        elif cat == "insufficient":
            for span in spans:
                errors.append(f"[{qid}] Insufficient question should not have evidence spans! Found: {span}")
            matched_chunk_ids = []
            matched_chunk_global_indices = []
        
        # Build clean verified record
        record = {
            "question_id": qid,
            "category": cat,
            "split": q["split"],
            "question": q["question"],
            "target_documents": target_docs,
            "ground_truth_chunk_ids": matched_chunk_ids,
            "ground_truth_global_indices": matched_chunk_global_indices,
            "exact_evidence_spans": spans,
            "reference_answer": q["reference_answer"],
            "expected_behavior": q["expected_behavior"],
            "refusal_expected": q["refusal_expected"],
            "partial_scope": q["partial_scope"]
        }
        verified_questions.append(record)

    return verified_questions, errors

verified_questions, verification_errors = verify_and_map_benchmark(QUESTIONS_RAW, all_chunks, corpus_info)

# ------------------------------------------------------------------------------
# 5. Split Dataset and Check for Near-Duplicates
# ------------------------------------------------------------------------------

def split_and_validate_leakage(verified_questions):
    dev_set = [q for q in verified_questions if q["split"] == "dev"]
    test_set = [q for q in verified_questions if q["split"] == "test"]
    
    leakage_warnings = []
    
    for q_dev in dev_set:
        dev_words = set(q_dev["question"].lower().replace("?", "").replace(",", "").split())
        for q_test in test_set:
            test_words = set(q_test["question"].lower().replace("?", "").replace(",", "").split())
            intersection = dev_words.intersection(test_words)
            union = dev_words.union(test_words)
            jaccard = len(intersection) / len(union) if union else 0.0
            
            if jaccard > 0.65:
                leakage_warnings.append(
                    f"High lexical similarity ({jaccard:.2f}) between {q_dev['question_id']} (dev) and {q_test['question_id']} (test)!"
                )
    
    return dev_set, test_set, leakage_warnings

dev_set, test_set, leakage_warnings = split_and_validate_leakage(verified_questions)

# ------------------------------------------------------------------------------
# 6. Save Manifest and Datasets
# ------------------------------------------------------------------------------

manifest = {
    "corpus_name": "VISTAAR_Phase2_Synthetic_Controlled_Evaluation_Corpus",
    "version": "1.0",
    "description": (
        "Synthetic, controlled benchmark dataset for VISTAAR RAG research evaluation. "
        "Engineered for retrieval selectivity and refusal calibration. Not real-world empirical hardware specs."
    ),
    "chunking_parameters": {
        "chunk_size": 1000,
        "overlap": 200,
        "stride": 800
    },
    "total_chunks": total_chunks,
    "documents": {
        doc_name: {
            "filename": info["filename"],
            "sha256": info["sha256"],
            "char_count": info["char_count"],
            "chunk_count": info["chunk_count"],
            "chunks_metadata": [
                {
                    "chunk_id": c["chunk_id"],
                    "global_idx": c["global_chunk_idx"],
                    "start_char": c["start_char"],
                    "end_char": c["end_char"],
                    "char_length": c["char_length"]
                }
                for c in info["chunks"]
            ]
        }
        for doc_name, info in corpus_info.items()
    }
}

manifest_path = CORPUS_DIR / "corpus_manifest.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

master_path = DATASETS_DIR / "benchmark_queries_master.json"
with open(master_path, "w", encoding="utf-8") as f:
    json.dump(verified_questions, f, indent=2)

dev_path = DATASETS_DIR / "tuning_queries.json"
with open(dev_path, "w", encoding="utf-8") as f:
    json.dump(dev_set, f, indent=2)

test_path = DATASETS_DIR / "test_queries_frozen.json"
with open(test_path, "w", encoding="utf-8") as f:
    json.dump(test_set, f, indent=2)

# ------------------------------------------------------------------------------
# 7. Print Comprehensive Summary
# ------------------------------------------------------------------------------

print("\n" + "=" * 70)
print(f"BENCHMARK DATASET GENERATION AND VALIDATION REPORT")
print("=" * 70)
print(f"Total Master Questions: {len(verified_questions)}")
print(f" - Dev Split (Tuning):  {len(dev_set)} questions")
print(f" - Test Split (Frozen): {len(test_set)} questions")
print("\nCategory Distribution:")
cats = {}
for q in verified_questions:
    cats[q["category"]] = cats.get(q["category"], 0) + 1
for cat, cnt in cats.items():
    print(f" - {cat:20s}: {cnt:2d} questions")

print("\nArtifacts Created:")
print(f" 1. Corpus Manifest:  {manifest_path}")
print(f" 2. Master Queries:   {master_path}")
print(f" 3. Dev Queries:      {dev_path}")
print(f" 4. Test Queries:     {test_path}")

if verification_errors:
    print("\n[!] VERIFICATION ERRORS DETECTED:")
    for err in verification_errors:
        print(f" - ERROR: {err}")
else:
    print("\n[V] ALL 32 QUESTIONS PASSED VERIFICATION (Exact spans mapped to real chunks).")

if leakage_warnings:
    print("\n[!] LEAKAGE WARNINGS:")
    for w in leakage_warnings:
        print(f" - WARNING: {w}")
else:
    print("[V] ZERO HIGH-LEXICAL-SIMILARITY LEAKAGE DETECTED BETWEEN DEV AND TEST.")
print("=" * 70)
