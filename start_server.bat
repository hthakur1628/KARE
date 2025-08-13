@echo off
echo ========================================
echo    KARE Healthcare Server Startup
echo ========================================
echo.
echo Starting server on port 3001...
echo Frontend will be available at: http://localhost:3001
echo.

cd backend
python start_server.py

pause