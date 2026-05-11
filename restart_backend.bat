@echo off
echo ========================================
echo Restarting Backend with Conversation Router
echo ========================================
echo.

cd /d "%~dp0apps\api"

echo [1/3] Checking if backend is running...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo Backend is running. Please stop it first (Ctrl+C in the terminal).
    echo Then run this script again.
    pause
    exit /b 1
)

echo [2/3] Starting backend...
echo.
echo Backend will start at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the backend
echo.

start "Food Advisor API" cmd /k "uvicorn app.main:app --reload"

timeout /t 3 >nul

echo [3/3] Testing conversation API...
timeout /t 2 >nul

curl -s http://localhost:8000/api/conversations?limit=1
echo.
echo.

echo ========================================
echo Backend started successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Start frontend: cd apps\web ^&^& npm run dev
echo 2. Open browser: http://localhost:3000
echo 3. Send a message to create a conversation
echo.
pause
