@echo off
setlocal
cd /d "%~dp0.."
echo Starting Guardian production stack (UI http://localhost:8080, API https://localhost:8000)...
docker compose -f docker-compose.yml up --build -d
if errorlevel 1 exit /b 1
echo.
echo Open: http://localhost:8080
exit /b 0
