from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import sys
import os
from pathlib import Path
import shutil
from typing import Optional

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from antispoofing_engine import AntiSpoofingEngine
from ID_Face_Ext import IDFaceExtractor
from ISF import FaceVerificationSystem

app = FastAPI(title="Identity Verification API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories for storing files
UPLOAD_DIR = Path("uploads")
EXTRACTED_FACES_DIR = Path("Extracted_Faces")
UPLOAD_DIR.mkdir(exist_ok=True)
EXTRACTED_FACES_DIR.mkdir(exist_ok=True)

# Mount static files to serve extracted faces
app.mount("/extracted", StaticFiles(directory=str(EXTRACTED_FACES_DIR)), name="extracted")

# Initialize engines
antispoofing_engine = None
id_extractor = None
face_verifier = None

@app.on_event("startup")
async def startup_event():
    global antispoofing_engine, id_extractor, face_verifier
    print("🚀 Initializing Identity Verification System...")
    
    try:
        # Initialize Anti-Spoofing Engine
        print("  ⏳ Loading Anti-Spoofing Engine...")
        antispoofing_engine = AntiSpoofingEngine(confidence_threshold=0.7)
        print("  ✅ Anti-Spoofing Engine ready")
        
        # Initialize ID Face Extractor
        print("  ⏳ Loading ID Face Extractor...")
        id_extractor = IDFaceExtractor(det_size=(640, 640))
        print("  ✅ ID Face Extractor ready")
        
        # Initialize Face Verification System
        print("  ⏳ Loading Face Verification System...")
        face_verifier = FaceVerificationSystem(
            model_name='buffalo_l',
            use_gpu=False,  # Set to True if you have GPU
            det_size=(640, 640)
        )
        print("  ✅ Face Verification System ready")
        
        print("🎉 All systems initialized successfully!")
        
    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
        raise

@app.get("/")
async def root():
    return {
        "message": "Identity Verification API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "antispoofing_ready": antispoofing_engine is not None,
        "id_extractor_ready": id_extractor is not None,
        "face_verifier_ready": face_verifier is not None
    }

@app.post("/extract-face")
async def extract_face_from_id(file: UploadFile = File(...)):
    """
    Extract face from ID document
    
    Returns:
        - success: boolean
        - message: status message
        - face_image_url: URL to access extracted face
        - confidence: detection confidence
        - bbox: bounding box coordinates
    """
    if id_extractor is None:
        raise HTTPException(status_code=503, detail="ID Extractor not initialized")
    
    try:
        # Save uploaded file temporarily
        temp_file_path = UPLOAD_DIR / file.filename
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract face from ID
        result = id_extractor.extract_face(
            image_path=str(temp_file_path),
            output_dir=str(EXTRACTED_FACES_DIR)
        )
        
        # Clean up temp file
        temp_file_path.unlink()
        
        if result is None:
            return JSONResponse(content={
                "success": False,
                "message": "No face detected in the ID document",
                "face_image_url": None,
                "confidence": 0.0,
                "bbox": None
            })
        
        # Get relative path for URL
        face_filename = Path(result["output_path"]).name
        face_url = f"/extracted/{face_filename}"
        
        return JSONResponse(content={
            "success": True,
            "message": "Face extracted successfully",
            "face_image_url": face_url,
            "confidence": result["confidence"],
            "bbox": result["bbox"]
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error extracting face: {str(e)}",
                "face_image_url": None,
                "confidence": 0.0,
                "bbox": None
            }
        )

@app.post("/liveness-check")
async def liveness_check(file: UploadFile = File(...)):
    """
    Perform liveness detection on uploaded image
    
    Returns:
        - is_live: boolean indicating if face is live
        - confidence: confidence score
        - message: status message
        - bbox: face bounding box
    """
    if antispoofing_engine is None:
        raise HTTPException(status_code=503, detail="Anti-Spoofing Engine not initialized")
    
    try:
        # Read image file
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Run anti-spoofing detection
        is_live, message, confidence, bbox = antispoofing_engine.verify(frame)
        
        return JSONResponse(content={
            "is_live": is_live,
            "confidence": confidence,
            "message": message,
            "bbox": bbox,
            "status": "success"
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "is_live": False,
                "confidence": 0.0,
                "message": f"Error: {str(e)}",
                "bbox": None,
                "status": "error"
            }
        )

@app.post("/verify-identity")
async def verify_identity(
    live_image: UploadFile = File(...),
    id_face_path: str = Form(...)
):
    """
    Verify identity by comparing live image with extracted ID face
    
    Args:
        live_image: Live captured image
        id_face_path: Path/URL to extracted face from ID
    
    Returns:
        - verified: boolean indicating if identity is verified
        - similarity: similarity score (0-1)
        - confidence: confidence level
        - message: status message
    """
    if face_verifier is None:
        raise HTTPException(status_code=503, detail="Face Verifier not initialized")
    
    try:
        # Save live image temporarily
        live_temp_path = UPLOAD_DIR / "live_capture.jpg"
        with open(live_temp_path, "wb") as buffer:
            shutil.copyfileobj(live_image.file, buffer)
        
        # Convert URL path to actual file path
        # id_face_path comes as "/extracted/filename.jpg"
        if id_face_path.startswith("/extracted/"):
            id_filename = id_face_path.replace("/extracted/", "")
            id_file_path = EXTRACTED_FACES_DIR / id_filename
        else:
            id_file_path = Path(id_face_path)
        
        if not id_file_path.exists():
            raise HTTPException(status_code=404, detail=f"ID face not found: {id_face_path}")
        
        # Perform verification
        verification_result = face_verifier.verify(
            id_photo_path=str(id_file_path),
            live_photo_path=str(live_temp_path)
        )
        
        # Clean up temp file
        live_temp_path.unlink()
        
        if not verification_result.get('success', False):
            return JSONResponse(content={
                "verified": False,
                "similarity": 0.0,
                "confidence": 0.0,
                "message": verification_result.get('error', 'Verification failed'),
                "status": "error"
            })
        
        # Extract results
        is_match = verification_result.get('match', False)
        similarity = verification_result.get('similarity', 0.0)
        
        # Determine confidence level
        if similarity >= 0.6:
            confidence_level = "high"
            confidence = 0.95
        elif similarity >= 0.5:
            confidence_level = "medium"
            confidence = 0.75
        else:
            confidence_level = "low"
            confidence = 0.5
        
        message = f"Identity {'verified' if is_match else 'not verified'} - {confidence_level} confidence"
        
        return JSONResponse(content={
            "verified": is_match,
            "similarity": float(similarity),
            "confidence": float(confidence),
            "confidence_level": confidence_level,
            "message": message,
            "processing_time": verification_result.get('processing_time_ms', 0),
            "status": "success"
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "verified": False,
                "similarity": 0.0,
                "confidence": 0.0,
                "message": f"Error: {str(e)}",
                "status": "error"
            }
        )

@app.post("/complete-verification")
async def complete_verification(
    id_image: UploadFile = File(...),
    live_image: UploadFile = File(...)
):
    """
    Complete end-to-end verification in one call:
    1. Extract face from ID
    2. Check liveness of live image
    3. Verify identity
    
    Returns complete verification result
    """
    try:
        # Step 1: Extract face from ID
        id_temp_path = UPLOAD_DIR / f"id_{id_image.filename}"
        with open(id_temp_path, "wb") as buffer:
            shutil.copyfileobj(id_image.file, buffer)
        
        id_result = id_extractor.extract_face(
            image_path=str(id_temp_path),
            output_dir=str(EXTRACTED_FACES_DIR)
        )
        
        if id_result is None:
            return JSONResponse(content={
                "success": False,
                "stage": "id_extraction",
                "message": "No face detected in ID document"
            })
        
        # Step 2: Check liveness
        live_temp_path = UPLOAD_DIR / f"live_{live_image.filename}"
        with open(live_temp_path, "wb") as buffer:
            shutil.copyfileobj(live_image.file, buffer)
        
        live_img = cv2.imread(str(live_temp_path))
        is_live, liveness_msg, liveness_conf, bbox = antispoofing_engine.verify(live_img)
        
        if not is_live:
            return JSONResponse(content={
                "success": False,
                "stage": "liveness_check",
                "message": f"Liveness check failed: {liveness_msg}",
                "liveness_confidence": liveness_conf
            })
        
        # Step 3: Verify identity
        verification_result = face_verifier.verify(
            id_photo_path=id_result["output_path"],
            live_photo_path=str(live_temp_path)
        )
        
        # Clean up
        id_temp_path.unlink()
        live_temp_path.unlink()
        
        if not verification_result.get('success', False):
            return JSONResponse(content={
                "success": False,
                "stage": "identity_verification",
                "message": verification_result.get('error', 'Verification failed')
            })
        
        return JSONResponse(content={
            "success": True,
            "verified": verification_result.get('match', False),
            "similarity": verification_result.get('similarity', 0.0),
            "liveness_confidence": liveness_conf,
            "id_extraction_confidence": id_result["confidence"],
            "message": "Complete verification successful",
            "processing_time": verification_result.get('processing_time_ms', 0)
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}"
            }
        )

@app.post("/reset")
async def reset_system():
    """
    Reset the system state
    """
    try:
        if antispoofing_engine is not None:
            antispoofing_engine.reset()
        
        # Clean up temporary files
        for file in UPLOAD_DIR.glob("*"):
            file.unlink()
        
        return {
            "status": "success",
            "message": "System reset successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
