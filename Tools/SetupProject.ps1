# Run SETUP_PROJECT.bat from the project root. Compatible with Windows PowerShell 5.1.
[CmdletBinding()]
param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$repositoryUrl = 'https://github.com/Username3000/Fruit_Example.git'
$projectRoot = Split-Path -Parent $PSScriptRoot
$logPath = $null
$transcriptStarted = $false

function Update-ProcessPath {
    param([switch]$AfterInstall)
    $paths = @($env:PATH)
    if ($AfterInstall) {
        $paths += [Environment]::GetEnvironmentVariable('Path', 'Machine')
        $paths += [Environment]::GetEnvironmentVariable('Path', 'User')
    }
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
        if ($base) { $paths += (Join-Path $base 'Git LFS') }
    }
    $env:PATH = ($paths | Where-Object { $_ }) -join ';'
}

function Find-Git {
    # Prefer the same Git/LFS bundle that students already use through Desktop.
    $candidates = @()
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if ($base) {
            $candidates += Join-Path $base 'GitHub Desktop\resources\app\git\cmd\git.exe'
        }
    }
    if ($env:LOCALAPPDATA) {
        $desktopRoot = Join-Path $env:LOCALAPPDATA 'GitHubDesktop'
        if (Test-Path -LiteralPath $desktopRoot) {
            $versions = Get-ChildItem -LiteralPath $desktopRoot -Directory -Filter 'app-*' |
                Sort-Object LastWriteTime -Descending
            foreach ($version in $versions) {
                $candidates += Join-Path $version.FullName 'resources\app\git\cmd\git.exe'
            }
        }
    }
    $command = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if ($base) { $candidates += Join-Path $base 'Git\cmd\git.exe' }
    }
    if ($env:LOCALAPPDATA) { $candidates += Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe' }
    # Native programs can write expected discovery errors to stderr in PowerShell 5.1.
    $ErrorActionPreference = 'Continue'
    $firstGit = $null
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        & $candidate --version *> $null
        if ($LASTEXITCODE -ne 0) { continue }
        if (-not $firstGit) { $firstGit = $candidate }
        & $candidate lfs version *> $null
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{ Path = $candidate; HasLfs = $true }
        }
    }
    if ($firstGit) { return [pscustomobject]@{ Path = $firstGit; HasLfs = $false } }
}

function Install-PackageWithWinget([string]$Id) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'Не найден winget. Установите или обновите GitHub Desktop: https://desktop.github.com/ Затем снова запустите батник.'
    }
    Write-Host "Установка $Id. Windows может запросить разрешение на установку."
    $ErrorActionPreference = 'Continue'
    & $winget.Source install --id $Id --exact --source winget --silent --no-upgrade --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось установить $Id (код $LASTEXITCODE). Проверьте сообщение выше и подключение к интернету."
    }
    Update-ProcessPath -AfterInstall
}

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$GitArguments)
    $ErrorActionPreference = 'Continue'
    & $script:gitPath @GitArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Команда git $($GitArguments -join ' ') завершилась с кодом $LASTEXITCODE. См. сообщение выше."
    }
}

