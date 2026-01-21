# test_insightface.py
from insightface.app import FaceAnalysis
import cv2
import numpy as np

print("Testing InsightFace installation...")

# Initialize
app = FaceAnalysis(providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0)

# Create a test image (or use your own)
test_img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.putText(test_img, "InsightFace Test", (50, 240), 
            cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2)

# Try detection
faces = app.get(test_img)
print(f"✓ Installation successful!")
print(f"  Detected {len(faces)} faces (expected 0 for blank image)")