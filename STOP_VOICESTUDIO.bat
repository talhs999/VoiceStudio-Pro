@echo off
title Stopping VoiceStudio Pro...
echo Stopping VoiceStudio Pro server...
taskkill /F /FI "WINDOWTITLE eq VoiceStudio Backend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo Done! VoiceStudio Pro stopped.
timeout /t 2 /nobreak >nul

