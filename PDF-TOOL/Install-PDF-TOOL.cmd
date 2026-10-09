@echo off
title Install PDF-TOOL
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desktop\install.ps1" %*
echo.
pause
