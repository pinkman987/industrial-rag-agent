@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
set "WEB_URL=http://127.0.0.1:8501"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment not found: %PYTHON_EXE%
    echo Please create .venv and install requirements first.
    pause
    exit /b 1
)

echo Starting FastAPI on http://127.0.0.1:8000 ...
start "Industrial RAG API" /min "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

timeout /t 3 /nobreak >nul

echo Starting Streamlit on %WEB_URL% ...
start "Industrial RAG Web" /min "%PYTHON_EXE%" -m streamlit run frontend\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true

timeout /t 3 /nobreak >nul
start "" "%WEB_URL%"

echo Web page opened: %WEB_URL%
echo Keep the two minimized service windows running while using the page.
endlocal
