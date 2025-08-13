# 🤖 MCP Integration Guide for AMI-WEB

This guide explains how to integrate AMI-WEB's browser automation capabilities with AI assistants like Claude Desktop, Claude Code, and Google Gemini CLI using the Model Context Protocol (MCP).

## 📋 Table of Contents

- [What is MCP?](#what-is-mcp)
- [Quick Start](#quick-start)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Claude Code Integration](#claude-code-integration)
- [Google Gemini CLI Integration](#google-gemini-cli-integration)
- [Available Browser Tools](#available-browser-tools)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## What is MCP?

The Model Context Protocol (MCP) is an open standard created by Anthropic that allows AI assistants to interact with external tools, databases, and APIs. AMI-WEB provides an MCP server that exposes 40+ browser automation tools to AI assistants.

## Quick Start

### Prerequisites

1. **Install Conda** (Recommended):
   - Download Miniconda: https://docs.conda.io/en/latest/miniconda.html
   - Or use an existing Anaconda installation
   - The provided start scripts will automatically create a 'web' environment

2. **Install AMI-WEB**:
```bash
git clone https://github.com/Independent-AI-Labs/AMI-WEB.git
cd AMI-WEB

# Option A: Using uv (Recommended - Fast)
pip install uv  # If not already installed
uv venv .venv
.venv/Scripts/activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux
uv pip install -r requirements.txt

# Option B: Use the start script (auto-creates .venv with uv)
python scripts/start_mcp_server.py              # Stdio mode (Claude Desktop) - default
python scripts/start_mcp_server.py websocket    # WebSocket mode (port 8765)

# Option C: Manual conda setup
conda create -n web python=3.12
conda activate web
pip install -r requirements.txt
```

3. **Verify Chrome/Chromium** is installed (AMI-WEB includes ChromeDriver)

4. **For Node.js-based integrations**: Ensure Node.js is installed (`node --version`)

## Claude Desktop Integration

Claude Desktop supports MCP servers through a configuration file. Here's how to set up AMI-WEB:

### Step 1: Locate Configuration File

The configuration file location varies by OS:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
  - Typically: `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: Coming soon

### Step 2: Configure AMI-WEB Server

Add the following to your `claude_desktop_config.json`:

#### Option 1: Using Start Script (Recommended)

The start script automatically handles virtual environment setup with uv:

```json
{
  "mcpServers": {
    "ami-web-browser": {
      "command": "python",
      "args": ["scripts/start_mcp_server.py"],
      "cwd": "/path/to/AMI-WEB",
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Windows users**: Replace `/path/to/AMI-WEB` with your actual path like `C:\\Users\\YourName\\AMI-WEB`

#### Option 2: Direct Python Execution

If you manage your Python environment manually:

```json
{
  "mcpServers": {
    "ami-web-browser": {
      "command": "python3",
      "args": ["backend/mcp/browser/run_stdio.py"],
      "cwd": "/path/to/AMI-WEB",
      "env": {
        "PYTHONPATH": "/path/to/AMI-WEB"
      }
    }
  }
}
```

**Note:** On Windows use `python` instead of `python3`.

**Startup scripts** are provided in the `scripts/` directory:
- `scripts/start_mcp_server.py` - Unified MCP server launcher (stdio or websocket)
- `scripts/run_tests.py` - Test runner with proper environment setup

### Step 3: Restart Claude Desktop

1. Completely quit Claude Desktop (not just close the window)
2. Restart Claude Desktop
3. Look for the MCP server indicator (🔌) in the bottom-right corner of the input box
4. Click it to see available browser tools

### Alternative: Using Desktop Extensions

Claude Desktop now supports one-click MCP server installation:

1. Open Claude Desktop
2. Navigate to **Settings > Extensions**
3. Search for browser automation tools
4. Click install on compatible servers

## Claude Code Integration

Claude Code (the CLI tool) supports MCP servers through different configuration methods.

### Method 1: Direct Configuration File

Create or edit `~/.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "ami-web": {
      "type": "stdio",
      "command": "python",
      "args": ["backend/mcp/browser/mcp_stdio_server.py"],
      "cwd": "/path/to/AMI-WEB",
      "env": {
        "PYTHONPATH": "/path/to/AMI-WEB"
      }
    }
  }
}
```

### Method 2: Project-Specific Configuration

For project-specific setup, create `.claude/settings.local.json` in your project directory:

```json
{
  "mcpServers": {
    "ami-web": {
      "command": "python",
      "args": ["/absolute/path/to/AMI-WEB/backend/mcp/browser/mcp_stdio_server.py"]
    }
  }
}
```

### Method 3: Using CLI Wizard

```bash
# Interactive setup
claude mcp add ami-web

# When prompted:
# Command: python
# Arguments: /path/to/AMI-WEB/backend/mcp/browser/mcp_stdio_server.py
```

### Windows-Specific Configuration

On Windows (not WSL), you may need to use the cmd wrapper:

```json
{
  "mcpServers": {
    "ami-web": {
      "command": "cmd",
      "args": ["/c", "python", "C:\\path\\to\\AMI-WEB\\backend\\mcp\\mcp_stdio_server.py"]
    }
  }
}
```

### Verifying Connection

After configuration:
1. Restart Claude Code or reload the project
2. Type `/tools` to see available browser tools
3. Type `/mcp` to check server connection status

## Google Gemini CLI Integration

Gemini CLI supports both local and remote MCP servers.

### Step 1: Configure Settings

Edit `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "ami-web": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/AMI-WEB/backend/mcp/browser/mcp_stdio_server.py"],
      "trust": false,
      "env": {
        "PYTHONPATH": "/path/to/AMI-WEB"
      }
    }
  }
}
```

**Note**: Set `"trust": true` only for servers you completely control, as it bypasses confirmation dialogs.

### Step 2: Verify Connection

```bash
# List configured MCP servers
gemini /mcp

# Show available tools
gemini /tools
```

### Using Browser Tools in Gemini

```bash
# Example: Navigate to a website
gemini "Launch a browser and go to example.com"

# Example: Extract content
gemini "Get the main content from the current page"
```

## Available Browser Tools

AMI-WEB exposes 40+ browser automation tools through MCP:

### Core Browser Control
- `browser_launch` - Start a new browser instance (with anti-detection)
- `browser_close` - Close browser instance
- `browser_navigate` - Navigate to URL
- `browser_back/forward/refresh` - Navigation controls

### Interaction Tools
- `browser_click` - Click elements
- `browser_type` - Type text with human-like timing
- `browser_scroll` - Smooth scrolling
- `browser_wait_for_element` - Wait for elements

### Content Extraction
- `browser_get_html` - Get HTML (token-limited for LLMs)
- `browser_extract_text` - Extract readable text
- `browser_extract_links` - Get all links
- `browser_screenshot` - Capture screenshots
- `browser_execute_script` - Run JavaScript

### Storage Management
- `browser_get/set_local_storage` - LocalStorage access
- `browser_get/set_session_storage` - SessionStorage access
- `browser_get/set_cookies` - Cookie management

### Debugging Tools
- `browser_get_console_logs` - Console output
- `browser_get_network_logs` - Network activity
- `browser_get_performance_metrics` - Performance data

## Usage Examples

### Claude Desktop Example

After setup, you can ask Claude:

> "Launch a browser, go to example.com, and extract the main heading"

Claude will:
1. Use `browser_launch` to start a browser
2. Use `browser_navigate` to go to the site
3. Use `browser_extract_text` or `browser_execute_script` to get the heading

### Claude Code Example

```bash
# Interactive browser automation
claude "I need to test the login flow on my website localhost:3000"

# Claude will use the browser tools to:
# 1. Launch browser
# 2. Navigate to localhost:3000
# 3. Find and fill login form
# 4. Submit and verify success
```

### Gemini CLI Example

```bash
# Web scraping with anti-detection
gemini "Extract product prices from this e-commerce site that blocks bots"

# Gemini will leverage AMI-WEB's anti-detection features
```

## Troubleshooting

### Common Issues

#### 1. Server Not Connecting

- **Check path**: Ensure the path to `backend/mcp/browser/run_stdio.py` is absolute
- **Python path**: Verify Python is in your system PATH
- **Permissions**: Ensure the script has execute permissions
- **Logs**: Check Claude/Gemini logs for error messages

#### 2. Tools Not Showing

- **Restart required**: Always restart the AI client after config changes
- **Config syntax**: Validate JSON syntax in configuration files
- **Server running**: Test the server standalone: `python scripts/start_mcp_server.py`

#### 3. Windows-Specific Issues

- Use forward slashes or escaped backslashes in paths
- Try the `cmd /c` wrapper if direct Python execution fails
- Run as administrator if encountering permission issues

### Debug Mode

Enable verbose logging by setting environment variable:

```json
{
  "mcpServers": {
    "ami-web": {
      "command": "python",
      "args": ["backend/mcp/browser/mcp_stdio_server.py"],
      "env": {
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "PYTHONPATH": "/path/to/AMI-WEB"
      }
    }
  }
}
```

## Security Considerations

### Best Practices

1. **Trust Settings**: Never set `"trust": true` for third-party servers
2. **Permissions**: AMI-WEB requests approval for sensitive operations
3. **Credentials**: Never store passwords or API keys in config files
4. **Sandboxing**: Run in isolated environments when possible
5. **Updates**: Keep AMI-WEB updated for security patches

### Data Access

AMI-WEB's MCP server can:
- ✅ Control browser instances
- ✅ Navigate to any URL you approve
- ✅ Execute JavaScript on pages
- ✅ Access cookies and storage
- ❌ Cannot access files outside browser context
- ❌ Cannot execute system commands
- ❌ Cannot access other applications

## Advanced Configuration

### Custom WebSocket Server

For distributed setups or custom integrations, use the WebSocket server:

```bash
# Start WebSocket server with proper environment
python scripts/start_mcp_server.py websocket

# Or specify custom host/port
python scripts/start_mcp_server.py websocket --host 0.0.0.0 --port 8080

# Connect from AI tools using WebSocket URL
ws://localhost:8765  # Default
```

### Environment Variables

Configure behavior through environment variables:

```bash
# Browser configuration
export AMI_HEADLESS=false
export AMI_ANTI_DETECT=true

# Pool configuration
export AMI_MIN_INSTANCES=1
export AMI_MAX_INSTANCES=5

# Logging
export LOG_LEVEL=INFO
```

### Docker Deployment

For containerized deployments (WIP):

```dockerfile
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "backend/mcp/browser/run_stdio.py"]
```

## Support and Resources

- **Documentation**: [AMI-WEB GitHub](https://github.com/Independent-AI-Labs/AMI-WEB)
- **MCP Specification**: [Model Context Protocol](https://modelcontextprotocol.io)
- **Issues**: [Report bugs](https://github.com/Independent-AI-Labs/AMI-WEB/issues)
- **Discord**: Join our community for support

## Contributing

We welcome contributions to improve MCP integration:

1. Test with different AI clients
2. Report compatibility issues
3. Submit documentation improvements
4. Add new browser automation tools

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**💡 Tip**: Start with simple browser automation tasks and gradually explore advanced features like anti-detection and session management.

**⚠️ Remember**: Always respect website terms of service and robots.txt when using browser automation.