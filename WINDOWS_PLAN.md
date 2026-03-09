# A-Parser CLI v2.3 — Windows Cross-Platform Plan

**Date:** 2026-03-09  
**Target:** Windows 10/11 + Linux + macOS  
**Goal:** Агенты на Windows могут использовать aparser-cli через MCP или CLI

---

## 📊 Текущая архитектура

```
aparser-cli/
├── src/aparser_cli/
│   ├── main.py              # Typer CLI entry point
│   ├── config.py            # Pydantic settings
│   ├── manifest.py          # Dynamic parser discovery
│   ├── commands/            # CLI commands (run, test, etc.)
│   ├── client/              # A-Parser API client
│   ├── mcp/                 # MCP server
│   └── utils/               # Helpers
├── pyproject.toml           # Build config
└── .env                     # Config (APARSER_URL, APARSER_PASSWORD)
```

**Зависимости:**
- ✅ typer, pydantic, httpx, redis, rich — кросс-платформенные
- ✅ keyring — работает на Windows (Credential Manager)
- ⚠️ MCP — кросс-платформенный

---

## 🎯 Проблемы для Windows

### 1. **Конфигурация**
❌ `.env` в корне проекта — неудобно для пользователей  
❌ Нет дефолтного конфига для Windows

**Решение:**
```python
# config.py
from pathlib import Path

def get_config_dir():
    if sys.platform == 'win32':
        # Windows: %APPDATA%\aparser-cli
        return Path.home() / 'AppData' / 'Roaming' / 'aparser-cli'
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Application Support
        return Path.home() / 'Library' / 'Application Support' / 'aparser-cli'
    else:
        # Linux: ~/.config/aparser-cli
        return Path.home() / '.config' / 'aparser-cli'
```

### 2. **Keyring на Windows**
❌ Может требовать дополнительной настройки

**Решение:**
```python
# Использовать Windows Credential Manager автоматически
import keyring
keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())
```

### 3. **MCP Server на Windows**
❌ Пути в Windows используют `\` вместо `/`

**Решение:**
```python
from pathlib import Path
# Всегда использовать Path для кросс-платформенности
config_path = get_config_dir() / 'config.json'
```

### 4. **Установка на Windows**
❌ Пользователи не знакомы с `pip install -e .`

**Решение:**
- Создать `.msi` инсталлятор или `.exe` через `PyInstaller`
- Или документировать простую установку через `pip`

---

## 🏗 Архитектура v2.3

### Вариант 1: **Standalone Executable** (Рекомендуется)

```bash
# Сборка для Windows
pyinstaller --onefile --name aparser src/aparser_cli/main.py
pyinstaller --onefile --name aparser-mcp src/aparser_cli/mcp/server.py
```

**Результат:**
- `aparser.exe` — CLI для пользователей
- `aparser-mcp.exe` — MCP server для агентов

**Преимущества:**
- ✅ Не требует Python
- ✅ Один файл
- ✅ Легко распространять

**Недостатки:**
- ⚠️ Большой размер (~50MB)
- ⚠️ Долгая сборка

---

### Вариант 2: **PyPI Package** (Простой)

```bash
# Публикация на PyPI
twine upload dist/*

# Установка пользователем
pip install aparser-cli
```

**Результат:**
- `aparser` — доступно в PATH
- `aparser-mcp` — доступно в PATH

**Преимущества:**
- ✅ Стандартный способ
- ✅ Автоматические обновления
- ✅ Маленький размер

**Недостатки:**
- ⚠️ Требует Python 3.10+
- ⚠️ Пользователи должны установить Python

---

### Вариант 3: **Docker Container** (Для серверов)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENTRYPOINT ["aparser"]
```

**Результат:**
```bash
docker run -e APARSER_URL=http://host:8080 aparser-cli run "query"
```

**Преимущества:**
- ✅ Изоляция
- ✅ Работает везде, где есть Docker
- ✅ Легко деплоить

**Недостатки:**
- ⚠️ Требует Docker
- ⚠️ Оверхеад

---

## 📋 План реализации

### Phase 1: Конфигурация (30 мин)
- [ ] Создать `get_config_dir()` для всех платформ
- [ ] Переместить `.env` → `%APPDATA%\aparser-cli\.env`
- [ ] Добавить валидацию конфига

### Phase 2: MCP Server (30 мин)
- [ ] Исправить пути для Windows
- [ ] Добавить авто-регистрацию MCP в конфиге агента
- [ ] Тесты на Windows (через GitHub Actions)

### Phase 3: Упаковка (1 час)
- [ ] Выбрать вариант (рекомендую PyPI + PyInstaller)
- [ ] Создать CI/CD для сборки
- [ ] Документация по установке

### Phase 4: Документация (30 мин)
- [ ] README.md для Windows пользователей
- [ ] Примеры использования с агентами
- [ ] Troubleshooting

---

## 🚀 Быстрый старт (Windows)

### Для разработчиков

```powershell
# 1. Установить Python 3.10+
# https://python.org/downloads

# 2. Клонировать репозиторий
git clone https://github.com/your-org/aparser-cli
cd aparser-cli

# 3. Установить
pip install -e .

# 4. Настроить
notepad $env:APPDATA\aparser-cli\.env
# APARSER_URL=http://localhost:8080
# APARSER_PASSWORD=123

# 5. Использовать
aparser run "query"
```

### Для пользователей агентов

```powershell
# 1. Установить
pip install aparser-cli

# 2. Настроить один раз
aparser init

# 3. Агент использует через MCP
# Автоматически доступно в Claude Code / Cursor / etc.
```

---

## 🔧 MCP Integration для Windows-агентов

### Claude Code (Windows)

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "aparser": {
      "command": "aparser-mcp",
      "args": []
    }
  }
}
```

### Cursor (Windows)

```json
// .cursor/mcp.json
{
  "servers": [
    {
      "name": "aparser",
      "command": "aparser-mcp"
    }
  ]
}
```

### Кастомный агент (Python)

```python
from mcp import ClientSession

async with ClientSession('aparser-mcp') as session:
    result = await session.call_tool('run_parser', {
        'parser': 'FreeAI::Perplexity',
        'query': 'OpenClaw competitors'
    })
```

---

## 📊 Сравнение вариантов

| Вариант | Размер | Python | Сложность | Рекомендация |
|---------|--------|--------|-----------|--------------|
| **PyPI** | ~1MB | Требуется | Низкая | ✅ Для разработчиков |
| **PyInstaller** | ~50MB | Не нужен | Средняя | ✅ Для пользователей |
| **Docker** | ~100MB | Не нужен | Высокая | ⚠️ Для серверов |

**Рекомендация:** Поддерживать **оба варианта** (PyPI + PyInstaller)

---

## ✅ Checklist для Windows

- [ ] `get_config_dir()` работает на Windows
- [ ] Keyring использует Windows Credential Manager
- [ ] MCP server работает через CMD/PowerShell
- [ ] Пути используют `pathlib.Path` (не строки)
- [ ] Тесты запускаются на Windows (GitHub Actions)
- [ ] Документация для Windows пользователей
- [ ] `.exe` билды через PyInstaller
- [ ] PyPI публикация

---

**Next Step:** Начать с Phase 1 (конфигурация) → 30 мин
