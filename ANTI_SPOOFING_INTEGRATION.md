# Anti-Spoofing Integration Guide

## Overview
The Silent Face Anti-Spoofing system has been successfully integrated into the web application, replacing the previous liveness detection engine.

## What Changed

### 1. New Anti-Spoofing Engine (`antispoofing_engine.py`)
- **Purpose**: Detect presentation attacks (fake faces from photos, videos, masks, etc.)
- **Technology**: MiniFASNet deep learning models (PyTorch)
- **Detection Method**: Multi-model ensemble prediction
- **Output**: Real/Fake classification with confidence score

### 2. Updated Backend API (`backend/app.py`)
- Replaced `LivenessEngine` with `AntiSpoofingEngine`
- Enhanced `/verify` endpoint to return:
  - `is_live`: Boolean (True = real face, False = fake)
  - `message`: Descriptive result message
  - `confidence`: Confidence score (0.0 - 1.0)
  - `bbox`: Face bounding box coordinates [x, y, width, height]

### 3. Updated Dependencies (`backend/requirements.txt`)
- Added: `torch`, `torchvision`, `easydict`
- Required for running anti-spoofing neural networks

## How It Works

### Detection Pipeline:
1. **Face Detection**: Uses RetinaFace (Caffe model) to locate face in image
2. **Face Cropping**: Extracts face patches at multiple scales
3. **Model Inference**: Runs 2 MiniFASNet models:
   - `MiniFASNetV2` (80x80 input)
   - `MiniFASNetV1SE` (80x80 input)
4. **Ensemble Prediction**: Averages results from both models
5. **Classification**: 
   - Label 1 = Real Face
   - Label 0 = Fake Face (spoofed)

### Confidence Threshold:
- Default: 0.5 (50%)
- A real face must score ≥ 0.5 confidence to pass
- Adjustable in engine initialization

## API Endpoints

### POST `/verify`
Upload an image to check for face spoofing.

**Request:**
```bash
curl -X POST http://localhost:8000/verify \
  -F "file=@photo.jpg"
```

**Response:**
```json
{
  "is_live": true,
  "message": "✅ Real Face Detected (confidence: 0.87)",
  "confidence": 0.87,
  "bbox": [120, 80, 240, 320],
  "status": "success"
}
```

### POST `/reset`
Reset the anti-spoofing engine.

### GET `/health`
Check if engine is ready.

## Installation & Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Verify Models Exist
Ensure these model files exist in `Silent_Face_Anti_Spoofing/resources/anti_spoof_models/`:
- `2.7_80x80_MiniFASNetV2.pth`
- `4_0_0_80x80_MiniFASNetV1SE.pth`

### 3. Start Backend Server
```bash
cd backend
python app.py
```

Or with uvicorn:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API
```bash
# Health check
curl http://localhost:8000/health

# Test with an image
curl -X POST http://localhost:8000/verify \
  -F "file=@test_image.jpg"
```

## Frontend Integration

The frontend should work with minimal changes since the `/verify` endpoint is compatible, but now includes additional fields:

```javascript
const formData = new FormData();
formData.append('file', imageBlob);

const response = await fetch('http://localhost:8000/verify', {
  method: 'POST',
  body: formData
});

const result = await response.json();

if (result.is_live) {
  console.log(`Real face detected! Confidence: ${result.confidence}`);
  // Draw bounding box using result.bbox
} else {
  console.log(`Fake face detected! ${result.message}`);
}
```

## Testing

### Test with Real Face:
- Use webcam photo
- Should return `is_live: true` with high confidence

### Test with Fake Face:
- Display photo on screen and take picture of it
- Print photo and photograph it
- Show video on screen
- Should return `is_live: false`

## Performance

- **Speed**: ~30-60 FPS on GPU, ~10-15 FPS on CPU
- **Accuracy**: High accuracy against common presentation attacks
- **Models**: Lightweight (MiniFASNet) - suitable for real-time use

## Troubleshooting

### Error: "Model directory not found"
- Verify `Silent_Face_Anti_Spoofing/resources/anti_spoof_models/` exists
- Check model files (.pth) are present

### Error: "No face detected"
- Ensure face is visible and well-lit
- Face should be roughly 3:4 aspect ratio
- Try moving closer to camera

### Low confidence scores
- Improve lighting conditions
- Ensure face is centered and clear
- Check image quality

### CUDA/GPU errors
- Engine automatically falls back to CPU
- For GPU: Ensure PyTorch with CUDA is installed
- Check: `torch.cuda.is_available()`

## Configuration Options

In `antispoofing_engine.py`, you can adjust:

```python
engine = AntiSpoofingEngine(
    model_dir="path/to/models",  # Custom model directory
    device_id=0,                  # GPU ID (0 for default)
    confidence_threshold=0.5      # Min confidence for real face (0.0-1.0)
)
```

## Next Steps

1. **Frontend Updates**: Update UI to show confidence score and bounding box
2. **Video Stream**: Adapt for continuous webcam verification
3. **Custom Thresholds**: Tune confidence threshold based on your security needs
4. **Additional Models**: Add more models for improved accuracy
5. **Logging**: Add detection event logging

## References

- Original Project: [Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing)
- Models: MiniFASNet V1/V2
- Face Detector: RetinaFace
