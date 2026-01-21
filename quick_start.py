from insightface.app import FaceAnalysis
import cv2
import numpy as np

# Initialize (one time)
app = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

# Load images
id_img = cv2.imread('id_photo.jpg')
selfie_img = cv2.imread('selfie.jpg')

# Get faces
id_faces = app.get(id_img)
selfie_faces = app.get(selfie_img)

# Extract embeddings
id_embedding = id_faces[0].embedding
selfie_embedding = selfie_faces[0].embedding

# Calculate similarity
similarity = np.dot(id_embedding, selfie_embedding) / (np.linalg.norm(id_embedding) * np.linalg.norm(selfie_embedding)) 
print(f"Similarity: {similarity:.4f}")
print(f"Match: {similarity > 0.35}")