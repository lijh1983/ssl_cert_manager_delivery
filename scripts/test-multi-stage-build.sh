#!/bin/bash

# 多阶段Docker构建测试脚本
# 测试基础镜像和应用镜像的完整构建流程

set -e

echo "=== SSL证书管理器多阶段构建测试 ==="
echo "测试时间: $(date)"
echo "======================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试结果统计
TOTAL_TESTS=0
SUCCESSFUL_TESTS=0
FAILED_TESTS=0

# 测试函数
test_build() {
    local name="$1"
    local context="$2"
    local dockerfile="$3"
    local tag="$4"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "\n${BLUE}测试构建: $name${NC}"
    echo "上下文目录: $context"
    echo "Dockerfile: $dockerfile"
    echo "镜像标签: $tag"
    
    local start_time=$(date +%s)
    
    if timeout 600 docker build -t "$tag" -f "$context/$dockerfile" "$context" --no-cache; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${GREEN}✓${NC} $name: 构建成功 (耗时: ${duration}秒)"
        SUCCESSFUL_TESTS=$((SUCCESSFUL_TESTS + 1))
        
        # 显示镜像信息
        echo "镜像大小: $(docker images --format "table {{.Size}}" "$tag" | tail -n 1)"
        return 0
    else
        echo -e "${RED}✗${NC} $name: 构建失败"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 测试镜像运行
test_run() {
    local name="$1"
    local tag="$2"
    local test_command="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "\n${BLUE}测试运行: $name${NC}"
    echo "镜像标签: $tag"
    echo "测试命令: $test_command"
    
    if docker run --rm "$tag" $test_command >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name: 运行测试成功"
        SUCCESSFUL_TESTS=$((SUCCESSFUL_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name: 运行测试失败"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo -e "${BLUE}1. 检查Docker环境${NC}"

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}错误: Docker未运行或无权限访问${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker环境正常${NC}"
echo "Docker版本: $(docker --version)"

echo -e "\n${BLUE}2. 清理旧镜像${NC}"

# 清理旧镜像
old_images=(
    "ssl-manager-frontend-base:latest"
    "ssl-manager-backend-base:latest"
    "ssl-manager-frontend-app:latest"
    "ssl-manager-backend-app:latest"
    "ssl-manager-nginx-test:latest"
)

for image in "${old_images[@]}"; do
    if docker images -q "$image" >/dev/null 2>&1; then
        echo "删除旧镜像: $image"
        docker rmi "$image" >/dev/null 2>&1 || true
    fi
done

echo -e "\n${BLUE}3. 阶段1: 构建基础镜像${NC}"

# 测试前端基础镜像构建
echo -e "\n${YELLOW}=== 测试前端基础镜像 ===${NC}"
test_build "前端基础镜像" "frontend" "Dockerfile.base" "ssl-manager-frontend-base:latest"

# 测试后端基础镜像构建
echo -e "\n${YELLOW}=== 测试后端基础镜像 ===${NC}"
test_build "后端基础镜像" "backend" "Dockerfile.base" "ssl-manager-backend-base:latest"

# 测试Nginx镜像构建
echo -e "\n${YELLOW}=== 测试Nginx镜像 ===${NC}"
test_build "Nginx代理镜像" "nginx" "Dockerfile.proxy.alpine" "ssl-manager-nginx-test:latest"

echo -e "\n${BLUE}4. 阶段2: 构建应用镜像${NC}"

# 测试前端应用镜像构建
echo -e "\n${YELLOW}=== 测试前端应用镜像 ===${NC}"
test_build "前端应用镜像" "frontend" "Dockerfile" "ssl-manager-frontend-app:latest"

# 测试后端应用镜像构建
echo -e "\n${YELLOW}=== 测试后端应用镜像 ===${NC}"
test_build "后端应用镜像" "backend" "Dockerfile" "ssl-manager-backend-app:latest"

echo -e "\n${BLUE}5. 运行时测试${NC}"

# 测试基础镜像运行
echo -e "\n${YELLOW}=== 测试基础镜像运行 ===${NC}"
test_run "前端基础镜像运行测试" "ssl-manager-frontend-base:latest" "node --version"
test_run "后端基础镜像运行测试" "ssl-manager-backend-base:latest" "python --version"

echo -e "\n${BLUE}6. 显示构建结果${NC}"

echo "构建的镜像列表:"
docker images | grep "ssl-manager" || echo "未找到SSL管理器镜像"

echo -e "\n${BLUE}7. 镜像大小分析${NC}"

echo "镜像大小对比:"
echo "基础镜像:"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "ssl-manager.*base" || true
echo "应用镜像:"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep -E "ssl-manager.*(app|test)" || true

echo -e "\n${BLUE}8. 构建效率测试${NC}"

# 测试增量构建（应该很快，因为基础镜像已缓存）
echo "测试增量构建效率..."
start_time=$(date +%s)
if docker build -t ssl-manager-frontend-app:test ./frontend >/dev/null 2>&1; then
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo -e "${GREEN}✓${NC} 前端增量构建: ${duration}秒 (应该很快，因为基础镜像已缓存)"
else
    echo -e "${RED}✗${NC} 前端增量构建失败"
fi

# 清理测试镜像
docker rmi ssl-manager-frontend-app:test >/dev/null 2>&1 || true

echo -e "\n======================================="
echo -e "${BLUE}测试结果汇总:${NC}"
echo -e "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}成功: $SUCCESSFUL_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有多阶段构建测试通过！${NC}"
    echo -e "${GREEN}多阶段Docker构建策略实施成功！${NC}"
    
    echo -e "\n${BLUE}构建策略优势:${NC}"
    echo -e "${YELLOW}1. 构建效率:${NC} 基础镜像缓存依赖，后续构建更快"
    echo -e "${YELLOW}2. 构建可靠性:${NC} 依赖安装与代码变更分离"
    echo -e "${YELLOW}3. 调试友好:${NC} 可以独立测试基础镜像"
    echo -e "${YELLOW}4. CI/CD优化:${NC} 基础镜像可以构建一次并重复使用"
    
    echo -e "\n${BLUE}下一步操作:${NC}"
    echo -e "${YELLOW}1. 使用Docker Compose构建完整服务:${NC}"
    echo -e "   docker-compose -f docker-compose.aliyun.yml build"
    echo -e "${YELLOW}2. 启动SSL证书管理器:${NC}"
    echo -e "   docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d"
    echo -e "${YELLOW}3. 或者使用管理脚本部署:${NC}"
    echo -e "   ./scripts/ssl-manager.sh deploy --domain ssl.gzyggl.com --email 19822088@qq.com --aliyun --monitoring"
    
    exit 0
else
    echo -e "\n${RED}❌ 发现 $FAILED_TESTS 个测试失败${NC}"
    
    echo -e "\n${BLUE}故障排除建议:${NC}"
    echo "1. 检查网络连接是否正常"
    echo "2. 确保Docker服务运行正常"
    echo "3. 检查磁盘空间是否充足"
    echo "4. 查看详细构建日志"
    echo "5. 检查基础镜像是否正确构建"
    echo "6. 验证Dockerfile语法是否正确"
    
    exit 1
fi
