<#
.SYNOPSIS
    Démarrage des services HealthCare AI
.DESCRIPTION
    Script PowerShell pour démarrer l'API et/ou le Worker séparément
.PARAMETER Service
    Service à démarrer: api, worker, ou both
.PARAMETER Port
    Port pour l'API (défaut: 8000)
.PARAMETER WorkerMode
    Mode du worker: auto, celery, standalone (défaut: auto)
.EXAMPLE
    .\Start-HealthCare.ps1 -Service api
    .\Start-HealthCare.ps1 -Service worker -WorkerMode standalone
    .\Start-HealthCare.ps1 -Service both
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("api", "worker", "both")]
    [string]$Service = "both",
    
    [Parameter(Mandatory=$false)]
    [int]$Port = 8000,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("auto", "celery", "standalone")]
    [string]$WorkerMode = "auto"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   HealthCare AI - Gestionnaire de Services" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Fonction pour activer l'environnement virtuel
function Activate-Venv {
    $venvPath = Join-Path $ScriptDir "venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
        & $venvPath
        return $true
    }
    return $false
}

# Fonction pour démarrer l'API
function Start-API {
    param([int]$Port)
    
    Write-Host ""
    Write-Host "🚀 Démarrage de l'API Server sur le port $Port..." -ForegroundColor Green
    Write-Host "   Documentation: http://localhost:$Port/docs" -ForegroundColor Gray
    Write-Host ""
    
    python start_api.py --port $Port
}

# Fonction pour démarrer le Worker
function Start-Worker {
    param([string]$Mode)
    
    Write-Host ""
    Write-Host "🔧 Démarrage du Worker en mode $Mode..." -ForegroundColor Green
    Write-Host ""
    
    python start_worker.py --mode $Mode
}

# Activer l'environnement virtuel
Activate-Venv | Out-Null

try {
    switch ($Service) {
        "api" {
            Start-API -Port $Port
        }
        "worker" {
            Start-Worker -Mode $WorkerMode
        }
        "both" {
            Write-Host "⚠️  Pour démarrer les deux services, ouvrez deux terminaux:" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "   Terminal 1 (API):" -ForegroundColor Cyan
            Write-Host "   .\Start-HealthCare.ps1 -Service api" -ForegroundColor White
            Write-Host ""
            Write-Host "   Terminal 2 (Worker):" -ForegroundColor Cyan
            Write-Host "   .\Start-HealthCare.ps1 -Service worker" -ForegroundColor White
            Write-Host ""
            
            $choice = Read-Host "Démarrer l'API maintenant? (o/n)"
            if ($choice -eq "o" -or $choice -eq "O") {
                Start-API -Port $Port
            }
        }
    }
}
catch {
    Write-Host "❌ Erreur: $_" -ForegroundColor Red
    exit 1
}
