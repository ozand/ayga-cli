# A-Parser CLI — Установка на Windows

**Версия:** 2.3  
**Статус:** Private (требует доступа к репозиторию)

---

## 🚀 Быстрая установка (для агентов)

### Шаг 1: Скачать скрипт установки

```powershell
# Скачать установочный скрипт из GitHub
$githubToken = "ghp_YOUR_GITHUB_TOKEN"  # Замени на свой токен
$rawUrl = "https://raw.githubusercontent.com/ozand/aparser-cli/main/scripts/install.ps1"

# Скачать с авторизацией (для приватного репо)
$headers = @{ Authorization = "token $githubToken" }
Invoke-RestMethod -Uri $rawUrl -Headers $headers -OutFile "$env:TEMP\install-aparser.ps1"
```

### Шаг 2: Запустить установку

```powershell
# Запустить скрипт установки
& "$env:TEMP\install-aparser.ps1" -AparserUrl "http://your-aparser-host:8080" -AparserPassword "123"
```

### Шаг 3: Проверить установку

```powershell
# Проверить версию
aparser --version

# Проверить статус
aparser status
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
pip install "git+https://$githubToken@github.com/ozand/aparser-cli.git@main"

# 3. Инициализировать конфигурацию
aparser init

# 4. Настроить
notepad $env:APPDATA\aparser-cli\.env
```

### Вариант B: Клонирование репозитория

```powershell
# 1. Клонировать репозиторий
$githubToken = "ghp_YOUR_TOKEN"
git clone "https://$githubToken@github.com/ozand/aparser-cli.git"
cd aparser-cli

# 2. Создать виртуальное окружение
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Установить зависимости
pip install -e .

# 4. Проверить
aparser --version
```

### Вариант C: Standalone EXE (без Python)

```powershell
# 1. Скачать .exe из Releases
# https://github.com/ozand/aparser-cli/releases/latest
# Скачать: aparser-cli-windows.exe

# 2. Запустить
.\aparser-cli-windows.exe --version

# 3. Настроить
.\aparser-cli-windows.exe init
```

---

## 🔧 Настройка

### Конфигурационный файл

После установки создать `%APPDATA%\aparser-cli\.env`:

```env
# A-Parser API
APARSER_URL=http://your-aparser-host:8080
APARSER_PASSWORD=123

# Redis (опционально)
# APARSER_REDIS_HOST=localhost
# APARSER_REDIS_PORT=6379

# Логирование
APARSER_LOG_LEVEL=INFO
```

### Быстрая настройка через CLI

```powershell
# Установить URL и пароль
aparser config set-url http://your-aparser-host:8080
aparser config set-password

# Вас попросят ввести пароль (безопасно, через keyring)
```

---

## 🤖 Интеграция с агентами

### Claude Code (Windows)

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "aparser": {
      "command": "aparser-mcp",
      "args": [],
      "env": {
        "APARSER_URL": "http://your-aparser-host:8080"
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
      "name": "aparser",
      "command": "aparser-mcp",
      "cwd": "."
    }
  ]
}
```

### Custom Python Agent

```python
from mcp import ClientSession

async with ClientSession('aparser-mcp') as session:
    result = await session.call_tool('run_parser', {
        'parser': 'FreeAI::Perplexity',
        'query': 'OpenClaw competitors'
    })
    print(result.content)
```

---

## 🐛 Troubleshooting

### Ошибка: "aparser: command not found"

**Решение:**
```powershell
# Добавить Python Scripts в PATH
$env:Path += ";$env:USERPROFILE\AppData\Roaming\Python\Python311\Scripts"

# Или переустановить
pip install --force-reinstall "git+https://github.com/ozand/aparser-cli.git"
```

### Ошибка: "404 Not Found" при установке из GitHub

**Причина:** Нет доступа к приватному репозиторию

**Решение:**
1. Создать GitHub Personal Access Token: https://github.com/settings/tokens/new
2. Scope: `repo` (full control of private repositories)
3. Использовать токен в URL:
   ```powershell
   pip install "git+https://ghp_YOUR_TOKEN@github.com/ozand/aparser-cli.git"
   ```

### Ошибка: Keyring не работает на Windows

**Решение:**
```powershell
# Использовать переменную окружения вместо keyring
$env:APARSER_PASSWORD = "123"

# Или установить Windows Credential Manager backend
pip install keyring-winvault
```

---

## 📞 Поддержка

- **GitHub Issues:** https://github.com/ozand/aparser-cli/issues
- **Документация:** https://github.com/ozand/aparser-cli/tree/main/docs
- **Контакт:** @ozand (Telegram)

---

**Last Updated:** 2026-03-09  
**Version:** 2.3
