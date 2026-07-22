# QNAP Container Station 部署指南

本指南介绍如何将该 M3U8 视频下载器部署到 QNAP 的 Container Station 中。
通过 Docker 部署可以让你随时随地访问 Web 界面进行视频下载，且下载的文件可以直接保存在 NAS 中。

## 前置准备：使用 GitHub 全自动打包（无需在本地安装 Docker）

考虑到你可能在办公电脑上无法安装 Docker，我们直接采用最高效的 **GitHub Actions 云端自动打包** 方案。
你只需要把代码上传到 GitHub，GitHub 的服务器就会自动帮你打包成镜像，并存放到 GitHub 的镜像库 (`ghcr.io`) 中。

1. **注册并登录 GitHub** (https://github.com/)。
2. **创建一个新的代码仓库 (Repository)**，例如命名为 `mediado`。注意将仓库设置为 **Public (公开)**（如果是私有仓库，QNAP 拉取镜像时需要额外配置复杂的登录凭证）。
3. **将本程序的所有文件上传到这个仓库中**。
   *(你可以直接在网页端点击 `Add file -> Upload files` 把所有文件拖进去，或者使用 Git 命令行推送)*。
4. **等待 GitHub 自动打包**：
   我已经为你写好了自动打包脚本(`.github/workflows/docker-publish.yml`)。只要你把文件传上 GitHub，它就会在后台自动开始构建 Docker 镜像。
   你可以点击仓库页面的 **Actions** 标签页查看打包进度。绿色打勾即代表打包成功！

打包成功后，你的镜像地址就是：
`ghcr.io/你的GitHub用户名/仓库名:latest` (例如：`ghcr.io/zhangsan/mediado:latest`)。

---

## 在 QNAP Container Station 中部署

1. 登录 QNAP 的 Web 界面，打开 **Container Station (容器工作站)**。
2. 在左侧菜单选择 **应用程序 (Applications)**，点击右上角的 **创建 (Create)**。
3. 应用程序名称填写：`mediado-downloader`（或任意你喜欢的名字）。
4. 将 `docker-compose.qnap.yml` 文件中的内容复制到 YAML 代码框中。

### 需要注意的核心参数配置

在复制 YAML 代码之前，请仔细核对并修改以下几个核心配置：

#### 1. 镜像名称 (Image)
请确保 `image` 字段填写的是你刚刚推送到 Docker Hub 的镜像名称：
```yaml
image: your-dockerhub-username/mediado:latest
```

#### 2. 持久化目录映射 (Volumes)
为了保证你下载的视频、日志和任务记录在容器重启或更新后不丢失，**必须**配置持久化目录映射。
假设你在 QNAP 的 `Container` 共享文件夹下新建了一个 `mediado` 目录，目录结构需要映射如下：

```yaml
volumes:
  # 格式: 宿主机(NAS)物理路径 : 容器内路径
  - /share/Container/mediado/downloads:/app/downloads   # 用于存放下载完成的视频文件
  - /share/Container/mediado/logs:/app/logs             # 用于存放运行日志
  - /share/Container/mediado/thumbnails:/app/thumbnails # 用于存放视频的缩略图
  - /share/Container/mediado/data/tasks.json:/app/tasks.json # 用于持久化保存任务列表
```
> [!WARNING]
> **极其重要的提示**：对于 `tasks.json` 的映射，Docker 会默认把宿主机上不存在的路径当作“文件夹”来创建。为了避免报错，**请务必在启动容器之前，通过 File Station 或 SSH 在 NAS 的 `/share/Container/mediado/data/` 目录下手动创建一个名为 `tasks.json` 的空文件**，或者在 YAML 中去掉这一行的映射（如果不介意重启后丢失历史任务列表的话）。

#### 3. 环境变量参数 (Environment)
你可以根据需求修改运行参数：
```yaml
environment:
  - TZ=Asia/Shanghai                  # 设置时区，确保日志时间正确
  - SECRET_KEY=your_secret_key_here   # Flask 的 Session 密钥，请务必修改为一串复杂的随机字符，保证安全
  - AUTH_USERNAME=admin               # Web 界面的登录用户名
  - AUTH_PASSWORD=password            # Web 界面的登录密码
```
> [!IMPORTANT]
> 部署到公网访问时，一定要修改 `AUTH_USERNAME` 和 `AUTH_PASSWORD`，防止被他人恶意使用下载器导致 NAS 宽带和存储被占满。

### 启动与更新

5. 配置检查无误后，点击底部的 **创建 (Create)** 按钮。Container Station 会自动拉取镜像并启动服务。
6. 启动成功后，在浏览器访问 `http://你的NAS_IP:5000` 即可使用。
7. **如何更新版本**：当你在本地修复了 Bug 或增加了功能，并 `push` 了新的 `latest` 镜像后，只需要在 Container Station 的应用程序列表中，找到 `mediado-downloader`，点击右上角的 **重新创建 (Recreate)**。系统会自动拉取最新镜像并重启，得益于上述的 Volumes 映射，你的所有数据都不会丢失。
