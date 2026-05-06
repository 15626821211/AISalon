#!/bin/bash
# AISalon 一键部署脚本
# 前置要求: CentOS 7/8, root 权限, 已安装 Docker 和 Docker Compose
# 使用方式: bash deploy.sh

set -e

echo "========== AISalon 部署 =========="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装 Docker，参考部署文档"
    exit 1
fi

# 检查 docker compose
if ! docker compose version &> /dev/null; then
    echo "❌ 请先安装 Docker Compose，参考部署文档"
    exit 1
fi

# 检查 .env.production
if [ ! -f .env.production ]; then
    cp .env.production.example .env.production
    echo "⚠️  已创建 .env.production，请编辑填入真实配置后重新运行"
    echo "   vi .env.production"
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
