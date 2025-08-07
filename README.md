# Chrome Manager - Enterprise Headless Chrome Instance Manager

A Python-based enterprise-grade headless Chrome instance manager with Model Context Protocol (MCP) support for AI agents.

## Features

- **Browser Lifecycle Management**: Complete control over Chrome/Chromium processes
- **WebDriver Abstraction**: High-level API over Selenium WebDriver
- **MCP Server**: Native support for AI agent integration
- **Media Capture**: Screenshots and video recording capabilities
- **Extension Management**: Install and configure Chrome extensions
- **DevTools Integration**: Access to Chrome DevTools Protocol

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start MCP server
python -m chrome_manager.mcp_server

# Or use as library
from chrome_manager import ChromeManager

async def main():
    manager = ChromeManager()
    browser = await manager.create_instance()
    await browser.navigate("https://example.com")
    screenshot = await browser.screenshot()
    await browser.terminate()
```

## Architecture

The system is built with a modular architecture:
- MCP Server Layer for AI agent integration
- Chrome Manager Core for instance lifecycle
- WebDriver Facade for simplified browser control
- Extension Services for advanced features

## Documentation

See the [Technical Specification](chrome_manager_tech_spec.md) for detailed documentation.

## License

MIT License