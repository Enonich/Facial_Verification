# System Architecture Diagram - ID Card OCR Integration

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WEB APPLICATION                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FRONTEND (React - frontend/src/)                            │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                                                               │   │
│  │  App.jsx (Main Application)                                  │   │
│  │  ├─ State Management                                         │   │
│  │  │  ├─ userDetails (new)                                     │   │
│  │  │  ├─ detailsSubmitted (new)                                │   │
│  │  │  ├─ extractedIdDetails (new)                              │   │
│  │  │  ├─ idDetailsVerified (new)                               │   │
│  │  │  ├─ ocrProcessing (new)                                   │   │
│  │  │  └─ ... (existing state)                                  │   │
│  │  ├─ Views                                                    │   │
│  │  │  ├─ Enter Details View (NEW)                              │   │
│  │  │  ├─ Upload ID View (UPDATED)                              │   │
│  │  │  └─ Face Verification View (existing)                     │   │
│  │  └─ Event Handlers                                           │   │
│  │     ├─ handleDetailsSubmit() (new)                           │   │
│  │     ├─ verifyIdDetails() (new)                               │   │
│  │     ├─ handleIdUpload() (updated)                            │   │
│  │     └─ captureId() (updated)                                 │   │
│  │                                                               │   │
│  │  IDVerificationForm.jsx (NEW COMPONENT)                      │   │
│  │  ├─ Form Fields                                              │   │
│  │  │  ├─ Full Name input                                       │   │
│  │  │  ├─ ID Type selector                                      │   │
│  │  │  └─ ID Number input                                       │   │
│  │  ├─ Validation                                               │   │
│  │  │  ├─ Name validation                                       │   │
│  │  │  ├─ ID type selection check                               │   │
│  │  │  └─ ID format validation                                  │   │
│  │  └─ Event Handlers                                           │   │
│  │     ├─ onFormSubmit()                                        │   │
│  │     └─ onCancel()                                            │   │
│  │                                                               │   │
│  │  App.css (UPDATED)                                           │   │
│  │  ├─ Form styling                                             │   │
│  │  ├─ Input field styles                                       │   │
│  │  ├─ Error message styles                                     │   │
│  │  └─ Details summary card styles                              │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              │ HTTP Requests                         │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  BACKEND (FastAPI - backend/app.py)                          │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                                                               │   │
│  │  Global State                                                │   │
│  │  ├─ antispoofing_engine                                      │   │
│  │  ├─ id_extractor                                             │   │
│  │  ├─ face_verifier                                            │   │
│  │  └─ ocr_engine (NEW)                                         │   │
│  │                                                               │   │
│  │  API Endpoints (NEW)                                         │   │
│  │  ├─ POST /ocr-extract                                        │   │
│  │  │  Input: file, id_type                                     │   │
│  │  │  Output: extracted_data, ocr_confidence                   │   │
│  │  │  Process:                                                 │   │
│  │  │    1. Save temp file                                      │   │
│  │  │    2. Call IDCardOCR.process_id_card()                    │   │
│  │  │    3. Extract name & ID based on type                     │   │
│  │  │    4. Return results with confidence                      │   │
│  │  │                                                            │   │
│  │  └─ POST /verify-id-details                                  │   │
│  │     Input: user_name, extracted_name, etc.                   │   │
│  │     Output: verified, name_similarity, differences           │   │
│  │     Process:                                                 │   │
│  │       1. Normalize both name and ID                          │   │
│  │       2. Calculate name similarity (SequenceMatcher)         │   │
│  │       3. Compare ID numbers (exact)                          │   │
│  │       4. Return verification result                          │   │
│  │                                                               │   │
│  │  Existing Endpoints (UNCHANGED)                              │   │
│  │  ├─ POST /extract-face                                       │   │
│  │  ├─ POST /liveness-check                                     │   │
│  │  ├─ POST /verify-identity                                    │   │
│  │  └─ POST /complete-verification                              │   │
│  │                                                               │   │
│  │  Helper Functions (NEW)                                      │   │
│  │  ├─ _string_similarity()                                     │   │
│  │  ├─ _normalize_name()                                        │   │
│  │  └─ _normalize_id_number()                                   │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              │ Use/Call                              │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  EXTERNAL MODULES                                            │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                                                               │   │
│  │  IDCardOCR (id_card_ocr.py) - EXISTING                       │   │
│  │  ├─ __init__()                                               │   │
│  │  ├─ perform_ocr()                                            │   │
│  │  ├─ extract_ghana_card_data()                                │   │
│  │  ├─ extract_voters_id_data()                                 │   │
│  │  ├─ extract_passport_data()                                  │   │
│  │  └─ process_id_card()                                        │   │
│  │                                                               │   │
│  │  Used by: /ocr-extract endpoint                              │   │
│  │                                                               │   │
│  │  SequenceMatcher (difflib) - EXISTING PYTHON MODULE          │   │
│  │  ├─ Calculates string similarity                             │   │
│  │  └─ Returns ratio (0.0 - 1.0)                                │   │
│  │                                                               │   │
│  │  Used by: _string_similarity() helper & /verify-id-details   │   │
│  │                                                               │   │
│  │  Other Modules (Unchanged)                                   │   │
│  │  ├─ AntiSpoofingEngine                                       │   │
│  │  ├─ IDFaceExtractor                                          │   │
│  │  └─ FaceVerificationSystem                                   │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
USER INTERACTION FLOW:

┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: User Enters Details                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  IDVerificationForm                                                  │
│  ├─ Display form                                                     │
│  ├─ User fills: Name, ID Type, ID Number                            │
│  ├─ Validation on each field change                                  │
│  └─ User clicks "Continue"                                           │
│       │                                                               │
│       ├─→ Form validation completes                                   │
│       │   ├─ Name: 3+ chars, letters/spaces/hyphens                  │
│       │   ├─ ID Type: Must be selected                               │
│       │   └─ ID Number: Must match format                            │
│       │                                                               │
│       └─→ handleDetailsSubmit({fullName, idType, idNumber})          │
│           ├─ setUserDetails()                                        │
│           ├─ setDetailsSubmitted(true)                               │
│           └─ setActiveView('upload-id')                              │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: User Uploads/Captures ID                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Upload ID View (Shows user details summary)                        │
│  ├─ Display: Name, ID Type, ID Number (read-only)                   │
│  ├─ User uploads file OR uses camera                                │
│  │                                                                    │
│  └─→ handleIdUpload() / captureId()                                 │
│       │                                                               │
│       ├─ (Existing) POST /extract-face                               │
│       │  ├─ Input: ID image file                                     │
│       │  ├─ Process: Face detection & extraction                     │
│       │  └─ Output: Face image URL, confidence                       │
│       │     ├─ setExtractedFace(url)                                │
│       │     ├─ setIdImage(preview)                                  │
│       │     └─ setIdMessage('✓ Face extracted')                     │
│       │                                                               │
│       ├─ (NEW) POST /ocr-extract ◄─────────────────────────────────┐
│       │  ├─ Input: Same image file, id_type                         │
│       │  ├─ Process:                                                 │
│       │  │  ├─ Save temp file                                        │
│       │  │  ├─ Call ocr_engine.process_id_card()                    │
│       │  │  ├─ Extract name & ID based on type                      │
│       │  │  └─ Cleanup temp file                                     │
│       │  └─ Output: extracted_data {name, id_number}                │
│       │     ├─ setExtractedIdDetails(data)                          │
│       │     └─ setOcrProcessing(false)                              │
│       │                                                               │
│       └─ (NEW) POST /verify-id-details ◄─────────────────────────┐
│          ├─ Input: {user_name, user_id_number, extracted_name,   │
│          │           extracted_id_number, id_type}                 │
│          ├─ Process:                                                │
│          │  ├─ Normalize user inputs                                │
│          │  ├─ Normalize extracted data                             │
│          │  ├─ Calculate name similarity                            │
│          │  │  └─ SequenceMatcher(None, name1, name2).ratio()      │
│          │  ├─ Compare ID numbers (exact)                           │
│          │  ├─ Determine if verified:                               │
│          │  │  ├─ name_similarity >= 0.80                           │
│          │  │  └─ id_match == True                                  │
│          │  └─ Build response with details                          │
│          └─ Output: {verified, name_similarity, differences}        │
│             ├─ If verified: setIdDetailsVerified(true)              │
│             │              enableProceedButton()                     │
│             └─ If not: showMismatchMessage()                        │
│                       keepProceedButtonDisabled()                   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: User Proceeds to Face Verification                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  (Existing flow continues)                                           │
│  ├─ User looks at camera                                             │
│  ├─ Liveness detection runs                                          │
│  ├─ Face comparison with ID photo                                    │
│  └─ Success → Identity Verified!                                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## State Transition Diagram

