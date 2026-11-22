# FilterMate, the standalone application, in one line (Windows PowerShell):
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/imagodata/filter_mate/main/standalone/install.ps1 | iex"
# Installs the `filtermate` command with pipx (installed first for this user when missing), then says
# which QGIS it will run on. Nothing needs administrator rights. $env:FILTERMATE_SOURCE changes what is installed.
# Not "Stop": Windows PowerShell 5 takes what a program writes on stderr for an error; exit codes are read instead.
$ErrorActionPreference = "Continue"
$source = if ($env:FILTERMATE_SOURCE) { $env:FILTERMATE_SOURCE } else { "git+https://github.com/imagodata/filter_mate" }

$python = $null
foreach ($candidate in @(@("py", "-3"), @("python"), @("python3"))) {
    $exe = Get-Command $candidate[0] -ErrorAction SilentlyContinue
    if (-not $exe -or $exe.Source -like "*WindowsApps*") { continue }  # the Store's placeholder opens the Store
    $arguments = @($candidate | Select-Object -Skip 1)
    & $candidate[0] @arguments -c "import sys; sys.exit(sys.version_info < (3, 9))" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
}
if (-not $python) {
    Write-Error "FilterMate needs Python 3.9 or later: install it from https://www.python.org/downloads/ (or 'winget install Python.Python.3.12'), then run this again."
    exit 1
}
$py = $python[0]
$pyArgs = @($python | Select-Object -Skip 1)

& $py @pyArgs -m pipx --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing pipx for this user..."
    & $py @pyArgs -m pip install --user --quiet pipx
    if ($LASTEXITCODE -ne 0) { Write-Error "pipx could not be installed." ; exit 1 }
}

Write-Host "Installing FilterMate from $source..."
& $py @pyArgs -m pipx install --force $source
if ($LASTEXITCODE -ne 0) { Write-Error "FilterMate could not be installed from $source."; exit 1 }
& $py @pyArgs -m pipx ensurepath | Out-Null

$filtermate = Join-Path $env:USERPROFILE ".local\bin\filtermate.exe"
if (Get-Command filtermate -ErrorAction SilentlyContinue) { $filtermate = "filtermate" }
Write-Host ""
& $filtermate doctor
Write-Host ""
Write-Host "Start it with: filtermate   (open a new terminal if the command is not found yet)"
Write-Host "No QGIS above? 'filtermate setup' installs one for FilterMate alone, or install QGIS from https://qgis.org"
