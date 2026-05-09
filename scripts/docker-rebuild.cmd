@echo off
setlocal
cd /d "%~dp0.."
echo Rebuilding production images without cache...
docker compose -f docker-compose.yml build --no-cache
if errorlevel 1 exit /b 1
docker compose -f docker-compose.yml up -d
exit /b %ERRORLEVEL%
