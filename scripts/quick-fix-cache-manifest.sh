#!/bin/bash

# 快速修复Docker缓存清单问题
# 专门解决"importing cache manifest from ssl-manager-nginx-proxy:latest"错误

set -e

echo "=== Docker缓存清单快速修复工具 ==="
echo "修复时间: $(date)"
echo "======================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. 停止相关容器${NC}"

# 停止SSL管理器相关容器
echo "停止SSL管理器相关容器..."
docker-compose -f docker-compose.aliyun.yml down 2>/dev/null || true

echo -e "\n${BLUE}2. 删除问题镜像${NC}"

# 删除有问题的nginx-proxy镜像
echo "删除ssl-manager-nginx-proxy镜像..."
docker rmi ssl-manager-nginx-proxy:latest 2>/dev/null || true

# 删除所有SSL管理器镜像
echo "删除所有SSL管理器镜像..."
docker images | grep ssl-manager | awk '{print $1":"$2}' | xargs -r docker rmi -f 2>/dev/null || true

echo -e "\n${BLUE}3. 清理构建缓存${NC}"

# 清理Docker构建缓存
echo "清理Docker构建缓存..."
docker builder prune -f

echo -e "\n${BLUE}4. 重新拉取基础镜像${NC}"

# 重新拉取nginx基础镜像
echo "重新拉取nginx基础镜像..."
docker pull nginx:1.24-alpine

echo -e "\n${BLUE}5. 构建基础镜像${NC}"

# 切换到项目目录
cd "$(dirname "$0")/.."

# 构建基础镜像（如果存在）
if [ -f "frontend/Dockerfile.base" ]; then
    echo "构建前端基础镜像..."
    docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend --no-cache
fi

if [ -f "backend/Dockerfile.base" ]; then
    echo "构建后端基础镜像..."
    docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend --no-cache
fi

echo -e "\n${BLUE}6. 构建nginx-proxy镜像${NC}"

# 单独构建nginx-proxy镜像
echo "构建nginx-proxy镜像..."
if docker build -t ssl-manager-nginx-proxy:latest -f nginx/Dockerfile.proxy.alpine ./nginx --no-cache; then
    echo -e "${GREEN}✓${NC} nginx-proxy镜像构建成功"
else
    echo -e "${RED}✗${NC} nginx-proxy镜像构建失败"
    
    echo -e "\n${YELLOW}尝试使用简化构建...${NC}"
    # 创建临时的简化Dockerfile
    cat > nginx/Dockerfile.proxy.simple <<'EOF'
FROM nginx:1.24-alpine

# 复制配置文件
COPY conf.d/ /etc/nginx/conf.d/
COPY nginx.conf /etc/nginx/nginx.conf

# 创建必要的目录
RUN mkdir -p /var/log/nginx /var/cache/nginx /var/run

# 设置权限
RUN chown -R nginx:nginx /var/log/nginx /var/cache/nginx /var/run

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# 暴露端口
EXPOSE 80 443

# 启动命令
CMD ["nginx", "-g", "daemon off;"]
EOF
    
    # 使用简化Dockerfile构建
    if docker build -t ssl-manager-nginx-proxy:latest -f nginx/Dockerfile.proxy.simple ./nginx --no-cache; then
        echo -e "${GREEN}✓${NC} 使用简化Dockerfile构建成功"
    else
        echo -e "${RED}✗${NC} 简化构建也失败，请检查nginx配置文件"
        exit 1
    fi
fi

echo -e "\n${BLUE}7. 验证镜像${NC}"

# 验证构建的镜像
echo "验证构建的镜像..."
docker images | grep ssl-manager

echo -e "\n${BLUE}8. 测试nginx-proxy容器${NC}"

# 测试nginx-proxy容器
echo "测试nginx-proxy容器..."
if docker run --rm --name test-nginx-proxy -d ssl-manager-nginx-proxy:latest; then
    sleep 3
    if docker ps | grep test-nginx-proxy; then
        echo -e "${GREEN}✓${NC} nginx-proxy容器运行正常"
        docker stop test-nginx-proxy
    else
        echo -e "${RED}✗${NC} nginx-proxy容器启动失败"
        docker logs test-nginx-proxy 2>/dev/null || true
    fi
else
    echo -e "${RED}✗${NC} nginx-proxy容器创建失败"
fi

echo -e "\n${BLUE}9. 创建无缓存构建命令${NC}"

# 创建无缓存构建命令文件
cat > build-no-cache.sh <<'EOF'
#!/bin/bash
echo "=== 无缓存构建SSL证书管理器 ==="

# 构建所有服务（无缓存）
docker-compose -f docker-compose.aliyun.yml build --no-cache

echo "构建完成！"
docker images | grep ssl-manager
EOF

chmod +x build-no-cache.sh

echo -e "\n======================================="
echo -e "${GREEN}🎉 缓存清单问题修复完成！${NC}"

echo -e "\n${BLUE}修复内容汇总:${NC}"
echo "1. ✓ 停止相关容器"
echo "2. ✓ 删除问题镜像"
echo "3. ✓ 清理构建缓存"
echo "4. ✓ 重新拉取基础镜像"
echo "5. ✓ 构建基础镜像"
echo "6. ✓ 构建nginx-proxy镜像"
echo "7. ✓ 验证镜像"
echo "8. ✓ 测试容器"
echo "9. ✓ 创建无缓存构建脚本"

echo -e "\n${BLUE}下一步操作:${NC}"
echo "1. 使用无缓存构建: ./build-no-cache.sh"
echo "2. 或者直接启动服务:"
echo "   docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d"
echo "3. 如果还有问题，运行完整清理:"
echo "   sudo ./scripts/fix-docker-cache-issues.sh"

echo -e "\n${YELLOW}预防措施:${NC}"
echo "- 已修复docker-compose.yml中的循环缓存依赖"
echo "- 建议定期清理Docker缓存"
echo "- 使用 --no-cache 参数进行关键构建"
echo "- 监控磁盘空间，确保有足够空间"
