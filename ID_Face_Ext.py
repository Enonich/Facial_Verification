import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from pathlib import Path


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

        # Get aligned face using landmarks (112x112 by default)
        face_img = face_align.norm_crop(img, landmark=face.kps, image_size=112)

        # Always save to Extracted_Faces directory
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        if output_path is None:
            img_name = Path(image_path).stem
            output_file = f"{img_name}_face.jpg"
        else:
            output_file = Path(output_path).name  # Use only the filename part
        final_output_path = str(output_dir_path / output_file)
        cv2.imwrite(final_output_path, face_img)

        return {
            "bbox": face.bbox.astype(int).tolist(),
            "confidence": float(face.det_score),
            "landmarks": face.kps.tolist(),
            "face_image": face_img,
            "output_path": final_output_path
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
