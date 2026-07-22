# 视频下载器

## 功能说明
- 通过输入视频网页地址或m3u8地址自动嗅探并下载视频
- 合并并转换为mp4格式
- 支持自定义文件名和保存路径
- 显示下载进度和下载速度

## 依赖安装
```bash
pip install -r requirements.txt
```

## 使用方法
```bash
python downloader.py -u <m3u8_url> -o <output_file> -p <save_path>
```

## 参数说明
- `-u, --url`: 视频网页地址或m3u8地址（必填）
- `-o, --output`: 输出文件名（可选，默认：output.mp4）
- `-p, --path`: 保存路径（可选，默认：当前目录）

## Web UI 与 Docker 部署
本项目提供基于 Flask 的 Web 界面，推荐使用 Docker 进行部署（支持 GitHub Actions 自动构建）。

### 部署配置说明
在部署前，请确保在宿主机（如 NAS）上准备好以下目录映射结构，并在 `docker-compose.yml` 中配置环境变量：

#### 1. 挂载目录 (Volumes) 说明
*   **`/app/downloads`**：用于存放**最终下载完成的视频文件**。这是最重要的文件夹。
*   **`/app/logs`**：用于存放**程序的运行日志**。出现下载失败等问题时，排查日志用到。
*   **`/app/thumbnails`**：用于存放视频的**缩略图封面**（如果程序抓取到了的话）。
*   **`/app/tasks.json`**：**（极其重要）** 这是用来存储你所有“下载历史记录”的数据库文件。**注意：在启动 Docker 前，你必须在宿主机的对应位置手动创建一个名为 `tasks.json` 的空白文本文件**，否则 Docker 会把它当成一个文件夹来创建，导致程序崩溃。

#### 2. 环境变量 (Environment) 说明
*   `TZ=Asia/Shanghai`：设置正确的时区，确保下载时间和日志时间准确。
*   `SECRET_KEY=你的随机字符串`：Flask 网站的安全密钥，建议随便敲一串复杂的英文字母，防止系统被攻击。
*   `AUTH_USERNAME=你的账号`：Web 界面的登录账号。
*   `AUTH_PASSWORD=你的密码`：Web 界面的登录密码。

有关如何在 QNAP 等 NAS 设备上通过 Docker 进行部署和持续更新的详细指引，请参阅：
[QNAP Container Station 部署指南](QNAP_DEPLOYMENT.md)
