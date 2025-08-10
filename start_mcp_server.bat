@echo off
REM MCP Server Start Script for AMI-WEB (Windows)
REM This script sets up and activates the conda environment before starting the MCP server

setlocal enabledelayedexpansion

echo AMI-WEB MCP Server Launcher
echo ================================

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Try to find conda
where conda >nul 2>&1
if %errorlevel% neq 0 (
    REM Try common conda installation paths
    if exist "%USERPROFILE%\Miniconda3\Scripts\conda.exe" (
        set "CONDA_PATH=%USERPROFILE%\Miniconda3"
    ) else if exist "%USERPROFILE%\Anaconda3\Scripts\conda.exe" (
        set "CONDA_PATH=%USERPROFILE%\Anaconda3"
    ) else if exist "C:\ProgramData\Miniconda3\Scripts\conda.exe" (
        set "CONDA_PATH=C:\ProgramData\Miniconda3"
    ) else if exist "C:\ProgramData\Anaconda3\Scripts\conda.exe" (
        set "CONDA_PATH=C:\ProgramData\Anaconda3"
    ) else (
        echo Error: conda is not installed or not in PATH
        echo Please install Miniconda or Anaconda first:
        echo   https://docs.conda.io/en/latest/miniconda.html
        pause
        exit /b 1
    )
    
    REM Initialize conda for this session
    call "%CONDA_PATH%\Scripts\activate.bat"
)

REM Check if 'web' environment exists
conda env list | findstr /B "web " >nul 2>&1
if %errorlevel% equ 0 (
    echo Found existing 'web' conda environment
) else (
    echo 'web' environment not found. Creating it now...
    
    REM Create the environment with Python 3.12
    call conda create -n web python=3.12 -y
    
    echo Created 'web' conda environment
)

REM Activate the environment
echo Activating 'web' environment...
call conda activate web

REM Check if requirements are installed
echo Checking dependencies...
python -c "import selenium" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing requirements...
    pip install -r requirements.txt
) else (
    echo Dependencies already installed
)

REM Set environment variables
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%
if not defined LOG_LEVEL set LOG_LEVEL=INFO

REM Check if Chrome is configured
if not exist "config.yaml" (
    echo Warning: config.yaml not found
    echo Using default configuration...
)

REM Start the MCP server
echo Starting MCP server...
echo ----------------------------------------
python chrome_manager\mcp\mcp_stdio_server.py