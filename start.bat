@echo off
TITLE Smart Medical System - Launcher
SETLOCAL EnableDelayedExpansion

:: Set colors for beauty
COLOR 0B

echo =====================================================================
echo           SMART MEDICAL RECORD SYSTEM - AUTO LAUNCHER
echo =====================================================================
echo.

:: Check for Server directory
if not exist "server" (
    echo [ERROR] Server directory not found!
    goto error
)

:: Check for Client directory
if not exist "client" (
    echo [ERROR] Client directory not found!
    goto error
)

:: Start Backend Server
echo [1/2] Starting Backend Server (FastAPI)...
cd server
:: Run in a new window and keep it open on exit/error
start "Backend Server (FastAPI)" cmd /k "echo Activating Virtual Environment... && venv\Scripts\activate && echo Starting Uvicorn... && uvicorn app.main:app --reload"
cd ..

:: Start Frontend Client
echo [2/2] Starting Frontend Client (Vite/React)...
cd client
:: Run in a new window and keep it open on exit/error
start "Frontend Client (Vite)" cmd /k "echo Starting Vite... && npm run dev"
cd ..

echo.
echo =====================================================================
echo  SERVICES INITIALIZED SUCCESSFULLY
echo =====================================================================
echo.
echo  - Backend API:    http://127.0.0.1:8000
echo  - Frontend Web:   Check the Frontend window for link (usually :5173)
echo  - Documentation:  http://127.0.0.1:8000/docs
echo.
echo  Wait a few seconds for systems to warm up. 
echo  Keep the separate windows open while working.
echo =====================================================================
echo.
echo Press any key to exit this launcher...
pause > nul
exit

:error
echo.
echo [FATAL] Startup failed. Please ensure you are in the project root.
pause
exit
