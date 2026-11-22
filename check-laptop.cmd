@echo off
setlocal
cd /d "%~dp0"
set "OPT_PY=venv\optimizer313\Scripts\python.exe"
if exist "%OPT_PY%" goto verify
py -3.13 -c "import sys" >nul 2>&1
if errorlevel 1 goto try_python
py -3.13 -m venv "venv\optimizer313"
if errorlevel 1 exit /b 1
goto verify

:try_python
python -c "import sys; sys.exit(sys.version_info[:2] != (3, 13))" >nul 2>&1
if errorlevel 1 (
    echo Windows could not find Python 3.13. Run py -0p to see installed versions.
    echo Install Python 3.13 for Windows if needed, then run this check again.
    exit /b 1
)
python -m venv "venv\optimizer313"
if errorlevel 1 exit /b 1

:verify
"%OPT_PY%" -c "import sys; sys.exit(sys.version_info[:2] != (3, 13))"
if errorlevel 1 (
    echo The project environment at venv\optimizer313 could not run Python 3.13.
    exit /b 1
)
"%OPT_PY%" -u -X utf8 src\check_laptop.py
exit /b %errorlevel%
