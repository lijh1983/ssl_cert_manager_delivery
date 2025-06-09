#!/bin/bash

# 部署配置测试脚本
# 用于验证Docker Compose配置文件和Dockerfile引用的正确性

set -e

echo "=== SSL Certificate Manager 部署配置测试 ==="
echo "测试时间: $(date)"
echo "============================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
test_file_exists() {
    local file_path="$1"
    local description="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ -f "$file_path" ]; then
        echo -e "${GREEN}✓${NC} $description: $file_path"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $description: $file_path (文件不存在)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

test_yaml_syntax() {
    local yaml_file="$1"
    local description="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $description: YAML语法正确"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $description: YAML语法错误"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo -e "${BLUE}1. 检查Docker Compose配置文件${NC}"
test_file_exists "docker-compose.aliyun.yml" "阿里云部署配置"
test_file_exists "docker-compose.yml" "标准部署配置"
test_file_exists "docker-compose.dev.yml" "开发环境配置"
test_file_exists "docker-compose.prod.yml" "生产环境配置"

echo -e "\n${BLUE}2. 检查YAML语法${NC}"
test_yaml_syntax "docker-compose.aliyun.yml" "阿里云配置语法"
test_yaml_syntax "docker-compose.yml" "标准配置语法"
test_yaml_syntax "docker-compose.dev.yml" "开发配置语法"
test_yaml_syntax "docker-compose.prod.yml" "生产配置语法"

echo -e "\n${BLUE}3. 检查Dockerfile文件${NC}"
test_file_exists "backend/Dockerfile" "后端Dockerfile"
test_file_exists "frontend/Dockerfile" "前端Dockerfile"
test_file_exists "nginx/Dockerfile.proxy.alpine" "Nginx代理Dockerfile"

echo -e "\n${BLUE}4. 验证docker-compose.aliyun.yml中的Dockerfile引用${NC}"

# 检查后端Dockerfile引用
TOTAL_TESTS=$((TOTAL_TESTS + 1))
backend_dockerfile=$(grep -A 5 "context: ./backend" docker-compose.aliyun.yml | grep "dockerfile:" | awk '{print $2}')
if [ "$backend_dockerfile" = "Dockerfile" ] && [ -f "backend/Dockerfile" ]; then
    echo -e "${GREEN}✓${NC} 后端Dockerfile引用正确: $backend_dockerfile"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} 后端Dockerfile引用错误: $backend_dockerfile"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# 检查前端Dockerfile引用
TOTAL_TESTS=$((TOTAL_TESTS + 1))
frontend_dockerfile=$(grep -A 5 "context: ./frontend" docker-compose.aliyun.yml | grep "dockerfile:" | awk '{print $2}')
if [ "$frontend_dockerfile" = "Dockerfile" ] && [ -f "frontend/Dockerfile" ]; then
    echo -e "${GREEN}✓${NC} 前端Dockerfile引用正确: $frontend_dockerfile"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} 前端Dockerfile引用错误: $frontend_dockerfile"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# 检查nginx Dockerfile引用
TOTAL_TESTS=$((TOTAL_TESTS + 1))
nginx_dockerfile=$(grep -A 5 "context: ./nginx" docker-compose.aliyun.yml | grep "dockerfile:" | awk '{print $2}')
if [ "$nginx_dockerfile" = "Dockerfile.proxy.alpine" ] && [ -f "nginx/Dockerfile.proxy.alpine" ]; then
    echo -e "${GREEN}✓${NC} Nginx Dockerfile引用正确: $nginx_dockerfile"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} Nginx Dockerfile引用错误: $nginx_dockerfile"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo -e "\n${BLUE}5. 检查必要的配置文件${NC}"
test_file_exists "backend/requirements.txt" "后端依赖文件"
test_file_exists "frontend/package.json" "前端依赖文件"
test_file_exists "nginx/nginx.conf" "Nginx主配置"

echo -e "\n${BLUE}6. 检查环境变量文件模板${NC}"
if [ -f ".env.example" ]; then
    test_file_exists ".env.example" "环境变量模板"
else
    echo -e "${YELLOW}⚠${NC} 建议创建 .env.example 文件作为环境变量模板"
fi

echo -e "\n============================================="
echo -e "${BLUE}测试结果汇总:${NC}"
echo -e "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有测试通过！部署配置正确。${NC}"
    echo -e "${GREEN}现在可以安全地运行以下命令进行部署:${NC}"
    echo -e "${YELLOW}docker-compose -f docker-compose.aliyun.yml up -d${NC}"
    exit 0
else
    echo -e "\n${RED}❌ 发现 $FAILED_TESTS 个问题，请修复后重新测试。${NC}"
    exit 1
fi
