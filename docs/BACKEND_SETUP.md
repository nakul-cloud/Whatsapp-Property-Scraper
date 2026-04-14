# Backend API Setup & Deployment Guide

## Architecture

The application now has a **decoupled architecture**:

- **Backend (FastAPI)**: Handles WhatsApp message processing, data extraction, and analysis
- **Frontend (React + Vite)**: User interface for uploading messages and viewing results
- **Streamlit App (Optional)**: Legacy UI that can run alongside the backend

## Development Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- Git

### 1. Backend Setup

```powershell
# Navigate to project root
cd "d:\Whatsapp Property Scrapper"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if not already done)
pip install -r requirements.txt

# Copy .env.example to .env and fill in your details
copy .env.example .env
```

### 2. Start Backend

```powershell
# Using the startup script
.\start-backend.ps1

# OR manually
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: **http://localhost:8000**
API Documentation: **http://localhost:8000/docs** (interactive Swagger UI)

### 3. Frontend Setup

```powershell
# In a new terminal
cd Frontend

# Install dependencies
npm install

# Create .env file with backend URL
echo "VITE_API_URL=http://localhost:8000" > .env

# Start dev server
npm run dev
```

Frontend will be available at: **http://localhost:5173**

## API Endpoints

### Core Endpoints

**POST /api/process-messages**
- Processes WhatsApp messages and extracts property leads
- Required: `raw_text` (WhatsApp text)
- Optional: `enable_ai`, `groq_api_key`, `groq_model`, `area_path`

```bash
curl -X POST http://localhost:8000/api/process-messages \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "[09/04, 2:49 pm] Easy Prop New:\nProperty Code: ABC123\n...",
    "enable_ai": false
  }'
```

**POST /api/analyze**
- Generate analysis metrics from extracted rows

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '[{...property_row...}, {...}]'
```

**POST /api/download**
- Export extracted leads as CSV

**POST /api/cache/manage**
- Manage combined cache (add, reset, export)

**GET /api/cache**
- View current combined cache

**GET /health**
- Health check endpoint

## Environment Variables

Create a `.env` file in the root directory:

```env
# Groq API (for AI fallback)
GROQ_API_KEY=your_api_key
GROQ_MODEL=llama-3.1-70b-versatile

# Files
AREAS_FILE=./areas_pune.txt

# Frontend (for CORS in development)
FRONTEND_URL=http://localhost:5173
```

## Running Streamlit (Optional)

The original Streamlit app still works:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

## Deployment on Vercel + Railway

### Backend Deployment (Railway)

1. Push code to GitHub
2. Create Railway account at https://railway.app
3. Connect GitHub repository
4. Create new Web Service
5. Set Python version and input variables (GROQ_API_KEY)
6. Deploy command:
   ```
   uvicorn backend:app --host 0.0.0.0 --port $PORT
   ```

### Frontend Deployment (Vercel)

1. Push code to GitHub
2. Import project in Vercel dashboard
3. Set root directory to `Frontend`
4. Set environment variable:
   ```
   VITE_API_URL=https://your-railway-app.up.railway.app
   ```
5. Deploy

### Environment Variables for Production

**Railway (Backend)**:
```
GROQ_API_KEY=your_api_key
GROQ_MODEL=llama-3.1-70b-versatile
AREAS_FILE=./areas_pune.txt
```

**Vercel (Frontend)**:
```
VITE_API_URL=https://your-railway-backend-url.up.railway.app
```

## Docker Deployment (Optional)

Create `Dockerfile` for backend:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```powershell
docker build -t property-scraper-backend .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key property-scraper-backend
```

## Testing the Integration

1. Start backend: `.\start-backend.ps1`
2. Start frontend: `npm run dev` (in Frontend folder)
3. Open http://localhost:5173
4. Paste WhatsApp messages and click "Process"
5. Frontend will call backend API and display results

## Troubleshooting

**Backend not responding?**
- Check if port 8000 is in use: `netstat -ano | findstr :8000`
- Verify .env file has correct GROQ_API_KEY
- Check backend logs for errors

**Frontend can't reach backend?**
- Verify VITE_API_URL is set correctly
- Check CORS settings in backend (currently allows all origins in dev)
- Open browser DevTools → Network tab to see API calls

**CSV export failing?**
- Ensure output columns match OUTPUT_COLUMNS in parser.py
- Check pandas version compatibility

## Next Steps

1. ✅ Backend API created
2. ✅ Frontend API utility updated
3. ⏭️ Deploy backend to Railway
4. ⏭️ Deploy frontend to Vercel
5. ⏭️ Update frontend with analysis charts
6. ⏭️ Add authentication (optional)
7. ⏭️ Set up database for persistent caching (replace in-memory cache)
