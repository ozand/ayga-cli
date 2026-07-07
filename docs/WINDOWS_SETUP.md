# ayga-cli — Windows Setup Guide

**Version:** 2.3
**Last Updated:** 2026-03-09

---

## 🚀 Quick Start (Windows)

### Option 1: Install from PyPI (Recommended for most users)

```powershell
# 1. Install Python 3.10+ (if not installed)
# Download from: https://python.org/downloads

# 2. Install ayga-cli
pip install ayga-cli

# 3. Initialize configuration
ayga_parser init

# 4. Configure
notepad $env:APPDATA\ayga-cli\.env

# Add your backend connection details:
# AYGA_HTTP_URL=http://127.0.0.1:9091/API
# AYGA_PASSWORD=123

# 5. Test
ayga_parser status
```

---

### Option 2: Standalone EXE (No Python required)

```powershell
# Download latest release
# https://github.com/ozand/ayga-cli/releases/latest

# Run directly
.\ayga-cli-windows.exe status
```

---

## 📁 File Locations (Windows)

| Type | Location |
|------|----------|
| **Config** | `%APPDATA%\ayga-cli\.env` |
| **Logs** | `%APPDATA%\ayga-cli\logs\` |
| **Keyring** | Windows Credential Manager |
| **Cache** | `%LOCALAPPDATA%\ayga-cli\cache\` |

To open config folder:
```powershell
explorer $env:APPDATA\ayga-cli
```

---

## 🔧 Configuration

### Environment Variables

Create `%APPDATA%\ayga-cli\.env`:

```env
# Backend connection
AYGA_HTTP_URL=http://127.0.0.1:9091/API
AYGA_PASSWORD=123

# Redis (optional)
AYGA_REDIS_HOST=localhost
AYGA_REDIS_PORT=6379
AYGA_REDIS_PASSWORD=your_redis_password

# Logging
AYGA_LOG_LEVEL=INFO
```

### Using Windows Credential Manager

Password is automatically stored in Windows Credential Manager:

```powershell
# Store password (done automatically by `ayga_parser init`)
ayga_parser config set-password

# View stored credentials
cmdkey /list | findstr ayga-cli
```

---

## 🤖 MCP Integration (Windows Agents)

### Claude Code

```powershell
# Edit Claude settings
notepad $env:APPDATA\Claude\settings.json
```

Add MCP server:
```json
{
  "mcpServers": {
    "ayga-cli": {
      "command": "ayga_parser-mcp",
      "args": [],
      "env": {
        "AYGA_HTTP_URL": "http://127.0.0.1:9091/API"
      }
    }
  }
}
```

### Cursor

```powershell
# Edit Cursor MCP config
notepad .cursor\mcp.json
```

Add:
```json
{
  "servers": [
    {
      "name": "ayga-cli",
      "command": "ayga_parser-mcp",
      "cwd": "."
    }
  ]
}
```

### Custom Python Agent

```python
# install: pip install mcp
from mcp import ClientSession

async with ClientSession('ayga_parser-mcp') as session:
    # Fetch data from a source
    result = await session.call_tool('get', {
        'source': 'web-search',
        'query': 'OpenClaw competitors'
    })

    print(result.content)
```

---

## 🛠️ Development Setup (Windows)

### Prerequisites

```powershell
# 1. Install Python 3.10+
# https://python.org/downloads

# 2. Install Git
# https://git-scm.com/download/win

# 3. Clone repository
git clone https://github.com/ozand/ayga-cli.git
cd ayga-cli

# 4. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 5. Install in development mode
pip install -e ".[dev,mcp]"
```

### Build Standalone EXE

```powershell
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller --onefile --name ayga_parser src\ayga_cli\main.py
pyinstaller --onefile --name ayga_parser-mcp src\ayga_cli\mcp\server.py

# Output: dist\ayga_parser.exe, dist\ayga_parser-mcp.exe
```

### Run Tests

```powershell
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=ayga_cli --cov-report=html
```

---

## 🐛 Troubleshooting

### Issue: "ayga_parser: command not found"

**Solution:**
```powershell
# Add Python Scripts to PATH
$env:Path += ";$env:USERPROFILE\AppData\Roaming\Python\Python311\Scripts"

# Or reinstall
pip install --force-reinstall ayga-cli
```

### Issue: Config file not found

**Solution:**
```powershell
# Create config directory
New-Item -ItemType Directory -Force -Path $env:APPDATA\ayga-cli

# Create .env file
@"
AYGA_HTTP_URL=http://127.0.0.1:9091/API
AYGA_PASSWORD=123
"@ | Out-File -FilePath $env:APPDATA\ayga-cli\.env -Encoding utf8
```

### Issue: Keyring not working on Windows

**Solution:**
```powershell
# Install Windows-specific keyring backend
pip install keyring-winvault

# Or use environment variable instead
$env:AYGA_PASSWORD = "123"
```

### Issue: MCP server not found by agent

**Solution:**
```powershell
# Check if MCP is installed
where ayga_parser-mcp

# If not found, install MCP extras
pip install "ayga-cli[mcp]"

# Verify MCP server
ayga_parser-mcp --help
```

---

## 📊 Comparison: Windows vs Linux

| Feature | Windows | Linux |
|---------|---------|-------|
| **Config Path** | `%APPDATA%\ayga-cli\` | `~/.config/ayga-cli/` |
| **Keyring** | Windows Credential Manager | SecretService/KWallet |
| **Shell** | PowerShell / CMD | Bash / Zsh |
| **Path Separator** | `\` | `/` |
| **EXE Support** | ✅ Native | ❌ Requires Wine |

---

## 🎯 Next Steps

1. ✅ **Configuration** — Cross-platform paths implemented
2. ⏳ **MCP Server** — Test on Windows
3. ⏳ **PyPI Publication** — Publish package
4. ⏳ **PyInstaller Build** — Create .exe
5. ⏳ **Documentation** — Complete Windows guide

---

**Support:** Open issue on GitHub or contact @gubin
