# Smart Research Paper Analyzer - Architecture

## System Overview

The Smart Research Paper Analyzer is a RAG (Retrieval-Augmented Generation) system that enables researchers to efficiently analyze academic papers through intelligent question-answering and automated insights extraction.

## High-Level Architecture

```
┌─────────────────┐
│   Frontend      │
│  (Next.js)      │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
│  ┌───────────────────────────────────┐  │
│  │      RAG Pipeline                 │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  1. PDF Parser              │  │  │
│  │  │  2. Text Chunker            │  │  │
│  │  │  3. Embedding Service       │  │  │
│  │  │  4. Vector Store            │  │  │
│  │  │  5. LLM Service             │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌──────────────┐      ┌──────────────┐
│   Qdrant     │      │   Gemini     │
│ Vector DB    │      │   LLM API    │
└──────────────┘      └──────────────┘
         ▲
         │
┌──────────────┐
│   OpenAI     │
│ Embeddings   │
└──────────────┘
```

## Core Components

### 1. PDF Parser (`services/pdf_parser.py`)

**Purpose**: Extract text and metadata from research papers

**Technologies**:
- PyPDF2: Primary extraction
- pdfplumber: Fallback for complex layouts

**Process**:
1. Receive PDF bytes
2. Extract text using pdfplumber (preferred)
3. Fallback to PyPDF2 if needed
4. Extract metadata (title, author, dates)
5. Return structured data

**Output**:
```python
{
    "text": "Full paper text...",
    "metadata": {"title": "...", "author": "..."},
    "page_count": 12,
    "char_count": 45000
}
```

### 2. Text Chunker (`services/text_chunker.py`)

**Purpose**: Split documents into semantic chunks for embedding

**Strategy**:
- Detect paper sections (Abstract, Introduction, Methods, etc.)
- Chunk by sentences while respecting boundaries
- Maintain context with overlapping chunks

**Configuration**:
- `chunk_size`: 1000 characters (configurable)
- `chunk_overlap`: 200 characters (configurable)

**Output**:
```python
[
    {
        "chunk_id": 0,
        "text": "Chunk text...",
        "section": "Introduction",
        "char_count": 950,
        "metadata": {...}
    },
    ...
]
```

### 3. Embedding Service (`services/embedding_service.py`)

**Purpose**: Generate vector embeddings for semantic search

**Model**: OpenAI `text-embedding-3-small`
- Dimension: 1536
- Cost-effective
- High quality

**Features**:
- Batch processing for efficiency
- Error handling with fallback
- Automatic retry logic

**Process**:
1. Receive text chunks
2. Batch into groups of 100
3. Call OpenAI API
4. Return embedding vectors

### 4. Vector Store (`services/vector_store.py`)

**Purpose**: Store and retrieve document embeddings

**Technology**: Qdrant Vector Database

**Features**:
- Cosine similarity search
- Metadata filtering
- Automatic collection management
- Document-level operations

**Schema**:
```python
{
    "id": "uuid",
    "vector": [1536 dimensions],
    "payload": {
        "document_id": "...",
        "chunk_id": 0,
        "text": "...",
        "section": "...",
        "metadata": {...}
    }
}
```

### 5. LLM Service (`services/llm_service.py`)

**Purpose**: Generate human-readable responses

**Model**: Google Gemini Pro

**Capabilities**:
- Question answering with citations
- Document summarization
- Key findings extraction
- Methodology identification
- Limitations extraction

**Configuration**:
```python
{
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 2048
}
```

### 6. RAG Pipeline (`services/rag_pipeline.py`)

**Purpose**: Orchestrate all services for end-to-end processing

**Main Operations**:

#### Document Processing Flow:
```
PDF Upload → Parse → Chunk → Embed → Store → Return ID
```

#### Query Flow:
```
Question → Embed Query → Search Vectors → Retrieve Chunks → Generate Answer → Return with Citations
```

#### Analysis Flow:
```
Document ID → Retrieve All Chunks → Generate Summary → Extract Findings → Identify Methods → Extract Limitations
```

## Data Flow

### 1. Document Upload

```
User uploads PDF
    ↓
FastAPI receives file
    ↓
PDF Parser extracts text
    ↓
Text Chunker creates chunks
    ↓
Embedding Service generates vectors
    ↓
Vector Store saves to Qdrant
    ↓
Return document_id to user
```

### 2. Question Answering

```
User asks question
    ↓
Embedding Service embeds question
    ↓
Vector Store searches similar chunks
    ↓
Top-K chunks retrieved
    ↓
LLM Service generates answer with context
    ↓
Return answer with citations
```

### 3. Document Analysis

```
User requests analysis
    ↓
Vector Store retrieves all document chunks
    ↓
LLM Service generates:
  - Summary
  - Key findings
  - Methodology
  - Limitations
    ↓
Return structured analysis
```

## API Layer

### FastAPI Application (`main.py`)

**Endpoints**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/upload` | POST | Upload PDF |
| `/query` | POST | Ask questions |
| `/analyze/{id}` | GET | Analyze document |
| `/documents/{id}` | DELETE | Delete document |
| `/stats` | GET | Get statistics |

**Middleware**:
- CORS for frontend integration
- Error handling
- Request logging

## Configuration Management

**File**: `config.py`

**Uses**: Pydantic Settings for type-safe configuration

**Sources**:
1. Environment variables
2. `.env` file
3. Default values

**Key Settings**:
- API keys (Google, OpenAI)
- Qdrant connection
- Model selection
- Chunking parameters
- Search parameters

## Security Considerations

1. **API Keys**: Stored in `.env`, never committed
2. **CORS**: Configurable origins
3. **Input Validation**: Pydantic models
4. **File Upload**: Size limits, type validation
5. **Error Handling**: No sensitive data in responses

## Scalability

### Current Design:
- Single server
- Local/Docker Qdrant
- Synchronous processing

### Future Improvements:
1. **Async Processing**: Celery for background jobs
2. **Caching**: Redis for frequent queries
3. **Load Balancing**: Multiple API instances
4. **Managed Services**: Qdrant Cloud, hosted LLMs
5. **CDN**: For static assets

## Performance Optimization

1. **Batch Embedding**: Process 100 texts at once
2. **Vector Search**: Optimized with Qdrant HNSW
3. **Chunking**: Parallel processing possible
4. **Caching**: LLM responses for common queries
5. **Connection Pooling**: Reuse HTTP connections

## Error Handling

1. **PDF Parsing**: Fallback to alternative library
2. **Embedding**: Retry with exponential backoff
3. **Vector Store**: Connection retry logic
4. **LLM**: Timeout and fallback responses
5. **API**: Proper HTTP status codes

## Monitoring & Logging

**Logging**:
- Console output (INFO level)
- File logging (`logs/app.log`, DEBUG level)
- Structured logging with loguru

**Metrics to Track**:
- Request latency
- Embedding generation time
- Vector search performance
- LLM response time
- Error rates

## Technology Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI | REST API |
| Vector DB | Qdrant | Embedding storage |
| Embeddings | OpenAI | Text vectorization |
| LLM | Google Gemini | Text generation |
| PDF Processing | PyPDF2, pdfplumber | Text extraction |
| Configuration | Pydantic | Settings management |
| Logging | Loguru | Application logging |
| Validation | Pydantic | Data validation |

