import React, { useRef, useState, useEffect, useCallback } from 'react';
import './App.css';

function App() {
  // Navigation state
  const [activeView, setActiveView] = useState('upload-id');

  // ID Upload state
  const [idImage, setIdImage] = useState(null);
  const [extractedFace, setExtractedFace] = useState(null);
  const [idProcessing, setIdProcessing] = useState(false);
  const [idMessage, setIdMessage] = useState('');

  // Liveness & Verification state
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [livenessStatus, setLivenessStatus] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [statusMessage, setStatusMessage] = useState('');

  // Start webcam
  const startCamera = async () => {
    try {
      setIdMessage('📹 Starting camera...');
      console.log('Requesting camera access...');
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }
      });
      
      console.log('Camera stream obtained:', stream);
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        
        // Wait for video to be ready
        videoRef.current.onloadedmetadata = () => {
          console.log('Video metadata loaded');
          setCameraActive(true);
          setIdMessage('✓ Camera active - Click "Capture ID Photo" when ready');
        };
      }
    } catch (err) {
      const errorMsg = err.name === 'NotAllowedError' 
        ? 'Camera permission denied. Please allow camera access.' 
        : `Camera error: ${err.message}`;
      setIdMessage(`✗ ${errorMsg}`);
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
      console.log('Camera stopped');
    }
  };

  // Handle ID upload
  const handleIdUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIdImage(URL.createObjectURL(file));
    setIdProcessing(true);
    setIdMessage('Processing ID...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/extract-face', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (data.success) {
        setExtractedFace(data.face_image_url);
        setIdMessage('✓ Face extracted successfully from ID');
        setCurrentStep(2);
      } else {
        setIdMessage(`✗ ${data.message}`);
      }
    } catch (err) {
      setIdMessage(`Connection error: ${err.message}`);
      console.error('ID processing error:', err);
    } finally {
      setIdProcessing(false);
    }
  };

  // Capture ID with camera
  const captureId = async () => {
    if (!canvasRef.current || !videoRef.current) {
      console.error('Canvas or video ref not available');
      return;
    }

    const canvas = canvasRef.current;
    const video = videoRef.current;

    // Wait for video to be ready
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      setIdMessage('⚠ Camera not ready, please wait...');
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
      if (!blob) return;

      setIdImage(URL.createObjectURL(blob));
      setIdProcessing(true);
      setIdMessage('Processing captured ID...');
      stopCamera();

      const formData = new FormData();
      formData.append('file', blob, 'id-capture.jpg');

      try {
        const response = await fetch('http://localhost:8000/extract-face', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();
        
        if (data.success) {
          setExtractedFace(data.face_image_url);
          setIdMessage('✓ Face extracted successfully from ID');
          setCurrentStep(2);
        } else {
          setIdMessage(`✗ ${data.message}`);
        }
      } catch (err) {
        setIdMessage(`Connection error: ${err.message}`);
        console.error('ID processing error:', err);
      } finally {
        setIdProcessing(false);
      }
    }, 'image/jpeg', 0.95);
  };

  // Perform liveness detection and verification
  const performLivenessAndVerification = useCallback(async () => {
    if (!canvasRef.current || !videoRef.current) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
      if (!blob) return;

      const formData = new FormData();
      formData.append('file', blob, 'live-frame.jpg');

      try {
        // First check liveness
        const livenessResponse = await fetch('http://localhost:8000/liveness-check', {
          method: 'POST',
          body: formData,
        });

        const livenessData = await livenessResponse.json();
        
        if (livenessData.is_live) {
          setLivenessStatus('live');
          setStatusMessage('✓ Liveness verified! Checking identity...');
          setCurrentStep(3);

          // Now verify against ID
          const verifyFormData = new FormData();
          verifyFormData.append('live_image', blob, 'live-frame.jpg');
          verifyFormData.append('id_face_path', extractedFace);

          const verifyResponse = await fetch('http://localhost:8000/verify-identity', {
            method: 'POST',
            body: verifyFormData,
          });

          const verifyData = await verifyResponse.json();
          
          setVerificationResult(verifyData);
          setIsChecking(false);
          stopCamera();
          
          if (verifyData.verified) {
            setStatusMessage('✓ Identity verified successfully!');
          } else {
            setStatusMessage('✗ Identity verification failed');
          }
        } else {
          setStatusMessage('⚠ Liveness check failed. Please try again.');
          setLivenessStatus('not-live');
        }
      } catch (err) {
        setStatusMessage(`Connection error: ${err.message}`);
        console.error('Verification error:', err);
        setIsChecking(false);
      }
    }, 'image/jpeg', 0.95);
  }, [extractedFace]);

  // Auto-verification loop
  useEffect(() => {
    let interval;
    if (isChecking && cameraActive) {
      interval = setInterval(() => {
        performLivenessAndVerification();
      }, 1000); // Check every second
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isChecking, cameraActive, performLivenessAndVerification]);

  // Start verification process
  const startVerification = async () => {
    if (!extractedFace) {
      setStatusMessage('Please upload an ID first');
      return;
    }
    await startCamera();
    setIsChecking(true);
    setLivenessStatus(null);
    setVerificationResult(null);
    setStatusMessage('Starting verification...');
  };

  // Reset to start over
  const resetProcess = () => {
    setIdImage(null);
    setExtractedFace(null);
    setIdMessage('');
    setLivenessStatus(null);
    setVerificationResult(null);
    setCurrentStep(1);
    setStatusMessage('');
    stopCamera();
    setIsChecking(false);
  };

  // Cleanup camera on unmount
  useEffect(() => {
    return () => stopCamera();
  }, []);

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <div className="sidebar">
        <div className="logo">
          <h1>
            <div className="logo-icon">🛡️</div>
            <span>SecureID</span>
          </h1>
        </div>
        
        <nav className="nav-menu">
          <div 
            className={`nav-item ${activeView === 'upload-id' ? 'active' : ''}`}
            onClick={() => setActiveView('upload-id')}
          >
            <span className="nav-icon">📇</span>
            <span>Upload ID</span>
          </div>
          <div 
            className={`nav-item ${activeView === 'verify' ? 'active' : ''}`}
            onClick={() => {
              if (extractedFace) setActiveView('verify');
            }}
          >
            <span className="nav-icon">✓</span>
            <span>Verify Identity</span>
          </div>
        </nav>
      </div>

      {/* Main Content Area */}
      <div className="main-content">
        {/* Progress Steps */}
        <div className="progress-steps">
          <div className={`step ${currentStep >= 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}>
            <div className="step-number">{currentStep > 1 ? '✓' : '1'}</div>
            <div className="step-label">Upload ID</div>
          </div>
          <div className={`step ${currentStep >= 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}`}>
            <div className="step-number">{currentStep > 2 ? '✓' : '2'}</div>
            <div className="step-label">Liveness Check</div>
          </div>
          <div className={`step ${currentStep >= 3 ? 'active' : ''}`}>
            <div className="step-number">3</div>
            <div className="step-label">Verify Identity</div>
          </div>
        </div>

        {/* Upload ID View */}
        {activeView === 'upload-id' && (
          <>
            <div className="header">
              <h2>Identity Document Upload</h2>
              <p>Upload or capture your government-issued ID to begin verification</p>
            </div>

            <div className="card">
              <div className="card-title">
                <span>📄</span>
                Upload Your ID
              </div>

              <div className="file-input-wrapper">
                <input 
                  type="file" 
                  id="id-upload" 
                  accept="image/*" 
                  onChange={handleIdUpload}
                  disabled={idProcessing}
                />
                <label htmlFor="id-upload" className="file-input-label">
                  <span>📁</span>
                  Choose ID Document
                </label>
              </div>

              <div style={{ textAlign: 'center', margin: '1.5rem 0', color: 'var(--text-secondary)' }}>
                OR
              </div>

              <div className="btn-group">
                <button 
                  className="btn btn-primary" 
                  onClick={cameraActive ? captureId : startCamera}
                  disabled={idProcessing}
                >
                  <span>📷</span>
                  {cameraActive ? 'Capture ID Photo' : 'Use Camera'}
                </button>
                {cameraActive && (
                  <button className="btn btn-secondary" onClick={stopCamera}>
                    Stop Camera
                  </button>
                )}
              </div>

              {cameraActive && activeView === 'upload-id' && !extractedFace && (
                <div className="video-container" style={{ marginTop: '1.5rem' }}>
                  <video ref={videoRef} autoPlay playsInline className="video-feed" />
                </div>
              )}

              {idProcessing && (
                <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                  <div className="spinner"></div>
                  <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Processing ID document...</p>
                </div>
              )}

              {idMessage && (
                <div className={`status-badge ${idMessage.includes('✓') ? 'success' : idMessage.includes('✗') ? 'error' : 'info'}`}>
                  {idMessage}
                </div>
              )}

              {idImage && (
                <div className="image-preview">
                  <img src={idImage} alt="Uploaded ID" />
                </div>
              )}

              {extractedFace && (
                <>
                  <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
                    <h3 style={{ color: 'var(--accent-green)', marginBottom: '1rem' }}>✓ Face Extracted</h3>
                    <div className="image-preview">
                      <img src={`http://localhost:8000${extractedFace}`} alt="Extracted Face" />
                    </div>
                  </div>
                  <div className="btn-group">
                    <button 
                      className="btn btn-primary" 
                      onClick={() => setActiveView('verify')}
                    >
                      <span>→</span>
                      Proceed to Verification
                    </button>
                    <button className="btn btn-secondary" onClick={resetProcess}>
                      Start Over
                    </button>
                  </div>
                </>
              )}
            </div>
          </>
        )}

        {/* Verify Identity View */}
        {activeView === 'verify' && (
          <>
            <div className="header">
              <h2>Live Identity Verification</h2>
              <p>Position your face in the camera for liveness detection and identity verification</p>
            </div>

            {!extractedFace && (
              <div className="card">
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                  <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⚠️</div>
                  <h3>No ID Uploaded</h3>
                  <p style={{ marginTop: '1rem' }}>Please upload an ID document first</p>
                  <button 
                    className="btn btn-primary" 
                    style={{ marginTop: '1.5rem' }}
                    onClick={() => setActiveView('upload-id')}
                  >
                    Go to Upload ID
                  </button>
                </div>
              </div>
            )}

            {extractedFace && !verificationResult && (
              <div className="card">
                <div className="card-title">
                  <span>🎥</span>
                  Live Verification
                </div>

                <div className="video-container">
                  {cameraActive ? (
                    <>
                      <video ref={videoRef} autoPlay playsInline className="video-feed" />
                      {isChecking && (
                        <div style={{
                          position: 'absolute',
                          top: '1rem',
                          right: '1rem',
                          background: 'rgba(59, 130, 246, 0.9)',
                          padding: '0.5rem 1rem',
                          borderRadius: '20px',
                          fontSize: '0.875rem',
                          fontWeight: '600'
                        }}>
                          🔍 Analyzing...
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="video-overlay">
                      <div className="overlay-text">
                        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <p>Camera not active</p>
                        <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>Click "Start Verification" to begin</p>
                      </div>
                    </div>
                  )}
                </div>

                <canvas ref={canvasRef} style={{ display: 'none' }} />

                {statusMessage && (
                  <div className={`status-badge ${
                    statusMessage.includes('✓') ? 'success' : 
                    statusMessage.includes('✗') ? 'error' : 'info'
                  }`}>
                    {statusMessage}
                  </div>
                )}

                <div className="btn-group">
                  {!isChecking ? (
                    <button className="btn btn-primary" onClick={startVerification}>
                      <span>▶</span>
                      Start Verification
                    </button>
                  ) : (
                    <button 
                      className="btn btn-secondary" 
                      onClick={() => {
                        setIsChecking(false);
                        stopCamera();
                      }}
                    >
                      <span>■</span>
                      Stop Verification
                    </button>
                  )}
                  <button className="btn btn-secondary" onClick={resetProcess}>
                    Start Over
                  </button>
                </div>
              </div>
            )}

            {verificationResult && (
              <div className="card">
                <div className="verification-results">
                  <div className="result-icon">
                    {verificationResult.verified ? '✅' : '❌'}
                  </div>
                  <div className="result-title">
                    {verificationResult.verified ? 'Identity Verified' : 'Verification Failed'}
                  </div>
                  
                  <div className="result-details">
                    {verificationResult.similarity && (
                      <div className="result-detail-item">
                        <span>Similarity Score:</span>
                        <strong>{(verificationResult.similarity * 100).toFixed(2)}%</strong>
                      </div>
                    )}
                    {verificationResult.confidence && (
                      <div className="result-detail-item">
                        <span>Confidence:</span>
                        <strong>{(verificationResult.confidence * 100).toFixed(2)}%</strong>
                      </div>
                    )}
                    <div className="result-detail-item">
                      <span>Status:</span>
                      <strong>{verificationResult.verified ? 'PASSED' : 'FAILED'}</strong>
                    </div>
                  </div>

                  <div className="btn-group" style={{ justifyContent: 'center', marginTop: '2rem' }}>
                    <button className="btn btn-primary" onClick={resetProcess}>
                      <span>↻</span>
                      Verify Another Person
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
