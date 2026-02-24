# Dependencies Documentation

## Complete List of Dependencies

### Core Framework (3 packages)

#### 1. FastAPI (0.109.0)
- **Purpose**: Modern, fast web framework for building APIs
- **Why**: High performance, automatic API documentation, async support
- **Used for**: REST API endpoints, request/response handling

#### 2. Uvicorn[standard] (0.27.0)
- **Purpose**: ASGI server for running FastAPI
- **Why**: Production-ready, supports WebSockets, auto-reload for development
- **Used for**: Running the application server

#### 3. python-multipart (0.0.6)
- **Purpose**: Streaming multipart parser
- **Why**: Required for file uploads in FastAPI
- **Used for**: Handling PDF file uploads

---

### PDF Processing (3 packages)

#### 4. PyPDF2 (3.0.1)
- **Purpose**: PDF manipulation library
- **Why**: Reliable text extraction, metadata reading
- **Used for**: Primary PDF parsing, metadata extraction

#### 5. pdfplumber (0.10.3)
- **Purpose**: Advanced PDF text extraction
- **Why**: Better handling of complex layouts, tables
- **Used for**: Fallback PDF parsing for complex documents

#### 6. pypdf (3.17.4)
- **Purpose**: Modern PDF library
- **Why**: Additional PDF processing capabilities
- **Used for**: Enhanced PDF handling

---

### Vector Database (1 package)

#### 7. qdrant-client (1.7.3)
- **Purpose**: Python client for Qdrant vector database
- **Why**: High-performance vector similarity search
- **Used for**: Storing and retrieving document embeddings

---

### AI & Machine Learning (3 packages)

#### 8. openai (1.12.0)
- **Purpose**: Official OpenAI Python library
- **Why**: Access to OpenAI's embedding models
- **Used for**: Generating text embeddings (text-embedding-3-small)

#### 9. google-generativeai (0.3.2)
- **Purpose**: Google's Generative AI Python SDK
- **Why**: Access to Gemini models
- **Used for**: LLM-based text generation, Q&A, summarization

#### 10. sentence-transformers (2.3.1)
- **Purpose**: Framework for sentence embeddings
- **Why**: Alternative embedding options, semantic similarity
- **Used for**: Potential local embedding generation (optional)

---

### Configuration & Environment (3 packages)

#### 11. python-dotenv (1.0.0)
- **Purpose**: Load environment variables from .env files
- **Why**: Secure configuration management
- **Used for**: Loading API keys and settings

#### 12. pydantic (2.5.3)
- **Purpose**: Data validation using Python type annotations
- **Why**: Type-safe data models, automatic validation
- **Used for**: API request/response schemas, configuration

#### 13. pydantic-settings (2.1.0)
- **Purpose**: Settings management for Pydantic
- **Why**: Type-safe configuration from environment variables
- **Used for**: Application settings management

---

### Utilities (3 packages)

#### 14. numpy (1.26.3)
- **Purpose**: Numerical computing library
- **Why**: Array operations, mathematical functions
- **Used for**: Vector operations, numerical processing

#### 15. pandas (2.1.4)
- **Purpose**: Data manipulation and analysis
- **Why**: Data processing, CSV handling
- **Used for**: Potential data analysis features

#### 16. tiktoken (0.5.2)
- **Purpose**: OpenAI's tokenizer library
- **Why**: Count tokens for API usage optimization
- **Used for**: Token counting for embeddings and LLM calls

---

### Security & Authentication (2 packages)

#### 17. python-jose[cryptography] (3.3.0)
- **Purpose**: JavaScript Object Signing and Encryption
- **Why**: JWT token handling
- **Used for**: Future authentication features

#### 18. passlib[bcrypt] (1.7.4)
- **Purpose**: Password hashing library
- **Why**: Secure password storage
- **Used for**: Future user authentication

---

### Logging (1 package)

#### 19. loguru (0.7.2)
- **Purpose**: Simplified logging library
- **Why**: Better logging experience, automatic formatting
- **Used for**: Application logging and debugging

---

## Total: 19 packages

## Installation Size
Approximate total size: ~2-3 GB (including dependencies)

## Python Version Requirement
- **Minimum**: Python 3.9
- **Recommended**: Python 3.10 or 3.11

## System Requirements

### Minimum:
- RAM: 4 GB
- Storage: 5 GB free space
- CPU: 2 cores

### Recommended:
- RAM: 8 GB or more
- Storage: 10 GB free space
- CPU: 4 cores or more

## External Services Required

### 1. Qdrant Vector Database
- **Installation**: Docker (recommended) or standalone
- **Port**: 6333 (HTTP), 6334 (gRPC)
- **Storage**: Varies by document count

### 2. OpenAI API
- **Requirement**: API key
- **Cost**: Pay-per-use (embeddings)
- **Get key**: https://platform.openai.com/api-keys

### 3. Google Gemini API
- **Requirement**: API key
- **Cost**: Free tier available
- **Get key**: https://makersuite.google.com/app/apikey

## Optional Dependencies

For development:
```txt
pytest==7.4.3           # Testing framework
black==23.12.1          # Code formatting
flake8==7.0.0          # Linting
mypy==1.8.0            # Type checking
```

## Dependency Tree (Simplified)

```
FastAPI
├── uvicorn (server)
├── pydantic (validation)
└── python-multipart (file upload)

RAG Pipeline
├── openai (embeddings)
├── google-generativeai (LLM)
├── qdrant-client (vector store)
├── PyPDF2 (PDF parsing)
└── pdfplumber (PDF parsing)

Configuration
├── python-dotenv (env vars)
└── pydantic-settings (settings)

Utilities
├── numpy (arrays)
├── pandas (data)
├── tiktoken (tokens)
└── loguru (logging)
```

## Installation Commands

### Full Installation
```bash
pip install -r requirements.txt
```

### Minimal Installation (Core only)
```bash
pip install fastapi uvicorn[standard] python-multipart
pip install qdrant-client openai google-generativeai
pip install PyPDF2 pdfplumber
pip install python-dotenv pydantic pydantic-settings
pip install loguru
```

## Troubleshooting

### Common Issues:

1. **Large download size**: Normal, ML libraries are large
2. **Compilation errors**: Install Visual C++ Build Tools (Windows)
3. **Memory errors**: Increase available RAM or use swap
4. **Slow installation**: Use faster mirror or upgrade pip

