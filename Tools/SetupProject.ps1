# Read-only project check, compatible with Windows PowerShell 5.1.
[CmdletBinding()]
param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$projectRoot = Split-Path -Parent $PSScriptRoot

try {
    $project = Join-Path $projectRoot 'Fruit_Example.uproject'
    $content = Join-Path $projectRoot 'Content'
    $map = Join-Path $content 'Root\Maps\L_Example.umap'
    if (!(Test-Path -LiteralPath $project -PathType Leaf) -or !(Test-Path -LiteralPath $map -PathType Leaf)) {
        throw 'Не найден проект или карта L_Example. Распакуйте весь архив в одну папку.'
    }

    $packages = @(Get-ChildItem -LiteralPath $content -Recurse -File |
        Where-Object { $_.Extension -in '.uasset', '.umap' })
    $pointers = @()
    $invalid = @()
    foreach ($package in $packages) {
        $stream = [IO.File]::OpenRead($package.FullName)
        try {
            $header = New-Object byte[] 64
            $count = $stream.Read($header, 0, $header.Length)
        } finally {
            $stream.Dispose()
        }

        $relativePath = $package.FullName.Substring($projectRoot.Length + 1)
        $prefix = [Text.Encoding]::ASCII.GetString($header, 0, $count)
        if ($prefix.StartsWith('version https://git-lfs.github.com/spec/v1')) {
            $pointers += $relativePath
        } elseif ($count -lt 4 -or [BitConverter]::ToUInt32($header, 0) -ne 2653586369) {
            $invalid += $relativePath
        }
    }

    if ($pointers.Count -gt 0) {
        $examples = ($pointers | Select-Object -First 3) -join ', '
        throw "В копии остались текстовые указатели Git LFS: $($pointers.Count). Например: $examples. Скачайте свежую версию ветки main с GitHub и распакуйте в новую папку."
    }
    if ($invalid.Count -gt 0) {
        $examples = ($invalid | Select-Object -First 3) -join ', '
        throw "Файлы Unreal с неверным заголовком: $($invalid.Count). Например: $examples. Скачайте проект заново."
    }

    Write-Host "Проверено файлов Unreal: $($packages.Count)." -ForegroundColor Green
    if (!$CheckOnly) {
        Write-Host 'Откройте этот файл в Unreal Engine 5.8:'
        Write-Host $project
    }
    exit 0
} catch {
    Write-Host ('ОШИБКА: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
