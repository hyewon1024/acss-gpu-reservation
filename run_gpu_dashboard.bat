@echo off
cd /d "%~dp0"
echo Starting ACSS GPUUsage_v1...

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    echo Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt
)

echo Launching Dashboard...
.venv\Scripts\streamlit run app.py
pause
