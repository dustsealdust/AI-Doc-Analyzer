@echo off
cd /d "%~dp0"

set "PY=python"
if exist "D:\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
    set "PY=D:\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
)

echo Starting Web App...
"%PY%" -m streamlit run app.py
pause