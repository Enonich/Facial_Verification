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
    
    def assess_image_quality(self, img: np.ndarray) -> Dict:
        """
        Assess image quality using multiple metrics
        
        Args:
            img: Input image (BGR format)
            
        Returns:
            Dictionary with quality metrics
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = img.shape[:2]
        
        # Calculate blur score (Laplacian variance)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Calculate brightness
        brightness = np.mean(gray)
        
        # Calculate contrast
        contrast = gray.std()
        
        # Overall quality score (0-100)
        quality_score = min(100, (
            (min(blur_score, 500) / 5) * 0.4 +  # Blur weight: 40%
            (min(contrast, 100)) * 0.3 +         # Contrast weight: 30%
            (abs(brightness - 128) / 128 * 100) * 0.3  # Brightness weight: 30%
        ))
        
        return {
            'blur_score': float(blur_score),
            'brightness': float(brightness),
            'contrast': float(contrast),
            'resolution': (w, h),
            'quality_score': float(quality_score),
            'needs_enhancement': blur_score < 100 or contrast < 30
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
        
        # Assess quality
        quality = self.assess_image_quality(img)
        
        # Apply preprocessing if needed and requested
        if preprocess and quality['needs_enhancement']:
            img = self.safe_preprocess(img)
            preprocessed = True
        else:
            preprocessed = False
        
        # Detect faces
        faces = self.app.get(img)
        
        if not faces:
            return {'error': 'No face detected in image'}
        
        if len(faces) > 1:
            # Multiple faces - use the largest one
            faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]), reverse=True)
        
        face = faces[0]
        
        return {
            'embedding': face.embedding,
            'bbox': face.bbox.tolist(),
            'landmark': face.kps.tolist(),
            'det_score': float(face.det_score),
            'quality': quality,
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
               adaptive_threshold: bool = True) -> Dict:
        """
        Verify if two faces match
        
        Args:
            id_photo_path: Path to ID photo
            live_photo_path: Path to live/selfie photo
            adaptive_threshold: Use quality-based adaptive thresholding
            
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
        
        # Calculate similarity
        similarity = self.calculate_similarity(
            id_result['embedding'], 
            live_result['embedding']
        )
        
        # Determine threshold based on ID quality
        if adaptive_threshold:
            id_quality = id_result['quality']['quality_score']
            if id_quality < 40:
                threshold = 0.4  # Very lenient for poor quality
                confidence_level = 'low'
            elif id_quality < 60:
                threshold = 0.60  # Moderate
                confidence_level = 'medium'
            else:
                threshold = 0.7  # Standard
                confidence_level = 'high'
        else:
            threshold = 0.7
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
                'match': similarity > 0.35
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