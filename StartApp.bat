@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title App Launcher

cd /d %~dp0

echo ===================================================
echo   Starting All Services...
echo ===================================================

REM ===================================================
REM 1. Python Backend (AI Server)
REM ===================================================
echo [*] Launching Python AI Server...
start  "Backend: Python (AI)" cmd /k "cd /d %~dp0 && python -m backend.api.ai_server"

REM Python起動待機
timeout /t 4 >nul

REM ===================================================
REM 2. Frontend (Vite)
REM ===================================================
echo [*] Launching Frontend (Vite)...
start  "Frontend: Vite" cmd /k "cd /d %~dp0frontend\Tokyo_hackson_23 && npm run dev -- --force"

REM Vite起動待機（長めに）
timeout /t 6 >nul

REM ===================================================
REM 3. StartApp.py (※ファイルが存在しない場合はコメントアウトを推奨)
REM ===================================================
REM echo [*] Launching StartApp.py...
REM start  "App: StartApp" cmd /k "cd /d %~dp0 && python StartApp.py"
REM timeout /t 3 >nul

REM ===================================================
REM 4. api.py (FastAPI Server)
REM ===================================================
echo [*] Launching api.py...
start  "App: API Server" cmd /k "cd /d %~dp0frontend\Tokyo_hackson_23\backend && python api.py"

start http://localhost:5173

echo ===================================================
echo   All services launched (Close individual windows to stop)
echo ===================================================
pause