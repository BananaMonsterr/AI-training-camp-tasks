<#
 ============================================
 员工入离职管理系统 - 前端部署脚本
 作者：张铃 - 前端开发工程师
 版本：v1.0.0
 环境：Windows PowerShell 5.1+
 说明：设置UTF-8编码，检查资源，输出部署文件
 ============================================
#>

# =========================================
# 1. 设置控制台编码为 UTF-8（防乱码）
# =========================================
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[System.Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  员工入离职管理系统 - 前端部署脚本" -ForegroundColor Cyan
Write-Host "  作者：张铃 | 版本：v1.0.0" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# =========================================
# 2. 配置参数
# =========================================
# ★★★ 部署时请根据实际环境修改以下参数 ★★★
$Config = @{
    # 项目根目录（脚本所在目录的上级，即 frontend 目录）
    ProjectRoot  = $PSScriptRoot
    
    # 输出目录（部署到的目标目录）
    OutputDir    = Join-Path $PSScriptRoot "dist"
    
    # 需要部署的文件清单
    Files = @(
        "login.html",
        "index.html",
        "styles.css",
        "app.js"
    )
    
    # 是否创建压缩包
    CreateZip = $true
    
    # 部署模式: "local" 本地 | "server" 服务器
    DeployMode = "local"
    
    # 服务器部署路径（DeployMode 为 "server" 时生效）
    ServerPath = "C:\inetpub\wwwroot\hr-system"
}

# =========================================
# 3. 检查项目根目录
# =========================================
Write-Host "[1/5] 检查项目根目录..." -ForegroundColor Yellow

if (-not (Test-Path $Config.ProjectRoot)) {
    Write-Host "  ❌ 错误：项目目录不存在！" -ForegroundColor Red
    Write-Host "  路径: $($Config.ProjectRoot)" -ForegroundColor Red
    exit 1
}
Write-Host "  ✅ 项目目录：$($Config.ProjectRoot)" -ForegroundColor Green
Write-Host ""

# =========================================
# 4. 检查静态资源文件
# =========================================
Write-Host "[2/5] 检查静态资源文件..." -ForegroundColor Yellow

$missingFiles = @()
$foundFiles = @()

foreach ($file in $Config.Files) {
    $filePath = Join-Path $Config.ProjectRoot $file
    if (Test-Path $filePath) {
        $fileSize = (Get-Item $filePath).Length
        $foundFiles += @{
            Name = $file
            Size = "{0:N0} 字节" -f $fileSize
            Path = $filePath
        }
        Write-Host "  ✅ $file ($($foundFiles[-1].Size))" -ForegroundColor Green
    } else {
        $missingFiles += $file
        Write-Host "  ❌ $file - 文件不存在！" -ForegroundColor Red
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "  ⚠️  缺少以下文件，请检查项目目录：" -ForegroundColor Red
    foreach ($f in $missingFiles) {
        Write-Host "    - $f" -ForegroundColor Red
    }
    exit 1
}

Write-Host "  ✅ 所有静态资源检查通过" -ForegroundColor Green
Write-Host ""

# =========================================
# 5. 创建输出目录
# =========================================
Write-Host "[3/5] 创建输出目录..." -ForegroundColor Yellow

if (-not (Test-Path $Config.OutputDir)) {
    New-Item -ItemType Directory -Path $Config.OutputDir -Force | Out-Null
    Write-Host "  ✅ 已创建输出目录：$($Config.OutputDir)" -ForegroundColor Green
} else {
    Write-Host "  ✅ 输出目录已存在：$($Config.OutputDir)" -ForegroundColor Green
}
Write-Host ""

# =========================================
# 6. 复制文件到输出目录
# =========================================
Write-Host "[4/5] 复制文件到输出目录..." -ForegroundColor Yellow

$copySuccess = $true
foreach ($file in $Config.Files) {
    $source = Join-Path $Config.ProjectRoot $file
    $dest = Join-Path $Config.OutputDir $file
    try {
        # 使用 UTF-8 编码复制文件内容
        $content = Get-Content -Path $source -Raw -Encoding UTF8
        # 确保写入时也是 UTF-8
        [System.IO.File]::WriteAllText($dest, $content, [System.Text.UTF8Encoding]::new($false))
        Write-Host "  ✅ 已复制：$file" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ 复制失败：$file - $_" -ForegroundColor Red
        $copySuccess = $false
    }
}

if (-not $copySuccess) {
    Write-Host "  ⚠️  部分文件复制失败，请检查上述错误" -ForegroundColor Red
} else {
    Write-Host "  ✅ 所有文件复制完成" -ForegroundColor Green
}
Write-Host ""

# =========================================
# 7. 创建部署摘要文件
# =========================================
$summaryLines = @(
    "=============================================",
    "  员工入离职管理系统 - 前端部署摘要",
    "  部署时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "=============================================",
    "",
    "部署目录: $($Config.OutputDir)",
    "文件清单:"
)

$totalSize = 0
foreach ($file in $Config.Files) {
    $filePath = Join-Path $Config.OutputDir $file
    if (Test-Path $filePath) {
        $size = (Get-Item $filePath).Length
        $totalSize += $size
        $summaryLines += "  - $file ($("{0:N0}" -f $size) 字节)"
    }
}

$summaryLines += ""
$summaryLines += "总大小: $("{0:N0}" -f $totalSize) 字节"
$summaryLines += "部署模式: $($Config.DeployMode)"
$summaryLines += ""

if ($Config.DeployMode -eq "server") {
    $summaryLines += "服务器路径: $($Config.ServerPath)"
}

$summaryLines | Out-File -FilePath (Join-Path $Config.OutputDir "deploy-summary.txt") -Encoding UTF8
Write-Host "  ✅ 已生成部署摘要：deploy-summary.txt" -ForegroundColor Green

# =========================================
# 可选：创建 ZIP 压缩包
# =========================================
if ($Config.CreateZip) {
    $zipName = "hr-system-frontend-v1.0.0-$(Get-Date -Format 'yyyyMMdd').zip"
    $zipPath = Join-Path $PSScriptRoot $zipName
    
    # 如果已存在则删除
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }
    
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory($Config.OutputDir, $zipPath)
        $zipSize = (Get-Item $zipPath).Length
        Write-Host "  ✅ 已创建压缩包：$zipName ($("{0:N0}" -f $zipSize) 字节)" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  创建压缩包失败：$_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ✅ 前端部署完成！" -ForegroundColor Green
Write-Host "  输出目录: $($Config.OutputDir)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# =========================================
# 服务器部署模式（可选）
# =========================================
if ($Config.DeployMode -eq "server") {
    Write-Host ""
    Write-Host "[5/5] 部署到服务器..." -ForegroundColor Yellow
    
    $serverDir = $Config.ServerPath
    if (-not (Test-Path $serverDir)) {
        try {
            New-Item -ItemType Directory -Path $serverDir -Force | Out-Null
            Write-Host "  ✅ 已创建服务器目录：$serverDir" -ForegroundColor Green
        } catch {
            Write-Host "  ❌ 无法创建服务器目录：$serverDir" -ForegroundColor Red
            Write-Host "  请手动将 dist/ 目录下的文件复制到服务器对应位置" -ForegroundColor Yellow
        }
    }
    
    foreach ($file in $Config.Files) {
        $source = Join-Path $Config.OutputDir $file
        $dest = Join-Path $serverDir $file
        try {
            Copy-Item -Path $source -Destination $dest -Force
            Write-Host "  ✅ 已部署：$file" -ForegroundColor Green
        } catch {
            Write-Host "  ❌ 部署失败：$file - $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "提示: 部署完成后，可通过浏览器访问 index.html（需Web服务器）" -ForegroundColor Magenta
Write-Host "或直接打开 login.html 文件进行本地预览（部分API功能需服务器环境）" -ForegroundColor Magenta
