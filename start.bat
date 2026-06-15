@echo off
setlocal

cd /d "%~dp0"

if not exist "backend\data" (
  mkdir "backend\data"
)

echo Starting frontend and backend with Docker Compose...
docker compose up --build
if errorlevel 1 (
  echo.
  echo Docker Compose failed to start the stack.
  exit /b 1
)

endlocal
