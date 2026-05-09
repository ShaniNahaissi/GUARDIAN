@echo off
setlocal
cd /d "%~dp0.."
echo Rebuilding dev images without cache...
docker compose -f docker-compose.dev.yml build --no-cache
if errorlevel 1 exit /b 1
docker compose -f docker-compose.dev.yml up -d
exit /b %ERRORLEVEL%
