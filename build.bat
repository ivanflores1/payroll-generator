@echo off
rem Recompila el ejecutable: dist\GeneradorLiquidaciones.exe
if not exist .venv\Scripts\python.exe (
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
)
.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name GeneradorLiquidaciones --paths src --add-data "config.json;." launcher.py
