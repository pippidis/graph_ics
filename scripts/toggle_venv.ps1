# Dot-source this script to activate/deactivate in the current PowerShell session.
$projectVenv = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\.venv'))
$activationScript = Join-Path $projectVenv 'Scripts\Activate.ps1'
if ($env:VIRTUAL_ENV -and [IO.Path]::GetFullPath($env:VIRTUAL_ENV) -eq $projectVenv) {
    if (-not (Get-Command deactivate -ErrorAction SilentlyContinue)) { throw 'Active environment has no deactivate function.' }
    Write-Host 'Deactivating the graph_ics environment...'
    deactivate
} else {
    if (-not (Test-Path -LiteralPath $activationScript)) { throw 'Project environment missing. Run scripts\setup_venv.bat first.' }
    if ($env:VIRTUAL_ENV) {
        if (-not (Get-Command deactivate -ErrorAction SilentlyContinue)) { throw 'Deactivate the current environment before switching.' }
        Write-Host "Switching from $env:VIRTUAL_ENV to $projectVenv"
        deactivate
    }
    Write-Host "Activating $projectVenv"
    . $activationScript
}
