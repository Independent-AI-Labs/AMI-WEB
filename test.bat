@echo off
REM Activate virtual environment and run tests

if not exist .venv (
    echo Creating virtual environment...
    uv venv .venv
    echo Installing dependencies...
    uv pip install -e ".[dev]"
)

echo Activating virtual environment...
call .venv\Scripts\activate

echo Running tests...
python -m pytest %*

deactivate