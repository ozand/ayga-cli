# ayga-cli — Установка на Windows

**Версия:** 2.3
**Статус:** Private (требует доступа к репозиторию)

---

## 🚀 Быстрая установка (для агентов)

### Шаг 1: Скачать скрипт установки

```powershell
# Скачать установочный скрипт из GitHub
$githubToken = "ghp_YOUR_GITHUB_TOKEN"  # Замени на свой токен
$rawUrl = "https://raw.githubusercontent.com/ozand/ayga-cli/main/scripts/install.ps1"

# Скачать с авторизацией (для приватного репо)
$headers = @{ Authorization = "token $githubToken" }
Invoke-RestMethod -Uri $rawUrl -Headers $headers -OutFile "$env:TEMP\install-ayga-cli.ps1"
```

### Шаг 2: Запустить установку

```powershell
# Запустить скрипт установки
& "$env:TEMP\install-ayga-cli.ps1" -BackendUrl "http://127.0.0.1:9091/API" -BackendPassword "123"
```

### Шаг 3: Проверить установку

```powershell
# Проверить версию
ayga_parser --version

# Проверить статус
ayga_parser status
```

---

## 📋 Полная инструкция

### Требования

- **Windows 10/11** (64-bit)
- **Python 3.10+** (https://python.org/downloads)
- **Git** (опционально, для клонирования)
- **Доступ к приватному репозиторию** GitHub

### Вариант A: Установка через pip (рекомендуется)

```powershell
# 1. Создать GitHub Personal Access Token
# https://github.com/settings/tokens/new
# Scopes: repo (full control of private repositories)

# 2. Установить из приватного репо
$githubToken = "ghp_YOUR_TOKEN"
pip install "git+https://$githubToken@github.com/ozand/ayga-cli.git@main"

# 3. Инициализировать конфигурацию
ayga_parser init

# 4. Настроить
notepad $env:APPDATA\ayga-cli\.env
```

### Вариант B: Клонирование репозитория

```powershell
# 1. Клонировать репозиторий
$githubToken = "ghp_YOUR_TOKEN"
git clone "https://$githubToken@github.com/ozand/ayga-cli.git"
cd ayga-cli

# 2. Создать виртуальное окружение
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Установить зависимости
pip install -e .

# 4. Проверить
ayga_parser --version
```

### Вариант C: Standalone EXE (без Python)

```powershell
# 1. Скачать .exe из Releases
# https://github.com/ozand/ayga-cli/releases/latest
# Скачать: ayga-cli-windows.exe

# 2. Запустить
.\ayga-cli-windows.exe --version

# 3. Настроить
.\ayga-cli-windows.exe init
```

---

## 🔧 Настройка

### Конфигурационный файл

После установки создать `%APPDATA%\ayga-cli\.env`:

```env
# Backend connection
AYGA_HTTP_URL=http://127.0.0.1:9091/API
AYGA_PASSWORD=123

# Redis (опционально)
# AYGA_REDIS_HOST=localhost
# AYGA_REDIS_PORT=6379

# Логирование
AYGA_LOG_LEVEL=INFO
```

### Быстрая настройка через CLI

```powershell
# Установить URL и пароль
ayga_parser config set-url http://127.0.0.1:9091/API
ayga_parser config set-password

# Вас попросят ввести пароль (безопасно, через keyring)
```

---

## 🤖 Интеграция с агентами

### Claude Code (Windows)

```json
// ~/.claude/settings.json
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

```json
// .cursor/mcp.json
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
from mcp import ClientSession

async with ClientSession('ayga_parser-mcp') as session:
    result = await session.call_tool('get', {
        'source': 'web-search',
        'query': 'OpenClaw competitors'
    })
    print(result.content)
```

---

## 🐛 Troubleshooting

### Ошибка: "ayga_parser: command not found"

**Решение:**
```powershell
# Добавить Python Scripts в PATH
$env:Path += ";$env:USERPROFILE\AppData\Roaming\Python\Python311\Scripts"

# Или переустановить
pip install --force-reinstall "git+https://github.com/ozand/ayga-cli.git"
```

### Ошибка: "404 Not Found" при установке из GitHub

**Причина:** Нет доступа к приватному репозиторию

**Решение:**
1. Создать GitHub Personal Access Token: https://github.com/settings/tokens/new
2. Scope: `repo` (full control of private repositories)
3. Использовать токен в URL:
   ```powershell
   pip install "git+https://ghp_YOUR_TOKEN@github.com/ozand/ayga-cli.git"
   ```

### Ошибка: Keyring не работает на Windows

**Решение:**
```powershell
# Использовать переменную окружения вместо keyring
$env:AYGA_PASSWORD = "123"

# Или установить Windows Credential Manager backend
pip install keyring-winvault
```

---

## 📞 Поддержка

- **GitHub Issues:** https://github.com/ozand/ayga-cli/issues
- **Документация:** https://github.com/ozand/ayga-cli/tree/main/docs
- **Контакт:** @ozand (Telegram)

---

**Last Updated:** 2026-03-09
**Version:** 2.3
