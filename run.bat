@echo off
setlocal
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo Creating virtual environment...
    py -m venv venv || goto :error
    call venv\Scripts\activate
    echo Installing dependencies...
    python -m pip install --upgrade pip
    if exist requirements.txt (
        python -m pip install -r requirements.txt || goto :error
    )
) else (
    call venv\Scripts\activate
)

echo Launching Han-Eng Lyric Video Maker GUI...
python main.py
goto :end

:error
echo Failed to set up or start the application.
exit /b 1

:end
exit /b 0
