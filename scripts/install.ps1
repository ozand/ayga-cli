# ayga-parser CLI — Windows Installation Script
# Usage: .\install.ps1

param(
    [switch]$Dev,
    [switch]$MCP,
    [string]$ayga-parserUrl = "http://localhost:8080",
    [string]$ayga-parserPassword = "123"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ayga-parser CLI — Windows Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found!" -ForegroundColor Red
    Write-Host "  Please install Python 3.10+ from https://python.org/downloads" -ForegroundColor Yellow
    exit 1
}

# Check pip
Write-Host "[2/5] Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    Write-Host "  ✓ $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ pip not found!" -ForegroundColor Red
    exit 1
}

# Install package
Write-Host "[3/5] Installing ayga-parser CLI..." -ForegroundColor Yellow
if ($Dev) {
    Write-Host "  Installing with dev dependencies..." -ForegroundColor Gray
    pip install -e ".[dev,mcp]"
} elseif ($MCP) {
    Write-Host "  Installing with MCP support..." -ForegroundColor Gray
    pip install "ayga-cli[mcp]"
} else {
    pip install ayga-cli
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Installation failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Installation complete" -ForegroundColor Green

# Create config directory
Write-Host "[4/5] Creating configuration..." -ForegroundColor Yellow
$configDir = "$env:APPDATA\ayga-cli"
if (!(Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    Write-Host "  ✓ Created: $configDir" -ForegroundColor Green
}

# Create .env file
$envFile = "$configDir\.env"
if (!(Test-Path $envFile)) {
    @"
# ayga-parser API Configuration
ayga-parser_URL=$ayga-parserUrl
ayga-parser_PASSWORD=$ayga-parserPassword

# Redis (optional)
# ayga-parser_REDIS_HOST=localhost
# ayga-parser_REDIS_PORT=6379
# ayga-parser_REDIS_PASSWORD=

# Logging
ayga-parser_LOG_LEVEL=INFO
"@ | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "  ✓ Created: $envFile" -ForegroundColor Green
}

# Verify installation
Write-Host "[5/5] Verifying installation..." -ForegroundColor Yellow
try {
    $version = ayga-parser --version 2>&1
    Write-Host "  ✓ ayga-parser CLI $version" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Verification failed, but installation may still work" -ForegroundColor Yellow
    Write-Host "  Try: ayga-parser status" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Edit config: notepad $envFile" -ForegroundColor White
Write-Host "  2. Test connection: ayga-parser status" -ForegroundColor White
Write-Host "  3. Run parser: ayga-parser run `"your query`"" -ForegroundColor White
Write-Host ""
Write-Host "Config location: $configDir" -ForegroundColor Gray
Write-Host ""
