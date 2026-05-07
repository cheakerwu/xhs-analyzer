@echo off
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if "%XHS_ANALYZER_PYTHON%"=="" (
  set "XHS_ANALYZER_PYTHON=python"
)

"%XHS_ANALYZER_PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8088 --reload
