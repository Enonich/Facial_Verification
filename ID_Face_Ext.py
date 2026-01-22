import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from pathlib import Path
import json
from typing import Dict, Tuple, Optional


class IDFaceExtractor:
    def __init__(self, det_size=(640, 640)):
        """
        Initialize InsightFace for ID photo extraction
        """
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=0, det_size=det_size)

    def _sanitize(self, obj):
        """Recursively convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize(v) for v in obj]
        elif isinstance(obj, set):
            return [self._sanitize(v) for v in list(obj)]
        return obj

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
            (float(det_score) < 0.7 and float(blur_normalized) < 0.3) or
            (float(face_size_ratio) < 0.02 and float(blur_normalized) < 0.4)
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
        

    def extract_face(self, image_path, output_path=None, output_dir="Extracted_Faces"):
        """
        Extract and align face from an ID image

        Args:
            image_path (str): Path to ID image
            output_path (str): Optional save path

        Returns:
            dict with face data or None
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Could not read image")

        faces = self.app.get(img)

        if len(faces) == 0:
            print("❌ No face detected")
            return None

        # Select best face (largest bounding box)
        face = max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
        )

        # Calculate quality scores BEFORE embedding usage/alignment
        quality = self.assess_face_quality(img, face)
        print(f"🔍 Face Quality Score: {quality['quality_score']:.2f}")

        # Get aligned face using landmarks - use larger size (224x224) for better detection later
        face_img_aligned = face_align.norm_crop(img, landmark=face.kps, image_size=224)
        
        # Also extract a padded crop from the original image for backup
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        h, w = img.shape[:2]
        
        # Add 30% padding around the face
        face_w = x2 - x1
        face_h = y2 - y1
        pad_w = int(face_w * 0.3)
        pad_h = int(face_h * 0.3)
        
        x1_pad = max(0, x1 - pad_w)
        y1_pad = max(0, y1 - pad_h)
        x2_pad = min(w, x2 + pad_w)
        y2_pad = min(h, y2 + pad_h)
        
        face_img_padded = img[y1_pad:y2_pad, x1_pad:x2_pad]
        
        # Resize padded crop to reasonable size if too small
        if face_img_padded.shape[0] < 224 or face_img_padded.shape[1] < 224:
            scale = max(224 / face_img_padded.shape[0], 224 / face_img_padded.shape[1])
            face_img_padded = cv2.resize(face_img_padded, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Always save to Extracted_Faces directory
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        if output_path is None:
            img_name = Path(image_path).stem
            output_file = f"{img_name}_face.jpg"
        else:
            output_file = Path(output_path).name  # Use only the filename part
        
        final_output_path = str(output_dir_path / output_file)
        
        # Save the padded crop (better for face detection in verification)
        cv2.imwrite(final_output_path, face_img_padded)
        
        # Also save the aligned face for reference
        aligned_output_path = str(output_dir_path / f"{Path(output_file).stem}_aligned.jpg")
        cv2.imwrite(aligned_output_path, face_img_aligned)
        
        # Save the embedding for direct use in verification (more reliable)
        embedding = face.embedding
        embedding_path = str(output_dir_path / f"{Path(output_file).stem}_embedding.npy")
        np.save(embedding_path, embedding)

        # Sanitize and save quality scores to JSON
        sanitized_quality = self._sanitize(quality)
        quality_path = str(output_dir_path / f"{Path(output_file).stem}_quality.json")
        with open(quality_path, 'w') as f:
            json.dump(sanitized_quality, f, indent=4)

        return {
            "bbox": face.bbox.astype(int).tolist(),
            "confidence": float(face.det_score),
            "landmarks": face.kps.tolist(),
            "face_image": face_img_padded,
            "output_path": final_output_path,
            "aligned_path": aligned_output_path,
            "embedding_path": embedding_path,
            "embedding": embedding,  # Include embedding in result
            "quality": sanitized_quality
        }


# ------------------- USAGE -------------------

if __name__ == "__main__":
    extractor = IDFaceExtractor(det_size=(640, 640))

    # Only provide image_path; output will be named after the ID file
    result = extractor.extract_face(
        image_path="photos/enoch_pass.jpeg"
    )

    if result:
        print("✅ Face extracted successfully")
        print("Confidence:", result["confidence"])
        print("Saved to:", result["output_path"])
