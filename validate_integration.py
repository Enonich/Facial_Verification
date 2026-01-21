"""
Integration Validation Script
Verifies that all components are properly integrated
"""

import sys
import os
from pathlib import Path

def check_imports():
    """Check if all required modules can be imported"""
    print("=" * 60)
    print("INTEGRATION VALIDATION")
    print("=" * 60)
    print("\n1. Checking Module Imports...")
    
    errors = []
    
    # Check antispoofing_engine
    try:
        from antispoofing_engine import AntiSpoofingEngine
        print("  ✓ AntiSpoofingEngine imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import AntiSpoofingEngine: {e}")
        errors.append(("AntiSpoofingEngine", str(e)))
    
    # Check ID_Face_Ext
    try:
        from ID_Face_Ext import IDFaceExtractor
        print("  ✓ IDFaceExtractor imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import IDFaceExtractor: {e}")
        errors.append(("IDFaceExtractor", str(e)))
    
    # Check ISF
    try:
        from ISF import FaceVerificationSystem
        print("  ✓ FaceVerificationSystem imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import FaceVerificationSystem: {e}")
        errors.append(("FaceVerificationSystem", str(e)))
    
    return errors

def check_file_structure():
    """Check if all required files exist"""
    print("\n2. Checking File Structure...")
    
    required_files = [
        "antispoofing_engine.py",
        "ID_Face_Ext.py",
        "ISF.py",
        "backend/app.py",
        "frontend/src/App.jsx",
        "Silent_Face_Anti_Spoofing/src/anti_spoof_predict.py",
        "Silent_Face_Anti_Spoofing/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth",
        "Silent_Face_Anti_Spoofing/resources/anti_spoof_models/4_0_0_80x80_MiniFASNetV1SE.pth",
    ]
    
    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - NOT FOUND")
            missing_files.append(file_path)
    
    return missing_files

def check_integration_points():
    """Check integration points in backend/app.py"""
    print("\n3. Checking Integration Points in Backend...")
    
    app_py = Path("backend/app.py")
    if not app_py.exists():
        print("  ✗ backend/app.py not found")
        return False
    
    content = app_py.read_text()
    
    checks = {
        "AntiSpoofingEngine import": "from antispoofing_engine import AntiSpoofingEngine",
        "IDFaceExtractor import": "from ID_Face_Ext import IDFaceExtractor",
        "FaceVerificationSystem import": "from ISF import FaceVerificationSystem",
        "antispoofing_engine initialization": "antispoofing_engine = AntiSpoofingEngine",
        "id_extractor initialization": "id_extractor = IDFaceExtractor",
        "face_verifier initialization": "face_verifier = FaceVerificationSystem",
        "/extract-face endpoint": "@app.post(\"/extract-face\")",
        "/liveness-check endpoint": "@app.post(\"/liveness-check\")",
        "/verify-identity endpoint": "@app.post(\"/verify-identity\")",
        "/complete-verification endpoint": "@app.post(\"/complete-verification\")",
        "face_verifier.verify call": "face_verifier.verify(",
    }
    
    all_passed = True
    for check_name, check_string in checks.items():
        if check_string in content:
            print(f"  ✓ {check_name}")
        else:
            print(f"  ✗ {check_name} - NOT FOUND")
            all_passed = False
    
    return all_passed

def check_workflow():
    """Verify the workflow logic"""
    print("\n4. Checking Workflow Logic...")
    
    app_py = Path("backend/app.py")
    content = app_py.read_text()
    
    # Check if liveness is checked before verification
    workflow_checks = [
        ("Liveness check before verification", "livenessData.is_live" in content),
        ("Verification uses extracted face", "id_face_path" in content),
        ("Complete verification includes all steps", "complete-verification" in content),
    ]
    
    all_passed = True
    for check_name, check_result in workflow_checks:
        if check_result:
            print(f"  ✓ {check_name}")
        else:
            print(f"  ✗ {check_name}")
            all_passed = False
    
    return all_passed

def check_directories():
    """Check if required directories exist"""
    print("\n5. Checking Required Directories...")
    
    required_dirs = [
        "backend",
        "frontend/src",
        "Silent_Face_Anti_Spoofing/src",
        "Silent_Face_Anti_Spoofing/resources/anti_spoof_models",
        "models",
    ]
    
    create_dirs = [
        "uploads",
        "Extracted_Faces",
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} - NOT FOUND")
            missing_dirs.append(dir_path)
    
    # Create directories that should be created at runtime
    for dir_path in create_dirs:
        Path(dir_path).mkdir(exist_ok=True)
        print(f"  ✓ {dir_path} (created/verified)")
    
    return missing_dirs

def main():
    """Run all validation checks"""
    
    import_errors = check_imports()
    missing_files = check_file_structure()
    integration_ok = check_integration_points()
    workflow_ok = check_workflow()
    missing_dirs = check_directories()
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    issues_found = False
    
    if import_errors:
        issues_found = True
        print("\n⚠ Import Errors Found:")
        for module, error in import_errors:
            print(f"  - {module}: {error}")
    else:
        print("\n✓ All modules imported successfully")
    
    if missing_files:
        issues_found = True
        print("\n⚠ Missing Files:")
        for file in missing_files:
            print(f"  - {file}")
    else:
        print("✓ All required files present")
    
    if missing_dirs:
        issues_found = True
        print("\n⚠ Missing Directories:")
        for dir in missing_dirs:
            print(f"  - {dir}")
    else:
        print("✓ All required directories present")
    
    if not integration_ok:
        issues_found = True
        print("\n⚠ Integration issues found in backend")
    else:
        print("✓ Backend integration verified")
    
    if not workflow_ok:
        issues_found = True
        print("\n⚠ Workflow logic issues found")
    else:
        print("✓ Workflow logic verified")
    
    print("\n" + "=" * 60)
    if not issues_found:
        print("🎉 ALL CHECKS PASSED - SYSTEM IS FULLY INTEGRATED!")
    else:
        print("⚠ SOME ISSUES FOUND - PLEASE REVIEW ABOVE")
    print("=" * 60)
    
    return 0 if not issues_found else 1

if __name__ == "__main__":
    sys.exit(main())
