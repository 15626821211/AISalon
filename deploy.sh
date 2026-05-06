#!/bin/bash
# AISalon 一键部署脚本
# 使用方式: bash deploy.sh

set -e

echo "========== AISalon 部署 =========="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，正在安装（阿里云镜像）..."
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo \
        -o /etc/yum.repos.d/docker-ce.repo 2>/dev/null || true
    curl -fsSL https://get.docker.com | sh -s -- --mirror Aliyun
    # 配置 Docker 镜像加速
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com", "https://docker.mirrors.ustc.edu.cn"]
}
EOF
    systemctl enable docker && systemctl start docker
    echo "✅ Docker 已安装"
fi

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装，正在安装..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose 已安装"
fi

# 检查 .env.production
if [ ! -f .env.production ]; then
    echo "⚠️  未找到 .env.production，从模板创建..."
    cp .env.production.example .env.production
    echo "📝 请编辑 .env.production 填入真实配置后重新运行此脚本"
    exit 1
fi

# 构建并启动
echo "🚀 构建并启动服务..."
docker compose up -d --build

echo ""
echo "========== 部署完成 =========="
echo "🌐 访问地址: http://$(hostname -I | awk '{print $1}')"
echo ""
echo "常用命令:"
echo "  查看日志:   docker compose logs -f app"
echo "  重启服务:   docker compose restart"
echo "  停止服务:   docker compose down"
echo "  更新部署:   git pull && docker compose up -d --build"
