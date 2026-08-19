@echo off
chcp 65001 >nul

title Backend Deep Health Check

set LOGFILE=backend_health_report.txt

echo ===
echo   Backend Deep Health Check
echo ===
echo.

echo === > %LOGFILE%
echo Backend Health Report >> %LOGFILE%
echo Generated: %date% %time% >> %LOGFILE%
echo === >> %LOGFILE%
echo. >> %LOGFILE%

echo [1/4] Python Version...
python --version >> %LOGFILE% 2>&1

echo. >> %LOGFILE%

echo [2/4] Python Path...
where python >> %LOGFILE% 2>&1

echo. >> %LOGFILE%

echo [3/4] Import Test...
python backend_import_test.py >> %LOGFILE% 2>&1

echo. >> %LOGFILE%

echo [4/4] ai_server Boot Test...
python -m backend.api.ai_server >> %LOGFILE% 2>&1

echo. >> %LOGFILE%

echo === >> %LOGFILE%
echo CHECK COMPLETE >> %LOGFILE%
echo === >> %LOGFILE%

echo.
echo ===
echo   CHECK COMPLETE
echo ===
echo.
echo Report:
echo %LOGFILE%
echo.

pause
