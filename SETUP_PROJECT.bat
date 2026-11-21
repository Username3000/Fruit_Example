@echo off
setlocal
title Fruit Example - Project Setup
chcp 65001 >nul
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Tools\SetupProject.ps1" %*
set "setup_result=%errorlevel%"
echo.
pause
exit /b %setup_result%
