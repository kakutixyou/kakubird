@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title App Launcher

cd /d %~dp0

echo ===================================================
echo   Starting Backend and Frontend...
echo ===================================================

REM ===================================================
REM Python Backend (AI Server)
REM ===================================================
echo [*] Launching Python AI Server...
start  "Backend: Python (AI)" cmd /k "cd /d %~dp0 && python -m backend.api.ai_server"

REM Python起動待機
timeout /t 4 >nul

REM ===================================================
REM Frontend
REM ===================================================
echo [*] Launching Frontend (Vite)...
start  "Frontend: Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

REM Vite起動待機（長めに）
timeout /t 6 >nul

start http://localhost:5173

echo ===================================================
echo   All services launched (Press CTRL+C to stop all)
echo ===================================================
pause