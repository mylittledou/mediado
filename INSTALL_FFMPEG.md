# FFmpeg安装和配置指南

## 问题描述
当运行m3u8下载器时，出现"未检测到ffmpeg"的错误，这是因为系统中没有安装ffmpeg或者ffmpeg没有添加到系统环境变量中。

## 解决方案

### Windows系统安装步骤

#### 1. 下载FFmpeg

1. 访问FFmpeg官网下载页面：https://ffmpeg.org/download.html
2. 在"Windows"部分，点击"Windows builds from gyan.dev"
3. 在新页面中，找到"release builds"部分，下载最新版本的"ffmpeg-release-full.7z"
   - 例如：ffmpeg-release-full.7z

#### 2. 解压FFmpeg

1. 下载7-Zip解压工具（如果没有的话）：https://www.7-zip.org/download.html
2. 使用7-Zip解压下载的ffmpeg-release-full.7z文件
3. 解压后会得到一个文件夹，例如：ffmpeg-7.0-full_build
4. 将该文件夹重命名为"ffmpeg"，并移动到C盘根目录，最终路径为：C:\ffmpeg

#### 3. 添加到系统环境变量

1. 右键点击"此电脑"或"我的电脑"，选择"属性"
2. 点击"高级系统设置"
3. 点击"环境变量"
4. 在"系统变量"中找到"Path"变量，点击"编辑"
5. 点击"新建"，输入：C:\ffmpeg\bin
6. 点击"确定"保存所有更改

#### 4. 验证安装

1. 打开新的命令行窗口（重要：必须重新打开，否则环境变量不会生效）
2. 运行命令：`ffmpeg -version`
3. 如果显示FFmpeg版本信息，则安装成功

### macOS系统安装步骤

#### 方法1：使用Homebrew（推荐）

1. 安装Homebrew（如果没有的话）：
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. 安装FFmpeg：
   ```bash
   brew install ffmpeg
   ```

3. 验证安装：
   ```bash
   ffmpeg -version
   ```

#### 方法2：手动安装

1. 访问FFmpeg官网下载页面：https://ffmpeg.org/download.html
2. 在"macOS"部分，点击"Static Builds for macOS 64-bit"
3. 下载最新版本的静态编译包
4. 解压并将ffmpeg添加到系统路径

### Linux系统安装步骤

#### Ubuntu/Debian系统

```bash
sudo apt update
sudo apt install ffmpeg
```

#### CentOS/RHEL系统

```bash
sudo yum install epel-release
sudo yum install ffmpeg ffmpeg-devel
```

#### 验证安装

```bash
ffmpeg -version
```

## 安装完成后

安装并配置好FFmpeg后，重新运行m3u8下载器：

```bash
# 命令行版本
python downloader.py -u <m3u8_url>

# GUI版本
python downloader_gui.py
```

## 常见问题

### 1. 仍然显示"未检测到ffmpeg"

- 确保已经重新打开了命令行窗口
- 检查环境变量是否正确添加
- 重启计算机后再次尝试

### 2. 命令行可以运行ffmpeg，但GUI版本仍然报错

- 确保GUI程序是在FFmpeg安装完成后启动的
- 尝试重启GUI程序
- 检查系统环境变量是否正确配置

### 3. 下载的FFmpeg版本不兼容

- 建议下载最新稳定版本
- 确保下载的版本与系统位数匹配（32位或64位）

## 自动化安装脚本（Windows）

对于Windows用户，也可以使用以下PowerShell脚本自动下载和安装FFmpeg：

```powershell
# 以管理员身份运行PowerShell

# 设置下载链接和安装路径
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z"
$downloadPath = "$env:TEMP\ffmpeg-release-full.7z"
$extractPath = "C:\"
$ffmpegPath = "C:\ffmpeg"

# 下载FFmpeg
Write-Host "正在下载FFmpeg..."
Invoke-WebRequest -Uri $ffmpegUrl -OutFile $downloadPath

# 安装7-Zip（如果没有）
if (-not (Test-Path "$env:ProgramFiles\7-Zip\7z.exe")) {
    Write-Host "正在安装7-Zip..."
    $7zipUrl = "https://www.7-zip.org/a/7z2301-x64.exe"
    $7zipInstaller = "$env:TEMP\7z2301-x64.exe"
    Invoke-WebRequest -Uri $7zipUrl -OutFile $7zipInstaller
    Start-Process -FilePath $7zipInstaller -ArgumentList "/S" -Wait
}

# 解压FFmpeg
Write-Host "正在解压FFmpeg..."
& "$env:ProgramFiles\7-Zip\7z.exe" x $downloadPath -o"$extractPath" -y

# 查找解压后的文件夹
$extractedFolder = Get-ChildItem -Path $extractPath -Name "ffmpeg-*-full_build" -Directory

# 重命名并移动到C盘根目录
if ($extractedFolder) {
    Remove-Item -Path $ffmpegPath -Recurse -ErrorAction SilentlyContinue
    Rename-Item -Path "$extractPath\$extractedFolder" -NewName "ffmpeg"
    Write-Host "FFmpeg已解压到：$ffmpegPath"
}

# 添加到环境变量
Write-Host "正在添加到系统环境变量..."
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if (-not $currentPath.Contains("$ffmpegPath\bin")) {
    $newPath = "$currentPath;$ffmpegPath\bin"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
    Write-Host "FFmpeg已添加到系统环境变量"
}

# 清理临时文件
Remove-Item -Path $downloadPath -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "FFmpeg安装完成！请重新打开命令行窗口并运行 'ffmpeg -version' 验证安装。"
```

将以上脚本保存为`install_ffmpeg.ps1`，然后以管理员身份运行PowerShell，执行：
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.nstall_ffmpeg.ps1
```
