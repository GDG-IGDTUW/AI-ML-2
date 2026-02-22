import React, { useState, useRef, useEffect } from 'react';
import { Camera, Download, RotateCcw, Smile, AlertCircle } from 'lucide-react';

const FILTERS = [
  { id: 'none',      label: 'None',      css: 'none' },
  { id: 'grayscale', label: 'Grayscale', css: 'grayscale(100%)' },
  { id: 'sepia',     label: 'Sepia',     css: 'sepia(80%)' },
  { id: 'blur',      label: 'Blur',      css: 'blur(4px)' },
  { id: 'vivid',     label: 'Vivid',     css: 'saturate(2) contrast(1.1)' },
];

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
  const [isCountingDown, setIsCountingDown] = useState(false);
  const [retakeIndex, setRetakeIndex] = useState(null);
  const [activeFilter, setActiveFilter] = useState('none');

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const stripCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const detectionActiveRef = useRef(false);
  const photoCountRef = useRef(0);
  const countdownIntervalRef = useRef(null);
  const lastCaptureTimestampRef = useRef(0);
  const abortControllerRef = useRef(null);
  const activeFilterRef = useRef('none');

  const DETECTION_INTERVAL = 900;
  const MIN_TIME_BETWEEN_CAPTURES = 4800;

  // ── Backend Health Check ───────────────────────────────────────
  const checkBackendConnection = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      const res = await fetch('http://localhost:5000/health', {
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      setIsBackendConnected(res.ok);
      setError(res.ok ? '' : 'Backend not responding');
    } catch (err) {
      setIsBackendConnected(false);
      setError(
        err.name === 'AbortError'
          ? 'Backend timeout'
          : 'Cannot reach backend (is it running on port 5000?)'
      );
    }
  };

  // ── Smile Detection Request ────────────────────────────────────
  const checkForSmile = async (imageData, signal) => {
    if (!detectionActiveRef.current) return false;

    try {
      const res = await fetch('http://localhost:5000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData }),
        signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return !!data.smile;
    } catch (err) {
      if (err.name !== 'AbortError') console.warn('Smile check failed:', err);
      return false;
    }
  };

  // ── Main Smile Detection Loop ──────────────────────────────────
  const startSmileDetection = () => {
    setIsCapturing(true);
    setCurrentPhase('capturing');
    detectionActiveRef.current = true;
    lastCaptureTimestampRef.current = 0;

    if (retakeIndex === null) {
      photoCountRef.current = 0;
      setCapturedPhotos([]);
    } else {
      photoCountRef.current = capturedPhotos.length;
    }

    if (abortControllerRef.current) abortControllerRef.current.abort();

    const detectLoop = async () => {
      if (!detectionActiveRef.current || photoCountRef.current >= 3) return;

      if (isCountingDown) {
        setTimeout(detectLoop, 1400);
        return;
      }

      const now = Date.now();
      if (now - lastCaptureTimestampRef.current < MIN_TIME_BETWEEN_CAPTURES) {
        setTimeout(detectLoop, 1000);
        return;
      }

      const photoData = capturePhoto();
      if (!photoData) {
        setTimeout(detectLoop, DETECTION_INTERVAL);
        return;
      }

      abortControllerRef.current = new AbortController();

      const smileDetected = await checkForSmile(photoData, abortControllerRef.current.signal);

      if (smileDetected && detectionActiveRef.current && !isCountingDown) {
        lastCaptureTimestampRef.current = Date.now();
        startCountdownAndCapture();
      }

      if (detectionActiveRef.current && photoCountRef.current < 3) {
        setTimeout(detectLoop, DETECTION_INTERVAL);
      }
    };

    detectLoop();
  };

  // ── Countdown & Photo Capture ──────────────────────────────────
  const startCountdownAndCapture = () => {
    if (isCountingDown) return;
    setIsCountingDown(true);
    setCountdown(3);

    let count = 3;
    countdownIntervalRef.current = setInterval(() => {
      count--;
      setCountdown(count);

      if (count <= 0) {
        clearInterval(countdownIntervalRef.current);
        setCountdown(null);

        const photo = captureFilteredPhoto();
        if (photo && detectionActiveRef.current) {
          setCapturedPhotos(prev => {
            let updated;

            if (retakeIndex !== null) {
              updated = [...prev];
              updated[retakeIndex] = photo;
              setRetakeIndex(null);
            } else {
              updated = [...prev, photo];
            }

            photoCountRef.current = updated.length;

            if (updated.length >= 3) {
              setIsCapturing(false);
              setCurrentPhase('preview');
              detectionActiveRef.current = false;
              stopWebcam();
            }

            return updated;
          });
        }

        setIsCountingDown(false);
      }
    }, 1000);
  };

  // ── Retake Single Photo ────────────────────────────────────────
  const handleRetakeSingle = (index) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to retake this photo?"
    );
    if (!confirmDelete) return;

    setRetakeIndex(index);
    setCurrentPhase('capturing');
    startWebcam();
    setTimeout(startSmileDetection, 800);
  };

  // ── Camera Helpers ─────────────────────────────────────────────
  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } }
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setError('');
    } catch (err) {
      setError('Webcam access denied or unavailable');
    }
  };

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  const capturePhoto = () => {
    if (!videoRef.current?.videoWidth || !canvasRef.current) return null;
    const canvas = canvasRef.current;
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
    return canvas.toDataURL('image/jpeg', 0.82);
  };

  // Captures with active filter applied — used for stored photos only.
  // capturePhoto() stays raw so backend smile detection is unaffected.
  const captureFilteredPhoto = () => {
    if (!videoRef.current?.videoWidth || !canvasRef.current) return null;
    const canvas = canvasRef.current;
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.filter = FILTERS.find(f => f.id === activeFilterRef.current)?.css || 'none';
    ctx.drawImage(videoRef.current, 0, 0);
    ctx.filter = 'none';
    return canvas.toDataURL('image/jpeg', 0.82);
  };

  // ── Generate Final Strip ───────────────────────────────────────
  const generatePhotoStrip = () => {
    if (!stripCanvasRef.current || capturedPhotos.length !== 3) return;

    const canvas = stripCanvasRef.current;
    const ctx = canvas.getContext('2d');

    canvas.width = 300;
    canvas.height = 600 + (message ? 80 : 0);

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, canvas.width, canvas.height);

    let loaded = 0;

    capturedPhotos.forEach((src, i) => {
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 10, 10 + i * 190, 280, 180);
        ctx.strokeStyle = '#d1d5db';
        ctx.lineWidth = 1;
        ctx.strokeRect(10, 10 + i * 190, 280, 180);

        loaded++;
        if (loaded === 3) {
          if (message) {
            ctx.fillStyle = '#111';
            ctx.font = '16px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(message.slice(0, 60), canvas.width / 2, canvas.height - 35);
          }
          setFinalImage(canvas.toDataURL('image/jpeg', 0.92));
          setCurrentPhase('final');
        }
      };
      img.src = src;
    });
  };

  const downloadImage = () => {
    if (!finalImage) return;
    const a = document.createElement('a');
    a.download = `smile-photobooth-${Date.now()}.jpg`;
    a.href = finalImage;
    a.click();
  };

  const resetSession = () => {
    detectionActiveRef.current = false;
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setIsCountingDown(false);
    setIsCapturing(false);
    setCapturedPhotos([]);
    photoCountRef.current = 0;
    setMessage('');
    setFinalImage(null);
    setCountdown(null);
    setCurrentPhase('setup');
    setError('');
    setActiveFilter('none');
    activeFilterRef.current = 'none';
    stopWebcam();
  };

  // Effects
  useEffect(() => {
    checkBackendConnection();
    const id = setInterval(checkBackendConnection, 15000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => setShowCursor(v => !v), 600);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    return () => {
      detectionActiveRef.current = false;
      stopWebcam();
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  // ── RENDER ─────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-indigo-900 to-blue-950 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur rounded-2xl shadow-2xl p-8 max-w-2xl w-full border border-gray-100">
        <h1 className="text-3xl font-bold text-center mb-6 text-gray-800 flex items-center justify-center gap-3">
          <Camera className="w-8 h-8" /> Smile Photobooth
        </h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-5 flex items-center gap-2 text-sm">
            <AlertCircle size={18} /> {error}
          </div>
        )}

        <div className="flex justify-center mb-6">
          <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium ${
            isBackendConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            <div className={`w-2.5 h-2.5 rounded-full ${isBackendConnected ? 'bg-green-500' : 'bg-red-500 animate-pulse'}`} />
            {isBackendConnected ? 'Backend Connected' : 'Backend Offline'}
          </div>
        </div>

        {currentPhase === 'setup' && (
          <div className="text-center py-10">
            <Camera className="w-24 h-24 mx-auto text-gray-400 mb-6 opacity-80" strokeWidth={1.2} />
            <p className="text-lg text-gray-700 mb-2">Ready for fun photos?</p>
            <p className="text-sm text-gray-500 mb-8">We'll capture 3 shots when you smile!</p>
            <button
              onClick={() => {
                startWebcam();
                setTimeout(startSmileDetection, 800);
              }}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-12 py-4 rounded-xl font-semibold shadow-lg hover:scale-105 transition-all"
            >
              Start Session
            </button>
          </div>
        )}

        {currentPhase === 'capturing' && (
          <div className="text-center">
            <div className="relative mb-8 rounded-2xl overflow-hidden shadow-2xl ring-1 ring-gray-200">
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="w-full max-w-md mx-auto"
                style={{ filter: FILTERS.find(f => f.id === activeFilter)?.css }}
              />
              {activeFilter !== 'none' && (
                <div className="absolute top-3 left-3 bg-black/60 text-white text-xs px-2.5 py-1 rounded-full font-medium pointer-events-none">
                  {FILTERS.find(f => f.id === activeFilter)?.label}
                </div>
              )}
              {countdown !== null && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                  <div className="text-white text-9xl font-black animate-pulse drop-shadow-2xl">
                    {countdown}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-center gap-3 mb-6 text-lg font-semibold text-gray-700">
              <Smile className="w-8 h-8 text-yellow-500" />
              Smile to capture! • {capturedPhotos.length}/3
            </div>

            <div className="flex justify-center gap-5 mb-10">
              {Array(3).fill(0).map((_, i) => (
                <div
                  key={i}
                  className={`w-6 h-6 rounded-full transition-all duration-500 ${
                    i < capturedPhotos.length
                      ? 'bg-green-500 scale-125 ring-4 ring-green-200'
                      : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>

            <div className="flex items-center justify-center gap-2 mb-6 flex-wrap">
              {FILTERS.map(f => (
                <button
                  key={f.id}
                  onClick={() => { setActiveFilter(f.id); activeFilterRef.current = f.id; }}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    activeFilter === f.id
                      ? 'bg-indigo-600 text-white shadow-md scale-105'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div className="flex justify-center gap-4 flex-wrap">
              <button
                onClick={resetSession}
                className="bg-gray-600 hover:bg-gray-700 text-white px-10 py-3 rounded-xl font-medium transition-colors"
              >
                Cancel
              </button>

              {isBackendConnected && (
                <button
                  onClick={() => {
                    const photo = capturePhoto();
                    if (photo) {
                      // Optional: notify backend (for logging or future features)
                      fetch('http://localhost:5000/manual_capture', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: photo })
                      }).catch(err => console.warn('Manual notify failed:', err));

                      // Trigger capture locally
                      startCountdownAndCapture();
                    }
                  }}
                  disabled={isCountingDown}
                  className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-medium transition-colors"
                >
                  Manual Capture
                </button>
              )}
            </div>
          </div>
        )}

        {currentPhase === 'preview' && (
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Your Photos!</h2>
            <div className="grid grid-cols-3 gap-4 mb-8">
              {capturedPhotos.map((photo, i) => (
                <div key={i} className="relative rounded-lg shadow-md">
                  <img
                    src={photo}
                    alt={`Photo ${i+1}`}
                    className="w-full aspect-square object-cover"
                  />
                  <button
                    onClick={() => handleRetakeSingle(i)}
                    className="absolute top-2 right-2 z-50 bg-red-600 text-white text-xl font-bold w-10 h-10 flex items-center justify-center rounded-full border-2 border-white shadow-lg"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>

            <div className="mb-8 max-w-md mx-auto">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Add a message (optional)
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  placeholder="Best moment ever..."
                  maxLength={60}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono"
                />
                <span className={`absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none ${showCursor ? 'opacity-100' : 'opacity-0'} transition-opacity duration-300`}>
                  |
                </span>
              </div>
            </div>

            <div className="flex justify-center gap-4">
              <button
                onClick={generatePhotoStrip}
                className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-10 py-4 rounded-xl font-semibold shadow-lg hover:scale-105 transition-all"
              >
                Create Strip
              </button>
              <button
                onClick={resetSession}
                className="bg-gray-600 hover:bg-gray-700 text-white px-8 py-4 rounded-xl font-medium transition-colors"
              >
                Retake
              </button>
            </div>
          </div>
        )}

        {currentPhase === 'final' && (
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Your Photobooth Strip!</h2>

            {finalImage && (
              <div className="mb-10 rounded-xl overflow-hidden shadow-2xl border border-gray-200">
                <img
                  src={finalImage}
                  alt="Final photobooth strip"
                  className="mx-auto max-h-[520px] w-auto"
                />
              </div>
            )}

            <div className="flex justify-center gap-6">
              <button
                onClick={downloadImage}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-10 py-4 rounded-xl font-semibold shadow-lg flex items-center gap-2 hover:scale-105 transition-all"
              >
                <Download size={20} /> Download
              </button>
              <button
                onClick={resetSession}
                className="bg-gray-600 hover:bg-gray-700 text-white px-10 py-4 rounded-xl font-semibold flex items-center gap-2 transition-colors"
              >
                <RotateCcw size={20} /> New Session
              </button>
            </div>
          </div>
        )}

        <canvas ref={canvasRef} className="hidden" />
        <canvas ref={stripCanvasRef} className="hidden" />
      </div>
    </div>
  );
};

export default PhotoboothApp;