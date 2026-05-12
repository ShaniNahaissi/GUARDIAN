# Install Node.js Current (latest stable major from nodejs.org via winget).
# Vite 8 needs Node >= 20.19 or >= 22.12; the winget package OpenJS.NodeJS.18 only goes to 18.x.
# Run this in an elevated PowerShell: Start menu -> type PowerShell -> Run as administrator.

$ErrorActionPreference = 'Stop'
winget install --id OpenJS.NodeJS -e --source winget `
  --accept-source-agreements --accept-package-agreements --disable-interactivity

Write-Host "Close all terminals, open a new one, then run: node -v" -ForegroundColor Green
Write-Host "Optional: remove old side-by-side install: winget uninstall OpenJS.NodeJS.18 -e" -ForegroundColor Yellow
