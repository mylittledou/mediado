FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    aria2 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements_web.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements_web.txt

# 复制应用程序代码
COPY . .

# 创建下载目录
RUN mkdir -p /downloads

# 设置环境变量
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "app.py"]