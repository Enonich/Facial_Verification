import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from pathlib import Path
import json


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

        return {
            "bbox": face.bbox.astype(int).tolist(),
            "confidence": float(face.det_score),
            "landmarks": face.kps.tolist(),
            "face_image": face_img_padded,
            "output_path": final_output_path,
            "aligned_path": aligned_output_path,
            "embedding_path": embedding_path,
            "embedding": embedding  # Include embedding in result
        }


# ------------------- USAGE -------------------

if __name__ == "__main__":
    extractor = IDFaceExtractor(det_size=(640, 640))

    # Only provide image_path; output will be named after the ID file
    result = extractor.extract_face(
        image_path="photos/IDFront.png"
    )

    if result:
        print("✅ Face extracted successfully")
        print("Confidence:", result["confidence"])
        print("Saved to:", result["output_path"])
