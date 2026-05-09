@echo off
setlocal
cd /d "%~dp0.."
echo Starting Guardian dev stack (Vite http://localhost:5173, API https://localhost:8000 with live reload)...
docker compose -f docker-compose.dev.yml up --build
if errorlevel 1 exit /b 1
echo.
echo Open: http://localhost:5173
exit /b 0
