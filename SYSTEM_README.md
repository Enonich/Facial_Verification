# 🛡️ Identity Verification System

A professional, bank-level identity verification system with liveness detection and face matching capabilities.

## 🌟 Features

- **ID Document Processing**: Extract face from government-issued IDs
- **Liveness Detection**: Real-time anti-spoofing to prevent photo/video attacks
- **Identity Verification**: Compare live face against ID photo using InsightFace
- **Professional UI**: Dark-themed, bank-grade user interface
- **Real-time Processing**: Live camera feed with instant verification

## 🏗️ Architecture

### Backend (FastAPI)
- **ID Face Extractor**: Uses InsightFace to extract and align faces from ID documents
- **Anti-Spoofing Engine**: Silent Face Anti-Spoofing for liveness detection
- **Face Verification**: ArcFace-based face matching with high accuracy

### Frontend (React + Vite)
- Modern React application with professional dark UI
- Side navigation for workflow management
- Real-time camera integration
- Progress tracking and status indicators

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- Webcam (for liveness detection)

## 🚀 Quick Start

### 1. Install Backend Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```powershell
cd frontend
npm install
```

### 3. Start the Application

#### Option A: Start All Services (Recommended)
```powershell
.\start-all.ps1
```

#### Option B: Start Manually

**Terminal 1 - Backend:**
```powershell
.\start-backend.ps1
```

**Terminal 2 - Frontend:**
```powershell
.\start-frontend.ps1
```

### 4. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📖 How to Use

### Step 1: Upload ID Document
1. Navigate to "Upload ID" in the sidebar
2. Choose to either:
   - Upload an ID image file, or
   - Capture ID using camera
3. System extracts face from the ID automatically

### Step 2: Verify Identity
1. Navigate to "Verify Identity" in the sidebar
2. Click "Start Verification"
3. Position your face in the camera
4. System performs:
   - Liveness detection (anti-spoofing)
   - Face matching against ID
5. View verification results

## 🔌 API Endpoints

### `POST /extract-face`
Extract face from ID document
- **Input**: Image file (multipart/form-data)
- **Output**: Extracted face URL, confidence, bbox

### `POST /liveness-check`
Perform liveness detection
- **Input**: Live image file
- **Output**: is_live, confidence, message

### `POST /verify-identity`
Verify identity against ID
- **Input**: live_image (file), id_face_path (string)
- **Output**: verified, similarity, confidence

### `POST /complete-verification`
End-to-end verification in one call
- **Input**: id_image, live_image
- **Output**: Complete verification result

### `GET /health`
Check system health
- **Output**: Status of all engines

## 🎨 UI Features

- **Dark Professional Theme**: Bank-level aesthetic
- **Progress Steps**: Visual workflow tracking
- **Real-time Feedback**: Status badges and messages
- **Responsive Design**: Works on desktop and mobile
- **Smooth Animations**: Professional transitions

## 📁 Project Structure

```
Insightface/
├── backend/
│   ├── app.py                 # FastAPI server
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main React component
│   │   ├── App.css           # Styling
│   │   └── main.jsx          # Entry point
│   ├── package.json
│   └── vite.config.js
├── ID_Face_Ext.py            # ID face extraction module
├── antispoofing_engine.py    # Liveness detection engine
├── ISF.py                    # Face verification system
├── Extracted_Faces/          # Stored extracted faces
├── uploads/                  # Temporary uploads
├── start-all.ps1            # Start all services
├── start-backend.ps1        # Start backend only
└── start-frontend.ps1       # Start frontend only
```

## 🔧 Configuration

### Backend Configuration

Edit `backend/app.py`:

```python
# GPU/CPU selection
face_verifier = FaceVerificationSystem(
    model_name='buffalo_l',
    use_gpu=True,  # Set to False for CPU
    det_size=(640, 640)
)

# Liveness threshold
antispoofing_engine = AntiSpoofingEngine(
    confidence_threshold=0.7  # Adjust 0.0-1.0
)
```

### Frontend Configuration

The frontend automatically connects to `http://localhost:8000`. To change:

Edit API calls in `frontend/src/App.jsx`:
```javascript
const response = await fetch('http://your-backend-url:8000/endpoint', {
  method: 'POST',
  body: formData,
});
```

## 🛠️ Troubleshooting

### Backend won't start
- Ensure all Python dependencies are installed
- Check if models are downloaded in `Silent_Face_Anti_Spoofing/resources/`
- Verify Python version is 3.8+

### Frontend won't start
- Run `npm install` in frontend directory
- Check Node.js version (16+)
- Clear cache: `npm cache clean --force`

### Camera not working
- Grant browser camera permissions
- Check if another application is using the camera
- Try a different browser (Chrome recommended)

### Low verification accuracy
- Ensure good lighting conditions
- Position face clearly in frame
- Use high-quality ID images
- Adjust confidence thresholds in backend

## 📊 Performance

- **ID Extraction**: ~500ms
- **Liveness Detection**: ~200-300ms per frame
- **Face Verification**: ~100-200ms
- **Total Verification**: ~1-2 seconds

## 🔒 Security Features

- Anti-spoofing detection prevents photo/video attacks
- Real-time liveness verification
- High-accuracy face matching (ArcFace)
- Secure file handling with automatic cleanup
- CORS protection

## 📄 License

See individual module licenses:
- InsightFace: MIT
- Silent Face Anti-Spoofing: Apache 2.0

## 🙏 Acknowledgments

- **InsightFace**: Face recognition toolkit
- **Silent Face Anti-Spoofing**: Liveness detection
- **FastAPI**: Modern web framework
- **React**: UI framework
- **Vite**: Build tool

## 📞 Support

For issues or questions, please check:
1. API documentation at http://localhost:8000/docs
2. Browser console for frontend errors
3. Backend terminal for server logs

---

**Built with ❤️ for secure identity verification**
