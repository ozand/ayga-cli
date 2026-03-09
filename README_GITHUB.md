# A-Parser CLI v2.3

**Google API Pool & Parser Management Tool**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](INSTALL_WINDOWS.md)

---

## 🎯 Описание

A-Parser CLI — кросс-платформенный инструмент для управления Google API с автоматической ротацией аккаунтов.

**Возможности:**
- ✅ **Google API Pool** — управление 50+ аккаунтами
- ✅ **Автоматическая ротация** — round-robin + circuit breaker
- ✅ **Безопасное хранение** — AES-256-GCM шифрование
- ✅ **MCP Server** — интеграция с AI агентами (Claude Code, Cursor)
- ✅ **Кросс-платформенность** — Windows, macOS, Linux

---

## 🚀 Быстрый старт

### Windows (PowerShell)

```powershell
# 1. Скачать установочный скрипт
$githubToken = "ghp_YOUR_GITHUB_TOKEN"
$rawUrl = "https://raw.githubusercontent.com/ozand/aparser-cli/main/scripts/install.ps1"
$headers = @{ Authorization = "token $githubToken" }
Invoke-RestMethod -Uri $rawUrl -Headers $headers -OutFile "$env:TEMP\install.ps1"

# 2. Запустить установку
& "$env:TEMP\install.ps1"

# 3. Проверить
aparser --version
```

### macOS / Linux

```bash
# 1. Клонировать репозиторий
git clone https://github.com/ozand/aparser-cli.git
cd aparser-cli

# 2. Установить
pip install -e .

# 3. Проверить
aparser --version
```

---

## 📋 Документация

| Документ | Описание |
|----------|----------|
| [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) | Полная инструкция по установке на Windows |
| [docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md) | Windows Setup Guide |
| [docs/PRD-v2.1.md](docs/PRD-v2.1.md) | Product Requirements |
| [docs/BACKLOG-v2.2.md](docs/BACKLOG-v2.2.md) | Roadmap & Backlog |

---

## 🔧 Использование

### CLI Commands

```bash
# Инициализация
aparser init

# Добавить API ключ
aparser keys-add google_001 gemini AIzaSy...

# Список ключей
aparser keys-list

# Поиск через Gemini
aparser search "OpenClaw competitors"

# Поиск компаний (Places API)
aparser business "Yandex" --location "Moscow"

# Геокодирование
aparser geocode "Red Square, Moscow"

# Статистика пула
aparser stats
```

### MCP Server (для агентов)

```bash
# Запустить MCP server
aparser-mcp

# Интеграция с Claude Code
# ~/.claude/settings.json:
{
  "mcpServers": {
    "aparser": {
      "command": "aparser-mcp"
    }
  }
}
```

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────┐
│           A-Parser CLI                  │
├─────────────────────────────────────────┤
│  CLI (Typer)                            │
│  ├── init, keys-add/list                │
│  ├── search, business, geocode          │
│  └── stats                              │
├─────────────────────────────────────────┤
│  Token Pool Manager (AES-256-GCM)       │
├─────────────────────────────────────────┤
│  Pool Core (Rotation + Circuit Breaker) │
├─────────────────────────────────────────┤
│  API Clients                            │
│  ├── Gemini (with Search Grounding)     │
│  ├── Places API                         │
│  └── Geocoding API                      │
├─────────────────────────────────────────┤
│  MCP Server                             │
└─────────────────────────────────────────┘
```

---

## 🔐 Безопасность

- **AES-256-GCM** шифрование всех API ключей
- **OS Keyring** для хранения мастер-ключа
  - Windows: Windows Credential Manager
  - macOS: Keychain
  - Linux: SecretService/KWallet
- **Никаких ключей в коде** — только через env/keyring

---

## 📦 Зависимости

```toml
[project]
dependencies = [
    "typer>=0.12.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.27.0",
    "redis>=5.0.0",
    "rich>=13.0.0",
    "keyring>=25.0.0",
    "cryptography>=41.0.0",
]
```

---

## 🧪 Разработка

```bash
# Клонировать
git clone https://github.com/ozand/aparser-cli.git
cd aparser-cli

# Создать venv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Установить dev зависимости
pip install -e ".[dev,mcp]"

# Запустить тесты
pytest

# Запустить линтеры
ruff check src/
mypy src/
```

---

## 📊 Metrics

| Metric | Value |
|--------|-------|
| **API Keys** | 2 unique keys |
| **Accounts Pooled** | 35 Google accounts |
| **Daily Capacity** | 35K-52K queries |
| **Encryption** | AES-256-GCM |
| **Profiles Available** | 42 Camoufox profiles |
| **Test Coverage** | 20+ tests |

---

## 🎯 Следующие шаги

- [ ] PyPI публикация (публично или privately)
- [ ] PyInstaller EXE builds для Windows
- [ ] Docker container для серверов
- [ ] GitHub Actions CI/CD

---

## 📞 Поддержка

- **Issues:** https://github.com/ozand/aparser-cli/issues
- **Discussions:** https://github.com/ozand/aparser-cli/discussions
- **Contact:** @ozand (Telegram)

---

## 📝 License

MIT License — см. [LICENSE](LICENSE)

---

**Version:** 2.3  
**Last Updated:** 2026-03-09  
**Author:** Gubin 🤖
