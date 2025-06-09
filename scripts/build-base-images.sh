#!/bin/bash

# 基础镜像构建脚本
# 用于构建包含依赖的基础镜像，提高后续构建效率

set -e

echo "=== SSL证书管理器基础镜像构建脚本 ==="
echo "构建时间: $(date)"
echo "======================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 构建结果统计
TOTAL_BUILDS=0
SUCCESSFUL_BUILDS=0
FAILED_BUILDS=0

# 构建函数
build_image() {
    local name="$1"
    local context="$2"
    local dockerfile="$3"
    local tag="$4"
    
    TOTAL_BUILDS=$((TOTAL_BUILDS + 1))
    
    echo -e "\n${BLUE}构建基础镜像: $name${NC}"
    echo "上下文目录: $context"
    echo "Dockerfile: $dockerfile"
    echo "镜像标签: $tag"
    
    local start_time=$(date +%s)
    
    if docker build -t "$tag" -f "$context/$dockerfile" "$context" --no-cache; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${GREEN}✓${NC} $name: 构建成功 (耗时: ${duration}秒)"
        SUCCESSFUL_BUILDS=$((SUCCESSFUL_BUILDS + 1))
        
        # 显示镜像信息
        echo "镜像大小: $(docker images --format "table {{.Size}}" "$tag" | tail -n 1)"
        return 0
    else
        echo -e "${RED}✗${NC} $name: 构建失败"
        FAILED_BUILDS=$((FAILED_BUILDS + 1))
        return 1
    fi
}

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo -e "${BLUE}1. 检查Docker环境${NC}"

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}错误: Docker未运行或无权限访问${NC}"
    echo "请确保Docker服务已启动，并且当前用户有权限访问Docker"
    exit 1
fi

echo -e "${GREEN}✓ Docker环境正常${NC}"
echo "Docker版本: $(docker --version)"

echo -e "\n${BLUE}2. 检查构建文件${NC}"

# 检查必要的文件
files_to_check=(
    "frontend/Dockerfile.base"
    "frontend/package.json"
    "backend/Dockerfile.base"
    "backend/requirements.txt"
    "nginx/Dockerfile.proxy.alpine"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file 存在"
    else
        echo -e "${RED}✗${NC} $file 不存在"
        exit 1
    fi
done

echo -e "\n${BLUE}3. 清理旧的基础镜像${NC}"

# 清理旧的基础镜像（可选）
old_images=(
    "ssl-manager-frontend-base:latest"
    "ssl-manager-backend-base:latest"
)

for image in "${old_images[@]}"; do
    if docker images -q "$image" >/dev/null 2>&1; then
        echo "删除旧镜像: $image"
        docker rmi "$image" >/dev/null 2>&1 || true
    fi
done

echo -e "\n${BLUE}4. 构建基础镜像${NC}"

# 构建前端基础镜像
echo -e "\n${YELLOW}=== 构建前端基础镜像 ===${NC}"
build_image "前端基础镜像" "frontend" "Dockerfile.base" "ssl-manager-frontend-base:latest"

# 构建后端基础镜像
echo -e "\n${YELLOW}=== 构建后端基础镜像 ===${NC}"
build_image "后端基础镜像" "backend" "Dockerfile.base" "ssl-manager-backend-base:latest"

echo -e "\n${BLUE}5. 验证基础镜像${NC}"

# 验证前端基础镜像
echo "验证前端基础镜像..."
if docker run --rm ssl-manager-frontend-base:latest node --version >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 前端基础镜像验证成功"
else
    echo -e "${RED}✗${NC} 前端基础镜像验证失败"
    FAILED_BUILDS=$((FAILED_BUILDS + 1))
fi

# 验证后端基础镜像
echo "验证后端基础镜像..."
if docker run --rm ssl-manager-backend-base:latest python --version >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 后端基础镜像验证成功"
else
    echo -e "${RED}✗${NC} 后端基础镜像验证失败"
    FAILED_BUILDS=$((FAILED_BUILDS + 1))
fi

echo -e "\n${BLUE}6. 显示镜像信息${NC}"

echo "构建的基础镜像:"
docker images | grep "ssl-manager.*base" || echo "未找到基础镜像"

echo -e "\n======================================="
echo -e "${BLUE}构建结果汇总:${NC}"
echo -e "总构建数: $TOTAL_BUILDS"
echo -e "${GREEN}成功: $SUCCESSFUL_BUILDS${NC}"
echo -e "${RED}失败: $FAILED_BUILDS${NC}"

if [ $FAILED_BUILDS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有基础镜像构建成功！${NC}"
    echo -e "${GREEN}现在可以使用这些基础镜像进行应用构建。${NC}"
    echo -e "\n${BLUE}下一步操作:${NC}"
    echo -e "${YELLOW}1. 构建应用镜像:${NC}"
    echo -e "   docker-compose -f docker-compose.aliyun.yml build"
    echo -e "${YELLOW}2. 启动服务:${NC}"
    echo -e "   docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d"
    echo -e "${YELLOW}3. 或者使用管理脚本:${NC}"
    echo -e "   ./scripts/ssl-manager.sh deploy --domain ssl.gzyggl.com --email 19822088@qq.com --aliyun --monitoring"
    exit 0
else
    echo -e "\n${RED}❌ 发现 $FAILED_BUILDS 个构建失败，请检查错误信息。${NC}"
    
    echo -e "\n${BLUE}故障排除建议:${NC}"
    echo "1. 检查网络连接是否正常"
    echo "2. 确保Docker服务运行正常"
    echo "3. 检查磁盘空间是否充足"
    echo "4. 查看详细构建日志"
    echo "5. 尝试手动构建单个镜像进行调试"
    
    exit 1
fi
