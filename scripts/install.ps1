# A-Parser CLI — Windows Installation Script
# Usage: .\install.ps1

param(
    [switch]$Dev,
    [switch]$MCP,
    [string]$AparserUrl = "http://localhost:8080",
    [string]$AparserPassword = "123"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "A-Parser CLI — Windows Installer" -ForegroundColor Cyan
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
Write-Host "[3/5] Installing A-Parser CLI..." -ForegroundColor Yellow
if ($Dev) {
    Write-Host "  Installing with dev dependencies..." -ForegroundColor Gray
    pip install -e ".[dev,mcp]"
} elseif ($MCP) {
    Write-Host "  Installing with MCP support..." -ForegroundColor Gray
    pip install "aparser-cli[mcp]"
} else {
    pip install aparser-cli
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Installation failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Installation complete" -ForegroundColor Green

# Create config directory
Write-Host "[4/5] Creating configuration..." -ForegroundColor Yellow
$configDir = "$env:APPDATA\aparser-cli"
if (!(Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    Write-Host "  ✓ Created: $configDir" -ForegroundColor Green
}

# Create .env file
$envFile = "$configDir\.env"
if (!(Test-Path $envFile)) {
    @"
# A-Parser API Configuration
APARSER_URL=$AparserUrl
APARSER_PASSWORD=$AparserPassword

# Redis (optional)
# APARSER_REDIS_HOST=localhost
# APARSER_REDIS_PORT=6379
# APARSER_REDIS_PASSWORD=

# Logging
APARSER_LOG_LEVEL=INFO
"@ | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "  ✓ Created: $envFile" -ForegroundColor Green
}

# Verify installation
Write-Host "[5/5] Verifying installation..." -ForegroundColor Yellow
try {
    $version = aparser --version 2>&1
    Write-Host "  ✓ A-Parser CLI $version" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Verification failed, but installation may still work" -ForegroundColor Yellow
    Write-Host "  Try: aparser status" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Edit config: notepad $envFile" -ForegroundColor White
Write-Host "  2. Test connection: aparser status" -ForegroundColor White
Write-Host "  3. Run parser: aparser run `"your query`"" -ForegroundColor White
Write-Host ""
Write-Host "Config location: $configDir" -ForegroundColor Gray
Write-Host ""
