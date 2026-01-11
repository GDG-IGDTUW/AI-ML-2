@echo off
echo ===============================
echo 🚀 Launching BAIDS Project
echo ===============================

:: Activate virtual environment
call venv\Scripts\activate

:: Start Flask API in background
start "BAIDS API" cmd /k python api.py

:: Wait for API to come online
timeout /t 5 /nobreak >nul

:: Start Streamlit UI
start "BAIDS Dashboard" cmd /k streamlit run app.py

:: Optional: Start simulator in demo mode
start "BAIDS Simulator" cmd /k python simulator.py --mode demo

echo All components launched! ✅
pause
