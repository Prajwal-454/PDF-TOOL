@echo off
title Uninstall PDF-TOOL
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desktop\uninstall.ps1" %*
echo.
pause
