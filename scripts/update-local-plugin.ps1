param(
  [string]$PluginName = "cxworkflow",
  [string]$MarketplaceName = "personal"
)

$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "==> $Message"
}

function Write-JsonFile {
  param(
    [Parameter(Mandatory = $true)]$Value,
    [Parameter(Mandatory = $true)][string]$Path
  )

  $json = $Value | ConvertTo-Json -Depth 20
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, $utf8NoBom)
}

function Invoke-Validator {
  param(
    [string]$ValidatorPath,
    [string]$PluginPath
  )

  python $ValidatorPath $PluginPath
  if ($LASTEXITCODE -ne 0) {
    throw "Plugin validation failed for $PluginPath"
  }
}

function Copy-PluginContents {
  param(
    [string]$SourceRoot,
    [string]$DestinationRoot
  )

  New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null

  Copy-Item -LiteralPath (Join-Path $SourceRoot ".codex-plugin") -Destination $DestinationRoot -Recurse -Force
  Copy-Item -LiteralPath (Join-Path $SourceRoot "skills") -Destination $DestinationRoot -Recurse -Force

  foreach ($fileName in @("README.md", "README.en.md", "INSTALL.md", "CHANGELOG.md")) {
    $sourceFile = Join-Path $SourceRoot $fileName
    if (Test-Path -LiteralPath $sourceFile) {
      Copy-Item -LiteralPath $sourceFile -Destination (Join-Path $DestinationRoot $fileName) -Force
    }
  }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$manifestPath = Join-Path $repoRoot ".codex-plugin\plugin.json"

if (-not (Test-Path -LiteralPath $manifestPath)) {
  throw "Missing plugin manifest: $manifestPath"
}

Write-Step "Updating Codex cachebuster version"
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
$baseVersion = [string]$manifest.version
if ($baseVersion.Contains("+")) {
  $baseVersion = $baseVersion.Split("+")[0]
}

$cachebuster = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
$newVersion = "$baseVersion+codex.$cachebuster"
$manifest.version = $newVersion
Write-JsonFile -Value $manifest -Path $manifestPath

$agentsPluginsRoot = Join-Path $env:USERPROFILE ".agents\plugins"
$marketplacePath = Join-Path $agentsPluginsRoot "marketplace.json"
$pluginSourceRoot = Join-Path $agentsPluginsRoot "plugins\$PluginName"

Write-Step "Ensuring personal marketplace entry"
New-Item -ItemType Directory -Force -Path $agentsPluginsRoot | Out-Null

if (Test-Path -LiteralPath $marketplacePath) {
  $marketplace = Get-Content -Raw -Encoding UTF8 -LiteralPath $marketplacePath | ConvertFrom-Json
} else {
  $marketplace = [pscustomobject]@{
    name = $MarketplaceName
    interface = [pscustomobject]@{
      displayName = "Personal"
    }
    plugins = @()
  }
}

if (-not $marketplace.plugins) {
  $marketplace | Add-Member -NotePropertyName plugins -NotePropertyValue @()
}

$existing = @($marketplace.plugins | Where-Object { $_.name -eq $PluginName })
if ($existing.Count -eq 0) {
  $marketplace.plugins += [pscustomobject]@{
    name = $PluginName
    source = [pscustomobject]@{
      source = "local"
      path = "./plugins/$PluginName"
    }
    policy = [pscustomobject]@{
      installation = "AVAILABLE"
      authentication = "ON_INSTALL"
    }
    category = "Productivity"
  }
} else {
  $entry = $existing[0]
  $entry.source.source = "local"
  $entry.source.path = "./plugins/$PluginName"
  $entry.policy.installation = "AVAILABLE"
  $entry.policy.authentication = "ON_INSTALL"
  $entry.category = "Productivity"
}

Write-JsonFile -Value $marketplace -Path $marketplacePath

Write-Step "Copying plugin source to personal marketplace"
Copy-PluginContents -SourceRoot $repoRoot -DestinationRoot $pluginSourceRoot

Write-Step "Writing matching Codex plugin cache"
$cacheRoot = Join-Path $env:USERPROFILE ".codex\plugins\cache\$MarketplaceName\$PluginName\$newVersion"
Copy-PluginContents -SourceRoot $pluginSourceRoot -DestinationRoot $cacheRoot

$validator = Join-Path $env:USERPROFILE ".codex\skills\.system\plugin-creator\scripts\validate_plugin.py"
if (Test-Path -LiteralPath $validator) {
  Write-Step "Validating repository plugin"
  Invoke-Validator -ValidatorPath $validator -PluginPath $repoRoot
  Write-Step "Validating marketplace source plugin"
  Invoke-Validator -ValidatorPath $validator -PluginPath $pluginSourceRoot
  Write-Step "Validating cached plugin"
  Invoke-Validator -ValidatorPath $validator -PluginPath $cacheRoot
} else {
  Write-Warning "Codex plugin validator not found: $validator"
}

Write-Step "Done"
Write-Host "Version: $newVersion"
Write-Host "Marketplace: $marketplacePath"
Write-Host "Source: $pluginSourceRoot"
Write-Host "Cache: $cacheRoot"
Write-Host "Open a new Codex thread or restart Codex to reload the plugin."
