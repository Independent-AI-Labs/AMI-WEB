# MCP Test Notes

The MCP (Model Context Protocol) tests require special handling because they import from the `base` module which is in the parent directory (AMI-ORCHESTRATOR root).

## Running MCP Tests

Due to Python import path issues, MCP tests cannot be run with the standard pytest collection. Use one of these methods:

### Method 1: Run directly as Python scripts
```bash
cd browser
.venv/Scripts/python.exe tests/integration/test_mcp_server.py
.venv/Scripts/python.exe tests/integration/test_mcp_environment_tools.py  
.venv/Scripts/python.exe tests/integration/test_mcp_logs_storage.py
```

### Method 2: Use the batch file (Windows)
```bash
cd browser
run_mcp_tests.bat
```

### Method 3: Use the test runner script
```bash
cd browser
.venv/Scripts/python.exe scripts/run_tests.py tests/integration/test_mcp_*
```

## Why This Is Necessary

The MCP server (`backend/mcp/browser/server.py`) imports from `base.mcp.mcp_server` which is located in the parent directory. When pytest collects test modules, it imports them before `conftest.py` can set up the path, causing import errors.

The test files add the necessary paths at the top of the file, but pytest's import mechanism bypasses this when collecting tests.

## Test Status

All 14 MCP tests pass when run directly:
- TestMCPServerConnection: 3 tests
- TestMCPBrowserOperations: 4 tests  
- TestMCPCookieManagement: 1 test
- TestMCPTabManagement: 1 test
- TestMCPErrorHandling: 3 tests
- TestMCPConcurrency: 2 tests