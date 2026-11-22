@echo off
call "%~dp0run-windows.cmd" --check
exit /b %errorlevel%
