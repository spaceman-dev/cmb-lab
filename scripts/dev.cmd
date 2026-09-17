@echo off
REM Run cmb-lab on Windows.
REM
REM   scripts\dev.cmd bootstrap
REM   scripts\dev.cmd up | down | status | logs | doctor
REM
REM Batch files are not subject to PowerShell's execution policy, which is Restricted on a
REM default Windows install and blocks dev.ps1 outright. This launches the same script with
REM the policy bypassed for that one process only, changing nothing on the machine.

setlocal

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
)

exit /b %ERRORLEVEL%
