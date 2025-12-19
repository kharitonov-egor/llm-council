@echo off
REM LLM Council - Start script for Windows

echo Starting LLM Council...
echo.

REM Start backend
echo Starting backend on http://localhost:8001...
start "LLM Council Backend" cmd /k "uv run python -m backend.main"

REM Wait a bit for backend to start
timeout /t 2 /nobreak >nul

REM Start frontend
echo Starting frontend on http://localhost:5173...
cd frontend
start "LLM Council Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ✓ LLM Council is running!
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:5173
echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the servers.
echo.
pause
