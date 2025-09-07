@echo off
REM Batch file wrapper for PowerShell SSH script
REM This allows easy execution on Windows systems

powershell.exe -ExecutionPolicy Bypass -File "%~dp0ssh-to-instance.ps1" %*
