@echo off
python -m pip install -r requirements.txt
start "AI Guardian Backend" cmd /k "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
python -m streamlit run app.py
