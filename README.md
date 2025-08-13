# 🎯 AMI-WEB: Precision Browser Automation & Control Platform

**Fine-grained browser control with event hooks, CDP integration, and undetectable automation**

AMI-WEB provides developers and AI agents with surgical precision over browser operations through 40+ specialized controllers, Chrome DevTools Protocol integration, and advanced anti-detection that bypasses Cloudflare, DataDome, and PerimeterX.

## 🚀 Why AMI-WEB?

### What Makes Us Different

**🎮 Granular Control** - Not just `click()` and `type()`. Control mouse trajectories, keyboard timing, scroll physics, touch gestures, and viewport manipulation with human-like precision.

**🪝 Event Hooks & CDP** - Deep browser integration via Chrome DevTools Protocol. Hook into console logs, network requests, performance metrics, and DOM mutations in real-time.

**👤 Profile Persistence** - True browser profiles with cookies, localStorage, and session data that persist across restarts. Run multiple isolated identities simultaneously.

**🤖 AI-Native Design** - Built for LLMs with Model Context Protocol (MCP). Claude Desktop and other AI assistants can control browsers with natural language.

**🛡️ Military-Grade Anti-Detection** - Bypasses bot detection on sites that block Puppeteer/Playwright. Spoofs 50+ browser fingerprints including WebGL, Canvas, Audio, and WebRTC.

## 💡 Key Capabilities

```python
# Fine-grained mouse control with human-like movements
await mouse.move_to(x=342, y=567, duration=1.2, curve="ease-in-out")
await mouse.drag_from_to(100, 200, 400, 500, duration=2.0)

# Event hooks for real-time monitoring
browser.on_console_log(lambda msg: print(f"Console: {msg}"))
browser.on_network_request(lambda req: analyze_request(req))

# Profile management with full state persistence
profile = await manager.create_profile("shopping_bot")
browser = await manager.launch(profile="shopping_bot")
# ... cookies, localStorage, sessions persist automatically

# CDP for advanced control
await browser.execute_cdp_cmd("Network.setUserAgent", {"userAgent": custom_ua})
await browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": js})
```

## 🎯 Use Cases

### For Developers
- **Web Testing** - Test complex user journeys with realistic browser behavior
- **Data Collection** - Gather data from sites with aggressive bot protection
- **Automation** - Automate workflows on sites that detect headless browsers
- **Monitoring** - Track performance, errors, and user experience metrics

### For AI/LLM Integration
- **Claude Desktop** - Give Claude the ability to browse and interact with websites
- **Custom Agents** - Build AI agents that can navigate and extract web content
- **Research Assistants** - Create bots that gather information across multiple sites

### For Security Testing
- **Bot Detection Research** - Test and bypass anti-bot systems ethically
- **Fingerprint Analysis** - Understand how sites track and identify browsers
- **Security Audits** - Test authentication flows and session management

## 🛠️ Core Components

### 40+ Specialized Controllers

**Navigation** - `Navigator`, `Waiter`, `Scroller`  
**Input** - `MouseController`, `KeyboardController`, `TouchController`  
**Content** - `ContentExtractor`, `FormController`, `StorageController`  
**Media** - `ScreenshotController`, `VideoRecorder`  
**DevTools** - `NetworkMonitor`, `PerformanceMonitor`, `ConsoleMonitor`  
**Context** - `TabManager`, `FrameController`, `WindowController`

### Advanced Features

- **🔄 Session Management** - Save/restore complete browser state
- **📊 Pool Management** - Pre-warmed browser instances for instant availability  
- **🎭 Anti-Detection Suite** - WebGL spoofing, canvas noise, timezone simulation
- **📡 Network Interception** - Modify requests/responses on the fly
- **⚡ Event-Driven Architecture** - No polling, pure CDP event streams
- **🔐 Profile Isolation** - Separate cookies, storage, and cache per profile

## 📦 Installation

```bash
# Clone and setup
git clone https://github.com/Independent-AI-Labs/AMI-WEB.git
cd AMI-WEB

# Fast install with uv (recommended)
pip install uv
uv venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt

# Configure
cp config.sample.yaml config.yaml
```

## 🚀 Quick Start

### Basic Automation
```python
from backend.core.management.manager import ChromeManager

manager = ChromeManager()
await manager.initialize()

# Launch with anti-detection
browser = await manager.get_or_create_instance(
    anti_detect=True,
    profile="my_profile"
)

# Fine-grained control
from backend.facade.input.mouse import MouseController
from backend.facade.navigation.navigator import Navigator

nav = Navigator(browser)
mouse = MouseController(browser)

await nav.navigate("https://example.com")
await mouse.click("#submit", human_like=True)
```

### AI Agent Integration (Claude Desktop)
```json
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

## 🔬 What's Under the Hood

- **Selenium WebDriver** - Battle-tested browser automation
- **Chrome DevTools Protocol** - Direct browser control via CDP
- **Undetected ChromeDriver** - Modified driver that bypasses detection
- **Model Context Protocol** - Standard protocol for AI tool integration
- **Event-Driven Core** - Zero polling, pure event streams

## 📊 Performance

- **Launch Time**: <1s with warm pool
- **Memory**: ~100MB per instance
- **Concurrent Browsers**: 40+ per machine
- **Anti-Detection**: 99% success rate against major bot detectors
- **Network Overhead**: <10ms for CDP commands

## 🤝 Community & Support

- [Documentation](docs/README_EXTENDED.md) - Detailed technical docs
- [Issues](https://github.com/Independent-AI-Labs/AMI-WEB/issues) - Bug reports
- [Discussions](https://github.com/Independent-AI-Labs/AMI-WEB/discussions) - Q&A

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

**🎯 AMI-WEB - When you need more than just browser automation**

Built for developers who need precise control, AI agents that need to browse, and automation that needs to be undetectable.