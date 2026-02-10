"""
Test for Photo-Holding Attack Prevention

This test verifies that the system correctly blocks attacks where:
- An attacker holds a photo of the authorized person next to their face
- The live person (attacker) would pass liveness
- But the photo could be used for face matching

The system MUST detect 2 faces and reject BEFORE checking liveness.
"""

import cv2
import numpy as np
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

def create_photo_holding_attack_frame():
    """
    Simulate someone holding a photo next to their face
    Creates a frame with two distinct faces that should both be detected
    """
    # Load two different people's faces
    face1 = cv2.imread('photos/enoch_pass.jpeg')
    face2 = cv2.imread('photos/ransford.jpeg')
    
    if face1 is None or face2 is None:
        print("❌ Test images not found")
        return None
    
    # Resize both to similar sizes so detector finds both
    target_height = 400
    
    # Resize face 1
    h1, w1 = face1.shape[:2]
    scale1 = target_height / h1
    face1_resized = cv2.resize(face1, (int(w1 * scale1), target_height))
    
    # Resize face 2 (slightly smaller to simulate a photo being held)
    h2, w2 = face2.shape[:2]
    scale2 = (target_height * 0.8) / h2  # 80% size
    face2_resized = cv2.resize(face2, (int(w2 * scale2), int(target_height * 0.8)))
    
    # Create canvas
    gap = 100
    canvas_height = target_height
    canvas_width = face1_resized.shape[1] + face2_resized.shape[1] + gap
    canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 150  # Gray background
    
    # Place both faces with good lighting
    canvas[0:face1_resized.shape[0], 0:face1_resized.shape[1]] = face1_resized
    
    y_offset = (canvas_height - face2_resized.shape[0]) // 2
    x_start = face1_resized.shape[1] + gap
    canvas[y_offset:y_offset+face2_resized.shape[0], x_start:x_start+face2_resized.shape[1]] = face2_resized
    
    return canvas

def test_photo_holding_attack():
    """
    Critical security test: Verify that photo-holding attacks are blocked
    """
    print("="*70)
    print("CRITICAL SECURITY TEST: Photo-Holding Attack Prevention")
    print("="*70)
    print()
    print("Scenario: Attacker holds a photo of authorized person next to their face")
    print("Expected: System detects 2 faces and rejects BEFORE liveness check")
    print()
    
    # Create the attack scenario
    print("📸 Creating simulated photo-holding attack frame...")
    attack_frame = create_photo_holding_attack_frame()
    
    if attack_frame is None:
        print("❌ Could not create test frame")
        return False
    
    # Save for inspection
    test_image_path = "test_photo_holding_attack.jpg"
    cv2.imwrite(test_image_path, attack_frame)
    print(f"✅ Attack frame saved to: {test_image_path}")
    print(f"   (You can open this to see the simulated attack)")
    print()
    
    # Test 1: Liveness check should detect multiple faces
    print("🔍 Test 1: Sending to /liveness-check endpoint...")
    with open(test_image_path, 'rb') as f:
        files = {'file': (test_image_path, f, 'image/jpeg')}
        response = requests.post(f"{BASE_URL}/liveness-check", files=files)
    
    liveness_data = response.json()
    print(f"   Response: {liveness_data.get('message', 'No message')}")
    print(f"   Error code: {liveness_data.get('error_code', 'None')}")
    print(f"   Face count: {liveness_data.get('face_count', 'Not provided')}")
    print()
    
    # Verify it was rejected for multiple faces
    test1_passed = (
        not liveness_data.get('is_live', True) and
        liveness_data.get('error_code') == 'MULTIPLE_FACES' and
        liveness_data.get('face_count', 0) > 1
    )
    
    if test1_passed:
        print("✅ TEST 1 PASSED: Multiple faces detected, attack blocked!")
    else:
        print("❌ TEST 1 FAILED: Attack not properly detected")
        print(f"   Expected: is_live=False, error_code='MULTIPLE_FACES', face_count > 1")
        print(f"   Got: is_live={liveness_data.get('is_live')}, error_code={liveness_data.get('error_code')}, face_count={liveness_data.get('face_count')}")
    print()
    
    # Test 2: Complete verification should also block
    print("🔍 Test 2: Sending to /complete-verification endpoint...")
    
    # First extract face from ID
    id_path = "photos/enoch_pass.jpeg"
    with open(id_path, 'rb') as f:
        files = {'file': ('id.jpg', f, 'image/jpeg')}
        id_response = requests.post(f"{BASE_URL}/extract-face", files=files)
    
    id_data = id_response.json()
    if not id_data.get('success'):
        print(f"   ⚠️  Could not extract ID face: {id_data.get('message')}")
        test2_passed = False
    else:
        # Now try complete verification with attack frame
        with open(id_path, 'rb') as id_file, open(test_image_path, 'rb') as attack_file:
            files = {
                'id_image': ('id.jpg', id_file, 'image/jpeg'),
                'live_image': ('attack.jpg', attack_file, 'image/jpeg')
            }
            response = requests.post(f"{BASE_URL}/complete-verification", files=files)
        
        verify_data = response.json()
        print(f"   Response: {verify_data.get('message', 'No message')}")
        print(f"   Error code: {verify_data.get('error_code', 'None')}")
        print(f"   Face count: {verify_data.get('face_count', 'Not provided')}")
        print()
        
        # Verify it was rejected for multiple faces
        test2_passed = (
            not verify_data.get('verified', True) and
            verify_data.get('error_code') == 'MULTIPLE_FACES' and
            verify_data.get('face_count', 0) > 1
        )
        
        if test2_passed:
            print("✅ TEST 2 PASSED: Complete verification blocked attack!")
        else:
            print("❌ TEST 2 FAILED: Complete verification did not properly block attack")
            print(f"   Expected: verified=False, error_code='MULTIPLE_FACES', face_count > 1")
            print(f"   Got: verified={verify_data.get('verified')}, error_code={verify_data.get('error_code')}, face_count={verify_data.get('face_count')}")
    
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    
    if test1_passed and test2_passed:
        print("✅ ALL TESTS PASSED - Photo-holding attacks are properly blocked!")
        print()
        print("Security verification:")
        print("  ✅ Multiple faces detected before liveness check")
        print("  ✅ Attack blocked at earliest possible stage")
        print("  ✅ System correctly enforces single-person requirement")
        return True
    else:
        print("❌ SECURITY VULNERABILITY DETECTED!")
        print()
        print("The system may be vulnerable to photo-holding attacks.")
        print("Please review the face detection sensitivity and verification flow.")
        return False

def check_backend_running():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║   PHOTO-HOLDING ATTACK PREVENTION TEST                            ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Check backend
    print("🔍 Checking backend status...")
    if not check_backend_running():
        print("❌ Backend is not running!")
        print("   Please start: python backend/app.py")
        exit(1)
    
    print("✅ Backend is running")
    print()
    
    # Run test
    success = test_photo_holding_attack()
    
    print()
    if success:
        print("🎉 System is secure against photo-holding attacks!")
    else:
        print("⚠️  System needs improvement to block photo-holding attacks")
    print()
