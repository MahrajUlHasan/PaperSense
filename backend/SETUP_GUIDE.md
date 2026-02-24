# Setup Guide - Smart Research Paper Analyzer Backend

## Quick Start

### 1. Prerequisites

Ensure you have the following installed:
- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Docker** - [Download](https://www.docker.com/products/docker-desktop/) (for Qdrant)
- **Git** - [Download](https://git-scm.com/downloads)

### 2. Get API Keys

You'll need two API keys:

#### Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key

#### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Copy the key

### 3. Installation Steps

#### Step 1: Clone and Navigate
```bash
cd backend
```

#### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Configure Environment
```bash
# Copy the example environment file
cp .env .env

# Edit .env with your API keys
# Windows: notepad .env
# Linux/Mac: nano .env
```

Edit the `.env` file:
```env
GOOGLE_API_KEY=your_actual_gemini_api_key_here
OPENAI_API_KEY=your_actual_openai_api_key_here
```

#### Step 5: Start Qdrant Vector Database
```bash
docker-compose up -d
```

Wait a few seconds for Qdrant to start, then verify it's running:
```bash
# Check if Qdrant is running
curl http://localhost:6333/
```

#### Step 6: Start the Backend Server
```bash
# Option 1: Using the startup script
# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh

# Option 2: Direct uvicorn command
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Installation

Open your browser and go to:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Qdrant Dashboard**: http://localhost:6333/dashboard

### 5. Test the API

Run the test script:
```bash
python test_api.py
```

Or test manually with curl:
```bash
# Health check
curl http://localhost:8000/health

# Upload a PDF
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@path/to/your/paper.pdf"
```

## Troubleshooting

### Issue: "Module not found" errors
**Solution**: Make sure you're in the virtual environment and all dependencies are installed
```bash
pip install -r requirements.txt
```

### Issue: "Connection refused" to Qdrant
**Solution**: Ensure Qdrant is running
```bash
docker-compose up -d
docker ps  # Should show qdrant container
```

### Issue: "Invalid API key" errors
**Solution**: Double-check your `.env` file has the correct API keys with no extra spaces

### Issue: Port 8000 already in use
**Solution**: Change the port in `.env`:
```env
PORT=8001
```

### Issue: Docker not running
**Solution**: 
- Windows: Start Docker Desktop
- Linux: `sudo systemctl start docker`
- Mac: Start Docker Desktop

## Project Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create from .env.example)
├── docker-compose.yml         # Qdrant setup
├── services/
│   ├── pdf_parser.py         # PDF text extraction
│   ├── text_chunker.py       # Intelligent text chunking
│   ├── embedding_service.py  # OpenAI embeddings
│   ├── vector_store.py       # Qdrant vector database
│   ├── llm_service.py        # Gemini LLM integration
│   └── rag_pipeline.py       # Main RAG orchestration
├── models/
│   └── schemas.py            # Pydantic data models
└── logs/                     # Application logs (auto-created)
```

## Next Steps

1. **Upload a research paper**: Use the `/upload` endpoint
2. **Ask questions**: Use the `/query` endpoint
3. **Analyze papers**: Use the `/analyze/{document_id}` endpoint
4. **Integrate with frontend**: Connect your Next.js frontend to this API

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root/health check |
| GET | `/health` | Detailed health status |
| POST | `/upload` | Upload and process PDF |
| POST | `/query` | Ask questions about papers |
| GET | `/analyze/{id}` | Comprehensive paper analysis |
| DELETE | `/documents/{id}` | Delete a document |
| GET | `/stats` | Vector store statistics |

## Development Tips

1. **Auto-reload**: The server auto-reloads when you change code (with `--reload` flag)
2. **Logs**: Check `logs/app.log` for detailed debugging
3. **API Docs**: Visit `/docs` for interactive API documentation
4. **Qdrant UI**: Visit `http://localhost:6333/dashboard` to inspect vectors

## Production Deployment

For production:
1. Set `DEBUG=False` in `.env`
2. Use a production WSGI server (gunicorn)
3. Set up proper CORS origins
4. Use managed Qdrant Cloud
5. Implement authentication
6. Add rate limiting

## Support

For issues or questions:
1. Check the logs in `logs/app.log`
2. Verify all services are running
3. Test with the provided `test_api.py` script

