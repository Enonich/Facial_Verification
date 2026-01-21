from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import sys
import os

# Add parent directory to path to import anti-spoofing engine
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from antispoofing_engine import AntiSpoofingEngine

app = FastAPI(title="Anti-Spoofing Detection API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize anti-spoofing engine
engine = None

@app.on_event("startup")
async def startup_event():
    global engine
    print("Initializing Anti-Spoofing Engine...")
    try:
        engine = AntiSpoofingEngine(confidence_threshold=0.5)
        print("✅ Anti-Spoofing Engine ready")
    except Exception as e:
        print(f"❌ Failed to initialize engine: {e}")
        raiseAnti-Spoofing

@app.get("/")
async def root():
    return {"message": "Liveness Detection API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "engine_ready": engine is not None}

@app.post("/verify")
async def verify_liveness(file: UploadFile = File(...)):
    """
    Verify if uploaded image contains a real face or a spoofed/fake face
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # Read image file
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Run anti-spoofing detection
        is_live, message, confidence, bbox = engine.verify(frame)
        
        return JSONResponse(content={
            "is_live": is_live,
            "message": message,
            "confidence": confidence,
            "bbox": bbox,
            "status": "success"
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "is_live": False,
                "message": f"Error: {str(e)}",
                "confidence": 0.0,
                "bbox": None,
                "status": "error"
            }
        )
anti-spoofing engine state
    """
    global engine
    try:
        if engine is not None:
            engine.reset()
        else:
            engine = AntiSpoofingEngine(confidence_threshold=0.5)
        return {"status": "success", "message": "Engine reset successfully
    global engine
    try:
        engine = LivenessEngine()
        return {"status": "success", "message": "Engine reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
