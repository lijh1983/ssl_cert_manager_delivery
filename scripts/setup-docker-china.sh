#!/bin/bash

# Docker 中国国内镜像源配置脚本
# 用于解决中国国内网络访问 Docker Hub 的问题

set -e

echo "=== Docker 中国国内镜像源配置脚本 ==="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 创建Docker配置目录
mkdir -p /etc/docker

# 备份现有配置
if [ -f /etc/docker/daemon.json ]; then
    echo "备份现有Docker配置..."
    cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
fi

# 配置Docker镜像源
echo "配置Docker镜像源..."
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://ccr.ccs.tencentyun.com"
  ],
  "insecure-registries": [],
  "debug": false,
  "experimental": false,
  "features": {
    "buildkit": true
  },
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "20GB"
    }
  }
}
EOF

echo "Docker配置文件已更新："
cat /etc/docker/daemon.json

# 重启Docker服务
echo "重启Docker服务..."
systemctl daemon-reload
systemctl restart docker

# 验证配置
echo "验证Docker配置..."
docker info | grep -A 10 "Registry Mirrors" || echo "镜像源配置可能未生效，请检查Docker版本"

echo "=== Docker 中国国内镜像源配置完成 ==="
echo ""
echo "现在可以尝试构建镜像："
echo "docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base.china ./backend"
echo ""
echo "如果仍有问题，请尝试："
echo "1. 重启Docker服务: sudo systemctl restart docker"
echo "2. 清理Docker缓存: docker system prune -a"
echo "3. 使用代理或VPN"
