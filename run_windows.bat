@echo off
python -m pip install -r requirements.txt
python modules\train_model.py
python -m streamlit run app.py
pause
