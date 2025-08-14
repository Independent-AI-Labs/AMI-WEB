@echo off
REM Run MCP tests with proper PYTHONPATH setup
set PYTHONPATH=%CD%;%CD%\..
echo Running MCP tests with PYTHONPATH=%PYTHONPATH%
".venv\Scripts\python.exe" -m pytest tests/integration/test_mcp_server.py tests/integration/test_mcp_environment_tools.py tests/integration/test_mcp_logs_storage.py %*