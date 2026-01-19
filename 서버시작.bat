@echo off
cd /d "%~dp0"
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8502
pause
