# Quick Claude Desktop Setup

## For macOS Users

1. **Copy the configuration to Claude Desktop:**
   ```bash
   cp claude_desktop_config_ready.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Restart Claude Desktop completely** (Quit from menu bar, not just close window)

3. **Verify connection** - Look for the 🔌 icon in Claude Desktop's input area

## Troubleshooting

If the server doesn't connect:

1. **Test the script manually:**
   ```bash
   python scripts/start_mcp_server.py
   ```

2. **Check Claude Desktop logs:**
   - Open Console.app
   - Search for "ami-web" or "mcp"

3. **Update the path in config:**
   - Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Replace `/Users/vladislavdonchev/Work/AMI-WEB` with your actual path

4. **Ensure uv is installed:**
   ```bash
   pip install uv
   ```
   The start script will automatically create and manage the virtual environment.

## Manual Configuration

If you need to customize the path:

```json
{
  "mcpServers": {
    "ami-web-browser": {
      "command": "python",
      "args": [
        "scripts/start_mcp_server.py"
      ],
      "cwd": "/YOUR/PATH/TO/AMI-WEB",
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Replace `/YOUR/PATH/TO/AMI-WEB` with your actual installation path.

## Alternative: Direct Python Execution

If the script doesn't work, try direct execution:

```json
{
  "mcpServers": {
    "ami-web-browser": {
      "command": "/YOUR/PATH/TO/AMI-WEB/.venv/bin/python",
      "args": [
        "backend/mcp/browser/run_stdio.py"
      ],
      "cwd": "/YOUR/PATH/TO/AMI-WEB",
      "env": {
        "PYTHONPATH": "/YOUR/PATH/TO/AMI-WEB",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Verify Installation

After setup, in Claude Desktop you should be able to:
1. Click the 🔌 icon to see available browser tools
2. Ask Claude to "Launch a browser and go to example.com"
3. Claude will use the browser automation tools automatically