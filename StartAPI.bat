@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title AI Backend Server

cd /d %~dp0

echo ===================================================
echo   Starting Python AI Server...
echo ===================================================

REM Python Backend (AI Server) だけを起動
start  "Backend: Python (AI)" cmd /k "cd /d %~dp0 && python -m backend.api.ai_server"

echo ===================================================
echo   Backend is running. You can now use the VS Code Extension!
echo ===================================================
pause