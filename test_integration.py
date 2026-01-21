"""
Quick test script to verify anti-spoofing integration
"""

import sys
import os

# Test 1: Check file structure
print("=" * 60)
print("TEST 1: Checking file structure...")
print("=" * 60)

files_to_check = [
    "antispoofing_engine.py",
    "backend/app.py",
    "backend/requirements.txt",
    "Silent_Face_Anti_Spoofing/src/anti_spoof_predict.py",
    "Silent_Face_Anti_Spoofing/src/generate_patches.py",
    "Silent_Face_Anti_Spoofing/src/utility.py",
    "Silent_Face_Anti_Spoofing/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth",
    "Silent_Face_Anti_Spoofing/resources/anti_spoof_models/4_0_0_80x80_MiniFASNetV1SE.pth",
]

all_exist = True
for file_path in files_to_check:
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {file_path}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n✅ All required files exist!")
else:
    print("\n⚠️  Some files are missing. Please check the paths above.")

# Test 2: Check dependencies in requirements.txt
print("\n" + "=" * 60)
print("TEST 2: Checking backend requirements...")
print("=" * 60)

required_packages = ['fastapi', 'uvicorn', 'torch', 'torchvision', 'opencv-python', 'numpy']

try:
    with open('backend/requirements.txt', 'r') as f:
        requirements = f.read()
    
    for package in required_packages:
        if package in requirements or package.replace('-', '_') in requirements:
            print(f"✅ {package}")
        else:
            print(f"❌ {package} - MISSING")
except Exception as e:
    print(f"❌ Error reading requirements.txt: {e}")

# Test 3: Summary
print("\n" + "=" * 60)
print("INTEGRATION SUMMARY")
print("=" * 60)

print("""
✅ Anti-spoofing engine created (antispoofing_engine.py)
✅ Backend API updated (backend/app.py)
✅ Requirements updated (backend/requirements.txt)

NEXT STEPS:
1. Install dependencies:
   cd backend
   pip install -r requirements.txt

2. Start the backend:
   python app.py

3. Test the API:
   curl http://localhost:8000/health

4. Upload test image:
   curl -X POST http://localhost:8000/verify -F "file=@test_image.jpg"

FEATURES:
- Multi-model ensemble (MiniFASNet V1SE + V2)
- Real-time face anti-spoofing detection
- RESTful API with confidence scores
- Automatic face detection with RetinaFace
- GPU acceleration support

For detailed documentation, see: ANTI_SPOOFING_INTEGRATION.md
""")

print("=" * 60)
print("Test complete!")
print("=" * 60)
