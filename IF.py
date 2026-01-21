from insightface.app import FaceAnalysis

# This will download models to ~/.insightface/models/
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640)) 