function Get-NormalizedRemote([string]$Url) {
    return ($Url.Trim().TrimEnd('/', '\') -replace '\.git$', '')
}

function Test-ProjectFiles {
    $entries = @(Invoke-Git -GitArguments @('-c', 'core.quotePath=false', 'lfs', 'ls-files', '--name-only', '--include=*', '--exclude='))
    $unavailable = @()
    foreach ($assetPath in $entries) {
        $fullPath = Join-Path $projectRoot $assetPath
        if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
            $unavailable += $assetPath
            continue
        }
        # The '-' marker in ls-files also denotes edited files with a different
        # size. Inspect the pointer signature instead, preserving student edits.
        $stream = [IO.File]::OpenRead($fullPath)
        try {
            $buffer = New-Object byte[] 256
            $count = $stream.Read($buffer, 0, $buffer.Length)
            $prefix = [Text.Encoding]::ASCII.GetString($buffer, 0, $count)
            if ($count -eq 0 -or $prefix.StartsWith('version https://git-lfs.github.com/spec/v1')) {
                $unavailable += $assetPath
            }
        } finally {
            $stream.Dispose()
        }
    }
    if ($unavailable.Count -gt 0) {
        $examples = ($unavailable | Select-Object -First 5) -join ', '
        throw "Остались указатели LFS или отсутствующие файлы: $($unavailable.Count). Например: $examples. Если ассеты изменялись вручную, сохраните свои изменения отдельно перед восстановлением через GitHub Desktop."
    }
    $map = Join-Path $projectRoot 'Content\Root\Maps\L_Example.umap'
    if (-not (Test-Path -LiteralPath $map -PathType Leaf)) { throw 'Не найдена карта L_Example.umap.' }
    $mapSize = (Get-Item -LiteralPath $map).Length
    if ($mapSize -lt 1024) { throw "Карта подозрительно мала: $mapSize байт. Возможно, это указатель LFS." }
    Write-Host "Проверено LFS-файлов: $($entries.Count). Размер карты: $mapSize байт."
}

try {
    if (-not $CheckOnly) {
        try {
            $logPath = Join-Path ([IO.Path]::GetTempPath()) ("FruitExample-Setup-$(Get-Date -Format 'yyyyMMdd-HHmmss')-$PID.log")
            Start-Transcript -Path $logPath -Force | Out-Null
            $transcriptStarted = $true
        } catch {
            $logPath = $null
            Write-Host 'Не удалось сохранить журнал. При ошибке скопируйте текст из этого окна.'
        }
    }
    Write-Host 'Fruit Example: подготовка Git и скачивание ассетов.'
    Write-Host 'Перед обычным запуском закройте этот проект в Unreal Editor.'
    Write-Host "Windows: $([Environment]::OSVersion.Version); PowerShell: $($PSVersionTable.PSVersion)"
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'Fruit_Example.uproject'))) {
        throw 'Не найден Fruit_Example.uproject. Сохраните батник и папку Tools вместе с остальным проектом.'
    }
    Set-Location -LiteralPath $projectRoot
    Update-ProcessPath
    $gitTool = Find-Git
    if (-not $gitTool) {
        if ($CheckOnly) { throw 'Git не найден. Для автоматической установки запустите батник без -CheckOnly.' }
        Install-PackageWithWinget 'Git.Git'
        $gitTool = Find-Git
        if (-not $gitTool) { throw 'После установки Git не найден. Перезапустите батник.' }
    }
    if (-not $gitTool.HasLfs) {
        if ($CheckOnly) { throw 'Git LFS не найден. Для установки запустите батник без -CheckOnly.' }
        Install-PackageWithWinget 'GitHub.GitLFS'
        $gitTool = Find-Git
        if (-not $gitTool -or -not $gitTool.HasLfs) { throw 'Git LFS не найден после установки. Перезапустите батник.' }
    }
    $script:gitPath = $gitTool.Path
    $env:PATH = (Split-Path -Parent $gitPath) + ';' + $env:PATH
    Write-Host "Git: $gitPath"
    Invoke-Git -GitArguments @('--version')
    Invoke-Git -GitArguments @('lfs', 'version')

    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.git'))) {
        Write-Host 'В этой папке нет .git: это архив или копия без истории Git.'
        $cloneRoot = Join-Path (Split-Path -Parent $projectRoot) 'Fruit_Example-Ready'
        if ($CheckOnly) {
            Write-Host "Обычный запуск скачает или проверит клон в: $cloneRoot"
            Write-Host 'Проверка завершена. Изменений нет.'
            exit 0
        }
        if (Test-Path -LiteralPath $cloneRoot) {
            if (-not (Test-Path -LiteralPath (Join-Path $cloneRoot '.git')) -or
                -not (Test-Path -LiteralPath (Join-Path $cloneRoot 'Fruit_Example.uproject') -PathType Leaf)) {
                throw "Папка $cloneRoot уже существует, но в ней нет полного клона проекта. Переместите её и снова запустите батник."
            }
            $existingOrigin = @(Invoke-Git -GitArguments @('-C', $cloneRoot, 'remote', 'get-url', 'origin'))
            if ((Get-NormalizedRemote $existingOrigin[-1]) -ne (Get-NormalizedRemote $repositoryUrl)) {
                throw "Папка $cloneRoot относится к другому репозиторию. Переместите её и снова запустите батник."
            }
            Write-Host "Повторная проверка и скачивание ассетов в: $cloneRoot"
        } else {
            Write-Host "Скачивание проекта в новую папку: $cloneRoot"
            # Download LFS in a separate step so failed asset downloads can be retried.
            $previousSkipSmudge = $env:GIT_LFS_SKIP_SMUDGE
            try {
                $env:GIT_LFS_SKIP_SMUDGE = '1'
                Invoke-Git -GitArguments @('clone', '--', $repositoryUrl, $cloneRoot)
            } finally {
                $env:GIT_LFS_SKIP_SMUDGE = $previousSkipSmudge
            }
        }
        $projectRoot = $cloneRoot
        Set-Location -LiteralPath $projectRoot
    }

    $topLevel = @(Invoke-Git -GitArguments @('rev-parse', '--show-toplevel'))
    if ([IO.Path]::GetFullPath($topLevel[-1]) -ne [IO.Path]::GetFullPath($projectRoot)) {
        throw 'Корень Git не совпадает с папкой проекта. Запустите батник из полного клона Fruit_Example.'
    }
    if ($CheckOnly) {
        Test-ProjectFiles
        Write-Host 'Проверка завершена. Изменений нет.'
        exit 0
    }

    Invoke-Git -GitArguments @('lfs', 'install', '--local')
    Write-Host 'Скачивание файлов Git LFS. Дождитесь завершения; окно не закрывайте.'
    Invoke-Git -GitArguments @('lfs', 'pull', '--include=*', '--exclude=', 'origin')
    Test-ProjectFiles
    Write-Host ''
    Write-Host 'ГОТОВО. Откройте в Unreal Engine 5.8 этот файл:' -ForegroundColor Green
    Write-Host (Join-Path $projectRoot 'Fruit_Example.uproject') -ForegroundColor Green
    if ($logPath) { Write-Host "Журнал проверки: $logPath" }
    exit 0
} catch {
    Write-Host ''
    Write-Host ('ОШИБКА: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'При ошибке скачивания проверьте интернет и доступ к репозиторию.'
    Write-Host 'Для закрытого репозитория сначала клонируйте его через GitHub Desktop, затем запустите батник из клона.'
    Write-Host 'Сообщения о quota/bandwidth/budget требуют проверки лимитов LFS владельцем репозитория.'
    if ($logPath) { Write-Host "Отправьте преподавателю этот файл с журналом: $logPath" }
    Write-Host 'Скопируйте сообщение об ошибке преподавателю. После исправления причины батник можно запустить повторно.'
    exit 1
} finally {
    if ($transcriptStarted) { Stop-Transcript -ErrorAction SilentlyContinue | Out-Null }
}
