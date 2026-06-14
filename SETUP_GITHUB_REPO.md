# Инструкция: Создание приватного репозитория для ayga-parser CLI

## 1. Создать приватный репозиторий на GitHub

```
URL: https://github.com/new
Name: ayga-cli
Description: Google API Pool & Parser Management Tool
Visibility: Private (🔒)
Initialize with: README (optional)
```

## 2. Запушить текущий код

```bash
cd /home/opencode/.openclaw/workspace/projects/ayga-cli

# Добавить remote (замени ozand на свой username)
git remote add ayga-parser https://github.com/ozand/ayga-cli.git

# Запушить
git push ayga-parser main
```

**Или если нужно создать новую ветку:**
```bash
git checkout -b ayga-parser-main
git push ayga-parser ayga-parser-main:main
```

## 3. Создать GitHub Personal Access Token

```
URL: https://github.com/settings/tokens/new
Name: ayga-cli-install
Expiration: No expiration (или 90 дней)
Scopes: ✅ repo (Full control of private repositories)
```

**Скопировать токен** (начинается с `ghp_...`)

## 4. Обновить INSTALL_WINDOWS.md

В файле `INSTALL_WINDOWS.md` заменить:
```powershell
$githubToken = "ghp_YOUR_GITHUB_TOKEN"  # Вставить реальный токен
```

## 5. Инструкция для агента

Агент выполняет:

```powershell
# 1. Скачать скрипт
$githubToken = "ghp_REAL_TOKEN_HERE"
$rawUrl = "https://raw.githubusercontent.com/ozand/ayga-cli/main/scripts/install.ps1"
$headers = @{ Authorization = "token $githubToken" }
Invoke-RestMethod -Uri $rawUrl -Headers $headers -OutFile "$env:TEMP\install.ps1"

# 2. Запустить
& "$env:TEMP\install.ps1"

# 3. Проверить
ayga-parser --version
```

## 6. (Опционально) Добавить агентов в Collaborators

```
GitHub Repo → Settings → Collaborators → Add people
Добавить: agent-username (если нужно)
```

---

## Готово!

Теперь агенты могут устанавливать ayga-parser CLI через:
```powershell
pip install "git+https://ghp_TOKEN@github.com/ozand/ayga-cli.git"
```
