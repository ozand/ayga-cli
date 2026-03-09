# Инструкция: Создание приватного репозитория для A-Parser CLI

## 1. Создать приватный репозиторий на GitHub

```
URL: https://github.com/new
Name: aparser-cli
Description: Google API Pool & Parser Management Tool
Visibility: Private (🔒)
Initialize with: README (optional)
```

## 2. Запушить текущий код

```bash
cd /home/opencode/.openclaw/workspace/projects/aparser-cli

# Добавить remote (замени ozand на свой username)
git remote add aparser https://github.com/ozand/aparser-cli.git

# Запушить
git push aparser main
```

**Или если нужно создать новую ветку:**
```bash
git checkout -b aparser-main
git push aparser aparser-main:main
```

## 3. Создать GitHub Personal Access Token

```
URL: https://github.com/settings/tokens/new
Name: aparser-cli-install
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
$rawUrl = "https://raw.githubusercontent.com/ozand/aparser-cli/main/scripts/install.ps1"
$headers = @{ Authorization = "token $githubToken" }
Invoke-RestMethod -Uri $rawUrl -Headers $headers -OutFile "$env:TEMP\install.ps1"

# 2. Запустить
& "$env:TEMP\install.ps1"

# 3. Проверить
aparser --version
```

## 6. (Опционально) Добавить агентов в Collaborators

```
GitHub Repo → Settings → Collaborators → Add people
Добавить: agent-username (если нужно)
```

---

## Готово!

Теперь агенты могут устанавливать A-Parser CLI через:
```powershell
pip install "git+https://ghp_TOKEN@github.com/ozand/aparser-cli.git"
```
