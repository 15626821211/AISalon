FROM docker.m.daocloud.io/python:3.12-slim

WORKDIR /app

# 使用阿里云镜像源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（阿里云 PyPI 镜像）
COPY src/requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    -r requirements.txt gunicorn httpx

# 复制项目代码
COPY src/ ./src/

WORKDIR /app/src

EXPOSE 5000

# Gunicorn 启动，preload 确保建表只执行一次，4 worker
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "300", "--preload", "app:create_app()"]
