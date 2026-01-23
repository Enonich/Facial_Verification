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
from difflib import SequenceMatcher

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from antispoofing_engine import AntiSpoofingEngine
from ID_Face_Ext import IDFaceExtractor
from ISF import FaceVerificationSystem
from id_card_ocr import IDCardOCR

def sanitize_for_json(obj):
    """Recursively convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, set):
        return [sanitize_for_json(v) for v in list(obj)]
    return obj

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
ocr_engine = None

@app.on_event("startup")
async def startup_event():
    global antispoofing_engine, id_extractor, face_verifier, ocr_engine
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
        
        # Initialize OCR Engine
        print("  ⏳ Loading OCR Engine...")
        ocr_engine = IDCardOCR()
        print("  ✅ OCR Engine ready")
        
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
        "face_verifier_ready": face_verifier is not None,
        "ocr_ready": ocr_engine is not None
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
        
        # Prepare response without non-serializable fields (face_image, embedding)
        response_data = {
            "success": True,
            "message": "Face extracted successfully",
            "face_image_url": face_url,
            "embedding_url": embedding_url,
            "confidence": result["confidence"],
            "bbox": result["bbox"],
            "quality": result.get("quality", {})
        }
        
        return JSONResponse(content=sanitize_for_json(response_data))
    
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
        is_live, message, confidence, bbox, face_count = antispoofing_engine.verify(frame)
        
        response_data = sanitize_for_json({
            "is_live": is_live,
            "confidence": confidence,
            "message": message,
            "bbox": bbox,
            "face_count": face_count,
            "status": "success"
        })
        
        if face_count > 1:
            response_data["error_code"] = "MULTIPLE_FACES"
            response_data["error_stage"] = "liveness_check"
            response_data["stage_description"] = "Verifying live presence"
            response_data["details"] = f"Multiple faces detected ({face_count}). Only one person should be visible in the frame."
            response_data["recommendation"] = "Please ensure only you are in the camera frame and retry."
            response_data["status"] = "error"
        elif not is_live:
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
    
    SECURITY: This endpoint performs BOTH liveness check AND face verification
    
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
    if antispoofing_engine is None:
        raise HTTPException(status_code=503, detail="Anti-Spoofing Engine not initialized")
    
    try:
        # Save live image temporarily
        live_temp_path = UPLOAD_DIR / "live_capture.jpg"
        with open(live_temp_path, "wb") as buffer:
            shutil.copyfileobj(live_image.file, buffer)
        
        # CRITICAL SECURITY STEP 1: Check liveness FIRST (with multiple face detection)
        live_img = cv2.imread(str(live_temp_path))
        if live_img is None:
            live_temp_path.unlink(missing_ok=True)
            return JSONResponse(content={
                "verified": False,
                "similarity": 0.0,
                "confidence": 0.0,
                "message": "Invalid live image data",
                "error_code": "IMAGE_DECODE_FAILED",
                "error_stage": "image_loading",
                "details": "Could not decode the live image.",
                "recommendation": "Please ensure the image is a valid JPEG or PNG file.",
                "status": "error"
            })
        
        # Perform liveness and multiple face detection
        is_live, liveness_msg, liveness_conf, bbox, face_count = antispoofing_engine.verify(live_img)
        
        # SECURITY CHECK: Reject if multiple faces detected
        if face_count > 1:
            live_temp_path.unlink(missing_ok=True)
            return JSONResponse(content={
                "verified": False,
                "similarity": 0.0,
                "confidence": 0.0,
                "message": f"Multiple faces detected ({face_count})",
                "face_count": face_count,
                "error_code": "MULTIPLE_FACES",
                "error_stage": "liveness_check",
                "stage_description": "Verifying live presence",
                "details": f"The system detected {face_count} faces in the frame. Only one person should be visible during verification.",
                "recommendation": "Please ensure only you are visible in the camera frame and retry.",
                "status": "error"
            })
        
        # SECURITY CHECK: Reject if liveness failed
        if not is_live:
            live_temp_path.unlink(missing_ok=True)
            return JSONResponse(content={
                "verified": False,
                "similarity": 0.0,
                "confidence": 0.0,
                "message": f"Liveness check failed: {liveness_msg}",
                "liveness_confidence": liveness_conf,
                "error_code": "LIVENESS_FAILED",
                "error_stage": "liveness_check",
                "stage_description": "Verifying live presence",
                "details": "The system detected that the image may not be from a live person (possible photo, screen, or mask).",
                "recommendation": "Please use a live camera in good lighting. Ensure your face is clearly visible and not obscured.",
                "status": "error"
            })
        
        # PASSED SECURITY CHECKS: Now proceed to face verification
        
        
        # PASSED SECURITY CHECKS: Now proceed to face verification
        
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
        
        # Try to load ID quality scores
        quality_filename = id_file_path.stem + "_quality.json"
        quality_path = EXTRACTED_FACES_DIR / quality_filename
        id_quality = None
        if quality_path.exists():
            try:
                import json
                with open(quality_path, 'r') as f:
                    id_quality = json.load(f)
            except:
                pass
        
        if embedding_path.exists():
            # Use pre-computed embedding for verification (more reliable)
            verification_result = face_verifier.verify_with_embedding(
                id_embedding_path=str(embedding_path),
                live_photo_path=str(live_temp_path),
                id_quality_metrics=id_quality  # Pass ID quality for logging
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
                "liveness_confidence": liveness_conf,  # Include liveness info
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
            
        # Get quality metrics
        live_quality = verification_result.get('live_quality', {})
        # id_quality is loaded from file or from verification_result if using image-based verify
        if not id_quality and 'id_quality' in verification_result:
             id_quality = verification_result['id_quality']

        # Generate recommendations based on quality
        recommendations = []
        if id_quality:
            if id_quality.get('blur_normalized', 1.0) < 0.3:
                recommendations.append("ID photo is blurry. Please provide a sharper image.")
            if id_quality.get('face_size_ratio', 1.0) < 0.02:
                recommendations.append("Face on ID is too small.")
            if id_quality.get('brightness_score', 1.0) < 0.3:
                 recommendations.append("ID photo is too dark or too bright.")
                 
        if live_quality:
            if live_quality.get('blur_normalized', 1.0) < 0.3:
                recommendations.append("Live photo is blurry. Hold the camera steady.")
            if live_quality.get('brightness_score', 1.0) < 0.3:
                 recommendations.append("Lighting is poor. Please move to a better lit area.")
            if live_quality.get('pose_score', 1.0) < 0.6:
                 recommendations.append("Please look directly at the camera.")
        
        # Build response with detailed information
        response_data = sanitize_for_json({
            "verified": is_match,
            "similarity": float(similarity),
            "similarity_percentage": verification_result.get('similarity_percentage', round(similarity * 100, 2)),
            "confidence": float(confidence),
            "confidence_level": confidence_level,
            "match_confidence": verification_result.get('match_confidence', 'unknown'),
            "match_description": verification_result.get('match_description', ''),
            "threshold": verification_result.get('threshold', 0.5),
            "threshold_percentage": verification_result.get('threshold_percentage', 50.0),
            "liveness_confidence": liveness_conf,  # Include liveness check result
            "face_count": face_count,  # Include face count for transparency
            "message": f"Identity {'verified' if is_match else 'not verified'} - {confidence_level} confidence (Liveness: ✓)",
            "processing_time": verification_result.get('processing_time_ms', 0),
            "status": "success",
            "id_quality": id_quality,
            "live_quality": live_quality,
            "quality_recommendations": recommendations,
            # Pass original failure reason if needed
            "non_match_reason": verification_result.get('match_description', 'Faces do not match') if not is_match else None
        })
        
        # Add failure details if verification failed
        if not is_match:
            # Providing details on why the match failed, but not marking as a system error
            base_rec = verification_result.get('recommendation', 'Faces do not match.')
            if recommendations:
                response_data["recommendation"] = f"{base_rec} Quality Tips: {' '.join(recommendations)}"
            else:
                response_data["recommendation"] = base_rec
                
            response_data["non_match_reason"] = verification_result.get('match_description', 'Faces do not match')
        elif recommendations:
             # Even on success, give warnings if quality is marginal
             response_data["message"] += f". Note: {' '.join(recommendations)}"
        
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
        is_live, liveness_msg, liveness_conf, bbox, face_count = antispoofing_engine.verify(live_img)
        
        if face_count > 1:
            return JSONResponse(content={
                "success": False,
                "verified": False,
                "error_stage": "liveness_check",
                "stage_description": "Verifying live presence",
                "error_code": "MULTIPLE_FACES",
                "message": f"Multiple faces detected ({face_count})",
                "liveness_confidence": liveness_conf,
                "face_count": face_count,
                "details": f"The system detected {face_count} faces in the frame. Only one person should be visible.",
                "recommendation": "Please ensure only you are visible in the camera frame and retry the verification."
            })
        
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
            # Try to load ID quality scores for logging
            id_quality = id_result.get("quality")
            
            verification_result = face_verifier.verify_with_embedding(
                id_embedding_path=embedding_path,
                live_photo_path=str(live_temp_path),
                id_quality_metrics=id_quality
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
        
        # Get quality metrics
        id_quality = id_result.get("quality", {})
        live_quality = verification_result.get("live_quality", {})
        
        # Generate recommendations based on quality
        recommendations = []
        if id_quality:
            if id_quality.get('blur_normalized', 1.0) < 0.3:
                recommendations.append("ID photo is blurry.")
            if id_quality.get('face_size_ratio', 1.0) < 0.02:
                recommendations.append("Face on ID is too small.")
            if id_quality.get('brightness_score', 1.0) < 0.3:
                 recommendations.append("ID photo lighting is poor.")
                 
        if live_quality:
            if live_quality.get('blur_normalized', 1.0) < 0.3:
                recommendations.append("Live photo is blurry.")
            if live_quality.get('brightness_score', 1.0) < 0.3:
                 recommendations.append("Live photo lighting is poor.")
            if live_quality.get('pose_score', 1.0) < 0.6:
                 recommendations.append("Look directly at the camera.")

        response_data = sanitize_for_json({
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
            "processing_time": verification_result.get('processing_time_ms', 0),
            "id_quality": id_quality,
            "live_quality": live_quality,
            "quality_recommendations": recommendations,
            # Pass original failure reason if needed
            "non_match_reason": verification_result.get('match_description', 'Faces do not match') if not is_match else None
        })
        
        if is_match:
            response_data["message"] = "Complete verification successful - Identity verified!"
            if recommendations:
                 response_data["message"] += f" (Note: {'; '.join(recommendations)})"
        else:
            base_msg = verification_result.get('match_description', 'Faces do not match')
            response_data["message"] = f"Verification complete but identity NOT verified: {base_msg}"
            
            # Combine generic recommendation with specific quality tips
            base_rec = verification_result.get('recommendation', 'Please ensure you are the person shown in the ID document.')
            if recommendations:
                response_data["recommendation"] = f"{base_rec} Tips: {'; '.join(recommendations)}"
            else:
                 response_data["recommendation"] = base_rec
                 
            response_data["non_match_reason"] = base_msg
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}"
            }
        )

def _string_similarity(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings (0-1)"""
    return SequenceMatcher(None, s1.upper(), s2.upper()).ratio()

