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

  // Store stream reference for cleanup
  const streamRef = useRef(null);

  // Start webcam
  const startCamera = async () => {
    try {
      setIdMessage('📹 Starting camera...');
      setStatusMessage('📹 Starting camera...');
      console.log('Requesting camera access...');
      
      // Stop any existing stream first
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }
      });
      
      console.log('Camera stream obtained:', stream);
      streamRef.current = stream;
      
      // Set camera active first so the video element renders
      setCameraActive(true);
      
      // Use a small delay to ensure the video element is mounted
      await new Promise(resolve => setTimeout(resolve, 100));
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        
        // Wait for video to be ready and play
        videoRef.current.onloadedmetadata = async () => {
          console.log('Video metadata loaded');
          try {
            await videoRef.current.play();
            console.log('Video playing');
            setIdMessage('✓ Camera active - Click "Capture ID Photo" when ready');
            setStatusMessage('✓ Camera active - Position your face in frame');
          } catch (playErr) {
            console.error('Error playing video:', playErr);
          }
        };
      } else {
        console.error('Video ref not available after delay');
        setIdMessage('✗ Camera initialization failed. Please try again.');
        setStatusMessage('✗ Camera initialization failed. Please try again.');
      }
    } catch (err) {
      const errorMsg = err.name === 'NotAllowedError' 
        ? 'Camera permission denied. Please allow camera access.' 
        : `Camera error: ${err.message}`;
      setIdMessage(`✗ ${errorMsg}`);
      setStatusMessage(`✗ ${errorMsg}`);
      console.error('Error accessing camera:', err);
      setCameraActive(false);
    }
  };

  // Stop webcam
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
    console.log('Camera stopped');
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
        // Show detailed error message for ID extraction failure
        let errorMsg = data.message || 'Failed to extract face from ID';
        if (data.recommendation) {
          errorMsg += ` | 💡 ${data.recommendation}`;
        }
        setIdMessage(`✗ ${errorMsg}`);
        console.log('ID extraction failed:', data);
      }
    } catch (err) {
      setIdMessage(`✗ Connection error: ${err.message}. Please ensure the backend server is running.`);
      console.error('ID processing error:', err);
    } finally {
      setIdProcessing(false);
    }
  };

  // Capture ID with camera
  const captureId = async () => {
    if (!canvasRef.current || !videoRef.current) {
      console.error('Canvas or video ref not available', { canvas: canvasRef.current, video: videoRef.current });
      setIdMessage('⚠ Camera not ready, please wait...');
      return;
    }

    const canvas = canvasRef.current;
    const video = videoRef.current;

    // Wait for video to be ready with retry
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      setIdMessage('⚠ Camera initializing, please wait...');
      // Try again after a short delay
      setTimeout(() => captureId(), 500);
      return;
    }

    setIdMessage('📸 Capturing...');
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
          // Show detailed error message for ID extraction failure
          let errorMsg = data.message || 'Failed to extract face from ID';
          if (data.recommendation) {
            errorMsg += ` | 💡 ${data.recommendation}`;
          }
          setIdMessage(`✗ ${errorMsg}`);
          console.log('ID capture extraction failed:', data);
        }
      } catch (err) {
        setIdMessage(`✗ Connection error: ${err.message}. Please ensure the backend server is running.`);
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
          
          // Enhance verification result with detailed info
          setVerificationResult(verifyData);
          setIsChecking(false);
          stopCamera();
          
          if (verifyData.verified) {
            setStatusMessage('✓ Identity verified successfully!');
          } else {
            // Show detailed failure reason
            const reason = verifyData.failure_reason || verifyData.match_description || verifyData.message || 'Faces do not match';
            setStatusMessage(`✗ Verification failed: ${reason}`);
          }
        } else {
          // Liveness failed - show detailed message
          const livenessReason = livenessData.details || livenessData.message || 'Liveness check failed';
          setStatusMessage(`⚠ ${livenessReason}`);
          setLivenessStatus('not-live');
          setVerificationResult({
            verified: false,
            stage: 'liveness',
            stageDescription: livenessData.stage_description || 'Liveness verification',
            error_code: livenessData.error_code || 'LIVENESS_FAILED',
            message: livenessData.message,
            details: livenessData.details,
            recommendation: livenessData.recommendation,
            confidence: livenessData.confidence
          });
        }
      } catch (err) {
        setStatusMessage(`Connection error: ${err.message}`);
        console.error('Verification error:', err);
        setIsChecking(false);
        setVerificationResult({
          verified: false,
          stage: 'connection',
          stageDescription: 'API Connection',
          error_code: 'CONNECTION_ERROR',
          message: 'Failed to connect to verification server',
          details: err.message,
          recommendation: 'Please check your internet connection and try again.'
        });
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
    setCameraActive(false);
    setActiveView('upload-id');
  };

  // Cleanup camera on unmount
  useEffect(() => {
    return () => stopCamera();
  }, []);

  // Re-attach stream when video element changes (e.g., view switch)
  useEffect(() => {
    if (cameraActive && streamRef.current && videoRef.current && !videoRef.current.srcObject) {
      console.log('Re-attaching stream to video element');
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(err => console.error('Error playing video:', err));
    }
  }, [cameraActive, activeView]);

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

              {cameraActive && activeView === 'upload-id' && (
                <div className="video-container" style={{ marginTop: '1.5rem' }}>
                  <video ref={videoRef} autoPlay muted playsInline className="video-feed" />
                  <canvas ref={canvasRef} style={{ display: 'none' }} />
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
                      <video ref={videoRef} autoPlay muted playsInline className="video-feed" />
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
                  
                  {/* Show failure stage indicator (System Errors) */}
                  {!verificationResult.verified && verificationResult.stage && (
                    <div className="failure-stage" style={{
                      background: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: '8px',
                      padding: '1rem',
                      marginTop: '1rem',
                      textAlign: 'left'
                    }}>
                      <div style={{ marginBottom: '0.5rem' }}>
                        <strong style={{ color: 'var(--accent-red)' }}>Failed at: </strong>
                        <span style={{ textTransform: 'capitalize' }}>
                          {verificationResult.stageDescription || verificationResult.stage}
                        </span>
                      </div>
                      {verificationResult.error_code && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                          Error Code: {verificationResult.error_code}
                        </div>
                      )}
                      {(verificationResult.failure_reason || verificationResult.match_description || verificationResult.details) && (
                        <div style={{ marginBottom: '0.5rem' }}>
                          <strong>Reason: </strong>
                          {verificationResult.failure_reason || verificationResult.match_description || verificationResult.details}
                        </div>
                      )}
                      {verificationResult.recommendation && (
                        <div style={{ 
                          marginTop: '0.75rem', 
                          padding: '0.75rem', 
                          background: 'rgba(59, 130, 246, 0.1)', 
                          borderRadius: '6px',
                          fontSize: '0.875rem'
                        }}>
                          <strong>💡 Recommendation: </strong>
                          {verificationResult.recommendation}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Show mismatch details (Verification Completed but Mismatch) */}
                  {!verificationResult.verified && !verificationResult.error_code && !verificationResult.stage && (
                    <div className="mismatch-details" style={{
                      background: 'rgba(245, 158, 11, 0.1)', // Amber background
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                      borderRadius: '8px',
                      padding: '1rem',
                      marginTop: '1rem',
                      textAlign: 'left'
                    }}>
                       <div style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                          <strong>Result: </strong>
                          Identity Not Verified
                       </div>

                      {(verificationResult.non_match_reason || verificationResult.match_description || verificationResult.details) && (
                        <div style={{ marginBottom: '0.5rem' }}>
                          <strong>Reason: </strong>
                          {verificationResult.non_match_reason || verificationResult.match_description || verificationResult.details}
                        </div>
                      )}
                      {verificationResult.recommendation && (
                        <div style={{ 
                          marginTop: '0.75rem', 
                          padding: '0.75rem', 
                          background: 'rgba(59, 130, 246, 0.1)', 
                          borderRadius: '6px',
                          fontSize: '0.875rem'
                        }}>
                          <strong>💡 Recommendation: </strong>
                          {verificationResult.recommendation}
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div className="result-details">
                    {verificationResult.similarity !== undefined && verificationResult.similarity > 0 && (
                      <div className="result-detail-item">
                        <span>Similarity Score:</span>
                        <strong>{(verificationResult.similarity * 100).toFixed(2)}%</strong>
                      </div>
                    )}
                    {verificationResult.threshold !== undefined && verificationResult.verified !== undefined && (
                      <div className="result-detail-item">
                        <span>Required Threshold:</span>
                        <strong>{(verificationResult.threshold * 100).toFixed(2)}%</strong>
                      </div>
                    )}
                    {verificationResult.confidence !== undefined && verificationResult.confidence > 0 && (
                      <div className="result-detail-item">
                        <span>Confidence:</span>
                        <strong>{(verificationResult.confidence * 100).toFixed(2)}%</strong>
                      </div>
                    )}
                    {verificationResult.match_confidence && verificationResult.verified && (
                      <div className="result-detail-item">
                        <span>Match Quality:</span>
                        <strong style={{ textTransform: 'capitalize' }}>
                          {verificationResult.match_confidence.replace('_', ' ')}
                        </strong>
                      </div>
                    )}
                    <div className="result-detail-item">
                      <span>Status:</span>
                      <strong style={{ color: verificationResult.verified ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {verificationResult.verified ? 'PASSED' : 'FAILED'}
                      </strong>
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
