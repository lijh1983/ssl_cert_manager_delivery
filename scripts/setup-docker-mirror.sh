#!/bin/bash

# Docker镜像加速器配置脚本
# 用于配置阿里云Docker镜像加速器，提升镜像拉取速度

set -e

echo "=== Docker镜像加速器配置脚本 ==="
echo "配置时间: $(date)"
echo "==============================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 此脚本需要root权限运行${NC}"
    echo "请使用: sudo $0"
    exit 1
fi

# 检查Docker是否已安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker未安装${NC}"
    echo "请先安装Docker后再运行此脚本"
    exit 1
fi

echo -e "${BLUE}1. 检查当前Docker配置${NC}"

# 检查Docker daemon配置文件
DOCKER_CONFIG_DIR="/etc/docker"
DOCKER_CONFIG_FILE="$DOCKER_CONFIG_DIR/daemon.json"

if [ ! -d "$DOCKER_CONFIG_DIR" ]; then
    echo -e "${YELLOW}创建Docker配置目录: $DOCKER_CONFIG_DIR${NC}"
    mkdir -p "$DOCKER_CONFIG_DIR"
fi

# 备份现有配置
if [ -f "$DOCKER_CONFIG_FILE" ]; then
    echo -e "${YELLOW}备份现有配置文件${NC}"
    cp "$DOCKER_CONFIG_FILE" "$DOCKER_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "备份文件: $DOCKER_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
fi

echo -e "\n${BLUE}2. 配置阿里云镜像加速器${NC}"

# 阿里云镜像加速器地址列表
MIRROR_URLS=(
    "https://registry.cn-hangzhou.aliyuncs.com"
    "https://docker.mirrors.ustc.edu.cn"
    "https://hub-mirror.c.163.com"
    "https://mirror.baidubce.com"
)

# 创建新的daemon.json配置
cat > "$DOCKER_CONFIG_FILE" << EOF
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "exec-opts": ["native.cgroupdriver=systemd"],
  "live-restore": true,
  "userland-proxy": false,
  "experimental": false,
  "debug": false
}
EOF

echo -e "${GREEN}✓ Docker配置文件已更新${NC}"
echo "配置文件位置: $DOCKER_CONFIG_FILE"

echo -e "\n${BLUE}3. 重启Docker服务${NC}"

# 重新加载systemd配置
systemctl daemon-reload

# 重启Docker服务
if systemctl restart docker; then
    echo -e "${GREEN}✓ Docker服务重启成功${NC}"
else
    echo -e "${RED}✗ Docker服务重启失败${NC}"
    exit 1
fi

# 等待Docker服务完全启动
sleep 3

echo -e "\n${BLUE}4. 验证配置${NC}"

# 检查Docker服务状态
if systemctl is-active --quiet docker; then
    echo -e "${GREEN}✓ Docker服务运行正常${NC}"
else
    echo -e "${RED}✗ Docker服务未正常运行${NC}"
    exit 1
fi

# 显示Docker信息
echo -e "\n${BLUE}5. Docker配置信息${NC}"
docker info | grep -A 10 "Registry Mirrors:" || echo "未找到镜像加速器配置"

echo -e "\n${BLUE}6. 测试镜像拉取${NC}"

# 测试拉取小镜像
echo "测试拉取hello-world镜像..."
if docker pull hello-world:latest; then
    echo -e "${GREEN}✓ 镜像拉取测试成功${NC}"
    # 清理测试镜像
    docker rmi hello-world:latest >/dev/null 2>&1 || true
else
    echo -e "${RED}✗ 镜像拉取测试失败${NC}"
fi

echo -e "\n==============================="
echo -e "${GREEN}🎉 Docker镜像加速器配置完成！${NC}"
echo -e "${BLUE}配置的镜像加速器:${NC}"
for url in "${MIRROR_URLS[@]}"; do
    echo "  - $url"
done

echo -e "\n${BLUE}使用说明:${NC}"
echo "1. 现在可以正常使用docker pull命令拉取镜像"
echo "2. 镜像拉取速度应该有显著提升"
echo "3. 如需恢复原配置，请使用备份文件"

echo -e "\n${BLUE}测试命令:${NC}"
echo "docker pull node:18-alpine"
echo "docker pull python:3.10-slim"
echo "docker pull nginx:1.24-alpine"
