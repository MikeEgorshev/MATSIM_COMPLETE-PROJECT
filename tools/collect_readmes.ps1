param(
    [string]$Root = ".",
    [string]$OutDir = "docs/readme-hub"
)

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -Path $Root).Path
$outPath = Join-Path $rootPath $OutDir
$filesPath = Join-Path $outPath "files"

New-Item -ItemType Directory -Path $filesPath -Force | Out-Null

# Skip heavy/generated/vendor folders.
$skipDirPatterns = @(
    "\\.git\\",
    "\\target\\",
    "\\output\\",
    "\\archive-outputs\\",
    "\\docs\\readme-hub\\"
)

function IsSkipped([string]$fullPath) {
    foreach ($p in $skipDirPatterns) {
        if ($fullPath -match $p) { return $true }
    }
    return $false
}

$readmes = Get-ChildItem -Path $rootPath -Recurse -File -Include README*.md |
    Where-Object {
        -not (IsSkipped $_.FullName) -and
        $_.FullName -ne (Join-Path $rootPath "README.md")
    }

$rootPrefix = $rootPath
if (-not $rootPrefix.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
    $rootPrefix = $rootPrefix + [System.IO.Path]::DirectorySeparatorChar
}

$indexLines = @()
$indexLines += "# README Hub"
$indexLines += ""
$indexLines += "Collected README files (excluding root `README.md`)."
$indexLines += ""
$indexLines += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$indexLines += ""

foreach ($f in $readmes) {
    $relative = $f.FullName.Substring($rootPrefix.Length)
    $dest = Join-Path $filesPath $relative
    $destDir = Split-Path -Parent $dest
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    Copy-Item -Path $f.FullName -Destination $dest -Force

    $indexLines += "- Source: `"${relative}`""
    $indexLines += "  - Copy: `"docs/readme-hub/files/${relative}`""
}

$indexFile = Join-Path $outPath "README.md"
Set-Content -Path $indexFile -Value ($indexLines -join [Environment]::NewLine) -Encoding UTF8

Write-Host "Collected $($readmes.Count) README files into $outPath"
