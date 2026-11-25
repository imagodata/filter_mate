# FilterMate, the standalone application, in one line (Windows PowerShell):
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/imagodata/filter_mate/v5.1.2/standalone/install.ps1 | iex"
# Installs the `filtermate` command with pipx (installed first for this user when missing), then says
# which QGIS it will run on. No administrator rights once Python 3.9+ and pipx are there; installing those
# themselves may need them. $env:FILTERMATE_SOURCE changes what is installed.
# "return", never "exit": pasted with "| iex", an exit would close the session it was pasted in (audit of
# 2026-11-24). Not "Stop": Windows PowerShell 5 takes what a program writes on stderr for an error; exit codes
# are read instead.
$ErrorActionPreference = "Continue"
# A release tag, not the moving main: what is installed is fixed (audit of 2026-11-24). The release process
# moves this default with the tag.
$source = if ($env:FILTERMATE_SOURCE) { $env:FILTERMATE_SOURCE } else { "https://github.com/imagodata/filter_mate/archive/refs/tags/v5.1.2.zip" }

function Find-Python($skipStoreAlias) {
    foreach ($candidate in @(@("py", "-3"), @("python"), @("python3"))) {
        $exe = Get-Command $candidate[0] -ErrorAction SilentlyContinue
        if (-not $exe) { continue }
        if ($skipStoreAlias -and $exe.Source -like "*WindowsApps*") { continue }
        $arguments = @($candidate | Select-Object -Skip 1)
        & $candidate[0] @arguments -c "import sys; sys.exit(sys.version_info < (3, 9))" 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    return $null
}
# First past the Store placeholder (running it opens the Store); then, when nothing else runs, the placeholder
# itself: a real Python from the Store lives there too, and a stub opens the Store to fetch one (audit of 2026-11-24).
$python = Find-Python $true
if (-not $python) { $python = Find-Python $false }
if (-not $python) {
    Write-Error "FilterMate needs Python 3.9 or later: install it from https://www.python.org/downloads/ (or 'winget install Python.Python.3.12'), then run this again."
    return
}
$py = $python[0]
$pyArgs = @($python | Select-Object -Skip 1)

& $py @pyArgs -m pipx --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing pipx for this user..."
    & $py @pyArgs -m pip install --user --quiet pipx
    if ($LASTEXITCODE -ne 0) { Write-Error "pipx could not be installed." ; return }
}

Write-Host "Installing FilterMate from $source..."
& $py @pyArgs -m pipx install --force $source
if ($LASTEXITCODE -ne 0) { Write-Error "FilterMate could not be installed from $source."; return }
Write-Host "Putting the pipx bin folder on the PATH of new shells (pipx ensurepath)..."
& $py @pyArgs -m pipx ensurepath | Out-Null

$filtermate = Join-Path $env:USERPROFILE ".local\bin\filtermate.exe"
if (Get-Command filtermate -ErrorAction SilentlyContinue) { $filtermate = "filtermate" }
Write-Host ""
& $filtermate doctor
Write-Host ""
Write-Host "Start it with: filtermate   (open a new terminal if the command is not found yet)"
Write-Host "No QGIS above? 'filtermate setup' installs one for FilterMate alone, or install QGIS from https://qgis.org"
