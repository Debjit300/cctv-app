@echo off
title Sentinel AI - CCTV Monitoring System
cd /d "C:\Users\debji\Downloads\cctv_app"
echo ========================================================
echo   Starting Sentinel AI CCTV Monitoring Dashboard...
echo ========================================================
echo.
echo Opening browser at http://localhost:5000 in 3 seconds...
start "" "http://localhost:5000"
echo.
python app.py
pause
