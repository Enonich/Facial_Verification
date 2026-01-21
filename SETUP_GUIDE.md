# 🚀 Quick Setup Guide

## Installation Steps

### 1️⃣ Backend Setup

```powershell
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Test backend
python -c "import fastapi, cv2, insightface; print('✅ All imports successful')"
```

### 2️⃣ Frontend Setup

```powershell
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Test build
npm run build
```

### 3️⃣ Verify Models

Ensure the following directories exist with models:

```
Silent_Face_Anti_Spoofing/resources/
├── anti_spoof_models/
│   ├── 2.7_80x80_MiniFASNetV2.pth
│   └── 4_0_0_80x80_MiniFASNetV1SE.pth
└── detection_model/
    ├── deploy.prototxt
    └── Widerface-RetinaFace.caffemodel
```

InsightFace models will be downloaded automatically on first run to:
```
~/.insightface/models/buffalo_l/
```

### 4️⃣ First Run

```powershell
# From project root
.\start-all.ps1
```

This will:
1. Start backend server on http://localhost:8000
2. Start frontend server on http://localhost:5173
3. Initialize all AI models (may take 1-2 minutes first time)

### 5️⃣ Test the System

1. Open browser to http://localhost:5173
2. Upload a test ID image
3. Verify face extraction works
4. Test liveness detection with webcam
5. Complete full verification workflow

## 🔍 Verification Checklist

- [ ] Backend server starts without errors
- [ ] Frontend opens in browser
- [ ] Camera permission granted
- [ ] ID upload works
- [ ] Face extraction successful
- [ ] Liveness detection working
- [ ] Identity verification completes

## ⚡ Quick Commands

```powershell
# Start backend only
cd backend
python app.py

# Start frontend only
cd frontend
npm run dev

# Check backend health
curl http://localhost:8000/health

# View API docs
# Open: http://localhost:8000/docs
```

## 🐛 Common Issues

### "Module not found" errors
```powershell
pip install -r backend/requirements.txt --force-reinstall
```

### Port already in use
```powershell
# Change ports in:
# - backend/app.py: uvicorn.run(app, host="0.0.0.0", port=8000)
# - frontend/vite.config.js: server: { port: 5173 }
```

### Models not loading
```powershell
# Download models manually or check internet connection
# InsightFace models auto-download on first run
```

---

**You're all set! 🎉**
