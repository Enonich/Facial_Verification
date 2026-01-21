# 🧪 API Testing Guide

Quick guide for testing the backend API endpoints.

## Using cURL

### 1. Health Check
```powershell
curl http://localhost:8000/health
```

### 2. Extract Face from ID
```powershell
curl -X POST http://localhost:8000/extract-face `
  -F "file=@photos/IDFront.png"
```

### 3. Liveness Check
```powershell
curl -X POST http://localhost:8000/liveness-check `
  -F "file=@photos/live_photo.jpg"
```

### 4. Verify Identity
```powershell
curl -X POST http://localhost:8000/verify-identity `
  -F "live_image=@photos/live_photo.jpg" `
  -F "id_face_path=/extracted/IDFront_face.jpg"
```

### 5. Complete Verification
```powershell
curl -X POST http://localhost:8000/complete-verification `
  -F "id_image=@photos/IDFront.png" `
  -F "live_image=@photos/live_photo.jpg"
```

## Using Python Requests

```python
import requests

# Health check
response = requests.get('http://localhost:8000/health')
print(response.json())

# Extract face from ID
with open('photos/IDFront.png', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/extract-face',
        files={'file': f}
    )
print(response.json())

# Liveness check
with open('photos/live_photo.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/liveness-check',
        files={'file': f}
    )
print(response.json())

# Verify identity
with open('photos/live_photo.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/verify-identity',
        files={'live_image': f},
        data={'id_face_path': '/extracted/IDFront_face.jpg'}
    )
print(response.json())
```

## Using FastAPI Docs (Recommended)

1. Start the backend server
2. Open http://localhost:8000/docs
3. Try out endpoints interactively with Swagger UI

## Expected Responses

### Successful ID Extraction
```json
{
  "success": true,
  "message": "Face extracted successfully",
  "face_image_url": "/extracted/IDFront_face.jpg",
  "confidence": 0.99,
  "bbox": [150, 200, 350, 450]
}
```

### Successful Liveness Check
```json
{
  "is_live": true,
  "confidence": 0.85,
  "message": "Real face detected",
  "bbox": [100, 150, 300, 400],
  "status": "success"
}
```

### Successful Identity Verification
```json
{
  "verified": true,
  "similarity": 0.78,
  "confidence": 0.95,
  "confidence_level": "high",
  "message": "Identity verified - high confidence",
  "processing_time": 150.5,
  "status": "success"
}
```

### Failed Verification
```json
{
  "verified": false,
  "similarity": 0.35,
  "confidence": 0.5,
  "confidence_level": "low",
  "message": "Identity not verified - low confidence",
  "processing_time": 145.2,
  "status": "success"
}
```

## Testing Tips

1. **Use Good Quality Images**: Clear, well-lit photos work best
2. **Front-facing Photos**: Face should be clearly visible
3. **Proper Lighting**: Avoid shadows and overexposure
4. **Single Face**: Ensure only one face per image
5. **Sufficient Resolution**: At least 640x480 recommended

## Error Responses

### No Face Detected
```json
{
  "success": false,
  "message": "No face detected in the ID document",
  "face_image_url": null,
  "confidence": 0.0,
  "bbox": null
}
```

### Liveness Check Failed
```json
{
  "is_live": false,
  "confidence": 0.25,
  "message": "Spoofed face detected",
  "bbox": [100, 150, 300, 400],
  "status": "success"
}
```

### Server Error
```json
{
  "detail": "Error message here"
}
```

---

**Happy Testing! 🎯**
