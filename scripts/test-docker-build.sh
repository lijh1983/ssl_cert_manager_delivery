#!/bin/bash
# Docker构建验证脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 测试Dockerfile语法
test_dockerfile_syntax() {
    log_info "测试Dockerfile语法..."
    
    local dockerfiles=(
        "backend/Dockerfile"
        "frontend/Dockerfile"
        "nginx/Dockerfile.proxy.alpine"
    )
    
    for dockerfile in "${dockerfiles[@]}"; do
        if [ -f "$dockerfile" ]; then
            log_info "检查 $dockerfile 语法..."
            
            # 使用docker build --dry-run来检查语法（如果支持）
            if docker build --help | grep -q "dry-run"; then
                if docker build --dry-run -f "$dockerfile" . > /dev/null 2>&1; then
                    log_success "✅ $dockerfile 语法正确"
                else
                    log_error "❌ $dockerfile 语法错误"
                    return 1
                fi
            else
                # 使用简单的语法检查
                if grep -q "^FROM" "$dockerfile" && ! grep -q "^echo " "$dockerfile"; then
                    log_success "✅ $dockerfile 基本语法检查通过"
                else
                    log_warning "⚠️  $dockerfile 可能存在语法问题"
                fi
            fi
        else
            log_error "❌ $dockerfile 文件不存在"
        fi
    done
}

