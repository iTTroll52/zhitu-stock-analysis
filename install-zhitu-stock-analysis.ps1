$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'work\skills\zhitu-stock-analysis'
$target = Join-Path $HOME '.codex\skills\zhitu-stock-analysis'

if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md'))) {
    throw "Skill source not found: $source"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'SKILL.md') -Destination (Join-Path $target 'SKILL.md') -Force

foreach ($directory in @('agents', 'references', 'scripts')) {
    $sourceDirectory = Join-Path $source $directory
    $targetDirectory = Join-Path $target $directory
    New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
    Copy-Item -Path (Join-Path $sourceDirectory '*') -Destination $targetDirectory -Recurse -Force
}

Write-Host "Installed: $target"
Write-Host 'Restart Codex or start a new task if the updated skill metadata is not refreshed immediately.'
