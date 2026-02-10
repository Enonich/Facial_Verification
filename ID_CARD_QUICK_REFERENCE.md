# ID Card OCR Integration - Quick Reference

## The Flow (What Users See)

```
┌─────────────────────────────────────────────────────────┐
│ 1. ENTER DETAILS (New!)                                 │
│    • Full Name input                                     │
│    • ID Type selector (GH Card / Voter's ID / Passport) │
│    • ID Number input                                     │
│    • Form validation                                     │
│    └─→ Click "Continue to ID Upload"                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. UPLOAD ID DOCUMENT (Updated!)                        │
│    • Shows your entered details at top                  │
│    • Upload file OR use camera                          │
│    • System extracts face                               │
│    • System extracts details via OCR                    │
│    • System verifies extracted details match            │
│    └─→ Click "Proceed to Face Verification"           │
│        (only when details match)                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. FACE VERIFICATION (Existing!)                        │
│    • Look at camera for liveness check                  │
│    • System verifies you match ID photo                 │
│    └─→ Success: Identity Verified!                     │
└─────────────────────────────────────────────────────────┘
```

## What Happens Behind the Scenes

### Step 2.1: Face Extraction
```
Upload ID Image
    ↓
Face detection & extraction
    ↓
Returns: Face image URL
```

### Step 2.2: OCR Details Extraction
```
Upload ID Image
    ↓
PaddleOCR reads text
    ↓
Extract based on ID type:
  • Ghana Card → Full Name, Card Number
  • Voter's ID → Full Name, ID Number
  • Passport → Full Name, Passport Number
    ↓
Returns: Extracted name & ID number
```

### Step 2.3: Details Verification
```
Compare:
  User Entered          vs          Extracted from ID
  "John Doe"                        "John Doe"
  "GHA-123456789-0"                "GHA-123456789-0"
    ↓
Name Similarity Check (≥80%)
ID Number Match Check (exact)
    ↓
Both Pass → ✓ Verified
Either Fails → ⚠️ Show details, ask to retry
```

## API Endpoints

### POST /ocr-extract
**Extracts details from ID document**

Input:
- Image file
- ID type

Output:
- name: "John Doe"
- id_number: "GHA-123456789-0"
- confidence: 0.95

### POST /verify-id-details
**Compares extracted vs entered details**

Input:
- user_name, user_id_number
- extracted_name, extracted_id_number
- id_type

Output:
- verified: true/false
- name_similarity: 95.5
- differences: [] or [mismatch details]

## Component Hierarchy

```
App.jsx (Main App)
├── IDVerificationForm.jsx (NEW)
│   └── Form fields + validation
├── Upload ID View
│   ├── Shows user details summary
│   ├── File upload / camera capture
│   └── Shows extracted face & details
└── Face Verification View
    └── (existing liveness + verification)
```

## State Variables (New)

In App.jsx:

```javascript
const [userDetails, setUserDetails] = useState(null);
// {fullName, idType, idNumber}

const [detailsSubmitted, setDetailsSubmitted] = useState(false);
// true = form submitted, show ID upload

const [extractedIdDetails, setExtractedIdDetails] = useState(null);
// {name, id_number, id_type}

const [idDetailsVerified, setIdDetailsVerified] = useState(false);
// true = extracted details match user entered

const [ocrProcessing, setOcrProcessing] = useState(false);
// true while OCR is processing
```

## Key Functions (New)

### handleDetailsSubmit(formData)
- Called when user submits the form
- Stores user details
- Moves to Upload ID step

### verifyIdDetails(userDetails, extractedData)
- Called after OCR extraction
- Compares names (fuzzy match, ≥80%)
- Compares ID numbers (exact match)
- Sets idDetailsVerified flag

## Validation Rules

### Name
- Minimum 3 characters
- Letters, spaces, hyphens only
- Case-insensitive comparison
- Fuzzy matching (80%+ similarity)

### Ghana Card Number
- Format: `GHA-XXXXXXXXX-X`
- Example: `GHA-123456789-0`

### Voter's ID Number
- 8-12 digits
- Example: `12345678`

### Passport Number
- 6-12 alphanumeric characters
- Example: `G1234567`

## Error Messages & Solutions

| Error | User Sees | What to Do |
|-------|-----------|-----------|
| Name mismatch | "Name mismatch detected (75% similar)" | Enter name exactly as shown on ID |
| ID number mismatch | "ID number mismatch" | Verify you entered the correct ID number |
| OCR failed | "Could not extract details" | Upload clearer, better-lit ID photo |
| Invalid format | "Invalid Ghana Card format" | Check format matches GHA-XXXXXXXXX-X |
| Multiple faces detected | "Multiple faces detected" | Ensure only your face is in frame |

## Testing with Real Scenarios

### Scenario 1: Perfect Match
```
Input: Name="John Doe", ID="GHA-123456789-0"
ID Photo: Shows "John Doe", "GHA-123456789-0"
Result: ✓ Details Verified → Proceed to face verification
```

### Scenario 2: Close Name Match
```
Input: Name="Jon Doe"
ID Photo: Shows "John Doe"
Similarity: 75%
Result: ⚠️ Name mismatch (below 80% threshold) → Cannot proceed
Action: Edit name or upload different ID
```

### Scenario 3: ID Type Mismatch
```
Input: Selected "Ghana Card"
Uploaded: Voter's ID
Result: May fail to extract or show wrong fields
Action: Select correct ID type and retry
```

## Files Changed

| File | Change | Type |
|------|--------|------|
| `frontend/src/IDVerificationForm.jsx` | NEW | Component |
| `frontend/src/App.jsx` | Updated | Integration |
| `frontend/src/App.css` | Updated | Styling |
| `backend/app.py` | Updated | Endpoints |
| `backend/app.py` | Import | OCR module |

## Frontend Routes

```
Enter Details (enter-details)
  ↓
Upload ID (upload-id) [only if detailsSubmitted]
  ↓
Verify Identity (verify) [only if idDetailsVerified]
```

## Status Indicators

| Icon | Meaning |
|------|---------|
| ✓ | Success / Verified |
| ⚠️ | Warning / Needs attention |
| ✗ | Error / Failed |
| 📝 | Form / Input |
| 📇 | ID Document |
| 🎥 | Camera / Video |

## Thresholds (Configurable)

```python
# Name similarity threshold (in verify-id-details endpoint)
name_verified = name_similarity >= 0.8  # 80%

# ID number comparison
id_match = normalized_user_id == normalized_extracted_id  # Exact match
```

To adjust: Edit `/verify-id-details` endpoint in `app.py`

---

**Quick Start:**
1. Start backend: `python -m uvicorn app:app --reload`
2. Start frontend: `npm run dev`
3. Navigate to Enter Details
4. Fill in your info
5. Upload ID
6. Proceed to face verification

**That's it!** The entire flow now requires users to verify their details before proceeding to face verification.
