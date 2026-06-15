@echo off
setlocal

cd /d "%~dp0"

echo Stopping frontend and backend...
docker compose down
if errorlevel 1 (
  echo.
  echo Docker Compose failed to stop the stack cleanly.
  exit /b 1
)

endlocal
