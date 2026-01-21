from ISF import FaceVerificationSystem

# Initialize once (loads models)
verifier = FaceVerificationSystem(
    model_name='buffalo_l',  # or 'buffalo_s' for speed
    use_gpu=True
)

# Verify faces
result = verifier.verify(
    id_photo_path='photos/ransford.jpeg',
    live_photo_path='photos/rans2.jpeg'
)

# Check result
if result['success']:
    print(f"Match: {result['match']}")
    print(f"Similarity: {result['similarity']:.4f}")
    print(f"Confidence: {result['match_confidence']}")
    print(f"Processing time: {result['processing_time_ms']:.1f}ms")
else:
    print(f"Error: {result['error']}")