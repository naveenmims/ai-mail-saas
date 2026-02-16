@echo off
setlocal

cd /d C:\Users\admin\ai-mail-saas\backend

REM activate venv
call .\venv\Scripts\activate.bat

REM force utf-8 for python output
set PYTHONUTF8=1

REM run forever loop
powershell -ExecutionPolicy Bypass -File .\run_forever.ps1
