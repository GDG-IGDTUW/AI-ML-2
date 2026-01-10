import React, { useState, useRef, useEffect } from 'react';
import { Camera, Download, RotateCcw, Smile, AlertCircle } from 'lucide-react';

const PhotoboothApp = () => {
  const [currentPhase, setCurrentPhase] = useState('setup');
  const [capturedPhotos, setCapturedPhotos] = useState([]);
  const [message, setMessage] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [finalImage, setFinalImage] = useState(null);
  const [showCursor, setShowCursor] = useState(true);
  const [error, setError] = useState('');
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const stripCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const detectionActiveRef = useRef(false);

  // Check backend connection
  const checkBackendConnection = async () => {
    try {
      const response = await fetch('http://localhost:5000/health');
      if (response.ok) {
        setIsBackendConnected(true);
        setError('');
      } else {
        setIsBackendConnected(false);
        setError('Backend server not responding');
      }
    } catch (error) {
      setIsBackendConnected(false);
      setError('Cannot connect to backend server. Make sure Flask server is running on port 5000.');
    }
  };

  // Check for smile using backend
  const checkForSmile = async (imageData) => {
    try {
      const response = await fetch('http://localhost:5000/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ image: imageData }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.smile;
    } catch (error) {
      console.error('Error calling Flask backend:', error);
      setError('Error detecting smile. Using manual capture.');
      return false;
    }
  };

  // Start webcam
  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setError('');
    } catch (err) {
      console.error('Error accessing webcam:', err);
      setError('Could not access webcam. Please check permissions.');
    }
  };

  // Stop webcam
  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  // Capture photo from video
  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      const ctx = canvas.getContext('2d');
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      
      return canvas.toDataURL('image/jpeg', 0.8);
    }
    return null;
  };

  // Manual capture for testing
  const manualCapture = () => {
    if (capturedPhotos.length < 3) {
      const photo = capturePhoto();
      if (photo) {
        setCapturedPhotos(prev => {
          const newPhotos = [...prev, photo];
          if (newPhotos.length >= 3) {
            setIsCapturing(false);
            setCurrentPhase('preview');
            detectionActiveRef.current = false;
          }
          return newPhotos;
        });
      }
    }
  };

  // Start smile detection
  const startSmileDetection = async () => {
    setIsCapturing(true);
    setCurrentPhase('capturing');
    detectionActiveRef.current = true;
    
    const detectSmile = async () => {
      if (!detectionActiveRef.current) return;
      
      // Check if we have enough photos
      if (capturedPhotos.length >= 3) {
        setIsCapturing(false);
        setCurrentPhase('preview');
        detectionActiveRef.current = false;
        return;
      }

      try {
        const photoData = capturePhoto();
        if (photoData && detectionActiveRef.current) {
          const smileDetected = await checkForSmile(photoData);
          
          if (smileDetected && detectionActiveRef.current) {
            // Show countdown
            setCountdown(3);
            let count = 3;
            
            const countdownInterval = setInterval(() => {
              count--;
              setCountdown(count);
              
              if (count === 0) {
                clearInterval(countdownInterval);
                setCountdown(null);
                
                // Capture the photo
                const finalPhoto = capturePhoto();
                if (finalPhoto && detectionActiveRef.current) {
                  setCapturedPhotos(prev => {
                    const newPhotos = [...prev, finalPhoto];
                    if (newPhotos.length >= 3) {
                      setIsCapturing(false);
                      setCurrentPhase('preview');
                      detectionActiveRef.current = false;
                    }
                    return newPhotos;
                  });
                }
              }
            }, 1000);
            
            // Wait for countdown to finish before next detection
            await new Promise(resolve => setTimeout(resolve, 3500));
          }
        }
      } catch (error) {
        console.error('Error in smile detection:', error);
      }
      
      // Continue detection if still active and haven't captured all photos
      if (detectionActiveRef.current && capturedPhotos.length < 3) {
        setTimeout(detectSmile, 500);
      }
    };
    
    detectSmile();
  };

  // Generate final photo strip
  const generatePhotoStrip = () => {
    if (stripCanvasRef.current && capturedPhotos.length === 3) {
      const canvas = stripCanvasRef.current;
      const ctx = canvas.getContext('2d');
      
      // Set canvas dimensions for photo strip
      canvas.width = 300;
      canvas.height = 600 + (message ? 80 : 0);
      
      // White background
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Add border
      ctx.strokeStyle = '#e5e7eb';
      ctx.lineWidth = 2;
      ctx.strokeRect(0, 0, canvas.width, canvas.height);
      
      let loadedCount = 0;
      
      // Draw photos
      capturedPhotos.forEach((photo, index) => {
        const img = new Image();
        img.onload = () => {
          ctx.drawImage(img, 10, 10 + index * 190, 280, 180);
          
          // Add photo border
          ctx.strokeStyle = '#d1d5db';
          ctx.lineWidth = 1;
          ctx.strokeRect(10, 10 + index * 190, 280, 180);
          
          loadedCount++;
          
          // Add message and generate final image after all photos are loaded
          if (loadedCount === 3) {
            if (message) {
              ctx.fillStyle = '#000000';
              ctx.font = '16px monospace';
              ctx.textAlign = 'center';
              ctx.fillText(message, canvas.width / 2, canvas.height - 30);
            }
            
            const finalImageData = canvas.toDataURL('image/jpeg', 0.9);
            setFinalImage(finalImageData);
            setCurrentPhase('final');
          }
        };
        img.src = photo;
      });
    }
  };

  // Download image
  const downloadImage = () => {
    if (finalImage) {
      const link = document.createElement('a');
      link.download = `photobooth-strip-${Date.now()}.jpg`;
      link.href = finalImage;
      link.click();
    }
  };

  // Reset session
  const resetSession = () => {
    detectionActiveRef.current = false;
    setIsCapturing(false);
    setCapturedPhotos([]);
    setMessage('');
    setFinalImage(null);
    setCurrentPhase('setup');
    setCountdown(null);
    setError('');
    stopWebcam();
  };

  // Blinking cursor effect
  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);
    return () => clearInterval(cursorInterval);
  }, []);

  // Check backend connection on mount
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      detectionActiveRef.current = false;
      stopWebcam();
    };
  }, []);

  return (
    <div className="min-h-screen max-w-full bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-2xl w-full">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">
          📸 Smile Photobooth
        </h1>
        
        {/* Error Display */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 flex items-center">
            <AlertCircle className="w-5 h-5 mr-2" />
            {error}
          </div>
        )}
        
        {/* Backend Status */}
        <div className="mb-4 text-center">
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${
            isBackendConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            <div className={`w-2 h-2 rounded-full mr-2 ${
              isBackendConnected ? 'bg-green-500' : 'bg-red-500'
            }`} />
            {isBackendConnected ? 'Backend Connected' : 'Backend Disconnected'}
          </div>
        </div>
        
        {/* Setup Phase */}
        {currentPhase === 'setup' && (
          <div className="text-center">
            <div className="bg-gray-100 rounded-lg p-8 mb-6">
              <Camera className="w-16 h-16 mx-auto text-gray-400 mb-4" />
              <p className="text-lg text-gray-600 mb-4">
                Get ready for your photobooth session!
              </p>
              <p className="text-sm text-gray-500">
                We'll capture 3 photos automatically when you smile
              </p>
            </div>
            <button
              onClick={() => {
                startWebcam();
                setTimeout(startSmileDetection, 1000);
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors"
            >
              Start Photobooth
            </button>
          </div>
        )}

        {/* Capturing Phase */}
        {currentPhase === 'capturing' && (
          <div className="text-center">
            <div className="relative mb-6">
              <video
                ref={videoRef}
                autoPlay
                muted
                className="w-full max-w-md mx-auto rounded-lg shadow-lg"
              />
              {countdown && (
                <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 rounded-lg">
                  <div className="text-white text-6xl font-bold animate-pulse">{countdown}</div>
                </div>
              )}
            </div>
            
            <div className="flex items-center justify-center space-x-4 mb-4">
              <Smile className="w-6 h-6 text-yellow-500" />
              <span className="text-lg font-semibold text-gray-700">
                {isBackendConnected ? 'Smile to capture!' : 'Click to capture!'} ({capturedPhotos.length}/3)
              </span>
            </div>
            
            <div className="flex space-x-2 justify-center mb-4">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className={`w-4 h-4 rounded-full ${
                    i < capturedPhotos.length
                      ? 'bg-green-500'
                      : 'bg-gray-300'
                  }`}
                />
              ))}
            </div>
            
            {!isBackendConnected && (
              <button
                onClick={manualCapture}
                className="bg-orange-600 hover:bg-orange-700 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
              >
                Manual Capture
              </button>
            )}
          </div>
        )}

        {/* Preview Phase */}
        {currentPhase === 'preview' && (
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">
              Your Photos!
            </h2>
            
            <div className="grid grid-cols-3 gap-4 mb-6">
              {capturedPhotos.map((photo, index) => (
                <img
                  key={index}
                  src={photo}
                  alt={`Photo ${index + 1}`}
                  className="w-full h-24 object-cover rounded-lg shadow-md"
                />
              ))}
            </div>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Add a message (optional):
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Sign your photobooth strip..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                  maxLength={50}
                />
                <span className={`absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 ${showCursor ? 'opacity-100' : 'opacity-0'}`}>
                  |
                </span>
              </div>
            </div>
            
            <button
              onClick={generatePhotoStrip}
              className="bg-green-600 hover:bg-green-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors"
            >
              Generate Photo Strip
            </button>
          </div>
        )}

        {/* Final Phase */}
        {currentPhase === 'final' && (
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">
              Your Photobooth Strip!
            </h2>
            
            {finalImage && (
              <div className="mb-6">
                <img
                  src={finalImage}
                  alt="Final photobooth strip"
                  className="mx-auto rounded-lg shadow-lg max-h-96"
                />
              </div>
            )}
            
            <div className="flex space-x-4 justify-center">
              <button
                onClick={downloadImage}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center space-x-2"
              >
                <Download className="w-5 h-5" />
                <span>Download</span>
              </button>
              
              <button
                onClick={resetSession}
                className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center space-x-2"
              >
                <RotateCcw className="w-5 h-5" />
                <span>Take New Photos</span>
              </button>
            </div>
          </div>
        )}
        
        {/* Hidden canvases for photo processing */}
        <canvas ref={canvasRef} className="hidden" />
        <canvas ref={stripCanvasRef} className="hidden" />
      </div>
    </div>
  );
};

export default PhotoboothApp;