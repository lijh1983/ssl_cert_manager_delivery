#!/bin/bash

# SSL证书自动化管理系统验证脚本
# 用于验证系统完整性和配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查文件是否存在
check_file() {
    if [ -f "$1" ]; then
        log_success "✓ $1 存在"
        return 0
    else
        log_error "✗ $1 不存在"
        return 1
    fi
}

# 检查目录是否存在
check_directory() {
    if [ -d "$1" ]; then
        log_success "✓ $1 目录存在"
        return 0
    else
        log_error "✗ $1 目录不存在"
        return 1
    fi
}

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log_info "开始验证SSL证书自动化管理系统..."
log_info "项目根目录: $PROJECT_ROOT"

# 验证计数器
TOTAL_CHECKS=0
PASSED_CHECKS=0

# 验证函数
verify_check() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if $1; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
}

echo ""
log_info "=== 验证项目结构 ==="

# 检查主要目录
verify_check "check_directory backend"
verify_check "check_directory frontend"
verify_check "check_directory client"
verify_check "check_directory docs"
verify_check "check_directory scripts"
verify_check "check_directory tests"

echo ""
log_info "=== 验证后端文件 ==="

# 检查后端关键文件
verify_check "check_file backend/app.py"
verify_check "check_file backend/models.py"
verify_check "check_file backend/config.py"
verify_check "check_file backend/requirements.txt"
verify_check "check_file backend/.env.example"

echo ""
log_info "=== 验证前端文件 ==="

# 检查前端关键文件
verify_check "check_file frontend/package.json"
verify_check "check_file frontend/vite.config.ts"
verify_check "check_file frontend/tsconfig.json"
verify_check "check_file frontend/index.html"
verify_check "check_file frontend/src/main.ts"
verify_check "check_file frontend/src/App.vue"

# 检查前端目录结构
verify_check "check_directory frontend/src/views"
verify_check "check_directory frontend/src/api"
verify_check "check_directory frontend/src/stores"
verify_check "check_directory frontend/src/types"
verify_check "check_directory frontend/src/layouts"

echo ""
log_info "=== 验证前端页面组件 ==="

# 检查主要页面组件
verify_check "check_file frontend/src/views/Login.vue"
verify_check "check_file frontend/src/views/Dashboard.vue"
verify_check "check_file frontend/src/views/servers/ServerList.vue"
verify_check "check_file frontend/src/views/servers/ServerDetail.vue"
verify_check "check_file frontend/src/views/certificates/CertificateList.vue"
verify_check "check_file frontend/src/views/certificates/CertificateDetail.vue"
verify_check "check_file frontend/src/views/alerts/AlertList.vue"
verify_check "check_file frontend/src/views/logs/LogList.vue"
verify_check "check_file frontend/src/views/users/UserList.vue"
verify_check "check_file frontend/src/views/settings/SystemSettings.vue"
verify_check "check_file frontend/src/views/profile/UserProfile.vue"

echo ""
log_info "=== 验证API接口文件 ==="

# 检查API文件
verify_check "check_file frontend/src/api/request.ts"
verify_check "check_file frontend/src/api/auth.ts"
verify_check "check_file frontend/src/api/server.ts"
verify_check "check_file frontend/src/api/certificate.ts"
verify_check "check_file frontend/src/api/alert.ts"

echo ""
log_info "=== 验证类型定义文件 ==="

# 检查类型定义文件
verify_check "check_file frontend/src/types/auth.ts"
verify_check "check_file frontend/src/types/server.ts"
verify_check "check_file frontend/src/types/certificate.ts"
verify_check "check_file frontend/src/types/alert.ts"

echo ""
log_info "=== 验证状态管理文件 ==="

# 检查状态管理文件
verify_check "check_file frontend/src/stores/auth.ts"

echo ""
log_info "=== 验证布局组件 ==="

# 检查布局组件
verify_check "check_file frontend/src/layouts/MainLayout.vue"

echo ""
log_info "=== 验证路由配置 ==="

# 检查路由配置
verify_check "check_file frontend/src/router/index.ts"

echo ""
log_info "=== 验证客户端脚本 ==="

# 检查客户端脚本
verify_check "check_file client/client.sh"

echo ""
log_info "=== 验证文档文件 ==="

# 检查文档文件
verify_check "check_file docs/api_reference.md"
verify_check "check_file docs/deployment_guide.md"
verify_check "check_file docs/user_manual.md"
verify_check "check_file docs/developer_guide.md"

echo ""
log_info "=== 验证脚本文件 ==="

# 检查脚本文件
verify_check "check_file scripts/build.sh"
verify_check "check_file tests/run_tests.sh"

echo ""
log_info "=== 验证项目配置文件 ==="

# 检查项目配置文件
verify_check "check_file README.md"
verify_check "check_file implementation_plan.md"

echo ""
log_info "=== 验证结果 ==="

# 显示验证结果
echo "总检查项: $TOTAL_CHECKS"
echo "通过检查: $PASSED_CHECKS"
echo "失败检查: $((TOTAL_CHECKS - PASSED_CHECKS))"

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    log_success "🎉 所有验证项都通过了！"
    echo ""
    log_info "系统完整性验证通过，可以进行构建和部署。"
    echo ""
    log_info "下一步操作："
    log_info "1. 运行构建脚本: ./scripts/build.sh"
    log_info "2. 配置环境变量: 编辑 backend/.env"
    log_info "3. 启动服务: ./start.sh dev"
    exit 0
else
    log_error "❌ 验证失败，请检查缺失的文件和目录。"
    echo ""
    log_info "请确保所有必需的文件都已创建。"
    exit 1
fi