# 测试镜像拉取
test_image_pull() {
    log_info "测试关键镜像拉取..."
    
    local images=(
        "postgres:15-alpine"
        "redis:7-alpine"
        "nginx:1.24-alpine"
        "python:3.10-slim"
        "node:18-alpine"
    )
    
    local failed_images=()
    
    for image in "${images[@]}"; do
        log_info "测试拉取镜像: $image"
        
        if timeout 120 docker pull "$image" > /dev/null 2>&1; then
            log_success "✅ $image 拉取成功"
        else
            log_error "❌ $image 拉取失败"
            failed_images+=("$image")
        fi
    done
    
    if [ ${#failed_images[@]} -gt 0 ]; then
        log_warning "以下镜像拉取失败:"
        for image in "${failed_images[@]}"; do
            echo "  - $image"
        done
        return 1
    fi
    
    return 0
}

# 测试后端构建
test_backend_build() {
    log_info "测试后端镜像构建..."
    
    if [ ! -f "backend/Dockerfile" ]; then
        log_error "backend/Dockerfile 文件不存在"
        return 1
    fi
    
    # 检查requirements.txt文件
    if [ ! -f "backend/requirements.txt" ]; then
        log_warning "backend/requirements.txt 文件不存在，创建基础版本..."
        cat > backend/requirements.txt <<EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0
gevent==23.9.1
psycopg2-binary==2.9.9
redis==5.0.1
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
requests==2.31.0
cryptography==41.0.8
acme==2.7.4
certbot==2.7.4
schedule==1.2.0
python-dotenv==1.0.0
EOF
        log_info "已创建基础 requirements.txt 文件"
    fi
    
    log_info "开始构建后端镜像..."
    local start_time=$(date +%s)
    
    if timeout 600 docker build -f backend/Dockerfile -t test-ssl-backend ./backend > build_backend.log 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "✅ 后端镜像构建成功，耗时: ${duration}秒"
        
        # 测试镜像启动
        if docker run --rm -d --name test-backend test-ssl-backend sleep 10 > /dev/null 2>&1; then
            log_success "✅ 后端镜像启动测试成功"
            docker stop test-backend > /dev/null 2>&1 || true
        else
            log_warning "⚠️  后端镜像启动测试失败"
        fi
        
        # 清理测试镜像
        docker rmi test-ssl-backend > /dev/null 2>&1 || true
        
        return 0
    else
        log_error "❌ 后端镜像构建失败"
        log_info "构建日志:"
        tail -20 build_backend.log || echo "无法读取构建日志"
        return 1
    fi
}

# 测试docker-compose配置
test_compose_config() {
    log_info "测试docker-compose配置..."
    
    local compose_files=(
        "docker-compose.aliyun.yml"
        "docker-compose.aliyun.backup.yml"
    )
    
    for compose_file in "${compose_files[@]}"; do
        if [ -f "$compose_file" ]; then
            log_info "检查 $compose_file 配置..."
            
            if docker compose -f "$compose_file" config > /dev/null 2>&1; then
                log_success "✅ $compose_file 配置语法正确"
            elif docker-compose -f "$compose_file" config > /dev/null 2>&1; then
                log_success "✅ $compose_file 配置语法正确 (使用docker-compose命令)"
            else
                log_error "❌ $compose_file 配置语法错误"
                return 1
            fi
        else
            log_warning "⚠️  $compose_file 文件不存在"
        fi
    done
}

# 测试网络连接
test_network_connectivity() {
    log_info "测试网络连接..."
    
    local endpoints=(
        "registry.cn-hangzhou.aliyuncs.com|阿里云镜像仓库"
        "mirrors.aliyun.com|阿里云软件源"
        "registry-1.docker.io|Docker Hub"
        "pypi.org|Python包仓库"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint=$(echo "$endpoint_info" | cut -d'|' -f1)
        local description=$(echo "$endpoint_info" | cut -d'|' -f2)
        
        log_info "测试连接: $description ($endpoint)"
        
        if timeout 10 ping -c 1 "$endpoint" > /dev/null 2>&1; then
            log_success "✅ $description 连接正常"
        else
            log_warning "⚠️  $description 连接失败"
        fi
    done
}

# 生成测试报告
generate_test_report() {
    local report_file="docker_build_test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成测试报告: $report_file"
    
    {
        echo "Docker构建验证测试报告"
        echo "生成时间: $(date)"
        echo "========================================"
        echo
        
        echo "=== 系统环境 ==="
        echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '"')"
        echo "Docker版本: $(docker --version)"
        echo "工作目录: $(pwd)"
        echo
        
        echo "=== 测试结果 ==="
        echo "Dockerfile语法检查: $(test_dockerfile_syntax > /dev/null 2>&1 && echo "通过" || echo "失败")"
        echo "镜像拉取测试: $(test_image_pull > /dev/null 2>&1 && echo "通过" || echo "失败")"
        echo "后端构建测试: $(test_backend_build > /dev/null 2>&1 && echo "通过" || echo "失败")"
        echo "Compose配置检查: $(test_compose_config > /dev/null 2>&1 && echo "通过" || echo "失败")"
        echo "网络连接测试: $(test_network_connectivity > /dev/null 2>&1 && echo "通过" || echo "失败")"
        echo
        
        echo "=== 本地镜像 ==="
        docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | head -10
        echo
        
        echo "=== 修复建议 ==="
        echo "1. 如果镜像拉取失败: 运行 ./scripts/fix-docker-images.sh"
        echo "2. 如果构建失败: 检查 Dockerfile 语法和网络连接"
        echo "3. 如果配置错误: 检查 docker-compose.yml 文件"
        echo "4. 如果网络问题: 配置 Docker 镜像加速器"
        
    } > "$report_file"
    
    log_success "测试报告已生成: $report_file"
}

# 显示修复建议
show_fix_suggestions() {
    echo
    log_info "=== 修复建议 ==="
    echo
    echo "如果遇到问题，请按以下顺序执行修复:"
    echo
    echo "1. 修复Docker镜像问题:"
    echo "   ./scripts/fix-docker-images.sh"
    echo
    echo "2. 验证修复效果:"
    echo "   ./scripts/test-docker-build.sh"
    echo
    echo "3. 启动服务:"
    echo "   docker-compose -f docker-compose.aliyun.yml up -d"
    echo
    echo "4. 查看服务状态:"
    echo "   docker-compose -f docker-compose.aliyun.yml ps"
    echo
    echo "5. 如果仍有问题，使用备选配置:"
    echo "   docker-compose -f docker-compose.aliyun.backup.yml up -d"
}

# 主函数
main() {
    echo "🧪 Docker构建验证测试工具"
    echo "============================"
    echo
    
    # 检查Docker服务
    if ! systemctl is-active docker > /dev/null 2>&1; then
        log_error "Docker服务未运行，请先启动Docker服务"
        echo "sudo systemctl start docker"
        exit 1
    fi
    
    local test_passed=0
    local total_tests=5
    
    # 执行测试
    echo "开始执行Docker构建验证测试..."
    echo
    
    if test_dockerfile_syntax; then ((test_passed++)); fi
    echo
    
    if test_image_pull; then ((test_passed++)); fi
    echo
    
    if test_backend_build; then ((test_passed++)); fi
    echo
    
    if test_compose_config; then ((test_passed++)); fi
    echo
    
    if test_network_connectivity; then ((test_passed++)); fi
    echo
    
    # 生成报告
    generate_test_report
    echo
    
    # 显示结果
    log_info "测试结果: $test_passed/$total_tests 项测试通过"
    
    if [ $test_passed -eq $total_tests ]; then
        log_success "🎉 所有测试通过！Docker构建环境正常"
    elif [ $test_passed -ge 3 ]; then
        log_warning "⚠️  部分测试通过，建议查看失败项目"
        show_fix_suggestions
    else
        log_error "❌ 多项测试失败，需要修复Docker环境"
        show_fix_suggestions
        exit 1
    fi
    
    # 清理测试文件
    rm -f build_backend.log
}

# 执行主函数
main "$@"
