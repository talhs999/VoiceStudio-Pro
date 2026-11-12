@echo off
title VoiceStudio Pro - Starting...
color 0A

echo.
echo  =========================================
echo   VOICESTUDIO PRO - ElevenLabs Clone
echo   100%% FREE - Local - No API Key Needed
echo  =========================================
echo.

echo [1/3] Starting Backend Server...
start "VoiceStudio Backend" /min cmd /c "cd /d ""%~dp0backend"" && python app.py"

echo [2/3] Waiting for server to start...
timeout /t 3 /nobreak >nul

echo [3/3] Opening VoiceStudio in Browser...
start "" "http://localhost:5000"

echo.
echo  =========================================
echo   App is running!
echo   
echo   - Backend: http://localhost:5000
echo   - Close this window to stop the server
echo  =========================================
echo.
pause

