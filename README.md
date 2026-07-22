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
本项目提供基于 Flask 的 Web 界面以及完善的 Docker 部署方案，特别优化了在 NAS（如 QNAP Container Station）上的部署体验。

有关如何在 QNAP 上通过 Docker 进行部署和持续更新的详细指引，请参阅：
[QNAP Container Station 部署指南](QNAP_DEPLOYMENT.md)
