$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$repoRootPrefix = $repoRoot.TrimEnd([char[]]@("\", "/"))
Set-Location $repoRoot

$excludedDirs = @(".git", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist")

$pythonFiles = @(
    Get-ChildItem -Path $repoRoot -Recurse -File -Filter "*.py" |
        Where-Object {
            $relativePath = $_.FullName.Substring($repoRootPrefix.Length).TrimStart([char[]]@("\", "/"))
            $pathParts = $relativePath -split "[\\/]"
            -not ($pathParts | Where-Object { $excludedDirs -contains $_ })
        } |
        Sort-Object FullName |
        ForEach-Object { $_.FullName.Substring($repoRootPrefix.Length).TrimStart([char[]]@("\", "/")) }
)

if ($pythonFiles.Count -eq 0) {
    throw "未找到 Python 文件。"
}

Write-Host "==> python -m py_compile"
python -m py_compile @pythonFiles
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> python -m pytest"
python -m pytest
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "验证通过。"
