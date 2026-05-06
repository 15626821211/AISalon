FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn httpx

# 复制项目代码
COPY src/ ./src/

WORKDIR /app/src

EXPOSE 5000

# Gunicorn 启动，4 worker，绑定 0.0.0.0:5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "300", "app:create_app()"]
