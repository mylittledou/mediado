# M3U8视频下载器使用说明

## 功能特点

- ✅ 通过m3u8地址自动下载视频
- ✅ 合并并转换为mp4格式
- ✅ 支持自定义文件名和保存路径
- ✅ 显示下载进度和实时速度
- ✅ 提供命令行和GUI两种使用方式
- ✅ 自动检查ffmpeg依赖
- ✅ 支持断点续传（理论上，实际取决于服务器支持）

## 环境要求

### 系统要求
- Windows 7/8/10/11
- macOS 10.14+
- Linux（Ubuntu 18.04+，CentOS 7+）

### 软件依赖

1. **Python 3.7+**
   - 下载地址：https://www.python.org/downloads/
   - 安装时请勾选"Add Python to PATH"

2. **FFmpeg**
   - 下载地址：https://ffmpeg.org/download.html
   - 安装后需要将ffmpeg添加到系统环境变量

## 安装步骤

### 1. 下载项目

将项目文件下载到本地目录，或者使用git克隆：

```bash
git clone <repository-url>
cd mediado
```

### 2. 安装Python依赖

打开命令行终端，进入项目目录，运行：

```bash
pip install -r requirements.txt
```

## 使用方式

### 方式一：命令行使用

**基本语法：**

```bash
python downloader.py -u <m3u8_url> -o <output_file> -p <save_path>
```

**参数说明：**

| 参数 | 简写 | 说明 | 是否必填 | 默认值 |
|------|------|------|----------|--------|
| --url | -u | m3u8视频地址 | 是 | 无 |
| --output | -o | 输出文件名 | 否 | output.mp4 |
| --path | -p | 保存路径 | 否 | 当前目录 |

**示例：**

```bash
# 基本使用
python downloader.py -u https://example.com/video.m3u8

# 自定义文件名
python downloader.py -u https://example.com/video.m3u8 -o "我的视频"

# 自定义保存路径和文件名
python downloader.py -u https://example.com/video.m3u8 -o "我的视频" -p D:\Downloads\Videos
```

### 方式二：GUI界面使用

**启动GUI：**

```bash
python downloader_gui.py
```

**使用步骤：**

1. 在"M3U8地址"输入框中粘贴m3u8链接
2. 在"输出文件名"输入框中设置保存的文件名
3. 点击"浏览"选择保存路径
4. 点击"开始下载"按钮
5. 等待下载完成，查看日志和进度条

## 常见问题

### 1. 错误：未检测到ffmpeg

**解决方法：**
- 确保已正确安装ffmpeg
- 将ffmpeg的bin目录添加到系统环境变量
- 重启命令行或GUI程序

### 2. 下载速度慢

**解决方法：**
- 检查网络连接
- 服务器可能限速，尝试其他时间下载
- 某些服务器可能限制并发连接数

### 3. 下载失败，提示"未找到ts片段"

**解决方法：**
- 检查m3u8地址是否正确
- 确认该m3u8链接是否可以正常访问
- 某些m3u8可能使用了加密或特殊格式，暂不支持

### 4. GUI界面卡顿

**解决方法：**
- 这是正常现象，因为下载过程会占用大量CPU和网络资源
- 请耐心等待，不要频繁操作界面

## 技术说明

### 工作原理

1. **下载m3u8文件**：从指定URL获取m3u8播放列表
2. **解析m3u8**：提取所有ts片段的URL
3. **下载ts片段**：逐个下载所有ts视频片段
4. **合并转换**：使用ffmpeg将多个ts片段合并为单个mp4文件
5. **清理临时文件**：删除下载过程中产生的临时文件

### 支持的m3u8格式

- 基本的m3u8格式
- 包含相对路径的m3u8
- 包含绝对路径的m3u8

### 暂不支持的格式

- 加密的m3u8（需要密钥解密）
- 动态生成的m3u8（如直播流）

## 开发说明

### 项目结构

```
mediado/
├── downloader.py          # 命令行版本下载器
├── downloader_gui.py      # GUI版本下载器
├── requirements.txt       # Python依赖
├── test_downloader.py     # 测试脚本
├── check_ffmpeg.py        # ffmpeg检查脚本
└── README.md              # 项目说明
```

### 测试

运行模拟测试：

```bash
python test_downloader.py
```

### 调试

如果遇到问题，可以查看：
- 命令行输出的错误信息
- GUI界面的日志窗口
- 确保ffmpeg已正确安装和配置

## 更新日志

### v1.0.0
- 首次发布
- 支持命令行和GUI两种使用方式
- 实现m3u8视频下载和mp4转换
- 显示下载进度和速度
- 自动检查ffmpeg依赖

## 后续计划

- [ ] 支持加密m3u8下载
- [ ] 支持批量下载
- [ ] 支持断点续传
- [ ] 支持更多视频格式转换
- [ ] 优化下载速度
- [ ] 实现Docker封装

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系开发者。
