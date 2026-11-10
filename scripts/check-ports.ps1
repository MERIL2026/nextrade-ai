[CmdletBinding()]
param(
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

$defaults = @{
    WEB_HOST_PORT      = 3000
    API_HOST_PORT      = 8001
    POSTGRES_HOST_PORT = 5435
    REDIS_HOST_PORT    = 6381
}

$ports = @{}
foreach ($key in $defaults.Keys) {
    $ports[$key] = $defaults[$key]
}

if (Test-Path $EnvFile) {
    foreach ($line in Get-Content -Path $EnvFile -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or ($trimmed -notmatch "=")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        $name = $parts[0].Trim()
        $val = $parts[1].Trim()
        if ($ports.ContainsKey($name) -and ($val -match '^\d+$')) {
            $ports[$name] = [int]$val
        }
    }
}

$activeListeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue
$dockerPorts = @()
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerPorts = & docker ps --format "{{.Names}}|{{.Ports}}" 2>$null
}

$hasCollision = $false
Write-Host "Checking NEXTRADE AI configured host ports..." -ForegroundColor Cyan

foreach ($entry in $ports.GetEnumerator() | Sort-Object Name) {
    $port = [int]$entry.Value
    $tcpHits = @($activeListeners | Where-Object { $_.LocalPort -eq $port })
    $dockerHits = @($dockerPorts | Where-Object { $_ -match "(?::|->)$port->" -or $_ -match ":$port->" })

    if ($tcpHits.Count -gt 0 -or $dockerHits.Count -gt 0) {
        $hasCollision = $true
        $procInfo = ($tcpHits | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
        Write-Host ("[BUSY]   {0} = {1} (PIDs: {2}; Docker: {3})" -f $entry.Name, $port, $procInfo, ($dockerHits -join "; ")) -ForegroundColor Red
    }
    else {
        Write-Host ("[FREE]   {0} = {1}" -f $entry.Name, $port) -ForegroundColor Green
    }
}

if ($hasCollision) {
    Write-Host "One or more host ports are busy. Update ports in .env before starting Docker Compose." -ForegroundColor Yellow
    exit 1
}

Write-Host "All configured Phase 1 host ports are available." -ForegroundColor Green
exit 0

