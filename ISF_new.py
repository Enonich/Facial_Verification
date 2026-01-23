import cv2
import numpy as np
from insightface.app import FaceAnalysis
from typing import Dict, Tuple, Optional
from datetime import datetime


class FaceVerificationSystem:
    """
    Bank-grade InsightFace / ArcFace verification system
    WITH strict single-face enforcement and face-count confidence checks
    """

    def __init__(
        self,
        model_name: str = "buffalo_l",
        use_gpu: bool = True,
        det_size: Tuple[int, int] = (640, 640),
    ):
        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if use_gpu
            else ["CPUExecutionProvider"]
        )

        self.app = FaceAnalysis(name=model_name, providers=providers)
        self.app.prepare(ctx_id=0 if use_gpu else -1, det_size=det_size)

        print("✓ InsightFace initialized")
        print(f"  Model: {model_name}")
        print(f"  Providers: {providers}")
        print(f"  det_size: {det_size}")

    # ------------------------------------------------------------------
    # 🔐 STRICT FACE COUNT VALIDATION
    # ------------------------------------------------------------------

    def _validate_single_face(self, faces) -> Tuple[bool, Optional[str], Optional[object]]:
        """
        Enforce EXACTLY one dominant face.
        Reject ambiguous multi-face images.
        """

        if not faces:
            return False, "No face detected", None

        if len(faces) == 1:
            return True, None, faces[0]

        # --- Multiple faces detected ---
        areas = []
        scores = []

        for f in faces:
            w = f.bbox[2] - f.bbox[0]
            h = f.bbox[3] - f.bbox[1]
            areas.append(w * h)
            scores.append(float(f.det_score))

        areas = np.array(areas)
        scores = np.array(scores)

        largest_idx = int(np.argmax(areas))
        largest_area_ratio = areas[largest_idx] / np.sum(areas)
        score_gap = scores[largest_idx] - np.partition(scores, -2)[-2]

        # --- Conservative dominance thresholds ---
        if largest_area_ratio < 0.75:
            return (
                False,
                f"Multiple faces detected (no dominant face). Largest face only "
                f"{largest_area_ratio*100:.1f}% of total area.",
                None,
            )

        if score_gap < 0.15:
            return (
                False,
                f"Multiple faces detected (confidence ambiguity). Score gap {score_gap:.2f}.",
                None,
            )

        # Dominant face is strong enough
        return True, None, faces[largest_idx]

    # ------------------------------------------------------------------
    # QUALITY ASSESSMENT (UNCHANGED CORE)
    # ------------------------------------------------------------------

    def assess_face_quality(self, img: np.ndarray, face) -> Dict:
        h, w = img.shape[:2]
        image_area = h * w

        x1, y1, x2, y2 = map(int, face.bbox)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        face_crop = img[y1:y2, x1:x2]
        if face_crop.size == 0:
            return self._default_quality_metrics()

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        fh, fw = face_crop.shape[:2]
        face_area = fh * fw

        det_score = float(face.det_score)
        face_size_ratio = face_area / image_area
        face_size_score = min(1.0, max(0.0, (face_size_ratio - 0.01) / 0.24))

        kps = face.kps
        iod = np.linalg.norm(np.array(kps[0]) - np.array(kps[1]))
        iod_score = min(1.0, max(0.0, (iod - 20) / 60))

        blur = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_norm = min(1.0, np.log1p(blur) / np.log1p(300))

        brightness = np.mean(gray)
        brightness_score = max(0.0, 1 - abs(brightness - 128) / 128)

        contrast = gray.std()
        contrast_score = min(1.0, contrast / 60)

        pose_score = self._estimate_pose_score(kps, fw)

        quality = (
            0.30 * det_score
            + 0.20 * face_size_score
            + 0.15 * iod_score
            + 0.15 * blur_norm
            + 0.10 * brightness_score
            + 0.05 * contrast_score
            + 0.05 * pose_score
        ) * 100

        return {
            "quality_score": float(quality),
            "det_score": det_score,
            "face_size_ratio": face_size_ratio,
            "inter_ocular_distance": iod,
            "blur_normalized": blur_norm,
            "brightness_score": brightness_score,
            "contrast_score": contrast_score,
            "pose_score": pose_score,
            "face_resolution": (fw, fh),
        }

    def _estimate_pose_score(self, landmarks, face_width):
        eye_mid = (landmarks[0][0] + landmarks[1][0]) / 2
        offset = abs(landmarks[2][0] - eye_mid)
        ratio = offset / max(face_width, 1)
        return max(0.0, 1.0 - ratio * 4)

    def _default_quality_metrics(self):
        return {"quality_score": 0.0}

    # ------------------------------------------------------------------
    # 🔐 STRICT EMBEDDING EXTRACTION
    # ------------------------------------------------------------------

    def extract_face_embedding(self, img_path: str, preprocess: bool = True) -> Dict:
        img = cv2.imread(img_path)
        if img is None:
            return {"error": f"Failed to load image: {img_path}"}

        faces = self.app.get(img)
        valid, error, face = self._validate_single_face(faces)
        if not valid:
            return {"error": error}

        quality = self.assess_face_quality(img, face)

        return {
            "embedding": face.embedding,
            "det_score": float(face.det_score),
            "bbox": face.bbox.tolist(),
            "quality": quality,
            "embedding_norm": float(np.linalg.norm(face.embedding)),
        }

    # ------------------------------------------------------------------
    # SIMILARITY
    # ------------------------------------------------------------------

    def calculate_similarity(self, emb1, emb2):
        e1 = emb1 / np.linalg.norm(emb1)
        e2 = emb2 / np.linalg.norm(emb2)
        return float(np.dot(e1, e2))

    # ------------------------------------------------------------------
    # 🔐 STRICT VERIFICATION
    # ------------------------------------------------------------------

    def verify(self, id_photo_path: str, live_photo_path: str) -> Dict:
        start = datetime.now()

        id_res = self.extract_face_embedding(id_photo_path)
        if "error" in id_res:
            return {"success": False, "error": f"ID image: {id_res['error']}"}

        live_res = self.extract_face_embedding(live_photo_path)
        if "error" in live_res:
            return {"success": False, "error": f"Live image: {live_res['error']}"}

        similarity = self.calculate_similarity(
            id_res["embedding"], live_res["embedding"]
        )

        threshold = 0.55
        match = similarity > threshold

        time_ms = (datetime.now() - start).total_seconds() * 1000

        return {
            "success": True,
            "match": match,
            "similarity": similarity,
            "threshold": threshold,
            "processing_time_ms": time_ms,
            "id_quality": id_res["quality"],
            "live_quality": live_res["quality"],
        }
