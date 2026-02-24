# Smart Research Paper Analyzer - Backend

## Overview

This is the backend implementation of the Smart Research Paper Analyzer, a RAG (Retrieval-Augmented Generation) system that combines vector search with LLMs to provide intelligent analysis of research papers.

## Architecture

### Core Components

1. **PDF Parser** (`services/pdf_parser.py`)
   - Extracts text and metadata from PDF research papers
   - Uses PyPDF2 and pdfplumber for robust extraction

2. **Text Chunker** (`services/text_chunker.py`)
   - Intelligently splits documents into semantic chunks
   - Detects paper sections (Abstract, Introduction, Methods, etc.)
   - Maintains context with overlapping chunks

3. **Embedding Service** (`services/embedding_service.py`)
   - Generates vector embeddings using OpenAI's text-embedding-3-small
   - Batch processing for efficiency

4. **Vector Store** (`services/vector_store.py`)
   - Manages Qdrant vector database
   - Stores and retrieves document chunks
   - Semantic search with cosine similarity

5. **LLM Service** (`services/llm_service.py`)
   - Uses Google Gemini API for text generation
   - Provides summaries, Q&A, key findings extraction
   - Citation-grounded responses

6. **RAG Pipeline** (`services/rag_pipeline.py`)
   - Orchestrates all services
   - End-to-end document processing
   - Query handling with retrieval + generation

## Tech Stack

- **Framework**: FastAPI
- **Vector Database**: Qdrant
- **Embeddings**: OpenAI (text-embedding-3-small)
- **LLM**: Google Gemini Pro
- **PDF Processing**: PyPDF2, pdfplumber
- **Configuration**: Pydantic Settings

## Setup

### Prerequisites

- Python 3.9+
- Qdrant (running locally or cloud)
- OpenAI API key
- Google Gemini API key

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env .env
# Edit .env with your API keys
```

3. Start Qdrant (if running locally):
```bash
docker run -p 6333:6333 qdrant/qdrant
```

4. Run the application:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
- `GET /` - Root endpoint
- `GET /health` - Health check

### Document Management
- `POST /upload` - Upload and process a PDF
- `DELETE /documents/{document_id}` - Delete a document

### Analysis
- `POST /query` - Ask questions about documents
- `GET /analyze/{document_id}` - Comprehensive document analysis
- `GET /stats` - Get vector store statistics

## API Usage Examples

### Upload a Document
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@research_paper.pdf"
```

### Query Documents
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main findings?",
    "top_k": 5
  }'
```

### Analyze Document
```bash
curl -X GET "http://localhost:8000/analyze/{document_id}"
```

## Configuration

Edit `.env` file:

```env
# API Keys
GOOGLE_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=research_papers

# Models
EMBEDDING_MODEL=text-embedding-3-small
GEMINI_MODEL=gemini-pro
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## Project Structure

```
backend/
├── main.py                 # FastAPI application
├── config.py              # Configuration management
├── requirements.txt       # Dependencies
├── services/
│   ├── pdf_parser.py      # PDF extraction
│   ├── text_chunker.py    # Text chunking
│   ├── embedding_service.py # Embeddings
│   ├── vector_store.py    # Qdrant integration
│   ├── llm_service.py     # Gemini LLM
│   └── rag_pipeline.py    # Main pipeline
└── models/
    └── schemas.py         # Pydantic models
```

## Development

### Logging

Logs are written to:
- Console (INFO level)
- `logs/app.log` (DEBUG level)

### Testing

Run tests (when implemented):
```bash
pytest tests/
```

## License

MIT License

