"""
InsightFace/ArcFace ID Verification System
Complete setup and implementation for facial verification against ID photos
"""

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from pathlib import Path
import json
from typing import Dict, Tuple, Optional
from datetime import datetime


class FaceVerificationSystem:
    """
    Production-ready face verification system using InsightFace/ArcFace
    """
    
    def __init__(self, 
                 model_name: str = 'buffalo_l',
                 use_gpu: bool = True,
                 det_size: Tuple[int, int] = (640, 640)):
        """
        Initialize the face verification system
        
        Args:
            model_name: Model pack to use ('buffalo_l', 'buffalo_s', 'antelopev2')
            use_gpu: Whether to use GPU acceleration
            det_size: Detection size for face detector
        """
        print(f"Initializing InsightFace with model: {model_name}")
        
        # Set up providers based on GPU availability
        if use_gpu:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        else:
            providers = ['CPUExecutionProvider']
        
        # Initialize FaceAnalysis
        self.app = FaceAnalysis(name=model_name, providers=providers)
        self.app.prepare(ctx_id=0, det_size=det_size)
        
        print(f"✓ InsightFace initialized successfully")
        print(f"  Providers: {providers}")
        print(f"  Detection size: {det_size}")
    
    def _validate_single_face(self, faces) -> Tuple[bool, Optional[str], Optional[object]]:
        """
        🔐 SECURITY: Enforce EXACTLY ONE face. Zero tolerance for multiple faces.
        Prevents photo-holding attacks and multi-person scenarios.
        
        Args:
            faces: List of detected faces
            
        Returns:
            Tuple of (is_valid, error_message, face_object)
        """
        if not faces:
            return False, "No face detected", None

        if len(faces) == 1:
            return True, None, faces[0]

        # --- STRICT REJECTION: Multiple faces detected ---
        return (
            False,
            f"Security violation: {len(faces)} faces detected. Only single-person verification allowed.",
            None
        )
    
    def _sanitize(self, obj):
        """Recursively convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize(v) for v in obj]
        elif isinstance(obj, set):
            return [self._sanitize(v) for v in list(obj)]
        return obj

    def assess_face_quality(self, img: np.ndarray, face) -> Dict:
        """
        Assess face quality using face-aware metrics (computed on face crop only)
        
        Args:
            img: Full input image (BGR format)
            face: Detected face object from InsightFace
            
        Returns:
            Dictionary with face-aware quality metrics
        """
        h, w = img.shape[:2]
        image_area = h * w
        
        # Extract face bounding box
        x1, y1, x2, y2 = map(int, face.bbox)
        # Clamp to image boundaries
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        # Extract face crop for quality assessment
        face_crop = img[y1:y2, x1:x2]
        if face_crop.size == 0:
            return self._default_quality_metrics()
        
        face_gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        face_h, face_w = face_crop.shape[:2]
        face_area = face_h * face_w
        
        # === Face-Aware Metrics ===
        
        # 1. Detection confidence (strong proxy for usability)
        det_score = float(face.det_score)
        
        # 2. Face size ratio (small faces = weak embeddings)
        face_size_ratio = face_area / image_area
        # Normalize: 0.01 (1%) is minimum usable, 0.25 (25%) is excellent
        face_size_score = min(1.0, max(0.0, (face_size_ratio - 0.01) / 0.24))
        
        # 3. Inter-ocular distance (proxy for face resolution)
        landmarks = face.kps  # 5-point landmarks: [left_eye, right_eye, nose, left_mouth, right_mouth]
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        inter_ocular_dist = np.linalg.norm(np.array(left_eye) - np.array(right_eye))
        # Normalize: 20px is minimum, 80px+ is excellent
        iod_score = min(1.0, max(0.0, (inter_ocular_dist - 20) / 60))
        
        # 4. Blur score on face region only (Laplacian variance)
        blur_score = cv2.Laplacian(face_gray, cv2.CV_64F).var()
        # Calibrated for ID photos: 30-80 is common, 100+ is good
        # Use log scale for better distribution
        blur_normalized = min(1.0, max(0.0, np.log1p(blur_score) / np.log1p(300)))
        
        # 5. Face brightness (on face crop only)
        brightness = np.mean(face_gray)
        # FIXED: Penalize deviation from ideal (was rewarding bad brightness)
        brightness_score = 1.0 - abs(brightness - 128) / 128
        brightness_score = max(0.0, brightness_score)
        
        # 6. Face contrast (on face crop only)
        contrast = face_gray.std()
        contrast_score = min(1.0, contrast / 60)  # 60+ std dev is good contrast
        
        # 7. Pose estimation (if available via landmarks)
        pose_score = self._estimate_pose_score(landmarks, face_w)
        
        # === Combined Quality Score ===
        # Weighted by importance for verification reliability
        quality_score = (
            0.30 * det_score +           # Detection confidence (most reliable)
            0.20 * face_size_score +     # Face size ratio
            0.15 * iod_score +           # Inter-ocular distance
            0.15 * blur_normalized +     # Sharpness
            0.10 * brightness_score +    # Brightness
            0.05 * contrast_score +      # Contrast
            0.05 * pose_score            # Frontal pose
        ) * 100
        
        # Conservative enhancement trigger:
        # Only enhance if face is very small OR detection confidence is borderline
        needs_enhancement = bool(
            (det_score < 0.7 and blur_normalized < 0.3) or
            (face_size_ratio < 0.02 and blur_normalized < 0.4)
        )
        
        return {
            'quality_score': float(quality_score),
            'det_score': float(det_score),
            'face_size_ratio': float(face_size_ratio),
            'face_size_score': float(face_size_score),
            'inter_ocular_distance': float(inter_ocular_dist),
            'iod_score': float(iod_score),
            'blur_score': float(blur_score),
            'blur_normalized': float(blur_normalized),
            'brightness': float(brightness),
            'brightness_score': float(brightness_score),
            'contrast': float(contrast),
            'contrast_score': float(contrast_score),
            'pose_score': float(pose_score),
            'resolution': (int(w), int(h)),
            'face_resolution': (int(face_w), int(face_h)),
            'needs_enhancement': needs_enhancement
        }
    
    def _estimate_pose_score(self, landmarks: np.ndarray, face_width: int) -> float:
        """
        Estimate how frontal the face is based on landmark symmetry
        
        Args:
            landmarks: 5-point facial landmarks
            face_width: Width of face bounding box
            
        Returns:
            Pose score (0-1, higher = more frontal)
        """
        if landmarks is None or len(landmarks) < 5:
            return 0.5  # Unknown
        
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        nose = landmarks[2]
        
        # Calculate horizontal offset of nose from eye midpoint
        eye_center_x = (left_eye[0] + right_eye[0]) / 2
        nose_offset = abs(nose[0] - eye_center_x)
        
        # Normalize by face width (0 = perfect frontal, 0.5 = extreme profile)
        offset_ratio = nose_offset / max(face_width, 1)
        
        # Convert to score (1 = frontal, 0 = profile)
        pose_score = max(0.0, 1.0 - (offset_ratio * 4))  # 25% offset = 0 score
        
        return pose_score
    
    def _default_quality_metrics(self) -> Dict:
        """Return default quality metrics when face crop is invalid"""
        return {
            'quality_score': 0.0,
            'det_score': 0.0,
            'face_size_ratio': 0.0,
            'face_size_score': 0.0,
            'inter_ocular_distance': 0.0,
            'iod_score': 0.0,
            'blur_score': 0.0,
            'blur_normalized': 0.0,
            'brightness': 0.0,
            'brightness_score': 0.0,
            'contrast': 0.0,
            'contrast_score': 0.0,
            'pose_score': 0.0,
            'resolution': (0, 0),
            'face_resolution': (0, 0),
            'needs_enhancement': False
        }
    
    def safe_preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Apply safe, identity-preserving preprocessing
        
        Args:
            img: Input image (BGR format)
            
        Returns:
            Enhanced image
        """
        # 1. Denoising (preserves structure)
        denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        
        # 2. CLAHE for contrast enhancement
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # 3. Mild sharpening
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]]) / 9
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # 4. Blend with original to preserve identity
        result = cv2.addWeighted(denoised, 0.6, sharpened, 0.4, 0)
        
        return result
    
    def extract_face_embedding(self, 
                               img_path: str, 
                               preprocess: bool = True) -> Optional[Dict]:
        """
        Extract face embedding from an image
        
        Args:
            img_path: Path to image file
            preprocess: Whether to apply preprocessing
            
        Returns:
            Dictionary with embedding and metadata, or None if no face found
        """
        # Load image
        img = cv2.imread(img_path)
        if img is None:
            return {'error': f'Failed to load image: {img_path}'}
        
        # Store original for quality assessment
        img_original = img.copy()
        
        # Detect faces FIRST (quality is computed on face crop)
        faces = self.app.get(img)
        
        # 🔐 SECURITY: Strict single-face validation
        valid, error, face = self._validate_single_face(faces)
        if not valid:
            return {'error': error}
        
        # Assess quality on FACE CROP only (not full image)
        quality = self.assess_face_quality(img_original, face)
        
        # Apply preprocessing only if conservative threshold met
        preprocessed = False
        if preprocess and quality['needs_enhancement']:
            img = self.safe_preprocess(img)
            # Re-detect face after preprocessing
            faces_pp = self.app.get(img)
            # 🔐 SECURITY: Re-validate after preprocessing
            valid_pp, error_pp, face_pp = self._validate_single_face(faces_pp)
            if valid_pp:
                face = face_pp
                preprocessed = True
            # If preprocessing broke single-face constraint, keep original
        
        return {
            'embedding': face.embedding,
            'bbox': face.bbox.tolist(),
            'landmark': face.kps.tolist(),
            'det_score': float(face.det_score),
            'quality': self._sanitize(quality),
            'preprocessed': preprocessed,
            'embedding_norm': float(np.linalg.norm(face.embedding))
        }
    
    def calculate_similarity(self, 
                           embedding1: np.ndarray, 
                           embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        # Normalize embeddings
        embedding1_norm = embedding1 / np.linalg.norm(embedding1)
        embedding2_norm = embedding2 / np.linalg.norm(embedding2)
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1_norm, embedding2_norm)
        
        return float(similarity)
    
    def verify(self, 
               id_photo_path: str, 
               live_photo_path: str,
               adaptive_threshold: bool = True,
               verbose: bool = True) -> Dict:
        """
        Verify if two faces match
        
        Args:
            id_photo_path: Path to ID photo
            live_photo_path: Path to live/selfie photo
            adaptive_threshold: Use quality-based adaptive thresholding
            verbose: Print quality scores during verification
            
        Returns:
            Verification result with match status and metadata
        """
        start_time = datetime.now()
        
        # Extract embeddings
        id_result = self.extract_face_embedding(id_photo_path, preprocess=True)
        live_result = self.extract_face_embedding(live_photo_path, preprocess=False)
        
        # Check for errors
        if 'error' in id_result:
            return {'success': False, 'error': id_result['error']}
        if 'error' in live_result:
            return {'success': False, 'error': live_result['error']}
        
        # Print quality scores if verbose
        if verbose:
            print("\n" + "="*50)
            print("📊 IMAGE QUALITY SCORES")
            print("="*50)
            
            # ID Photo Quality (Face-Aware Metrics)
            id_q = id_result['quality']
            print(f"\n🪪  ID Photo Quality (Face-Aware):")
            print(f"    • Overall Score: {id_q['quality_score']:.1f}/100")
            print(f"    • Detection Confidence: {id_q['det_score']:.3f} {'✓' if id_q['det_score'] >= 0.8 else '⚠'}")
            print(f"    • Face Size: {id_q['face_size_ratio']*100:.1f}% of image {'✓' if id_q['face_size_ratio'] >= 0.05 else '⚠ (small)'}")
            print(f"    • Inter-Ocular Dist: {id_q['inter_ocular_distance']:.1f}px {'✓' if id_q['inter_ocular_distance'] >= 40 else '⚠ (low res)'}")
            print(f"    • Face Sharpness: {id_q['blur_normalized']*100:.0f}% {'✓' if id_q['blur_normalized'] >= 0.3 else '⚠ (blurry)'}")
            print(f"    • Brightness Score: {id_q['brightness_score']*100:.0f}% {'✓' if id_q['brightness_score'] >= 0.5 else '⚠'}")
            print(f"    • Pose Score: {id_q['pose_score']*100:.0f}% {'✓' if id_q['pose_score'] >= 0.7 else '⚠ (angled)'}")
            print(f"    • Face Resolution: {id_q['face_resolution'][0]}x{id_q['face_resolution'][1]}")
            print(f"    • Preprocessed: {'Yes' if id_result['preprocessed'] else 'No'}")
            
            # Live Photo Quality (Face-Aware Metrics)
            live_q = live_result['quality']
            print(f"\n📸 Live Photo Quality (Face-Aware):")
            print(f"    • Overall Score: {live_q['quality_score']:.1f}/100")
            print(f"    • Detection Confidence: {live_q['det_score']:.3f} {'✓' if live_q['det_score'] >= 0.8 else '⚠'}")
            print(f"    • Face Size: {live_q['face_size_ratio']*100:.1f}% of image {'✓' if live_q['face_size_ratio'] >= 0.05 else '⚠ (small)'}")
            print(f"    • Inter-Ocular Dist: {live_q['inter_ocular_distance']:.1f}px {'✓' if live_q['inter_ocular_distance'] >= 40 else '⚠ (low res)'}")
            print(f"    • Face Sharpness: {live_q['blur_normalized']*100:.0f}% {'✓' if live_q['blur_normalized'] >= 0.3 else '⚠ (blurry)'}")
            print(f"    • Brightness Score: {live_q['brightness_score']*100:.0f}% {'✓' if live_q['brightness_score'] >= 0.5 else '⚠'}")
            print(f"    • Pose Score: {live_q['pose_score']*100:.0f}% {'✓' if live_q['pose_score'] >= 0.7 else '⚠ (angled)'}")
            print(f"    • Face Resolution: {live_q['face_resolution'][0]}x{live_q['face_resolution'][1]}")
            print("="*50)
        
        # Calculate similarity
        similarity = self.calculate_similarity(
            id_result['embedding'], 
            live_result['embedding']
        )
        
        # Determine threshold based on ID quality
        # SECURITY: Threshold is BOUNDED to prevent fraud amplification
        if adaptive_threshold:
            id_quality = id_result['quality']['quality_score']
            base_threshold = 0.55  # Base threshold for verification
            
            # Quality-based adjustment (bounded)
            # Lower quality = HIGHER threshold (more strict, not more lenient)
            # This prevents poor quality from enabling fraud
            quality_normalized = id_quality / 100.0  # 0-1 scale
            
            # Small adjustment based on quality (max ±0.10)
            # High quality (1.0) -> -0.05 (slightly easier)
            # Low quality (0.0) -> +0.05 (slightly harder)
            adjustment = (0.5 - quality_normalized) * 0.10
            
            threshold = base_threshold + adjustment
            # HARD BOUNDS: Never go below 0.50 or above 0.65
            threshold = max(0.50, min(0.65, threshold))
            
            if quality_normalized >= 0.7:
                confidence_level = 'high'
            elif quality_normalized >= 0.5:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'
        else:
            threshold = 0.55
            confidence_level = 'standard'
        
        # Determine match
        is_match = similarity > threshold
        
        # Calculate confidence
        if is_match:
            if similarity > threshold + 0.15:
                match_confidence = 'very_high'
            elif similarity > threshold + 0.10:
                match_confidence = 'high'
            else:
                match_confidence = 'medium'
        else:
            match_confidence = 'no_match'
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Print verification result if verbose
        if verbose:
            print(f"\n🔐 VERIFICATION RESULT:")
            print(f"    • Similarity: {similarity:.4f} ({similarity*100:.2f}%)")
            print(f"    • Threshold: {threshold:.2f} ({threshold*100:.0f}%)")
            print(f"    • Match: {'✅ YES' if is_match else '❌ NO'}")
            print(f"    • Confidence: {match_confidence}")
            print(f"    • Processing Time: {processing_time:.1f}ms")
            print("="*50 + "\n")
        
        return {
            'success': True,
            'match': is_match,
            'similarity': similarity,
            'threshold': threshold,
            'match_confidence': match_confidence,
            'id_quality': id_result['quality'],
            'live_quality': live_result['quality'],
            'id_preprocessed': id_result['preprocessed'],
            'processing_time_ms': processing_time,
            'details': {
                'id_face_score': id_result['det_score'],
                'live_face_score': live_result['det_score'],
                'threshold_type': confidence_level
            }
        }

    def verify_with_embedding(self, 
                            id_embedding_path: str, 
                            live_photo_path: str,
                            adaptive_threshold: bool = True,
                            verbose: bool = True,
                            id_quality_metrics: Optional[Dict] = None) -> Dict:
        """
        Verify live photo against a pre-computed ID embedding
        
        Args:
            id_embedding_path: Path to .npy file containing ID embedding
            live_photo_path: Path to live/selfie photo
            adaptive_threshold: Use quality-based adaptive thresholding
            verbose: Print verification details
            id_quality_metrics: Optional dictionary with ID quality scores (for logging/thresholding)
            
        Returns:
            Verification result
        """
        start_time = datetime.now()
        
        # Load ID embedding
        try:
            id_embedding = np.load(id_embedding_path)
        except Exception as e:
            return {'success': False, 'error': f'Failed to load ID embedding: {str(e)}'}
            
        # Extract live embedding
        live_result = self.extract_face_embedding(live_photo_path, preprocess=False)
        
        if 'error' in live_result:
            return {'success': False, 'error': live_result['error']}
            
        # Print quality scores if verbose
        if verbose:
            print("\n" + "="*50)
            print("📊 IMAGE QUALITY SCORES (Embedding Mode)")
            print("="*50)
            
            # ID Photo Quality (if provided)
            if id_quality_metrics:
                id_q = id_quality_metrics
                print(f"\n🪪  ID Photo Quality (From Pre-computation):")
                print(f"    • Overall Score: {id_q.get('quality_score', 0):.1f}/100")
                print(f"    • Detection Confidence: {id_q.get('det_score', 0):.3f} {'✓' if id_q.get('det_score', 0) >= 0.8 else '⚠'}")
                print(f"    • Face Size: {id_q.get('face_size_ratio', 0)*100:.1f}% of image {'✓' if id_q.get('face_size_ratio', 0) >= 0.05 else '⚠ (small)'}")
                print(f"    • Inter-Ocular Dist: {id_q.get('inter_ocular_distance', 0):.1f}px {'✓' if id_q.get('inter_ocular_distance', 0) >= 40 else '⚠ (low res)'}")
                print(f"    • Face Sharpness: {id_q.get('blur_normalized', 0)*100:.0f}% {'✓' if id_q.get('blur_normalized', 0) >= 0.3 else '⚠ (blurry)'}")
                print(f"    • Brightness Score: {id_q.get('brightness_score', 0)*100:.0f}% {'✓' if id_q.get('brightness_score', 0) >= 0.5 else '⚠'}")
                print(f"    • Pose Score: {id_q.get('pose_score', 0)*100:.0f}% {'✓' if id_q.get('pose_score', 0) >= 0.7 else '⚠ (angled)'}")
                
            # Live Photo Quality (Face-Aware Metrics)
            live_q = live_result['quality']
            print(f"\n📸 Live Photo Quality (Face-Aware):")
            print(f"    • Overall Score: {live_q['quality_score']:.1f}/100")
            print(f"    • Detection Confidence: {live_q['det_score']:.3f} {'✓' if live_q['det_score'] >= 0.8 else '⚠'}")
            print(f"    • Face Size: {live_q['face_size_ratio']*100:.1f}% of image {'✓' if live_q['face_size_ratio'] >= 0.05 else '⚠ (small)'}")
            print(f"    • Inter-Ocular Dist: {live_q['inter_ocular_distance']:.1f}px {'✓' if live_q['inter_ocular_distance'] >= 40 else '⚠ (low res)'}")
            print(f"    • Face Sharpness: {live_q['blur_normalized']*100:.0f}% {'✓' if live_q['blur_normalized'] >= 0.3 else '⚠ (blurry)'}")
            print(f"    • Brightness Score: {live_q['brightness_score']*100:.0f}% {'✓' if live_q['brightness_score'] >= 0.5 else '⚠'}")
            print(f"    • Pose Score: {live_q['pose_score']*100:.0f}% {'✓' if live_q['pose_score'] >= 0.7 else '⚠ (angled)'}")
            print("="*50)

        # Calculate similarity
        similarity = self.calculate_similarity(
            id_embedding, 
            live_result['embedding']
        )
        
        # Determine threshold
        if adaptive_threshold and id_quality_metrics:
            try:
                id_quality = id_quality_metrics.get('quality_score', 50.0)
                base_threshold = 0.55
                
                # Quality-based adjustment (bounded)
                quality_normalized = id_quality / 100.0  # 0-1 scale
                
                # Small adjustment based on quality (max ±0.10)
                adjustment = (0.5 - quality_normalized) * 0.10
                
                threshold = base_threshold + adjustment
                # HARD BOUNDS: Never go below 0.50 or above 0.65
                threshold = max(0.50, min(0.65, threshold))
                confidence_level = 'quality-adjusted'
            except:
                threshold = 0.55
                confidence_level = 'standard'
        else:
            # Fall back to standard threshold if no ID quality available
            threshold = 0.55
            confidence_level = 'standard'
        
        # Determine match
        is_match = similarity > threshold
        
        # Calculate confidence
        if is_match:
            if similarity > threshold + 0.15:
                match_confidence = 'very_high'
            elif similarity > threshold + 0.10:
                match_confidence = 'high'
            else:
                match_confidence = 'medium'
        else:
            match_confidence = 'no_match'
            
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if verbose:
            print(f"\n🔐 VERIFICATION RESULT:")
            print(f"    • Similarity: {similarity:.4f} ({similarity*100:.2f}%)")
            print(f"    • Threshold: {threshold:.2f} ({threshold*100:.0f}%)")
            print(f"    • Match: {'✅ YES' if is_match else '❌ NO'}")
            print(f"    • Confidence: {match_confidence}")
            print(f"    • Processing Time: {processing_time:.1f}ms")
            print("="*50 + "\n")
        
        return {
            'success': True,
            'match': is_match,
            'similarity': similarity,
            'similarity_percentage': similarity * 100,
            'threshold': threshold,
            'threshold_percentage': threshold * 100,
            'match_confidence': match_confidence,
            'match_description': 'Faces match' if is_match else 'Faces do not match',
            'live_quality': live_result['quality'],
            'id_quality': id_quality_metrics,
            'processing_time_ms': processing_time,
            'details': {
                'live_face_score': live_result['det_score'],
                'threshold_type': confidence_level
            }
        }
    
    def batch_verify(self, 
                    id_photo_path: str, 
                    live_photo_paths: list) -> list:
        """
        Verify one ID photo against multiple live photos
        
        Args:
            id_photo_path: Path to ID photo
            live_photo_paths: List of paths to live photos
            
        Returns:
            List of verification results
        """
        # Extract ID embedding once
        id_result = self.extract_face_embedding(id_photo_path, preprocess=True)
        
        if 'error' in id_result:
            return [{'error': id_result['error']} for _ in live_photo_paths]
        
        results = []
        for live_path in live_photo_paths:
            live_result = self.extract_face_embedding(live_path, preprocess=False)
            
            if 'error' in live_result:
                results.append({'error': live_result['error'], 'path': live_path})
                continue
            
            similarity = self.calculate_similarity(
                id_result['embedding'],
                live_result['embedding']
            )
            
            results.append({
                'path': live_path,
                'similarity': similarity,
                'match': similarity > 0.50  # Use bounded minimum threshold
            })
        
        return results


