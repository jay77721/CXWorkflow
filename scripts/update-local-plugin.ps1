# Thin wrapper around the cross-platform update_local_plugin.py.
# Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\update-local-plugin.ps1
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "python"
if (Get-Command py -ErrorAction SilentlyContinue) { $python = "py -3" }
& $python (Join-Path $scriptDir "update_local_plugin.py") @args
if ($LASTEXITCODE -ne 0) { throw "CXWorkflow plugin update failed" }
