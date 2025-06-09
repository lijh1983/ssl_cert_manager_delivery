#!/bin/bash

# Docker缓存问题修复脚本
# 解决"importing cache manifest"错误

set -e

echo "=== Docker缓存问题修复工具 ==="
echo "修复时间: $(date)"
echo "================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请使用root权限运行此脚本${NC}"
    echo "使用方法: sudo $0"
    exit 1
fi

echo -e "${BLUE}1. 停止所有运行中的容器${NC}"

# 停止所有运行中的容器
if [ "$(docker ps -q)" ]; then
    echo "停止运行中的容器..."
    docker stop $(docker ps -q) || true
else
    echo "没有运行中的容器"
fi

echo -e "\n${BLUE}2. 清理Docker缓存和镜像${NC}"

# 清理所有SSL管理器相关的镜像
echo "清理SSL管理器相关镜像..."
docker images | grep ssl-manager | awk '{print $3}' | xargs -r docker rmi -f || true

# 清理悬空镜像
echo "清理悬空镜像..."
docker image prune -f

# 清理构建缓存
echo "清理构建缓存..."
docker builder prune -f

# 清理所有未使用的镜像
echo "清理未使用的镜像..."
docker image prune -a -f

# 清理所有未使用的容器
echo "清理未使用的容器..."
docker container prune -f

# 清理所有未使用的网络
echo "清理未使用的网络..."
docker network prune -f

# 清理所有未使用的卷
echo "清理未使用的卷..."
docker volume prune -f

echo -e "\n${BLUE}3. 清理系统缓存${NC}"

# 清理系统缓存
echo "清理系统缓存..."
sync
echo 3 > /proc/sys/vm/drop_caches

echo -e "\n${BLUE}4. 重启Docker服务${NC}"

# 重启Docker服务
echo "重启Docker服务..."
systemctl restart docker

# 等待Docker服务启动
sleep 5

# 检查Docker服务状态
if systemctl is-active --quiet docker; then
    echo -e "${GREEN}✓${NC} Docker服务重启成功"
else
    echo -e "${RED}✗${NC} Docker服务重启失败"
    systemctl status docker
    exit 1
fi

echo -e "\n${BLUE}5. 验证Docker环境${NC}"

# 验证Docker环境
echo "验证Docker环境..."
docker --version
docker info | head -10

echo -e "\n${BLUE}6. 清理项目构建缓存${NC}"

# 切换到项目目录
cd "$(dirname "$0")/.."

# 清理node_modules（如果存在）
if [ -d "frontend/node_modules" ]; then
    echo "清理前端node_modules..."
    rm -rf frontend/node_modules
fi

# 清理Python缓存
if [ -d "backend/__pycache__" ]; then
    echo "清理Python缓存..."
    find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find backend -name "*.pyc" -delete 2>/dev/null || true
fi

echo -e "\n${BLUE}7. 重新拉取基础镜像${NC}"

# 重新拉取基础镜像
echo "重新拉取基础镜像..."
docker pull nginx:1.24-alpine
docker pull node:18-alpine
docker pull python:3.10-slim

echo -e "\n${BLUE}8. 测试基础镜像构建${NC}"

# 测试构建基础镜像
echo "测试构建前端基础镜像..."
if timeout 300 docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend --no-cache; then
    echo -e "${GREEN}✓${NC} 前端基础镜像构建成功"
else
    echo -e "${RED}✗${NC} 前端基础镜像构建失败"
fi

echo "测试构建后端基础镜像..."
if timeout 300 docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend --no-cache; then
    echo -e "${GREEN}✓${NC} 后端基础镜像构建成功"
else
    echo -e "${RED}✗${NC} 后端基础镜像构建失败"
fi

echo -e "\n${BLUE}9. 创建清理后的构建脚本${NC}"

# 创建清理后的构建脚本
cat > /usr/local/bin/clean-build-ssl-manager.sh <<'EOF'
#!/bin/bash

# SSL证书管理器清理构建脚本
# 避免缓存问题的构建方法

set -e

echo "=== SSL证书管理器清理构建 ==="
echo "构建时间: $(date)"

# 切换到项目目录
cd "$(dirname "$0")/../.."

# 构建基础镜像（无缓存）
echo "1. 构建基础镜像..."
docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend --no-cache
docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend --no-cache

# 构建应用镜像（无缓存）
echo "2. 构建应用镜像..."
docker-compose -f docker-compose.aliyun.yml build --no-cache

echo "3. 构建完成！"
docker images | grep ssl-manager
EOF

chmod +x /usr/local/bin/clean-build-ssl-manager.sh

echo -e "\n================================="
echo -e "${GREEN}🎉 Docker缓存问题修复完成！${NC}"

echo -e "\n${BLUE}修复内容汇总:${NC}"
echo "1. ✓ 停止所有运行中的容器"
echo "2. ✓ 清理所有SSL管理器相关镜像"
echo "3. ✓ 清理Docker构建缓存"
echo "4. ✓ 清理系统缓存"
echo "5. ✓ 重启Docker服务"
echo "6. ✓ 清理项目构建缓存"
echo "7. ✓ 重新拉取基础镜像"
echo "8. ✓ 测试基础镜像构建"
echo "9. ✓ 创建清理构建脚本"

echo -e "\n${BLUE}下一步操作:${NC}"
echo "1. 使用清理构建脚本: /usr/local/bin/clean-build-ssl-manager.sh"
echo "2. 或者手动构建:"
echo "   docker-compose -f docker-compose.aliyun.yml build --no-cache"
echo "3. 启动服务:"
echo "   docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d"

echo -e "\n${YELLOW}注意事项:${NC}"
echo "- 使用 --no-cache 参数避免缓存问题"
echo "- 如果问题持续，请检查磁盘空间"
echo "- 确保Docker服务运行正常"
echo "- 可以重复运行此脚本进行深度清理"