def main():
    """
    Example usage and testing
    """
    print("=" * 60)
    print("InsightFace/ArcFace ID Verification System")
    print("=" * 60)
    
    # Initialize system
    print("\n1. Initializing system...")
    try:
        verifier = FaceVerificationSystem(
            model_name='buffalo_l',  # Use 'buffalo_s' for faster, smaller model
            use_gpu=True,            # Set to False if no GPU
            det_size=(640, 640)
        )
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        print("\nTrying CPU-only mode...")
        verifier = FaceVerificationSystem(
            model_name='buffalo_l',
            use_gpu=False,
            det_size=(640, 640)
        )
    
    print("\n2. System ready for verification!")
    print("\nUsage examples:")
    print("-" * 60)
    
    # Example 1: Basic verification
    print("\nExample 1: Basic Verification")
    print("```python")
    print("result = verifier.verify(")
    print("    id_photo_path='path/to/id_photo.jpg',")
    print("    live_photo_path='path/to/selfie.jpg'")
    print(")")
    print("print(f\"Match: {result['match']}\")")
    print("print(f\"Similarity: {result['similarity']:.4f}\")")
    print("```")
    
    # Example 2: Quality assessment
    print("\nExample 2: Assess Image Quality")
    print("```python")
    print("import cv2")
    print("img = cv2.imread('path/to/photo.jpg')")
    print("quality = verifier.assess_image_quality(img)")
    print("print(f\"Quality score: {quality['quality_score']:.1f}/100\")")
    print("```")
    
    # Example 3: Extract embedding
    print("\nExample 3: Extract Face Embedding")
    print("```python")
    print("result = verifier.extract_face_embedding('path/to/photo.jpg')")
    print("if 'error' not in result:")
    print("    embedding = result['embedding']  # 512-dimensional vector")
    print("    print(f\"Detection score: {result['det_score']:.4f}\")")
    print("```")
    
    print("\n" + "=" * 60)
    print("Setup complete! Ready to process images.")
    print("=" * 60)


if __name__ == "__main__":
    main()