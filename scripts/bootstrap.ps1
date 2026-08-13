# Thin wrapper around scripts/bootstrap.py. Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 [-WithPlugin]
param([switch]$WithPlugin)
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "python"
if (Get-Command py -ErrorAction SilentlyContinue) { $python = "py -3" }
$extra = @()
if ($WithPlugin) { $extra = @("--with-plugin") }
& $python (Join-Path $scriptDir "bootstrap.py") @extra
if ($LASTEXITCODE -ne 0) { throw "CXWorkflow bootstrap failed" }
