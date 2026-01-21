import React, { useRef, useState, useEffect, useCallback } from 'react';
import './App.css';

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isLive, setIsLive] = useState(null);
  const [message, setMessage] = useState('Click "Start Liveness Check" to begin');
  const [isChecking, setIsChecking] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [verificationCount, setVerificationCount] = useState(0);

  // Start webcam
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
      }
    } catch (err) {
      setMessage(`Camera error: ${err.message}`);
      console.error('Error accessing camera:', err);
    }
  };

  // Stop webcam
  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
      setCameraActive(false);
    }
  };

  // Capture frame and send to backend
  const captureAndVerify = useCallback(async () => {
    if (!canvasRef.current || !videoRef.current) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;

    // Draw current video frame to canvas
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    // Convert canvas to blob
    canvas.toBlob(async (blob) => {
      if (!blob) return;

      const formData = new FormData();
      formData.append('file', blob, 'frame.jpg');

      try {
        const response = await fetch('http://localhost:8000/verify', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();
        setIsLive(data.is_live);
        setMessage(data.message);
        setVerificationCount(prev => prev + 1);

        // If verified, stop checking
        if (data.is_live) {
          setIsChecking(false);
        }
      } catch (err) {
        setMessage(`Connection error: ${err.message}`);
        console.error('Verification error:', err);
        setIsChecking(false);
      }
    }, 'image/jpeg', 0.95);
  }, []);

  // Auto-verify loop
  useEffect(() => {
    let interval;
    if (isChecking && cameraActive) {
      interval = setInterval(() => {
        captureAndVerify();
      }, 500); // Check every 500ms
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isChecking, cameraActive, captureAndVerify]);

  // Cleanup camera on unmount
  useEffect(() => {
    return () => stopCamera();
  }, []);

  const handleStartCheck = async () => {
    // Start camera if not already active
    if (!cameraActive) {
      await startCamera();
    }
    
    // Reset engine state
    try {
      await fetch('http://localhost:8000/reset', { method: 'POST' });
    } catch (err) {
      console.error('Reset error:', err);
    }
    
    setIsLive(null);
    setMessage('Checking liveness... Please blink or move your head.');
    setIsChecking(true);
    setVerificationCount(0);
  };

  const handleStopCheck = () => {
    setIsChecking(false);
    setMessage('Check stopped.');
  };

  return (
    <div className="App">
      <div className="container">
        <h1>🔐 Liveness Detection</h1>
        
        <div className="video-container">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="video-feed"
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          
          <div className={`status-overlay ${isLive === true ? 'success' : isLive === false ? 'failure' : ''}`}>
            {isLive === true && <span className="status-icon">✅</span>}
            {isLive === false && <span className="status-icon">❌</span>}
          </div>
        </div>

        <div className={`message-box ${isLive === true ? 'success' : isLive === false ? 'failure' : ''}`}>
          <p>{message}</p>
          {isChecking && <p className="checking-indicator">Checking... ({verificationCount} frames)</p>}
        </div>

        <div className="controls">
          {!isChecking ? (
            <button 
              className="btn btn-primary" 
              onClick={handleStartCheck}
            >
              Start Liveness Check
            </button>
          ) : (
            <button 
              className="btn btn-secondary" 
              onClick={handleStopCheck}
            >
              Stop Check
            </button>
          )}
        </div>

        <div className="instructions">
          <h3>Instructions:</h3>
          <ul>
            <li>Allow camera access when prompted</li>
            <li>Position your face in front of the camera</li>
            <li>Click "Start Liveness Check"</li>
            <li>Blink your eyes or move your head slightly</li>
            <li>Wait for verification</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default App;
