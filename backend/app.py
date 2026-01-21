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
                "error_code": "NO_FACE_DETECTED",
                "error_stage": "id_extraction",
                "stage_description": "Extracting face from ID document",
                "details": "The system could not detect a face in the uploaded ID document.",
                "recommendation": "Please ensure your ID photo is clear, the face is visible, and the image is not blurry or obstructed.",
                "face_image_url": None,
                "confidence": 0.0,
                "bbox": None
            })
        
        # Get relative path for URL
        face_filename = Path(result["output_path"]).name
        face_url = f"/extracted/{face_filename}"
        
        # Also get embedding path for direct verification
        embedding_filename = Path(result.get("embedding_path", "")).name if result.get("embedding_path") else None
        embedding_url = f"/extracted/{embedding_filename}" if embedding_filename else None
        
        return JSONResponse(content={
            "success": True,
            "message": "Face extracted successfully",
            "face_image_url": face_url,
            "embedding_url": embedding_url,
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
            return JSONResponse(content={
                "is_live": False,
                "confidence": 0.0,
                "message": "Invalid image data - could not decode image",
                "error_code": "IMAGE_DECODE_FAILED",
                "error_stage": "image_loading",
                "bbox": None,
                "status": "error"
            })
        
        # Run anti-spoofing detection
        is_live, message, confidence, bbox = antispoofing_engine.verify(frame)
        
        response_data = {
            "is_live": is_live,
            "confidence": confidence,
            "message": message,
            "bbox": bbox,
            "status": "success"
        }
        
        if not is_live:
            response_data["error_code"] = "LIVENESS_FAILED"
            response_data["error_stage"] = "liveness_check"
            response_data["stage_description"] = "Verifying live presence"
            response_data["details"] = "The system detected that the image may be a spoof attempt (printed photo, screen display, or mask)."
            response_data["recommendation"] = "Please use a live camera in good lighting. Ensure your face is clearly visible and not obscured."
        
        return JSONResponse(content=response_data)
    
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
            # Clean up temp file before returning error
            if live_temp_path.exists():
                live_temp_path.unlink()
            raise HTTPException(status_code=404, detail=f"ID face not found: {id_face_path}")
        
        # Try to use pre-computed embedding first (more reliable)
        # The embedding file should be named like: originalname_face_embedding.npy
        embedding_filename = id_file_path.stem + "_embedding.npy"
        embedding_path = EXTRACTED_FACES_DIR / embedding_filename
        
        if embedding_path.exists():
            # Use pre-computed embedding for verification (more reliable)
            verification_result = face_verifier.verify_with_embedding(
                id_embedding_path=str(embedding_path),
                live_photo_path=str(live_temp_path)
            )
        else:
            # Fall back to image-based verification
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
                "error_code": verification_result.get('error_code', 'UNKNOWN_ERROR'),
                "error_stage": verification_result.get('error_stage', 'unknown'),
                "stage_description": verification_result.get('stage_description', 'Unknown stage'),
                "details": verification_result.get('details', ''),
                "recommendation": verification_result.get('recommendation', 'Please try again.'),
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
        
        # Build response with detailed information
        response_data = {
            "verified": is_match,
            "similarity": float(similarity),
            "similarity_percentage": verification_result.get('similarity_percentage', round(similarity * 100, 2)),
            "confidence": float(confidence),
            "confidence_level": confidence_level,
            "match_confidence": verification_result.get('match_confidence', 'unknown'),
            "match_description": verification_result.get('match_description', ''),
            "threshold": verification_result.get('threshold', 0.5),
            "threshold_percentage": verification_result.get('threshold_percentage', 50.0),
            "message": f"Identity {'verified' if is_match else 'not verified'} - {confidence_level} confidence",
            "processing_time": verification_result.get('processing_time_ms', 0),
            "status": "success"
        }
        
        # Add failure details if verification failed
        if not is_match:
            # Providing details on why the match failed, but not marking as a system error
            response_data["recommendation"] = verification_result.get('recommendation', 'Please try again with better lighting.')
            response_data["non_match_reason"] = verification_result.get('match_description', 'Faces do not match')
        
        return JSONResponse(content=response_data)
    
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
                "verified": False,
                "error_stage": "id_extraction",
                "stage_description": "Extracting face from ID document",
                "error_code": "ID_FACE_NOT_DETECTED",
                "message": "No face detected in ID document",
                "details": "The system could not detect a face in the uploaded ID document.",
                "recommendation": "Please ensure your ID photo is clear, well-lit, and shows your full face without obstruction."
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
                "verified": False,
                "error_stage": "liveness_check",
                "stage_description": "Verifying live presence",
                "error_code": "LIVENESS_FAILED",
                "message": f"Liveness check failed: {liveness_msg}",
                "liveness_confidence": liveness_conf,
                "details": "The system detected that the captured image may not be from a live person.",
                "recommendation": "Please ensure you are using a live camera (not a photo), have good lighting, and your face is clearly visible."
            })
        
        # Step 3: Verify identity using pre-computed embedding (more reliable)
        embedding_path = id_result.get("embedding_path")
        
        if embedding_path and Path(embedding_path).exists():
            # Use pre-computed embedding for verification
            verification_result = face_verifier.verify_with_embedding(
                id_embedding_path=embedding_path,
                live_photo_path=str(live_temp_path)
            )
        else:
            # Fall back to image-based verification
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
                "verified": False,
                "error_stage": verification_result.get('error_stage', 'identity_verification'),
                "stage_description": verification_result.get('stage_description', 'Verifying identity'),
                "error_code": verification_result.get('error_code', 'VERIFICATION_ERROR'),
                "message": verification_result.get('error', 'Verification failed'),
                "details": verification_result.get('details', ''),
                "recommendation": verification_result.get('recommendation', 'Please try again.')
            })
        
        # Build comprehensive success response
        is_match = verification_result.get('match', False)
        
        response_data = {
            "success": True,
            "verified": is_match,
            "similarity": verification_result.get('similarity', 0.0),
            "similarity_percentage": verification_result.get('similarity_percentage', 0.0),
            "threshold": verification_result.get('threshold', 0.5),
            "threshold_percentage": verification_result.get('threshold_percentage', 50.0),
            "match_confidence": verification_result.get('match_confidence', 'unknown'),
            "match_description": verification_result.get('match_description', ''),
            "liveness_confidence": liveness_conf,
            "id_extraction_confidence": id_result["confidence"],
            "processing_time": verification_result.get('processing_time_ms', 0)
        }
        
        if is_match:
            response_data["message"] = "Complete verification successful - Identity verified!"
        else:
            response_data["message"] = f"Verification complete but identity NOT verified: {verification_result.get('match_description', 'Faces do not match')}"
            response_data["recommendation"] = verification_result.get('recommendation', 'Please ensure you are the person shown in the ID document.')
            response_data["non_match_reason"] = verification_result.get('match_description', 'Faces do not match')
        
        return JSONResponse(content=response_data)
    
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
