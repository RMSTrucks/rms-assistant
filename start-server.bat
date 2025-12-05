@echo off
cd /d C:\Users\Jake\WorkProjects\rms-assistant-extension\agent
call .venv\Scripts\activate.bat
python -m app.server
