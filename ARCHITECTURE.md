# 🏗️ System Architecture

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│                     http://localhost:5173                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │   Upload ID      │         │  Verify Identity │             │
│  │                  │         │                  │             │
│  │  • File Upload   │         │  • Camera Feed   │             │
│  │  • Camera Capture│         │  • Liveness Check│             │
│  │  • Face Extract  │         │  • ID Comparison │             │
│  └──────────────────┘         └──────────────────┘             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Progress: ID → Liveness → Verify              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/CORS
                         │ Fetch API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│                     http://localhost:8000                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  API Endpoints:                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ POST /extract-face       │ Extract face from ID        │    │
│  │ POST /liveness-check     │ Verify liveness             │    │
│  │ POST /verify-identity    │ Match faces                 │    │
│  │ POST /complete-verification │ Full workflow            │    │
│  │ GET  /health             │ System status               │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└────────┬──────────────┬──────────────┬─────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌────────────────┐ ┌────────────┐ ┌──────────────────┐
│ ID Face        │ │ Anti-      │ │ Face             │
│ Extractor      │ │ Spoofing   │ │ Verification     │
│                │ │ Engine     │ │ System           │
│ (InsightFace)  │ │ (MiniFAS)  │ │ (ArcFace)        │
└────────────────┘ └────────────┘ └──────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────────────────────────────────────────────┐
│                   AI Models                         │
├─────────────────────────────────────────────────────┤
│ • Buffalo_L (Face Detection & Recognition)          │
│ • MiniFASNet V1/V2 (Anti-Spoofing)                 │
│ • RetinaFace (Face Detection)                       │
│ • ArcFace Embeddings (Face Matching)                │
└─────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌──────────┐
│  User    │
└────┬─────┘
     │
     │ 1. Upload ID Image
     ▼
┌─────────────────────┐
│  Frontend (React)   │
└─────────┬───────────┘
          │
          │ POST /extract-face
          ▼
┌─────────────────────────────┐
│  Backend API (FastAPI)      │
└─────────┬───────────────────┘
          │
          │ Process with InsightFace
          ▼
┌─────────────────────────────┐
│  ID_Face_Ext.py             │
│  • Detect face in ID        │
│  • Extract & align face     │
│  • Save to Extracted_Faces/ │
└─────────┬───────────────────┘
          │
          │ Return face URL
          ▼
┌─────────────────────┐
│  Frontend           │
│  • Show extracted   │
│  • Move to step 2   │
└─────────┬───────────┘
          │
          │ 2. Start Camera
          │ 3. Capture Live Frame
          ▼
┌─────────────────────┐
│  Frontend           │
└─────────┬───────────┘
          │
          │ POST /liveness-check
          ▼
┌─────────────────────────────┐
│  Backend API                │
└─────────┬───────────────────┘
          │
          │ Verify liveness
          ▼
┌─────────────────────────────┐
│  antispoofing_engine.py     │
│  • Detect face              │
│  • Check for spoofing       │
│  • Return is_live status    │
└─────────┬───────────────────┘
          │
          │ If live: continue
          ▼
┌─────────────────────┐
│  Frontend           │
└─────────┬───────────┘
          │
          │ POST /verify-identity
          │ (live_image + id_face_path)
          ▼
┌─────────────────────────────┐
│  Backend API                │
└─────────┬───────────────────┘
          │
          │ Compare faces
          ▼
┌─────────────────────────────┐
│  ISF.py (FaceVerifier)      │
│  • Extract embeddings       │
│  • Calculate similarity     │
│  • Return match result      │
└─────────┬───────────────────┘
          │
          │ Return verification
          ▼
┌─────────────────────┐
│  Frontend           │
│  • Display result   │
│  • Show similarity  │
│  • ✅ or ❌         │
└───────────────────┘
```

## File Structure Flow

```
User Interaction
       │
       ▼
┌──────────────────┐
│  ID Image Upload │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│  uploads/                    │
│  └── id_temp.jpg (temporary) │
└────────┬─────────────────────┘
         │ Extract Face
         ▼
┌──────────────────────────────┐
│  Extracted_Faces/            │
│  └── id_temp_face.jpg        │
└────────┬─────────────────────┘
         │ Serve via /extracted/
         ▼
┌──────────────────────────────┐
│  Frontend displays extracted │
└──────────────────────────────┘
         │
         │ Live Capture
         ▼
┌──────────────────────────────┐
│  uploads/                    │
│  └── live_capture.jpg (temp) │
└────────┬─────────────────────┘
         │ Verify
         ▼
┌──────────────────────────────┐
│  Comparison & Result         │
└──────────────────────────────┘
         │ Cleanup
         ▼
┌──────────────────────────────┐
│  Temp files deleted          │
└──────────────────────────────┘
```

## Technology Stack Flow

```
┌───────────────────────────────────────────┐
│           User Browser                     │
│  ┌──────────────────────────────────┐    │
│  │  React 18 + Vite                 │    │
│  │  • State Management              │    │
│  │  • Camera Access (WebRTC)        │    │
│  │  • HTTP Fetch                    │    │
│  └──────────────────────────────────┘    │
└──────────────┬────────────────────────────┘
               │ CORS-enabled
               │ JSON/FormData
               ▼
┌───────────────────────────────────────────┐
│         FastAPI Server                     │
│  ┌──────────────────────────────────┐    │
│  │  • Async endpoints               │    │
│  │  • File handling                 │    │
│  │  • Static files                  │    │
│  └──────────────────────────────────┘    │
└──────────┬────────────────────────────────┘
           │
           ├─────────────────┬──────────────┐
           ▼                 ▼              ▼
    ┌─────────────┐  ┌────────────┐  ┌──────────┐
    │ InsightFace │  │  OpenCV    │  │  NumPy   │
    │             │  │            │  │          │
    │ • Buffalo_L │  │ • imread   │  │ • Arrays │
    │ • ArcFace   │  │ • imencode │  │ • Math   │
    └─────────────┘  └────────────┘  └──────────┘
           │
           ▼
    ┌─────────────┐
    │ PyTorch     │
    │ • MiniFAS   │
    │ • Models    │
    └─────────────┘
```

---

**Visual guides to understand the complete system architecture**