```
┌─────────────────┐
│  INITIAL STATE  │
├─────────────────┤
│ activeView: 'enter-details'
│ detailsSubmitted: false
│ userDetails: null
│ extractedIdDetails: null
│ idDetailsVerified: false
└─────────────────┘
        │
        │ User fills form & submits
        ▼
┌─────────────────┐
│ DETAILS ENTERED │
├─────────────────┤
│ activeView: 'upload-id'
│ detailsSubmitted: true
│ userDetails: {fullName, idType, idNumber}
│ extractedIdDetails: null
│ idDetailsVerified: false
└─────────────────┘
        │
        │ User uploads ID
        ├─→ Face extraction starts
        │
        ├─→ Face extraction completes
        │
        └─→ OCR extraction starts
               │
               └─→ OCR extraction completes
                      │
                      ├─ No errors
                      │    │
                      │    └─→ Details verification starts
                      │
                      └─ Errors
                           │
                           └─→ Show error message
                               User can retry
        │
        │ Details verification completes
        ▼
┌──────────────────────┐        ┌──────────────────┐
│ DETAILS MATCH        │   OR   │ DETAILS MISMATCH │
├──────────────────────┤        ├──────────────────┤
│ idDetailsVerified: true        │ idDetailsVerified: false
│ ✓ Proceed button enabled       │ ✗ Proceed button disabled
│ ✓ Can move to verify view      │ User can retry upload
└──────────────────────┘        └──────────────────┘
        │                               │
        │ User clicks "Proceed"         │ User clicks "Upload Again"
        │ OR navigates to verify        │ OR "Start Over"
        │                               │
        ▼                               ▼
┌─────────────────────────────────────────┐
│ FACE VERIFICATION                       │
│ (Existing system continues)             │
└─────────────────────────────────────────┘
        │
        ├─ Success: Identity Verified!
        └─ Failure: Show feedback, retry
```

## Validation Flow

```
NAME VALIDATION:
  User Input: "John Doe"
    │
    ├─ Frontend: Regex check (letters/spaces/hyphens, 3+)
    │  └─ ✓ Valid format
    │
    └─ Backend: Name comparison (from /verify-id-details)
       ├─ Extract from ID: "John Kwame Doe"
       ├─ Normalize both
       ├─ Calculate similarity: 85%
       └─ 85% >= 80%? YES → name_verified = true

ID NUMBER VALIDATION:
  User Input: "GHA-123456789-0"
    │
    ├─ Frontend: Regex check (GHA-\d{9}-\d)
    │  └─ ✓ Valid format
    │
    └─ Backend: ID comparison (from /verify-id-details)
       ├─ Extract from ID: "GHA-123456789-0"
       ├─ Normalize both
       ├─ Compare: "GHA123456789" == "GHA123456789"?
       └─ YES → id_verified = true

OVERALL VERIFICATION:
  name_verified && id_verified → verified = true
  └─→ User can proceed to face verification
```

## Error Flow

```
ERROR SCENARIOS:

1. OCR EXTRACTION FAILS
   ├─ Invalid image
   ├─ Unreadable text
   ├─ Wrong ID type selected
   └─ Response: Error message + Retry option

2. NAME MISMATCH
   ├─ User: "Jon Doe"
   ├─ Extracted: "John Doe"
   ├─ Similarity: 75%
   ├─ Threshold: 80%
   └─ Response: ⚠️ Show mismatch, disable proceed

3. ID NUMBER MISMATCH
   ├─ User: "GHA-111111111-1"
   ├─ Extracted: "GHA-123456789-0"
   └─ Response: ⚠️ Show mismatch, disable proceed

4. INVALID FORMAT
   ├─ User enters: "123abc" (for Ghana Card)
   ├─ Expected: "GHA-XXXXXXXXX-X"
   └─ Response: ✗ Field error, block submission

5. MISSING DETAILS
   ├─ User leaves field empty
   └─ Response: ✗ Field required error
```

## Integration Points

```
EXISTING SYSTEMS ←→ NEW SYSTEMS

Face Extraction        ←→ (No change, still works)
ID Uploading          ←→ Now requires OCR extraction after
User Details          ←→ (NEW) Must be entered first
ID Validation         ←→ (NEW) Automatic via OCR
Name Matching         ←→ (NEW) Fuzzy comparison
Details Verification  ←→ (NEW) Gates face verification
Liveness Check        ←→ (No change, still works)
Face Verification     ←→ (No change, still works)
```

---

**Architecture Last Updated:** January 23, 2026
**Status:** ✅ Complete
