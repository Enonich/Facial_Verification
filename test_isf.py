"""
Test script for ISF.py - Face Verification System
Tests the FaceVerificationSystem and displays quality grades
"""

import cv2
import sys
from pathlib import Path

# Import the FaceVerificationSystem
from ISF import FaceVerificationSystem


def get_quality_grade(score: float) -> str:
    """Convert quality score to letter grade"""
    if score >= 90:
        return "A+ (Excellent)"
    elif score >= 80:
        return "A (Very Good)"
    elif score >= 70:
        return "B (Good)"
    elif score >= 60:
        return "C (Acceptable)"
    elif score >= 50:
        return "D (Poor)"
    else:
        return "F (Very Poor)"


def get_blur_assessment(blur_score: float) -> str:
    """Assess blur level"""
    if blur_score >= 500:
        return "Very Sharp"
    elif blur_score >= 200:
        return "Sharp"
    elif blur_score >= 100:
        return "Acceptable"
    elif blur_score >= 50:
        return "Slightly Blurry"
    else:
        return "Very Blurry"


def get_brightness_assessment(brightness: float) -> str:
    """Assess brightness level"""
    if brightness < 50:
        return "Too Dark"
    elif brightness < 80:
        return "Slightly Dark"
    elif brightness <= 180:
        return "Good"
    elif brightness <= 210:
        return "Slightly Bright"
    else:
        return "Too Bright"


def get_contrast_assessment(contrast: float) -> str:
    """Assess contrast level"""
    if contrast >= 60:
        return "High"
    elif contrast >= 40:
        return "Good"
    elif contrast >= 30:
        return "Acceptable"
    elif contrast >= 20:
        return "Low"
    else:
        return "Very Low"


def print_quality_report(quality: dict, image_name: str):
    """Print a detailed quality report"""
    print(f"\n{'='*60}")
    print(f"📊 IMAGE QUALITY REPORT: {image_name}")
    print(f"{'='*60}")
    
    # Overall grade
    score = quality['quality_score']
    grade = get_quality_grade(score)
    print(f"\n🏆 Overall Quality Score: {score:.1f}/100 - Grade: {grade}")
    
    # Resolution
    w, h = quality['resolution']
    print(f"\n📐 Resolution: {w} x {h} pixels")
    if w >= 640 and h >= 640:
        print("   ✅ Resolution is sufficient")
    elif w >= 320 and h >= 320:
        print("   ⚠️ Resolution is acceptable but could be better")
    else:
        print("   ❌ Resolution is too low")
    
    # Blur assessment
    blur = quality['blur_score']
    blur_assessment = get_blur_assessment(blur)
    print(f"\n🔍 Sharpness Score: {blur:.1f}")
    print(f"   Assessment: {blur_assessment}")
    if blur >= 100:
        print("   ✅ Image is sharp enough")
    else:
        print("   ⚠️ Image may be too blurry")
    
    # Brightness assessment
    brightness = quality['brightness']
    brightness_assessment = get_brightness_assessment(brightness)
    print(f"\n💡 Brightness: {brightness:.1f}/255")
    print(f"   Assessment: {brightness_assessment}")
    if 80 <= brightness <= 180:
        print("   ✅ Brightness is optimal")
    else:
        print("   ⚠️ Brightness could be improved")
    
    # Contrast assessment
    contrast = quality['contrast']
    contrast_assessment = get_contrast_assessment(contrast)
    print(f"\n🎨 Contrast: {contrast:.1f}")
    print(f"   Assessment: {contrast_assessment}")
    if contrast >= 30:
        print("   ✅ Contrast is sufficient")
    else:
        print("   ⚠️ Low contrast may affect detection")
    
    # Enhancement recommendation
    print(f"\n🔧 Needs Enhancement: {'Yes' if quality['needs_enhancement'] else 'No'}")
    
    print(f"\n{'='*60}\n")


