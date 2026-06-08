# CXWorkflow Installation

This guide keeps the local Codex plugin stable during development.

## Recommended Local Setup

CXWorkflow works best when the personal marketplace points to a real local plugin source:

```text
%USERPROFILE%\.agents\plugins\marketplace.json
%USERPROFILE%\.agents\plugins\plugins\cxworkflow
```

The marketplace entry should point at:

```json
{
  "name": "cxworkflow",
  "source": {
    "source": "local",
    "path": "./plugins/cxworkflow"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

If the source directory is missing, Codex may keep using an old cache until the next refresh, then the plugin can appear to disappear.

## Update The Local Plugin

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\update-local-plugin.ps1
```

The script:

- Updates `.codex-plugin/plugin.json` with a Codex cachebuster version.
- Copies the plugin source to `%USERPROFILE%\.agents\plugins\plugins\cxworkflow`.
- Ensures `%USERPROFILE%\.agents\plugins\marketplace.json` contains the `cxworkflow` entry.
- Writes a matching cache copy under `%USERPROFILE%\.codex\plugins\cache\personal\cxworkflow\<version>`.
- Validates all plugin copies when the Codex plugin validator is available.

After updating, open a new Codex thread or restart Codex so the app reloads the plugin skill.

## Troubleshooting

### Plugin Disappears After Restart

Check that the source path exists:

```powershell
Test-Path "$env:USERPROFILE\.agents\plugins\plugins\cxworkflow"
```

If it returns `False`, run the update script again.

### Plugin Loads Old Instructions

Check that the source and cache versions match:

```powershell
Get-Content .\.codex-plugin\plugin.json | ConvertFrom-Json | Select-Object name,version
Get-Content "$env:USERPROFILE\.agents\plugins\plugins\cxworkflow\.codex-plugin\plugin.json" | ConvertFrom-Json | Select-Object name,version
```

If the versions differ, run the update script and start a new thread.

### Manifest Validation

If the validator is installed, run:

```powershell
python "$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py" .
```

