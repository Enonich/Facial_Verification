# 🔐 Liveness Detection Web Application

A real-time face liveness detection system with a React frontend and FastAPI backend using InsightFace.

## 🌟 Features

- **Real-time webcam capture** in the browser
- **Active liveness detection** (blink detection, head movement)
- **Passive anti-spoofing** (texture analysis, motion detection)
- **Beautiful responsive UI** with visual feedback
- **Fast API** with CORS support

## 📁 Project Structure

```
Insightface/
├── backend/
│   ├── app.py                 # FastAPI server
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main React component
│   │   ├── App.css           # Styles
│   │   ├── main.jsx          # Entry point
│   │   └── index.css
│   ├── index.html
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Vite configuration
├── liveness_det.py           # Core liveness detection engine
└── README.md
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- Webcam

### Backend Setup

1. **Navigate to the backend folder:**
   ```bash
   cd backend
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the FastAPI server:**
   ```bash
   python app.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

   The backend will run on `http://localhost:8000`

### Frontend Setup

1. **Open a new terminal and navigate to the frontend folder:**
   ```bash
   cd frontend
   ```

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will run on `http://localhost:3000`

## 🎮 Usage

1. Open your browser and go to `http://localhost:3000`
2. Allow camera access when prompted
3. Position your face in front of the camera
4. Click **"Start Liveness Check"**
5. Perform the requested actions:
   - Blink your eyes
   - Move your head slightly
6. Wait for verification ✅

## 🔧 API Endpoints

### `GET /`
Health check endpoint

### `GET /health`
Returns API health status and engine readiness

### `POST /verify`
Verify liveness from uploaded image frame
- **Body:** `multipart/form-data` with `file` field
- **Returns:** 
  ```json
  {
    "is_live": true,
    "message": "Liveness verified",
    "status": "success"
  }
  ```

### `POST /reset`
Reset the liveness engine state (clears blink counter, previous frames)

## 🛠 Technology Stack

**Backend:**
- FastAPI - Modern Python web framework
- InsightFace - Face analysis
- OpenCV - Image processing
- Uvicorn - ASGI server

**Frontend:**
- React - UI library
- Vite - Build tool
- Modern CSS with gradients and animations

## 📝 How It Works

1. **Frontend** captures video frames from webcam
2. **Frames** are sent to backend API every 500ms
3. **Backend** runs liveness detection:
   - Active checks (blink, head movement)
   - Passive checks (texture, motion analysis)
4. **Results** are displayed in real-time
5. **Success** when liveness is confirmed

## 🐛 Troubleshooting

**Camera not working:**
- Ensure you've granted camera permissions
- Check if another application is using the camera
- Try a different browser (Chrome/Edge recommended)

**Backend connection error:**
- Verify backend is running on port 8000
- Check CORS settings in `app.py`
- Ensure no firewall is blocking the connection

**Liveness check always fails:**
- Ensure good lighting
- Position face clearly in frame
- Try blinking or moving head more noticeably

## 📄 License

MIT License

## 👨‍💻 Author

Created for a robust facial verification while checking for face liveness detection using InsightFace
