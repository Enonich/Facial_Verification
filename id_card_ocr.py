"""
ID Card OCR Module
Extracts names and ID numbers from Ghana Card, Voter's ID, and Passport using PaddleOCR
"""
import os
os.environ["FLAGS_use_pir_api"] = "0"
os.environ["FLAGS_enable_mkldnn"] = "0"
os.environ["FLAGS_new_executor"] = "0"
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

from paddleocr import PaddleOCR
import cv2
import re
import numpy as np
from typing import Dict, Optional
from difflib import SequenceMatcher



class IDCardOCR:
    """
    A class for extracting information from ID cards using OCR.
    Supports Ghana Card and Voter's ID formats.
    """
    
    def __init__(self, use_textline_orientation: bool = False, lang: str = 'en'):
        """
        Initialize the OCR engine.
        
        Args:
            use_textline_orientation: Whether to use angle classification (default: False for stability)
            lang: Language for OCR (default: 'en')
        """
        self.ocr = PaddleOCR(use_textline_orientation=use_textline_orientation, lang=lang)
    
    def _normalize(self, text: str) -> str:
        """Normalize text by removing special characters and converting to uppercase."""
        return re.sub(r'[^A-Z0-9<]', '', text.upper())
    
    def _similar(self, a: str, b: str) -> float:
        """Calculate similarity ratio between two strings."""
        return SequenceMatcher(None, a, b).ratio()
    
    def read_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Read an image from the specified path.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Numpy array of the image or None if failed
        """
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not read image from {image_path}")
            print("Please check if the file exists and the path is correct")
            return None
        print(f"Image loaded successfully! Shape: {img.shape}")
        return img
    
    def perform_ocr(self, image: np.ndarray) -> list:
        """
        Perform OCR on the given image.
        
        Args:
            image: Image as numpy array
            
        Returns:
            OCR result from PaddleOCR
        """
        return self.ocr.predict(image)
    
    def extract_ghana_card_data(self, ocr_result: list, debug: bool = False) -> Dict[str, str]:
        """
        Extract name and ID number from Ghana Card format using improved label matching.
        
        Args:
            ocr_result: OCR result from PaddleOCR
            debug: Whether to print debug information
            
        Returns:
            Dictionary containing Surname, First_Names, Full_Name, and Ghana_Card_Number
        """
        data = ocr_result[0]
        texts = data["rec_texts"]
        boxes = data["dt_polys"]

        # Build items with normalized text and positions
        items = []
        for text, box in zip(texts, boxes):
            y = np.mean([p[1] for p in box])
            x = np.mean([p[0] for p in box])
            items.append({
                "text": text.strip(),
                "norm": self._normalize(text),
                "x": x,
                "y": y
            })

        # Ensure reading order (top to bottom, left to right)
        items.sort(key=lambda i: (i["y"], i["x"]))
        
        if debug:
            print("[DEBUG] Ghana Card - All OCR items:")
            for i, item in enumerate(items):
                print(f"  [{i}] text='{item['text']}' norm='{item['norm']}'")

        result = {
            "Surname": "Not Found",
            "First_Names": "Not Found",
            "Full_Name": "Not Found",
            "Ghana_Card_Number": "Not Found",
            "Ghana_Card_Number_Source": None
        }

        surname_idx = None
        firstname_idx = None

        # -------- LABEL DETECTION with multiple pattern support --------
        surname_patterns = ["SURNAMENOM", "SURNAME", "NOM"]
        firstname_patterns = ["FIRSTNAMESAPRENOMS", "FIRSTNAMES", "PRENOMS", "FIRSTNAME"]
        
        for i, item in enumerate(items):
            t = item["norm"]

            # Try surname patterns
            if surname_idx is None:
                for pattern in surname_patterns:
                    if self._similar(t, pattern) > 0.7 or pattern in t:
                        surname_idx = i
                        if debug:
                            print(f"[DEBUG] Found surname label at index {i}: '{item['text']}' matched '{pattern}'")
                        break

            # Try firstname patterns
            if firstname_idx is None:
                for pattern in firstname_patterns:
                    if self._similar(t, pattern) > 0.7 or pattern in t:
                        firstname_idx = i
                        if debug:
                            print(f"[DEBUG] Found firstname label at index {i}: '{item['text']}' matched '{pattern}'")
                        break

        # -------- VALUE EXTRACTION --------
        def next_value(idx):
            if idx is not None and idx + 1 < len(items):
                return items[idx + 1]["text"]
            return None

        result["Surname"] = next_value(surname_idx) or result["Surname"]
        result["First_Names"] = next_value(firstname_idx) or result["First_Names"]
        
        if debug:
            print(f"[DEBUG] Extracted Surname: '{result['Surname']}'")
            print(f"[DEBUG] Extracted First_Names: '{result['First_Names']}'")

        if result["Surname"] != "Not Found" and result["First_Names"] != "Not Found":
            result["Full_Name"] = f"{result['Surname']} {result['First_Names']}"

        # -------- GHANA CARD NUMBER (AUTHORITATIVE REGEX) --------
        # Format: GHA-XXXXXXXXX-X
        for item in items:
            raw = item["text"].upper().replace(" ", "")
            match = re.search(r"GHA-\d{9}-\d", raw)
            if match:
                result["Ghana_Card_Number"] = match.group()
                result["Ghana_Card_Number_Source"] = "Regex"
                break

        return result
    
    def extract_voters_id_data(self, ocr_result: list, debug: bool = False) -> Dict[str, str]:
        """
        Extract name and ID number from Voter's ID format using improved label matching.
        
        Args:
            ocr_result: OCR result from PaddleOCR
            debug: Whether to print debug information
            
        Returns:
            Dictionary containing Surname, Othernames, Full_Name, and ID_Number
        """
        data = ocr_result[0]
        texts = data["rec_texts"]
        boxes = data["dt_polys"]

        items = []
        for text, box in zip(texts, boxes):
            y = np.mean([p[1] for p in box])
            x = np.mean([p[0] for p in box])
            items.append({
                "text": text.strip(),
                "norm": self._normalize(text),
                "x": x,
                "y": y
            })

        # Ensure reading order
        items.sort(key=lambda i: (i["y"], i["x"]))
        
        if debug:
            print("[DEBUG] Voter's ID - All OCR items:")
            for i, item in enumerate(items):
                print(f"  [{i}] text='{item['text']}' norm='{item['norm']}'")

        result = {
            "Surname": "Not Found",
            "Othernames": "Not Found",
            "Full_Name": "Not Found",
            "ID_Number": "Not Found",
            "ID_Number_Source": None
        }

        surname_idx = None
        othernames_idx = None
        id_idx = None

        def next_value_same_row_right(idx: Optional[int], y_tol: float = 12.0) -> Optional[str]:
            """Prefer the OCR token on the same row (similar y) that is immediately to the right."""
            if idx is None or idx < 0 or idx >= len(items):
                return None

            label = items[idx]
            label_x = label["x"]
            label_y = label["y"]

            candidates = [
                it for it in items
                if abs(it["y"] - label_y) <= y_tol and it["x"] > label_x
            ]
            if not candidates:
                return None

            candidates.sort(key=lambda it: (it["x"] - label_x))
            return candidates[0]["text"]

        # ---- LABEL DETECTION (keep it strict to avoid false matches) ----
        # The notebook version is strict here; that helps prevent selecting unrelated numbers.
        for i, item in enumerate(items):
            t = item["norm"]

            if surname_idx is None and self._similar(t, "SURNAME") > 0.8:
                surname_idx = i
                if debug:
                    print(f"[DEBUG] Found surname label at index {i}: '{item['text']}'")

            if othernames_idx is None and self._similar(t, "OTHERNAMES") > 0.8:
                othernames_idx = i
                if debug:
                    print(f"[DEBUG] Found othernames label at index {i}: '{item['text']}'")

            if id_idx is None and (
                self._similar(t, "VOTERIDENTIFICATIONNUMBER") > 0.8 or
                self._similar(t, "VOTERIDNUMBER") > 0.8
            ):
                id_idx = i
                if debug:
                    print(f"[DEBUG] Found ID label at index {i}: '{item['text']}'")

        # ---- VALUE EXTRACTION ----
        def next_value(idx):
            if idx is not None and idx + 1 < len(items):
                return items[idx + 1]["text"]
            return None

        result["Surname"] = next_value(surname_idx) or result["Surname"]
        result["Othernames"] = next_value(othernames_idx) or result["Othernames"]
        
        if debug:
            print(f"[DEBUG] Extracted Surname: '{result['Surname']}'")
            print(f"[DEBUG] Extracted Othernames: '{result['Othernames']}'")

        if result["Surname"] != "Not Found" and result["Othernames"] != "Not Found":
            result["Full_Name"] = f"{result['Surname']} {result['Othernames']}"

        # ---- ID NUMBER EXTRACTION ----
        # Prefer a value on the same row, to the right of the label.
        # Fallback to the "next item" behavior from the notebook.
        id_candidate = next_value_same_row_right(id_idx) or next_value(id_idx)

        def is_plausible_voter_id(digits: str) -> bool:
            if not re.fullmatch(r"\d{8,12}", digits):
                return False
            # Avoid common false positives like YYYYMMDD / YYYY.... (often DOB/issue dates)
            if len(digits) == 8 and digits[:4] in {str(y) for y in range(1900, 2101)}:
                return False
            return True

        if id_candidate:
            id_norm = re.sub(r"\D", "", id_candidate)
            if is_plausible_voter_id(id_norm):
                result["ID_Number"] = id_norm
                result["ID_Number_Source"] = "Label"

        # ---- FALLBACK: REGEX SCAN ----
        if result["ID_Number"] == "Not Found":
            digit_candidates = []
            for item in items:
                digits = re.sub(r"\D", "", item["text"])
                if is_plausible_voter_id(digits):
                    digit_candidates.append({"digits": digits, "x": item["x"], "y": item["y"]})

            if digit_candidates:
                # Prefer longest (dates are often 8), then top-most.
                digit_candidates.sort(key=lambda d: (-len(d["digits"]), d["y"], d["x"]))
                result["ID_Number"] = digit_candidates[0]["digits"]
                result["ID_Number_Source"] = "Regex"
        return result
    
    def extract_passport_data(self, ocr_result: list, debug: bool = False) -> Dict[str, str]:
        """
        Extract information from Ghana Passport using improved label matching and MRZ.
        
        Args:
            ocr_result: OCR result from PaddleOCR
            debug: Whether to print debug information
            
        Returns:
            Dictionary containing Surname, Given_Names, and Passport_Number
        """
        data = ocr_result[0]
        boxes = data['dt_polys']
        texts = data['rec_texts']

        items = []
        for text, box in zip(texts, boxes):
            y = np.mean([p[1] for p in box])
            x = np.mean([p[0] for p in box])
            items.append({
                "text": text.strip(),
                "norm": self._normalize(text),
                "x": x,
                "y": y
            })

        # Sort in reading order
        items.sort(key=lambda i: (i["y"], i["x"]))
        
        if debug:
            print("[DEBUG] Passport - All OCR items:")
            for i, item in enumerate(items):
                print(f"  [{i}] text='{item['text']}' norm='{item['norm']}'")
                print(f"       SURNAMENOM similarity: {self._similar(item['norm'], 'SURNAMENOM'):.2f}")
                print(f"       GIVENNAMESPRENOMS similarity: {self._similar(item['norm'], 'GIVENNAMESPRENOMS'):.2f}")

        info = {
            "Surname": "Not Found",
            "Given_Names": "Not Found",
            "Passport_Number": "Not Found",
            "Passport_Number_Source": None
        }

        surname_idx = None
        given_idx = None
        passport_label_idx = None

        # -------- LABEL DETECTION (with multiple pattern support) --------
        # Try multiple label patterns for better matching
        surname_patterns = ["SURNAMENOM", "SURNAME", "NOM", "FAMILYNAME"]
        given_patterns = ["GIVENNAMESPRENOMS", "GIVENNAMES", "PRENOMS", "FIRSTNAME", "FIRSTNAMES"]
        passport_patterns = ["PASSPORTNO", "PASSPORTNUMBER", "PASSPORTNUM", "PASSNO"]
        
        for i, item in enumerate(items):
            t = item["norm"]

            # Try surname patterns
            if surname_idx is None:
                for pattern in surname_patterns:
                    if self._similar(t, pattern) > 0.7 or pattern in t:
                        surname_idx = i
                        if debug:
                            print(f"[DEBUG] Found surname label at index {i}: '{item['text']}' matched '{pattern}'")
                        break

            # Try given name patterns
            if given_idx is None:
                for pattern in given_patterns:
                    if self._similar(t, pattern) > 0.7 or pattern in t:
                        given_idx = i
                        if debug:
                            print(f"[DEBUG] Found given names label at index {i}: '{item['text']}' matched '{pattern}'")
                        break

            # Try passport number patterns
            if passport_label_idx is None:
                for pattern in passport_patterns:
                    if self._similar(t, pattern) > 0.7 or pattern in t:
                        passport_label_idx = i
                        if debug:
                            print(f"[DEBUG] Found passport label at index {i}: '{item['text']}' matched '{pattern}'")
                        break

        # -------- VALUE EXTRACTION --------
        if surname_idx is not None and surname_idx + 1 < len(items):
            info["Surname"] = items[surname_idx + 1]["text"]
            if debug:
                print(f"[DEBUG] Extracted surname from label: '{info['Surname']}'")

        if given_idx is not None and given_idx + 1 < len(items):
            info["Given_Names"] = items[given_idx + 1]["text"]
            if debug:
                print(f"[DEBUG] Extracted given names from label: '{info['Given_Names']}'")

        if passport_label_idx is not None and passport_label_idx + 1 < len(items):
            candidate = items[passport_label_idx + 1]["norm"]
            if re.match(r"G[0-9]{6,8}", candidate):
                info["Passport_Number"] = candidate
                info["Passport_Number_Source"] = "Label"

        # -------- MRZ SCAN (AUTHORITATIVE) --------
        mrz_candidates = [
            i["norm"] for i in items
            if len(i["norm"]) >= 30 and i["norm"].count("<") >= 5
        ]
        
        if debug:
            print(f"[DEBUG] MRZ candidates found: {len(mrz_candidates)}")
            for idx, mrz in enumerate(mrz_candidates):
                print(f"  MRZ[{idx}]: {mrz}")

        if len(mrz_candidates) >= 2:
            mrz_line_1 = mrz_candidates[0]  # Contains document type and names
            mrz_line_2 = mrz_candidates[-1]  # Contains passport number

            # Extract passport number from line 2
            passport_no = mrz_line_2[:9].replace("<", "")
            passport_no = passport_no.replace("O", "0").replace("I", "1")

            if re.match(r"G[0-9]{6,8}", passport_no):
                info["Passport_Number"] = passport_no
                info["Passport_Number_Source"] = "MRZ"
                if debug:
                    print(f"[DEBUG] Passport number from MRZ: {passport_no}")
            
            # -------- FALLBACK: Extract names from MRZ if not found --------
            if info["Surname"] == "Not Found" or info["Given_Names"] == "Not Found":
                # MRZ Line 1 format: P<GHAAIDOO<<ENOCH<KWADWO<<<<<<<<<<<<<<<
                # After "P<GHA" comes SURNAME<<GIVENNAMES
                if debug:
                    print(f"[DEBUG] Attempting to extract names from MRZ line 1: {mrz_line_1}")
                
                # Remove document type prefix (P<GHA or similar)
                mrz_name_part = mrz_line_1
                if mrz_name_part.startswith("P"):
                    # Skip P<XXX (document type + country code)
                    parts = mrz_name_part.split("<", 2)
                    if len(parts) >= 3:
                        # Find where country code ends (usually 3 chars after P<)
                        country_end_idx = mrz_name_part.find("<", 2)
                        if country_end_idx > 0:
                            mrz_name_part = mrz_name_part[country_end_idx + 1:]
                
                # Now mrz_name_part should be: SURNAME<<GIVENNAMES<<<<
                # Split by << to separate surname from given names
                name_parts = mrz_name_part.split("<<")
                if len(name_parts) >= 2:
                    mrz_surname = name_parts[0].replace("<", " ").strip()
                    mrz_given = name_parts[1].replace("<", " ").strip()
                    
                    if info["Surname"] == "Not Found" and mrz_surname:
                        info["Surname"] = mrz_surname
                        if debug:
                            print(f"[DEBUG] Surname from MRZ: {mrz_surname}")
                    
                    if info["Given_Names"] == "Not Found" and mrz_given:
                        info["Given_Names"] = mrz_given
                        if debug:
                            print(f"[DEBUG] Given names from MRZ: {mrz_given}")

        return info
    
    def process_ghana_card(self, image_path: str) -> Optional[Dict[str, str]]:
        """
        Process a Ghana Card image and extract information.
        
        Args:
            image_path: Path to the Ghana Card image
            
        Returns:
            Dictionary with extracted data or None if failed
        """
        img = self.read_image(image_path)
        if img is None:
            return None
        
        ocr_result = self.perform_ocr(img)
        return self.extract_ghana_card_data(ocr_result)
    
    def process_voters_id(self, image_path: str) -> Optional[Dict[str, str]]:
        """
        Process a Voter's ID image and extract information.
        
        Args:
            image_path: Path to the Voter's ID image
            
        Returns:
            Dictionary with extracted data or None if failed
        """
        img = self.read_image(image_path)
        if img is None:
            return None
        
        ocr_result = self.perform_ocr(img)
        return self.extract_voters_id_data(ocr_result)
    
    def process_passport(self, image_path: str) -> Optional[Dict[str, str]]:
        """
        Process a Passport image and extract information.
        
        Args:
            image_path: Path to the Passport image
            
        Returns:
            Dictionary with extracted data or None if failed
        """
        img = self.read_image(image_path)
        if img is None:
            return None
        
        ocr_result = self.perform_ocr(img)
        return self.extract_passport_data(ocr_result)
    
    def process_id_card(self, image_path: str, card_type: str = 'auto', debug: bool = True) -> Optional[Dict[str, str]]:
        """
        Process an ID card and automatically detect or use specified type.
        Supports: Ghana Card, Voter's ID, and Passport formats
        
        Args:
            image_path: Path to the ID card image
            card_type: Type of card ('ghana_card', 'voters_id', 'passport', or 'auto')
            debug: Whether to print debug information (default: True for troubleshooting)
            
        Returns:
            Dictionary with extracted data or None if failed
        """
        img = self.read_image(image_path)
        if img is None:
            return None
        
        ocr_result = self.perform_ocr(img)
        
        if debug:
            print(f"[DEBUG] process_id_card called with card_type='{card_type}'")
            print(f"[DEBUG] OCR detected {len(ocr_result[0]['rec_texts'])} text items")
        
        if card_type == 'ghana_card':
            return self.extract_ghana_card_data(ocr_result, debug=debug)
        elif card_type == 'voters_id':
            return self.extract_voters_id_data(ocr_result, debug=debug)
        elif card_type == 'passport':
            return self.extract_passport_data(ocr_result, debug=debug)
        else:
            # Auto-detect based on content
            texts = ocr_result[0]['rec_texts']
            all_text = ' '.join(texts).upper()
            
            if debug:
                print(f"[DEBUG] Auto-detecting card type from text: {all_text[:200]}...")
            
            if 'GHA-' in all_text or 'GHANA CARD' in all_text:
                return self.extract_ghana_card_data(ocr_result, debug=debug)
            elif 'VOTER IDENTIFICATION' in all_text or 'ELECTORAL' in all_text:
                return self.extract_voters_id_data(ocr_result, debug=debug)
            elif 'PASSPORT' in all_text or 'MRZ' in all_text:
                return self.extract_passport_data(ocr_result, debug=debug)
            else:
                # Default to Ghana Card extraction
                print("Warning: Could not determine card type. Attempting Ghana Card extraction.")
                return self.extract_ghana_card_data(ocr_result, debug=debug)


if __name__ == "__main__":
    # Example usage
    ocr_processor = IDCardOCR()
    
    # Process Ghana Card
    print("=== Processing Ghana Card ===")
    ghana_data = ocr_processor.process_ghana_card('./photos/ransford.jpeg')
    if ghana_data:
        print("--- Ghana Card Extraction ---")
        for key, value in ghana_data.items():
            print(f"{key}: {value}")
    
    print("\n" + "="*50 + "\n")
    
    # # Process Voter's ID
    # print("=== Processing Voter's ID ===")
    # voters_data = ocr_processor.process_voters_id('./photos/Voters_ID.jpeg')
    # if voters_data:
    #     print("--- Voter's ID Extraction ---")
    #     for key, value in voters_data.items():
    #         print(f"✅ {key}: {value}")
    
    # print("\n" + "="*50 + "\n")
    
    # # Process Passport
    # print("=== Processing Passport ===")
    # passport_data = ocr_processor.process_passport('./photos/enoch_pass.jpg')
    # if passport_data:
    #     print("--- Passport Extraction ---")
    #     for key, value in passport_data.items():
    #         print(f"✅ {key}: {value}")
