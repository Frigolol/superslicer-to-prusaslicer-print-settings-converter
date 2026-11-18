@echo off
rem Build dist\ss2ps.exe (requires: pip install pyinstaller)
python -m PyInstaller --onefile --windowed --name ss2ps --clean --noconfirm ss2ps.py
