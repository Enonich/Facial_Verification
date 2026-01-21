# -*- coding: utf-8 -*-
"""
Anti-Spoofing Engine for Web Application
Integrates Silent Face Anti-Spoofing detection into the web API
"""

import os
import cv2
import numpy as np
import time
import sys

# Add Silent_Face_Anti_Spoofing to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sfas_dir = os.path.join(current_dir, 'Silent_Face_Anti_Spoofing')
sys.path.insert(0, sfas_dir)

from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name
import math
import torch
import torch.nn.functional as F
from src.model_lib.MiniFASNet import MiniFASNetV1, MiniFASNetV2, MiniFASNetV1SE, MiniFASNetV2SE
from src.data_io import transform as trans
from src.utility import get_kernel

MODEL_MAPPING = {
    'MiniFASNetV1': MiniFASNetV1,
    'MiniFASNetV2': MiniFASNetV2,
    'MiniFASNetV1SE': MiniFASNetV1SE,
    'MiniFASNetV2SE': MiniFASNetV2SE
}


class Detection:
    """Custom Detection class with absolute paths"""
    def __init__(self, detection_model_dir):
        caffemodel = os.path.join(detection_model_dir, "Widerface-RetinaFace.caffemodel")
        deploy = os.path.join(detection_model_dir, "deploy.prototxt")
        
        if not os.path.exists(caffemodel):
            raise FileNotFoundError(f"Caffe model not found: {caffemodel}")
        if not os.path.exists(deploy):
            raise FileNotFoundError(f"Deploy prototxt not found: {deploy}")
        
        self.detector = cv2.dnn.readNetFromCaffe(deploy, caffemodel)
        self.detector_confidence = 0.6

    def get_bbox(self, img):
        height, width = img.shape[0], img.shape[1]
        aspect_ratio = width / height
        if img.shape[1] * img.shape[0] >= 192 * 192:
            img = cv2.resize(img,
                             (int(192 * math.sqrt(aspect_ratio)),
                              int(192 / math.sqrt(aspect_ratio))), interpolation=cv2.INTER_LINEAR)

        blob = cv2.dnn.blobFromImage(img, 1, mean=(104, 117, 123))
        self.detector.setInput(blob, 'data')
        out = self.detector.forward('detection_out').squeeze()
        max_conf_index = np.argmax(out[:, 2])
        left, top, right, bottom = out[max_conf_index, 3]*width, out[max_conf_index, 4]*height, \
                                   out[max_conf_index, 5]*width, out[max_conf_index, 6]*height
        bbox = [int(left), int(top), int(right-left+1), int(bottom-top+1)]
        return bbox


class CustomAntiSpoofPredict:
    """Custom AntiSpoofPredict with absolute paths"""
    def __init__(self, device_id, detection_model_dir):
        self.device = torch.device("cuda:{}".format(device_id)
                                   if torch.cuda.is_available() else "cpu")
        self.detector = Detection(detection_model_dir)

    def get_bbox(self, img):
        return self.detector.get_bbox(img)

    def _load_model(self, model_path):
        # define model
        model_name = os.path.basename(model_path)
        h_input, w_input, model_type, _ = parse_model_name(model_name)
        self.kernel_size = get_kernel(h_input, w_input)
        self.model = MODEL_MAPPING[model_type](conv6_kernel=self.kernel_size).to(self.device)

        # load model weight
        state_dict = torch.load(model_path, map_location=self.device)
        keys = iter(state_dict)
        first_layer_name = keys.__next__()
        if first_layer_name.find('module.') >= 0:
            from collections import OrderedDict
            new_state_dict = OrderedDict()
            for key, value in state_dict.items():
                name_key = key[7:]
                new_state_dict[name_key] = value
            self.model.load_state_dict(new_state_dict)
        else:
            self.model.load_state_dict(state_dict)
        return None

    def predict(self, img, model_path):
        test_transform = trans.Compose([
            trans.ToTensor(),
        ])
        img = test_transform(img)
        img = img.unsqueeze(0).to(self.device)
        self._load_model(model_path)
        self.model.eval()
        with torch.no_grad():
            result = self.model.forward(img)
            result = F.softmax(result).cpu().numpy()
        return result


