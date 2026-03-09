# A-Parser CLI — Windows Setup Guide

**Version:** 2.3  
**Last Updated:** 2026-03-09

---

## 🚀 Quick Start (Windows)

### Option 1: Install from PyPI (Recommended for most users)

```powershell
# 1. Install Python 3.10+ (if not installed)
# Download from: https://python.org/downloads

# 2. Install A-Parser CLI
pip install aparser-cli

# 3. Initialize configuration
aparser init

# 4. Configure
notepad $env:APPDATA\aparser-cli\.env

# Add your A-Parser credentials:
# APARSER_URL=http://localhost:8080
# APARSER_PASSWORD=123

# 5. Test
aparser status
```

---

### Option 2: Standalone EXE (No Python required)

```powershell
# Download latest release
# https://github.com/your-org/aparser-cli/releases/download/v2.3/aparser-cli-windows.exe

# Run directly
.\aparser-cli-windows.exe status
```

---

## 📁 File Locations (Windows)

| Type | Location |
|------|----------|
| **Config** | `%APPDATA%\aparser-cli\.env` |
| **Logs** | `%APPDATA%\aparser-cli\logs\` |
| **Keyring** | Windows Credential Manager |
| **Cache** | `%LOCALAPPDATA%\aparser-cli\cache\` |

To open config folder:
```powershell
explorer $env:APPDATA\aparser-cli
```

---

## 🔧 Configuration

### Environment Variables

Create `%APPDATA%\aparser-cli\.env`:

```env
# A-Parser API
APARSER_URL=http://localhost:8080
APARSER_PASSWORD=123

# Redis (optional)
APARSER_REDIS_HOST=localhost
APARSER_REDIS_PORT=6379
APARSER_REDIS_PASSWORD=your_redis_password

# Logging
APARSER_LOG_LEVEL=INFO
```

### Using Windows Credential Manager

Password is automatically stored in Windows Credential Manager:

```powershell
# Store password (done automatically by `aparser init`)
aparser config set-password

# View stored credentials
cmdkey /list | findstr aparser-cli
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
    "aparser": {
      "command": "aparser-mcp",
      "args": [],
      "env": {
        "APARSER_URL": "http://localhost:8080"
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
      "name": "aparser",
      "command": "aparser-mcp",
      "cwd": "."
    }
  ]
}
```

### Custom Python Agent

```python
# install: pip install mcp
from mcp import ClientSession

async with ClientSession('aparser-mcp') as session:
    # Run parser
    result = await session.call_tool('run_parser', {
        'parser': 'FreeAI::Perplexity',
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
git clone https://github.com/your-org/aparser-cli
cd aparser-cli

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
pyinstaller --onefile --name aparser src\aparser_cli\main.py
pyinstaller --onefile --name aparser-mcp src\aparser_cli\mcp\server.py

# Output: dist\aparser.exe, dist\aparser-mcp.exe
```

### Run Tests

```powershell
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=aparser_cli --cov-report=html
```

---

## 🐛 Troubleshooting

### Issue: "aparser: command not found"

**Solution:**
```powershell
# Add Python Scripts to PATH
$env:Path += ";$env:USERPROFILE\AppData\Roaming\Python\Python311\Scripts"

# Or reinstall
pip install --force-reinstall aparser-cli
```

### Issue: Config file not found

**Solution:**
```powershell
# Create config directory
New-Item -ItemType Directory -Force -Path $env:APPDATA\aparser-cli

# Create .env file
@"
APARSER_URL=http://localhost:8080
APARSER_PASSWORD=123
"@ | Out-File -FilePath $env:APPDATA\aparser-cli\.env -Encoding utf8
```

### Issue: Keyring not working on Windows

**Solution:**
```powershell
# Install Windows-specific keyring backend
pip install keyring-winvault

# Or use environment variable instead
$env:APARSER_PASSWORD = "123"
```

### Issue: MCP server not found by agent

**Solution:**
```powershell
# Check if MCP is installed
where aparser-mcp

# If not found, install MCP extras
pip install "aparser-cli[mcp]"

# Verify MCP server
aparser-mcp --help
```

---

## 📊 Comparison: Windows vs Linux

| Feature | Windows | Linux |
|---------|---------|-------|
| **Config Path** | `%APPDATA%\aparser-cli\` | `~/.config/aparser-cli/` |
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
