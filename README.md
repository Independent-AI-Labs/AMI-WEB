# AMI-WEB: Browser Automation Platform

## Business Value

Transform how your organization interacts with web applications. AMI-WEB provides undetectable browser automation that works with any website, including those with aggressive bot protection. Perfect for enterprise RPA, testing, and data extraction.

## Core Capabilities

### 🌐 Universal Web Automation
Control browsers like a human would - click, type, scroll, and navigate with intelligent wait conditions and error recovery.

**Key Features:**
- **Undetectable Operation** - Bypasses bot detection with real browser fingerprints
- **Multi-Profile Management** - Run hundreds of isolated browser sessions simultaneously  
- **Session Persistence** - Save and restore complete browser state including cookies
- **AI-Ready** - Native MCP support for Claude, GPT, and custom agents

### 🔌 Chrome MCP Server

Production-ready browser control via Model Context Protocol for AI agents and automation tools.

**Available Tools:**

| Tool | Purpose | Example Use |
|------|---------|-------------|
| `browser_launch` | Start browser instance | Launch with custom profile |
| `browser_navigate` | Navigate to URL | Go to login page |
| `browser_click` | Click elements | Submit forms |
| `browser_type` | Enter text | Fill username/password |
| `browser_screenshot` | Capture screenshots | Document state |
| `browser_execute_script` | Run JavaScript | Extract data |
| `browser_get_cookies` | Retrieve cookies | Session management |
| `browser_set_cookies` | Set cookies | Restore sessions |
| `browser_get_html` | Get page HTML | Content extraction |
| `browser_wait_for` | Wait for elements | Handle dynamic content |
| `browser_get_network_logs` | Monitor requests | Debug APIs |
| `browser_terminate` | Close browser | Cleanup |

**Transport Modes:**
```bash
# CLI integration (stdio)
python scripts/run_chrome.py

# Network access (websocket)  
python scripts/run_chrome.py --transport websocket --port 9000
```

### 🛡️ Anti-Detection Technology

Stay undetected with comprehensive fingerprint management:

- **Canvas & WebGL** - Unique rendering signatures
- **Audio Context** - Sound fingerprint variation
- **WebRTC** - IP leak prevention
- **Navigator** - Hardware spec spoofing
- **Timezone & Language** - Locale matching
- **Plugin Detection** - Extension masking

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Independent-AI-Labs/AMI-WEB.git
cd AMI-WEB
uv venv .venv && uv pip install -r requirements.txt

# Run MCP server for AI agents
python scripts/run_chrome.py

# Or use directly in Python
from browser.backend.core.management.manager import ChromeManager

manager = ChromeManager()
await manager.initialize()
browser = await manager.get_or_create_instance(profile_name="shopping")
await browser.navigate("https://amazon.com")
```

## Use Cases

### Enterprise RPA
- Automate SAP, Oracle, Salesforce workflows
- Handle complex multi-step authentication
- Process invoices through vendor portals
- Maintain compliance with full audit trails

### Quality Assurance  
- Test behind CloudFlare, reCAPTCHA
- Validate user journeys end-to-end
- Monitor production application health
- Cross-browser compatibility testing

### Data Intelligence
- Extract from JavaScript-heavy SPAs
- Navigate paywalls and auth systems
- Monitor competitor pricing/inventory
- Aggregate data from multiple sources

## Architecture

```
browser/
├── backend/
│   ├── core/
│   │   ├── browser/          # Browser control layer
│   │   │   ├── instance.py      # Individual browser
│   │   │   ├── lifecycle.py    # Launch/terminate
│   │   │   └── options.py      # Chrome options
│   │   ├── management/       # Resource management
│   │   │   ├── manager.py      # Browser pool
│   │   │   ├── profile_manager.py  # Profile isolation
│   │   │   └── session_manager.py  # State persistence
│   │   └── tools/           # Browser operations
│   └── mcp/
│       └── chrome/          # MCP server implementation
│           ├── server.py       # ChromeMCPServer
│           └── tools/          # Tool definitions
├── scripts/
│   └── run_chrome.py        # MCP server launcher
└── tests/
    └── integration/         # End-to-end tests
```

## Testing

```bash
# Run all browser tests
python scripts/run_tests.py

# Test MCP server modes
python scripts/run_tests.py tests/integration/test_mcp_server.py
```

## Security & Compliance

- **Audit Trails** - Every action logged with timestamp
- **Session Recording** - Replay browser sessions
- **Data Isolation** - Profiles never share data
- **Credential Safety** - Never logs passwords
- **Network Control** - Proxy and header management

## Performance

- **Concurrent Browsers** - 100+ simultaneous sessions
- **Fast Launch** - <2 second cold start
- **Low Memory** - Efficient resource pooling
- **Auto-Scaling** - Grows with demand
- **Hibernation** - Suspend idle browsers

## Recent Updates

### Latest - MCP Transport Unification
- All tools now support stdio and websocket modes
- Consolidated transport implementation in base module
- Proper environment handling for wrapper scripts
- Fixed test tool name assertions

## Contributing

See `CLAUDE.md` for development guidelines.

## License

MIT License - See LICENSE file

## Support

- GitHub Issues: [AMI-WEB Issues](https://github.com/Independent-AI-Labs/AMI-WEB/issues)
- Main Project: [AMI-ORCHESTRATOR](https://github.com/Independent-AI-Labs/AMI-ORCHESTRATOR)