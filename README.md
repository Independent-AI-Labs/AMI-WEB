# AMI-WEB: Compliant Browser Automation Platform

## Business Value

AMI-WEB enables enterprises to automate web interactions while maintaining complete compliance with data protection regulations. Every browser action is auditable, sandboxed, and traceable, ensuring your automation meets EU AI Act transparency requirements and GDPR data handling standards.

## Core Capabilities

### 🌐 Auditable Web Automation
Every browser interaction is logged, sandboxed, and compliant with enterprise security requirements.

**Compliance Features:**
- **Complete Audit Trail** - Every click, type, and navigation logged with timestamps
- **Profile Isolation** - Sandboxed sessions prevent data leakage between automations
- **Session Recording** - Full replay capability for compliance reviews and audits
- **AI Transparency** - MCP protocol ensures explainable automation decisions

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

### 🛡️ Privacy-Preserving Automation

Maintain data sovereignty while automating web interactions:

- **Data Localization** - All browser data stays on your infrastructure
- **Cookie Isolation** - Separate cookie stores per profile
- **Network Control** - Route traffic through your proxies
- **Credential Security** - Never logs passwords or sensitive data
- **GDPR Compliance** - Respect consent banners and privacy settings
- **Session Encryption** - All stored sessions encrypted at rest

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

### Compliant Enterprise Automation
- **Regulatory Reporting** - Automate submissions with full audit trails
- **Vendor Portal Management** - Process invoices with compliance tracking
- **HR System Integration** - Automate workflows with data protection
- **Compliance Monitoring** - Track website changes for regulatory updates

### Secure Testing & Validation
- **GDPR Testing** - Validate consent flows and data handling
- **Security Testing** - Sandboxed penetration testing
- **Compliance Validation** - Verify regulatory requirements
- **Audit Trail Generation** - Document testing for compliance

### Privacy-Preserving Data Collection
- **Consent-Aware Scraping** - Respect user privacy settings
- **Data Minimization** - Collect only necessary information
- **Purpose Limitation** - Track data usage and retention
- **Right to Erasure** - Support GDPR deletion requirements

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