# -*- coding: utf-8 -*-
# Live Face Anti-Spoofing Detection
# Based on test.py implementation but using live video capture

import os
import cv2
import numpy as np
import argparse
import warnings
import time

from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name
warnings.filterwarnings('ignore')


def check_image(image):
    """Check if image has appropriate dimensions"""
    height, width, channel = image.shape
    if width/height != 3/4:
        print("Image is not appropriate!!!\nHeight/Width should be 4/3.")
        return False
    else:
        return True


def test_live(model_dir, device_id, camera_id=0):
    """
    Perform live face anti-spoofing detection using webcam
    
    Args:
        model_dir: Directory containing anti-spoofing models
        device_id: GPU device ID for inference
        camera_id: Camera device ID (default: 0 for default webcam)
    """
    # Initialize model and image cropper
    model_test = AntiSpoofPredict(device_id)
    image_cropper = CropImage()
    
    # Open video capture
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print(f"Error: Could not open camera {camera_id}")
        return
    
    # Set camera resolution (optional - adjust as needed)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("Starting live face anti-spoofing detection...")
    print("Press 'q' to quit, 's' to save current frame")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Failed to capture frame")
            break
        
        frame_count += 1
        
        # Get face bounding box
        try:
            image_bbox = model_test.get_bbox(frame)
            
            if image_bbox is not None:
                # Initialize prediction array
                prediction = np.zeros((1, 3))
                test_speed = 0
                
                # Sum predictions from all models
                for model_name in os.listdir(model_dir):
                    h_input, w_input, model_type, scale = parse_model_name(model_name)
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
                    img = image_cropper.crop(**param)
                    
                    start = time.time()
                    prediction += model_test.predict(img, os.path.join(model_dir, model_name))
                    test_speed += time.time() - start
                
                # Get prediction result
                label = np.argmax(prediction)
                value = prediction[0][label] / 2
                
                if label == 1:
                    result_text = "RealFace: {:.2f}".format(value)
                    color = (0, 255, 0)  # Green for real face
                else:
                    result_text = "FakeFace: {:.2f}".format(value)
                    color = (0, 0, 255)  # Red for fake face
                
                # Draw bounding box and result
                cv2.rectangle(
                    frame,
                    (image_bbox[0], image_bbox[1]),
                    (image_bbox[0] + image_bbox[2], image_bbox[1] + image_bbox[3]),
                    color, 2)
                cv2.putText(
                    frame,
                    result_text,
                    (image_bbox[0], image_bbox[1] - 10),
                    cv2.FONT_HERSHEY_COMPLEX, 
                    0.8, 
                    color, 
                    2)
                
                # Display FPS
                fps_text = "FPS: {:.1f}".format(1.0 / (test_speed + 0.001))
                cv2.putText(
                    frame,
                    fps_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2)
            else:
                # No face detected
                cv2.putText(
                    frame,
                    "No face detected",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2)
        
        except Exception as e:
            # Handle any errors gracefully
            cv2.putText(
                frame,
                f"Error: {str(e)[:50]}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1)
        
        # Display the frame
        cv2.imshow('Live Face Anti-Spoofing Detection', frame)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("Quitting...")
            break
        elif key == ord('s'):
            # Save current frame
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"./live_capture/live_capture_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Saved frame as {filename}")
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    print(f"Processed {frame_count} frames")


if __name__ == "__main__":
    desc = "Live Face Anti-Spoofing Detection"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--device_id",
        type=int,
        default=0,
        help="which gpu id, [0/1/2/3]")
    parser.add_argument(
        "--model_dir",
        type=str,
        default="./resources/anti_spoof_models",
        help="model_lib used to test")
    parser.add_argument(
        "--camera_id",
        type=int,
        default=0,
        help="camera device id (default: 0)")
    args = parser.parse_args()
    
    test_live(args.model_dir, args.device_id, args.camera_id)