def _normalize_name(name: str) -> str:
    """Normalize a name by removing extra spaces and special characters"""
    return ' '.join(name.upper().split())

def _normalize_id_number(id_number: str, id_type: str) -> str:
    """Normalize ID number based on type"""
    id_number = id_number.strip()
    if id_type == 'GH_CARD':
        # Keep as is for Ghana Card
        return id_number.upper()
    else:
        # Remove all non-alphanumeric for other types
        return ''.join(c for c in id_number if c.isalnum()).upper()
@app.post("/ocr-extract")
async def ocr_extract(
    file: UploadFile = File(...),
    id_type: str = Form(...)
):
    """Extract information from ID document using OCR."""
    if ocr_engine is None:
        raise HTTPException(status_code=503, detail="OCR Engine not initialized")
    
    try:
        # Map frontend ID type to OCR module format
        id_type_map = {
            'GH_CARD': 'ghana_card',
            'VOTERS_ID': 'voters_id',
            'PASSPORT': 'passport'
        }
        
        ocr_id_type = id_type_map.get(id_type, 'auto')
        
        # Save uploaded file temporarily
        temp_file_path = UPLOAD_DIR / f"ocr_temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # Perform OCR extraction
            ocr_result = ocr_engine.process_id_card(
                image_path=str(temp_file_path),
                card_type=ocr_id_type
            )
            
            if ocr_result is None:
                return JSONResponse(content={
                    "success": False,
                    "message": "Failed to extract information from ID document",
                    "error_code": "OCR_EXTRACTION_FAILED",
                    "extracted_data": None,
                    "ocr_confidence": 0.0
                })
            
            # Extract fields based on ID type WITHOUT additional splitting
            extracted_surname = None
            extracted_first_name = None
            extracted_other_names = None
            extracted_id = None
            
            if id_type == 'GH_CARD':
                # Ghana Card format
                extracted_surname = ocr_result.get('Surname', 'Not Found')
                first_names_full = ocr_result.get('First_Names', 'Not Found')
                
                # Split First_Names into first name and other names
                if first_names_full and first_names_full != 'Not Found':
                    names_parts = first_names_full.strip().split(None, 1)
                    extracted_first_name = names_parts[0] if len(names_parts) > 0 else 'Not Found'
                    extracted_other_names = names_parts[1] if len(names_parts) > 1 else ''
                else:
                    extracted_first_name = 'Not Found'
                    extracted_other_names = ''
                
                extracted_id = ocr_result.get('Ghana_Card_Number', 'Not Found')
                
            elif id_type == 'VOTERS_ID':
                # Voter's ID format - DON'T split Othernames, use as-is
                extracted_surname = ocr_result.get('Surname', 'Not Found')
                othernames_full = ocr_result.get('Othernames', 'Not Found')
                
                # Split Othernames into first name and remaining names
                if othernames_full and othernames_full != 'Not Found':
                    names_parts = othernames_full.strip().split(None, 1)
                    extracted_first_name = names_parts[0] if len(names_parts) > 0 else 'Not Found'
                    extracted_other_names = names_parts[1] if len(names_parts) > 1 else ''
                else:
                    extracted_first_name = 'Not Found'
                    extracted_other_names = ''
                
                extracted_id = ocr_result.get('ID_Number', 'Not Found')
                
            elif id_type == 'PASSPORT':
                # Passport format
                extracted_surname = ocr_result.get('Surname', 'Not Found')
                given_names_full = ocr_result.get('Given_Names', 'Not Found')
                
                # Split Given_Names into first name and other names
                if given_names_full and given_names_full != 'Not Found':
                    names_parts = given_names_full.strip().split(None, 1)
                    extracted_first_name = names_parts[0] if len(names_parts) > 0 else 'Not Found'
                    extracted_other_names = names_parts[1] if len(names_parts) > 1 else ''
                else:
                    extracted_first_name = 'Not Found'
                    extracted_other_names = ''
                
                extracted_id = ocr_result.get('Passport_Number', 'Not Found')
            
            # Build full name
            name_parts = []
            if extracted_surname and extracted_surname != 'Not Found':
                name_parts.append(extracted_surname)
            if extracted_first_name and extracted_first_name != 'Not Found':
                name_parts.append(extracted_first_name)
            if extracted_other_names:  # Don't check for 'Not Found' since it can be empty string
                name_parts.append(extracted_other_names)
            
            extracted_name = ' '.join(name_parts) if name_parts else 'Not Found'
            
            # Check extraction success
            has_surname = extracted_surname and extracted_surname != 'Not Found'
            has_first_name = extracted_first_name and extracted_first_name != 'Not Found'
            has_id = extracted_id and extracted_id != 'Not Found'
            
            confidence = 0.95 if (has_surname and has_first_name and has_id) else 0.5
            
            if not has_surname or not has_first_name or not has_id:
                return JSONResponse(content={
                    "success": False,
                    "message": "Could not extract complete information from ID document",
                    "error_code": "INCOMPLETE_EXTRACTION",
                    "extracted_data": {
                        "name": extracted_name,
                        "surname": extracted_surname if extracted_surname != 'Not Found' else '',
                        "first_name": extracted_first_name if extracted_first_name != 'Not Found' else '',
                        "other_names": extracted_other_names if extracted_other_names and extracted_other_names != 'Not Found' else '',
                        "id_number": extracted_id if extracted_id != 'Not Found' else '',
                        "id_type": id_type
                    },
                    "ocr_confidence": confidence,
                    "details": "The OCR system could not read all required fields from the ID document",
                    "recommendation": "Please ensure the ID document is clearly visible, well-lit, and the text is legible.",
                    "raw_ocr_result": ocr_result
                })
            
            return JSONResponse(content={
                "success": True,
                "message": "Information extracted successfully",
                "extracted_data": {
                    "name": extracted_name,
                    "surname": extracted_surname,
                    "first_name": extracted_first_name,
                    "other_names": extracted_other_names,
                    "id_number": extracted_id,
                    "id_type": id_type
                },
                "ocr_confidence": confidence,
                "raw_ocr_result": ocr_result
            })
        
        finally:
            # Clean up temp file
            temp_file_path.unlink(missing_ok=True)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error during OCR extraction: {str(e)}",
                "extracted_data": None,
                "ocr_confidence": 0.0
            }
        )


