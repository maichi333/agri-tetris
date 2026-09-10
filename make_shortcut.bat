@echo off
cd /d "%~dp0"

:: tetris.ico がなければ生成
if not exist "%~dp0tetris.ico" (
    python "%~dp0make_icon.py"
)

:: PowerShell スクリプトでショートカットをデスクトップに作成
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1"

pause
