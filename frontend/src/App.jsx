import React, { useRef, useState, useEffect, useCallback } from 'react';
import './App.css';
import IDVerificationForm from './IDVerificationForm';

function App() {
  // Navigation state
  const [activeView, setActiveView] = useState('enter-details');

  // User Details state
  const [userDetails, setUserDetails] = useState(null);
  const [detailsSubmitted, setDetailsSubmitted] = useState(false);

  // ID Upload state
  const [idImage, setIdImage] = useState(null);
  const [extractedFace, setExtractedFace] = useState(null);
  const [idProcessing, setIdProcessing] = useState(false);
  const [idMessage, setIdMessage] = useState('');
  const [extractedIdDetails, setExtractedIdDetails] = useState(null);
  const [idDetailsVerified, setIdDetailsVerified] = useState(false);
  const [ocrProcessing, setOcrProcessing] = useState(false);

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
  // Store verification start time
  const verificationStartTimeRef = useRef(null);
  // Store processing state to prevent overlapping requests
  const isProcessingRef = useRef(false);

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

  // Handle user details form submission
  const handleDetailsSubmit = async (formData) => {
    setUserDetails(formData);
    setDetailsSubmitted(true);
    setCurrentStep(1);
    setActiveView('upload-id');
  };

  // Handle canceling details entry
  const handleDetailsCancel = () => {
    setDetailsSubmitted(false);
    setUserDetails(null);
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
      // Step 1: Extract face from ID
      const response = await fetch('http://localhost:8000/extract-face', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (data.success) {
        setExtractedFace(data.face_image_url);
        setIdMessage('✓ Face extracted successfully');
        setCurrentStep(2);
        
        // Step 2: Extract text/details from ID using OCR
        setOcrProcessing(true);
        setIdMessage('Extracting details from ID document...');
        
        const ocrFormData = new FormData();
        ocrFormData.append('file', file);
        ocrFormData.append('id_type', userDetails.idType);
        
        const ocrResponse = await fetch('http://localhost:8000/ocr-extract', {
          method: 'POST',
          body: ocrFormData,
        });
        
        const ocrData = await ocrResponse.json();
        
        if (ocrData.success) {
          setExtractedIdDetails(ocrData.extracted_data);
          setIdMessage('✓ Details extracted from ID');
          
          // Step 3: Verify extracted details against user-entered details
          await verifyIdDetails(userDetails, ocrData.extracted_data);
        } else {
          setIdMessage(`⚠️ Face extracted but could not extract details: ${ocrData.message}`);
          console.log('OCR extraction warning:', ocrData);
        }
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
      setOcrProcessing(false);
    }
  };

  // Verify extracted ID details against user-entered details
  const verifyIdDetails = async (details, extractedData) => {
    try {
      const verifyFormData = new FormData();
      verifyFormData.append('user_surname', details.surname || '');
      verifyFormData.append('user_first_name', details.firstName || '');
      verifyFormData.append('user_other_names', details.otherNames || '');
      verifyFormData.append('extracted_surname', extractedData?.surname || '');
      verifyFormData.append('extracted_first_name', extractedData?.first_name || '');
      verifyFormData.append('extracted_other_names', extractedData?.other_names || '');
      verifyFormData.append('id_type', details.idType || '');
      verifyFormData.append('extracted_id_number', extractedData?.id_number || '');
      verifyFormData.append('user_id_number', details.idNumber || '');
      
      const response = await fetch('http://localhost:8000/verify-id-details', {
        method: 'POST',
        body: verifyFormData,
      });
      
      const verifyData = await response.json();
      
      if (verifyData.verified) {
        setIdDetailsVerified(true);
        setIdMessage(`✓ ID details verified! (Name match: ${verifyData.name_similarity}%)`);
        setCurrentStep(3);
      } else {
        setIdDetailsVerified(false);
        let errorMsg = verifyData.message || 'ID details do not match';
        if (verifyData.recommendation) {
          errorMsg += ` | 💡 ${verifyData.recommendation}`;
        }
        setIdMessage(`⚠️ ${errorMsg}`);
        console.log('ID details verification failed:', verifyData);
      }
    } catch (err) {
      console.error('ID details verification error:', err);
      setIdMessage(`⚠️ Could not verify ID details: ${err.message}`);
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
        // Step 1: Extract face from ID
        const response = await fetch('http://localhost:8000/extract-face', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();
        
        if (data.success) {
          setExtractedFace(data.face_image_url);
          setIdMessage('✓ Face extracted successfully');
          setCurrentStep(2);
          
          // Step 2: Extract text/details from ID using OCR
          setOcrProcessing(true);
          setIdMessage('Extracting details from ID document...');
          
          const ocrFormData = new FormData();
          ocrFormData.append('file', blob, 'id-capture.jpg');
          ocrFormData.append('id_type', userDetails.idType);
          
          const ocrResponse = await fetch('http://localhost:8000/ocr-extract', {
            method: 'POST',
            body: ocrFormData,
          });
          
          const ocrData = await ocrResponse.json();
          
          if (ocrData.success) {
            setExtractedIdDetails(ocrData.extracted_data);
            setIdMessage('✓ Details extracted from ID');
            
            // Step 3: Verify extracted details against user-entered details
            await verifyIdDetails(userDetails, ocrData.extracted_data);
          } else {
            setIdMessage(`⚠️ Face extracted but could not extract details: ${ocrData.message}`);
            console.log('OCR extraction warning:', ocrData);
          }
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
        setOcrProcessing(false);
      }
    }, 'image/jpeg', 0.95);
  };

  // Perform liveness detection and verification
  const performLivenessAndVerification = useCallback(async () => {
    if (!canvasRef.current || !videoRef.current || isProcessingRef.current) return;
    
    // Mark as processing
    isProcessingRef.current = true;

    // Check for timeout (30 seconds)
    if (verificationStartTimeRef.current && (Date.now() - verificationStartTimeRef.current > 30000)) {
       console.log("Verification timed out");
       setIsChecking(false);
       stopCamera();
       setVerificationResult({
         verified: false,
         stage: 'timeout',
         stageDescription: 'Verification Timeout',
         error_code: 'TIMEOUT',
         message: 'Verification timed out after 30 seconds',
         details: 'Could not verify identity within the time limit.',
         recommendation: 'Please ensure good lighting and look directly at the camera.'
       });
       if (statusMessage.startsWith('✓')) {
           // If we previously had a success (shouldn't happen here usually), keep it? 
           // No, validation failed if we hit timeout without stopping.
       }
       isProcessingRef.current = false;
       return;
    }

    const canvas = canvasRef.current;
    const video = videoRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
      if (!blob) {
          isProcessingRef.current = false;
          return;
      }

      const formData = new FormData();
      formData.append('file', blob, 'live-frame.jpg');

      try {
        // First check liveness
        const livenessResponse = await fetch('http://localhost:8000/liveness-check', {
          method: 'POST',
          body: formData,
        });

        const livenessData = await livenessResponse.json();
        
        // Check for multiple faces first
        if (livenessData.error_code === 'MULTIPLE_FACES') {
          setStatusMessage(`⚠ ${livenessData.details || 'Multiple faces detected. Only one person allowed.'}`);
          // Keep retrying
          return;
        }
        
        if (livenessData.is_live) {
          setLivenessStatus('live');
          setStatusMessage('✓ Liveness verified! Checking identity...');
          
          // Now verify against ID
          const verifyFormData = new FormData();
          verifyFormData.append('live_image', blob, 'live-frame.jpg');
          verifyFormData.append('id_face_path', extractedFace);

          const verifyResponse = await fetch('http://localhost:8000/verify-identity', {
            method: 'POST',
            body: verifyFormData,
          });

          const verifyData = await verifyResponse.json();
          
          // Check for multiple faces in verification
          if (verifyData.error_code === 'MULTIPLE_FACES') {
            setStatusMessage(`⚠ ${verifyData.details || 'Multiple faces detected. Only one person allowed.'}`);
            return;
          }
          
          if (verifyData.verified) {
             // SUCCESS: Live AND Verified - Stop immediately
             setVerificationResult(verifyData);
             setIsChecking(false);
             stopCamera();
             setStatusMessage('✓ Identity verified successfully!');
          } else {
             // Liveness passed, but Verification failed - KEEP TRYING
             // Do NOT setVerificationResult (which shows the result screen)
             // Instead, just update status message/feedback
             const reason = verifyData.non_match_reason || 'Faces do not match';
             setStatusMessage(`⏳ Verifying... (${reason})`);
             // We don't stop camera, loop continues
          }
        } else {
          // Liveness failed - KEEP TRYING
          const livenessReason = livenessData.details || 'Liveness check failed';
          setStatusMessage(`⚠ Liveness: ${livenessReason} (Retrying...)`);
          // We don't stop camera, loop continues
        }
      } catch (err) {
        // Error (network etc) - KEEP TRYING until timeout
        console.error('Verification attempt error:', err);
        setStatusMessage('⚠ Connection unstable, retrying...');
      } finally {
        isProcessingRef.current = false;
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
    verificationStartTimeRef.current = Date.now();
    isProcessingRef.current = false;
  };

  // Reset to start over
  const resetProcess = () => {
    setIdImage(null);
    setExtractedFace(null);
    setIdMessage('');
    setExtractedIdDetails(null);
    setIdDetailsVerified(false);
    setLivenessStatus(null);
    setVerificationResult(null);
    setCurrentStep(1);
    setStatusMessage('');
    stopCamera();
    setIsChecking(false);
    setCameraActive(false);
    setActiveView('enter-details');
    setUserDetails(null);
    setDetailsSubmitted(false);
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
            className={`nav-item ${activeView === 'enter-details' ? 'active' : ''}`}
            onClick={() => setActiveView('enter-details')}
          >
            <span className="nav-icon">📝</span>
            <span>Enter Details</span>
          </div>
          <div 
            className={`nav-item ${activeView === 'upload-id' ? 'active' : ''}`}
            onClick={() => {
              if (detailsSubmitted) setActiveView('upload-id');
            }}
          >
            <span className="nav-icon">📇</span>
            <span>Upload ID</span>
          </div>
          <div 
            className={`nav-item ${activeView === 'verify' ? 'active' : ''}`}
            onClick={() => {
              if (idDetailsVerified && extractedFace) setActiveView('verify');
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
        {detailsSubmitted && (
          <div className="progress-steps">
            <div className={`step ${currentStep >= 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}>
              <div className="step-number">{currentStep > 1 ? '✓' : '1'}</div>
              <div className="step-label">Upload ID</div>
            </div>
            <div className={`step ${currentStep >= 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}`}>
              <div className="step-number">{currentStep > 2 ? '✓' : '2'}</div>
              <div className="step-label">Verify Details</div>
            </div>
            <div className={`step ${currentStep >= 3 ? 'active' : ''}`}>
              <div className="step-number">3</div>
              <div className="step-label">Face Verification</div>
            </div>
          </div>
        )}

        {/* Enter Details View */}
        {activeView === 'enter-details' && !detailsSubmitted && (
          <div className="view-container">
            <IDVerificationForm 
              onFormSubmit={handleDetailsSubmit}
              onCancel={handleDetailsCancel}
            />
          </div>
        )}

        {/* Upload ID View */}
        {activeView === 'upload-id' && detailsSubmitted && (
          <>
            <div className="header">
              <h2>Identity Document Upload</h2>
              <p>Upload or capture your government-issued ID to begin verification</p>
            </div>

            {/* User Details Summary */}
            {userDetails && (
              <div className="card" style={{ marginBottom: '1.5rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', borderColor: 'var(--accent-green)' }}>
                <div className="card-title" style={{ color: 'var(--accent-green)' }}>
                  <span>📋</span>
                  Your Details to Match
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Surname</p>
                    <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>{userDetails.surname}</p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>First Name</p>
                    <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>{userDetails.firstName}</p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Other Names</p>
                    <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>{userDetails.otherNames || '(none)'}</p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>ID Type</p>
                    <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>
                      {userDetails.idType === 'GH_CARD' ? 'Ghana Card' : userDetails.idType === 'VOTERS_ID' ? "Voter's ID" : 'Passport'}
                    </p>
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>ID Number</p>
                    <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>{userDetails.idNumber}</p>
                  </div>
                </div>
              </div>
            )}

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

                  {/* Extracted Details Verification */}
                  {extractedIdDetails && (
                    <div className="card" style={{ marginTop: '1.5rem', backgroundColor: idDetailsVerified ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', borderColor: idDetailsVerified ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                      <div className="card-title" style={{ color: idDetailsVerified ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        <span>{idDetailsVerified ? '✓' : '⚠️'}</span>
                        Extracted Information
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Surname</p>
                          <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>{extractedIdDetails.surname || '(not found)'}</p>
                        </div>
                        <div>
                          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>First Name</p>
                          <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>{extractedIdDetails.first_name || '(not found)'}</p>
                        </div>
                        <div>
                          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Other Names</p>
                          <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>{extractedIdDetails.other_names || '(none)'}</p>
                        </div>
                        <div>
                          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Status</p>
                          <p style={{ color: idDetailsVerified ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: '500' }}>
                            {idDetailsVerified ? 'Verified ✓' : 'Mismatch ⚠️'}
                          </p>
                        </div>
                        <div style={{ gridColumn: '1 / -1' }}>
                          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>ID Number From Document</p>
                          <p style={{ color: 'var(--text-primary)', fontWeight: '500' }}>{extractedIdDetails.id_number || '(not found)'}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="btn-group">
                    <button 
                      className="btn btn-primary" 
                      onClick={() => setActiveView('verify')}
                      disabled={!idDetailsVerified}
                      title={idDetailsVerified ? 'Proceed to face verification' : 'Upload ID with matching details to proceed'}
                    >
                      <span>→</span>
                      {idDetailsVerified ? 'Proceed to Face Verification' : 'Awaiting Details Verification'}
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
                  
                  {/* Unified Failure Display */}
                  {!verificationResult.verified && (
                    <div className="failure-container" style={{
                      textAlign: 'center',
                      padding: '1.5rem',
                      marginTop: '1rem'
                    }}>
                      <div style={{ 
                        color: 'var(--accent-red)', 
                        fontSize: '1.25rem', 
                        fontWeight: 'bold',
                        marginBottom: '1rem' 
                      }}>
                        Verification Failed
                      </div>
                      
                      <div style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                        {verificationResult.details || verificationResult.non_match_reason || verificationResult.message || 'Identity could not be verified.'}
                      </div>

                      <div className="recommendations-box" style={{
                         background: 'rgba(255, 255, 255, 0.05)',
                         borderRadius: '8px',
                         padding: '1.5rem',
                         textAlign: 'left'
                      }}>
                         <div style={{ fontWeight: 'bold', marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
                           💡 Recommendations to improve success:
                         </div>
                         <ul style={{ margin: 0, paddingLeft: '1.5rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                           <li>Ensure you are in a well-lit area</li>
                           <li>Remove sunglasses, masks, or hats</li>
                           <li>Look directly at the camera</li>
                           <li>Hold the camera steady</li>
                           <li>Make sure your face is clearly visible</li>
                           {/* Add specific recommendation if available */}
                           {verificationResult.recommendation && (
                              <li style={{ color: 'var(--accent-blue)', fontWeight: '500', marginTop: '0.5rem' }}>
                                 {verificationResult.recommendation}
                              </li>
                           )}
                         </ul>
                      </div>
                      
                      {/* Debug info (optional, kept small) */}
                      {verificationResult.error_code && verificationResult.error_code !== 'TIMEOUT' && (
                         <div style={{ marginTop: '2rem', fontSize: '0.75rem', color: 'var(--text-secondary)', opacity: 0.7 }}>
                            Internal Code: {verificationResult.error_code}
                         </div>
                      )}
                    </div>
                  )}

                  {/* Show Quality Recommendations for Success Case */}
                  {verificationResult.verified && verificationResult.quality_recommendations && verificationResult.quality_recommendations.length > 0 && (
                     <div className="success-recommendations" style={{
                        background: 'rgba(59, 130, 246, 0.1)',
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                        borderRadius: '8px',
                        padding: '1rem',
                        marginTop: '1rem',
                        textAlign: 'left'
                     }}>
                        <div style={{ fontSize: '0.875rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                           💡 Quality Improvements:
                        </div>
                        <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.875rem' }}>
                           {verificationResult.quality_recommendations.map((rec, i) => (
                              <li key={i}>{rec}</li>
                           ))}
                        </ul>
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