class AntiSpoofingEngine:
    """
    Anti-Spoofing Engine for detecting face presentation attacks
    (fake faces from photos, videos, masks, etc.)
    """
    
    def __init__(self, model_dir=None, device_id=0, confidence_threshold=0.5):
        """
        Initialize the anti-spoofing engine
        
        Args:
            model_dir: Directory containing anti-spoofing models
            device_id: GPU device ID (0 for CPU/default GPU)
            confidence_threshold: Minimum confidence for real face detection (0.0-1.0)
        """
        if model_dir is None:
            # Default model directory
            model_dir = os.path.join(
                current_dir, 
                'Silent_Face_Anti_Spoofing', 
                'resources', 
                'anti_spoof_models'
            )
        
        self.model_dir = model_dir
        self.device_id = device_id
        self.confidence_threshold = confidence_threshold
        
        # Set detection model directory (absolute path)
        detection_model_dir = os.path.join(
            current_dir,
            'Silent_Face_Anti_Spoofing',
            'resources',
            'detection_model'
        )
        
        # Initialize model with absolute paths
        self.model = CustomAntiSpoofPredict(device_id, detection_model_dir)
        self.image_cropper = CropImage()
        
        # Verify model directory exists
        if not os.path.exists(self.model_dir):
            raise FileNotFoundError(f"Model directory not found: {self.model_dir}")
        
        # Check if models exist
        model_files = [f for f in os.listdir(self.model_dir) if f.endswith('.pth')]
        if not model_files:
            raise FileNotFoundError(f"No model files (.pth) found in {self.model_dir}")
        
        print(f"✅ Anti-Spoofing Engine initialized with {len(model_files)} model(s)")
        print(f"   Models: {', '.join(model_files)}")
    
    def verify(self, frame):
        """
        Verify if the face in the frame is real or spoofed
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            tuple: (is_live, message, confidence, bbox)
                - is_live: True if real face, False if fake
                - message: Descriptive message
                - confidence: Confidence score (0.0-1.0)
                - bbox: Face bounding box [x, y, w, h] or None
        """
        try:
            if frame is None or frame.size == 0:
                return False, "Invalid image", 0.0, None
            
            # Get face bounding box
            image_bbox = self.model.get_bbox(frame)
            
            if image_bbox is None:
                return False, "No face detected", 0.0, None
            
            # Initialize prediction array
            prediction = np.zeros((1, 3))
            
            # Get predictions from all models
            for model_name in os.listdir(self.model_dir):
                if not model_name.endswith('.pth'):
                    continue
                    
                h_input, w_input, model_type, scale = parse_model_name(model_name)
                
                # Prepare crop parameters
                param = {
                    "org_img": frame,
                    "bbox": image_bbox,
                    "scale": scale,
                    "out_w": w_input,
                    "out_h": h_input,
                    "crop": True,
                }
                
                if scale is None:
                    param["crop"] = False
                
                # Crop face patch
                img = self.image_cropper.crop(**param)
                
                # Get prediction from model
                model_path = os.path.join(self.model_dir, model_name)
                prediction += self.model.predict(img, model_path)
            
            # Get final prediction
            # Label 1 = Real Face, Label 0 = Fake Face
            label = np.argmax(prediction)
            confidence = float(prediction[0][label] / len([f for f in os.listdir(self.model_dir) if f.endswith('.pth')]))
            
            is_live = (label == 1) and (confidence >= self.confidence_threshold)
            
            if label == 1:
                if confidence >= self.confidence_threshold:
                    message = f"✅ Real Face Detected (confidence: {confidence:.2f})"
                else:
                    message = f"⚠️ Real Face but low confidence: {confidence:.2f}"
            else:
                message = f"❌ Fake Face Detected (confidence: {confidence:.2f})"
            
            return is_live, message, confidence, image_bbox
            
        except Exception as e:
            return False, f"Error during verification: {str(e)}", 0.0, None
    
    def verify_with_visualization(self, frame):
        """
        Verify and return frame with visualization (bounding box and text)
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            tuple: (is_live, message, confidence, annotated_frame)
        """
        is_live, message, confidence, bbox = self.verify(frame)
        
        # Create annotated frame
        annotated_frame = frame.copy()
        
        if bbox is not None:
            # Choose color based on result
            color = (0, 255, 0) if is_live else (0, 0, 255)
            
            # Draw bounding box
            cv2.rectangle(
                annotated_frame,
                (bbox[0], bbox[1]),
                (bbox[0] + bbox[2], bbox[1] + bbox[3]),
                color, 2
            )
            
            # Add text label
            result_text = f"{'REAL' if is_live else 'FAKE'}: {confidence:.2f}"
            cv2.putText(
                annotated_frame,
                result_text,
                (bbox[0], bbox[1] - 10),
                cv2.FONT_HERSHEY_COMPLEX,
                0.8,
                color,
                2
            )
        else:
            # No face detected
            cv2.putText(
                annotated_frame,
                "No face detected",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )
        
        return is_live, message, confidence, annotated_frame
    
    def reset(self):
        """
        Reset the engine state (reinitialize models)
        """
        detection_model_dir = os.path.join(
            current_dir,
            'Silent_Face_Anti_Spoofing',
            'resources',
            'detection_model'
        )
        self.model = CustomAntiSpoofPredict(self.device_id, detection_model_dir)
        self.image_cropper = CropImage()
        return True


if __name__ == "__main__":
    # Test the engine
    print("Testing Anti-Spoofing Engine...")
    
    try:
        engine = AntiSpoofingEngine()
        print("Engine initialized successfully!")
        
        # Test with webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Could not open webcam")
            exit()
        
        print("Press 'q' to quit")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            is_live, message, confidence, annotated_frame = engine.verify_with_visualization(frame)
            
            print(f"Result: {message}")
            cv2.imshow("Anti-Spoofing Test", annotated_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"Error: {e}")
