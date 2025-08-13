# 🛡️ AMI-WEB: Enterprise Browser Automation Platform

**Complete control over every browser parameter with undetectable automation for enterprise applications**

![](res/notbot.png)

AMI-WEB provides organizations with comprehensive browser automation that offers full control over WebGL, Canvas, Audio, WebRTC, and all browser fingerprinting parameters. Built for enterprises requiring compliant web automation, security testing, and AI-powered browser interactions.

## 🎯 Key Differentiators

### Enterprise-Grade Capabilities

**🔐 Complete Browser Control** - Full manipulation of every browser parameter including user agents, fingerprints, viewport settings, timezone, language, plugins, and hardware specifications.

**🏢 Multi-Profile Management** - Create, manage, and isolate browser profiles with persistent cookies, localStorage, and session data. Run multiple identities simultaneously with complete isolation.

**📊 Real-Time Monitoring** - Hook into console logs, network requests, performance metrics, and browser events through Chrome DevTools Protocol integration.

**🤖 AI-Native Architecture** - Native Model Context Protocol (MCP) support enables Claude, GPT, and custom AI agents to control browsers through natural language.

**✅ Compliance & Auditability** - Full activity logging, session recording, and audit trails for regulatory compliance and security reviews.

## 💼 Enterprise Use Cases

### Business Process Automation
- Automate complex workflows on legacy web applications
- Handle multi-step authentication flows with MFA support
- Process invoices, orders, and documents through web portals
- Maintain session state across long-running operations

### Quality Assurance & Testing
- Test applications behind aggressive bot protection
- Validate user journeys with realistic browser behavior
- Monitor performance metrics and error rates
- Cross-browser compatibility testing with profile management

### Data Intelligence
- Extract data from JavaScript-heavy applications
- Navigate complex authentication systems
- Handle CAPTCHAs and anti-bot challenges
- Maintain persistent sessions for continuous monitoring

### Security & Compliance
- Penetration testing with full browser control
- Audit authentication and session management
- Test against bot detection systems
- Compliance monitoring and reporting

## 🛠️ Comprehensive Toolset

### Browser Lifecycle Management
- Launch instances with custom profiles
- Terminate and manage browser pools
- Anti-detection mode with fingerprint control
- Headless and headed operation modes

### Navigation & Interaction
- Navigate with intelligent wait conditions
- Execute custom JavaScript in page context
- Handle popups, alerts, and new windows
- Manage browser history and refresh cycles

### Content Extraction & Analysis
- Extract text, HTML, and structured data
- Identify and interact with forms
- Harvest links with URL normalization
- Screenshot capture (viewport, full-page, element)

### Session & State Management
- Save and restore complete browser sessions
- Cookie management with domain isolation
- localStorage and sessionStorage control
- Profile persistence across restarts

### Monitoring & Debugging
- Real-time console log streaming
- Network request/response monitoring
- Performance metrics collection
- Error tracking and alerting

### Input Simulation
- Human-like typing with configurable delays
- Mouse movements with trajectory control
- Scroll physics and touch gestures
- Dropdown and form field interaction

## 🏗️ Architecture & Integration

### Technology Stack
- **Selenium WebDriver** - Industry-standard browser automation
- **Chrome DevTools Protocol** - Deep browser integration
- **Model Context Protocol** - AI agent communication standard
- **Event-Driven Core** - Reactive architecture with no polling

### Integration Options
```python
# Python SDK
from backend.core.management.manager import ChromeManager

manager = ChromeManager()
await manager.initialize()

# Launch with full control
browser = await manager.get_or_create_instance(
    profile="production_profile",
    anti_detect=True
)
```

```json
// AI Agent Configuration (Claude Desktop)
{
  "mcpServers": {
    "ami-web": {
      "command": "python",
      "args": ["scripts/start_mcp_server.py"],
      "cwd": "/path/to/AMI-WEB"
    }
  }
}
```

## 🚀 Running

### Docker
Coming soon

### Local MCP Server
Simply run:
```bash
python scripts/start_mcp_server.py
```

The script automatically handles:
- Virtual environment creation
- Dependency installation
- Server startup

For detailed setup instructions, see [Extended Documentation](docs/README_EXTENDED.md#installation--setup).

## 🔒 Security & Compliance

- **Isolated Profiles** - Complete separation between browser instances
- **Audit Logging** - Comprehensive activity tracking
- **Credential Management** - Secure storage of authentication data
- **Network Control** - Request/response modification capabilities
- **Compliance Ready** - Built for regulated industries

## 📚 Documentation

- [Technical Documentation](docs/README_EXTENDED.md) - Complete API reference
- [Architecture Guide](docs/ARCHITECTURE.md) - System design and patterns
- [MCP Integration](docs/MCP.md) - (WIP) AI agent setup guide
- [Contributing](CONTRIBUTING.md) - Development guidelines

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

**AMI-WEB - Enterprise Browser Automation with Complete Control**

Built for organizations that need reliable, compliant, and undetectable browser automation at scale.

[Get Started](https://github.com/Independent-AI-Labs/AMI-WEB) | [Extended Readme](docs/README_EXTENDED.md) | [Support](https://github.com/Independent-AI-Labs/AMI-WEB/issues)