def test_verification(verifier, id_path: str, live_path: str):
    """Test verification between two images"""
    print(f"\n{'#'*60}")
    print("🔐 RUNNING VERIFICATION TEST")
    print(f"{'#'*60}")
    print(f"\n📄 ID Photo: {id_path}")
    print(f"📸 Live Photo: {live_path}")
    
    # Check if files exist
    if not Path(id_path).exists():
        print(f"❌ Error: ID photo not found at {id_path}")
        return
    if not Path(live_path).exists():
        print(f"❌ Error: Live photo not found at {live_path}")
        return
    
    # Load and assess ID image quality
    id_img = cv2.imread(id_path)
    id_quality = verifier.assess_image_quality(id_img)
    print_quality_report(id_quality, f"ID Photo ({Path(id_path).name})")
    
    # Load and assess live image quality
    live_img = cv2.imread(live_path)
    live_quality = verifier.assess_image_quality(live_img)
    print_quality_report(live_quality, f"Live Photo ({Path(live_path).name})")
    
    # Run verification
    print("🔄 Running face verification...")
    result = verifier.verify(id_path, live_path)
    
    # Print results
    print(f"\n{'='*60}")
    print("🎯 VERIFICATION RESULT")
    print(f"{'='*60}")
    
    if not result.get('success', False):
        print(f"\n❌ Verification Failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        return result
    
    match = result['match']
    similarity = result['similarity']
    threshold = result['threshold']
    
    if match:
        print(f"\n✅ MATCH CONFIRMED!")
    else:
        print(f"\n❌ NO MATCH!")
    
    print(f"\n📊 Similarity Score: {similarity:.4f} ({similarity*100:.2f}%)")
    print(f"📏 Threshold Used: {threshold:.4f} ({threshold*100:.2f}%)")
    print(f"🎚️ Match Confidence: {result['match_confidence']}")
    print(f"⏱️ Processing Time: {result['processing_time_ms']:.1f} ms")
    
    print(f"\n📋 Additional Details:")
    print(f"   ID Face Detection Score: {result['details']['id_face_score']:.4f}")
    print(f"   Live Face Detection Score: {result['details']['live_face_score']:.4f}")
    print(f"   Threshold Type: {result['details']['threshold_type']}")
    print(f"   ID Photo Preprocessed: {result['id_preprocessed']}")
    
    print(f"\n{'='*60}\n")
    return result


def main():
    print("\n" + "🚀"*30)
    print("\n  INSIGHTFACE VERIFICATION SYSTEM TEST")
    print("\n" + "🚀"*30 + "\n")
    
    # Initialize the system
    print("⏳ Initializing Face Verification System...")
    try:
        verifier = FaceVerificationSystem(
            model_name='buffalo_l',
            use_gpu=False,  # Set to True if you have GPU
            det_size=(640, 640)
        )
        print("✅ System initialized successfully!\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    
    # Check for test images
    photos_dir = Path("photos")
    extracted_dir = Path("Extracted_Faces")
    backend_extracted = Path("backend/Extracted_Faces")
    
    # Find available images
    print("🔍 Looking for test images...\n")
    
    # List available photos
    if photos_dir.exists():
        photos = list(photos_dir.glob("*.jpg")) + list(photos_dir.glob("*.png")) + list(photos_dir.glob("*.jpeg"))
        if photos:
            print(f"📁 Found {len(photos)} images in 'photos/' directory:")
            for p in photos:
                print(f"   - {p.name}")
    
    # List extracted faces
    for ext_dir in [extracted_dir, backend_extracted]:
        if ext_dir.exists():
            faces = list(ext_dir.glob("*.jpg")) + list(ext_dir.glob("*.png"))
            if faces:
                print(f"\n📁 Found {len(faces)} images in '{ext_dir}/' directory:")
                for f in faces:
                    print(f"   - {f.name}")
    
    # Ask user for image paths or use defaults
    print("\n" + "-"*60)
    
    # Try to find default test images
    id_photo = None
    live_photo = None
    
    # Look for ID photos
    for pattern in ["*ID*", "*id*", "*front*", "*Front*"]:
        matches = list(photos_dir.glob(f"{pattern}.jpg")) + list(photos_dir.glob(f"{pattern}.png"))
        if matches:
            id_photo = str(matches[0])
            break
    
    # Look for live/selfie photos
    for pattern in ["*live*", "*Live*", "*selfie*", "*Selfie*", "*face*"]:
        matches = list(photos_dir.glob(f"{pattern}.jpg")) + list(photos_dir.glob(f"{pattern}.png"))
        if matches:
            live_photo = str(matches[0])
            break
    
    if id_photo and live_photo:
        print(f"\n🎯 Using detected images:")
        print(f"   ID Photo: {id_photo}")
        print(f"   Live Photo: {live_photo}")
        test_verification(verifier, id_photo, live_photo)
    else:
        print("\n⚠️ Could not auto-detect test images.")
        print("\n📝 To test verification, call:")
        print("   python test_isf.py <id_photo_path> <live_photo_path>")
        print("\n   Or place images named with 'ID' and 'live' in the 'photos/' directory.")
        
        # If command line args provided
        if len(sys.argv) >= 3:
            id_photo = sys.argv[1]
            live_photo = sys.argv[2]
            test_verification(verifier, id_photo, live_photo)
        else:
            # Just test image quality on any available image
            all_images = []
            for d in [photos_dir, extracted_dir, backend_extracted]:
                if d.exists():
                    all_images.extend(list(d.glob("*.jpg")) + list(d.glob("*.png")))
            
            if all_images:
                print("\n📊 Testing image quality on available images:\n")
                for img_path in all_images[:3]:  # Test first 3 images
                    img = cv2.imread(str(img_path))
                    if img is not None:
                        quality = verifier.assess_image_quality(img)
                        print_quality_report(quality, img_path.name)


if __name__ == "__main__":
    main()
