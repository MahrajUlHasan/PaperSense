# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Run Setup Script

**Windows:**
```bash
cd backend
setup.bat
```

**Linux/Mac:**
```bash
cd backend
chmod +x setup.sh
./setup.sh
```

This will:
- ✅ Create a virtual environment
- ✅ Install all dependencies
- ✅ Set up the project structure

### Step 2: Configure API Keys

1. Copy the example environment file:
```bash
copy .env.example .env    # Windows
cp .env.example .env      # Linux/Mac
```

2. Edit `.env` and add your API keys:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Get API Keys:**
- Google Gemini: https://makersuite.google.com/app/apikey
- OpenAI: https://platform.openai.com/api-keys

### Step 3: Start Qdrant Database

```bash
docker-compose up -d
```

Wait 5 seconds for Qdrant to start.

### Step 4: Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Step 5: Run the Backend

```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload
```

### Step 6: Test the API

Open your browser:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

Or run the test script:
```bash
python test_api.py
```

## 🎉 You're Ready!

Your backend is now running at `http://localhost:8000`

## 📝 Next Steps

1. **Upload a PDF**: Use the `/upload` endpoint
2. **Ask Questions**: Use the `/query` endpoint
3. **Analyze Papers**: Use the `/analyze/{id}` endpoint

## 🔧 Troubleshooting

### Issue: "Python not found"
**Solution**: Install Python 3.9+ from https://www.python.org/downloads/

### Issue: "Docker not running"
**Solution**: Install and start Docker Desktop

### Issue: "Module not found"
**Solution**: Make sure virtual environment is activated and run:
```bash
pip install -r requirements.txt
```

### Issue: "Port 8000 in use"
**Solution**: Change port in `.env`:
```env
PORT=8001
```

## 📚 Documentation

- **Full Setup Guide**: See `SETUP_GUIDE.md`
- **Dependencies**: See `DEPENDENCIES.md`
- **API Reference**: Visit http://localhost:8000/docs when running

## 💡 Tips

- Use `--reload` flag for auto-restart during development
- Check `logs/app.log` for detailed debugging
- Visit Qdrant dashboard at http://localhost:6333/dashboard