@app.post("/verify-id-details")
async def verify_id_details(
    user_surname: str = Form(""),
    user_first_name: str = Form(""),
    user_other_names: str = Form(""),
    extracted_surname: str = Form(""),
    extracted_first_name: str = Form(""),
    extracted_other_names: str = Form(""),
    user_id_number: str = Form(""),
    extracted_id_number: str = Form(""),
    id_type: str = Form("")
):
    """
    Verify that extracted ID details match user-entered details.
    Now compares Surname, First Name, and Other Names separately.
    
    Args:
        user_surname: Surname entered by user
        user_first_name: First name entered by user
        user_other_names: Other names entered by user
        extracted_surname: Surname extracted from ID
        extracted_first_name: First name extracted from ID
        extracted_other_names: Other names extracted from ID
        user_id_number: ID number entered by user
        extracted_id_number: ID number extracted from ID
        id_type: Type of ID document
    
    Returns:
        - verified: boolean indicating if details match
        - name_similarity: overall name similarity score (0-1)
        - id_match: boolean for ID number match
        - message: status message
        - differences: details on any mismatches
    """
    try:
        # Normalize inputs for comparison
        norm_user_surname = _normalize_name(user_surname) if user_surname else ""
        norm_extracted_surname = _normalize_name(extracted_surname) if extracted_surname else ""
        
        norm_user_first_name = _normalize_name(user_first_name) if user_first_name else ""
        norm_extracted_first_name = _normalize_name(extracted_first_name) if extracted_first_name else ""
        
        norm_user_other_names = _normalize_name(user_other_names) if user_other_names else ""
        norm_extracted_other_names = _normalize_name(extracted_other_names) if extracted_other_names else ""
        
        norm_user_id = _normalize_id_number(user_id_number, id_type) if user_id_number else ""
        norm_extracted_id = _normalize_id_number(extracted_id_number, id_type) if extracted_id_number else ""
        
        # Calculate name similarity for each component
        # If extraction failed (empty string), treat as 0% match
        surname_similarity = _string_similarity(norm_user_surname, norm_extracted_surname) if norm_extracted_surname else 0.0
        first_name_similarity = _string_similarity(norm_user_first_name, norm_extracted_first_name) if norm_extracted_first_name else 0.0
        other_names_similarity = _string_similarity(norm_user_other_names, norm_extracted_other_names) if norm_user_other_names or norm_extracted_other_names else 1.0
        
        # Check ID number match
        id_match = (norm_user_id == norm_extracted_id) if (norm_user_id and norm_extracted_id) else False
        
        # Determine verification status
        # Both surname and first name should have >0.8 similarity
        surname_verified = surname_similarity >= 0.8
        first_name_verified = first_name_similarity >= 0.8
        other_names_verified = other_names_similarity >= 0.75 or (not norm_user_other_names and not norm_extracted_other_names)
        
        # Overall verification: surnames and first names must match, ID must match exactly
        details_verified = surname_verified and first_name_verified and id_match
        
        # Build response with details
        differences = []
        
        if not surname_verified:
            differences.append({
                "field": "Surname",
                "user_entered": user_surname,
                "extracted": extracted_surname,
                "similarity": round(surname_similarity * 100, 2),
                "status": "mismatch"
            })
        
        if not first_name_verified:
            differences.append({
                "field": "First Name",
                "user_entered": user_first_name,
                "extracted": extracted_first_name,
                "similarity": round(first_name_similarity * 100, 2),
                "status": "mismatch"
            })
        
        if not other_names_verified and (norm_user_other_names or norm_extracted_other_names):
            differences.append({
                "field": "Other Names",
                "user_entered": user_other_names,
                "extracted": extracted_other_names,
                "similarity": round(other_names_similarity * 100, 2),
                "status": "mismatch"
            })
        
        if not id_match:
            differences.append({
                "field": "ID Number",
                "user_entered": user_id_number,
                "extracted": extracted_id_number,
                "status": "mismatch"
            })
        
        # Calculate overall name similarity (average of main components)
        overall_name_similarity = round((surname_similarity + first_name_similarity) / 2 * 100, 2)
        
        response_data = {
            "verified": details_verified,
            "surname_verified": surname_verified,
            "first_name_verified": first_name_verified,
            "other_names_verified": other_names_verified,
            "id_verified": id_match,
            "name_similarity": overall_name_similarity,
            "surname_similarity": round(surname_similarity * 100, 2),
            "first_name_similarity": round(first_name_similarity * 100, 2),
            "other_names_similarity": round(other_names_similarity * 100, 2),
            "differences": differences,
            "message": "Details match successfully!" if details_verified else "Details do not match",
        }
        
        if not details_verified:
            response_data["error_code"] = "ID_DETAILS_MISMATCH"
            response_data["details"] = f"The information extracted from your ID document does not match what you entered."
            
            if not surname_verified:
                response_data["recommendation"] = f"Surname mismatch. You entered '{user_surname}' but the ID shows '{extracted_surname}' ({round(surname_similarity * 100, 1)}% match). Please verify and try again."
            elif not first_name_verified:
                response_data["recommendation"] = f"First name mismatch. You entered '{user_first_name}' but the ID shows '{extracted_first_name}' ({round(first_name_similarity * 100, 1)}% match). Please verify and try again."
            elif not id_match:
                response_data["recommendation"] = f"ID number mismatch. You entered '{user_id_number}' but the ID shows '{extracted_id_number}'. Please verify you entered the correct ID number."
            else:
                response_data["recommendation"] = "Details do not match. Please verify your information and try again."
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "verified": False,
                "message": f"Error verifying details: {str(e)}"
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
