#!/bin/bash
# 镜像问题验证和修复一体化脚本

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

# 检查Docker环境
check_docker_environment() {
    log_info "检查Docker环境..."
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行"
        return 1
    fi
    
    log_success "Docker服务正常"
    
    # 检查Docker版本
    local docker_version=$(docker --version)
    log_info "Docker版本: $docker_version"
    
    # 检查Docker Compose
    if docker compose version > /dev/null 2>&1; then
        local compose_version=$(docker compose version)
        log_info "Docker Compose版本: $compose_version"
    elif command -v docker-compose > /dev/null 2>&1; then
        local compose_version=$(docker-compose --version)
        log_info "Docker Compose版本: $compose_version"
    else
        log_warning "Docker Compose未安装"
    fi
    
    return 0
}

# 检查网络连接
check_network_connectivity() {
    log_info "检查网络连接..."
    
    local registries=(
        "registry-1.docker.io|Docker Hub"
        "registry.cn-hangzhou.aliyuncs.com|阿里云镜像仓库"
        "docker.mirrors.ustc.edu.cn|中科大镜像"
    )
    
    local connectivity_ok=true
    
    for registry_info in "${registries[@]}"; do
        local registry=$(echo "$registry_info" | cut -d'|' -f1)
        local description=$(echo "$registry_info" | cut -d'|' -f2)
        
        if ping -c 1 -W 3 "$registry" > /dev/null 2>&1; then
            log_success "网络连接正常: $description"
        else
            log_warning "网络连接失败: $description"
            connectivity_ok=false
        fi
    done
    
    if [ "$connectivity_ok" = "true" ]; then
        return 0
    else
        return 1
    fi
}

# 测试关键镜像拉取
test_critical_images() {
    log_info "测试关键镜像拉取..."
    
    local critical_images=(
        "python:3.10-slim|Python后端基础镜像"
        "node:18-alpine|Node.js前端基础镜像"
        "nginx:alpine|Nginx代理基础镜像"
        "postgres:15-alpine|PostgreSQL数据库镜像"
        "redis:7-alpine|Redis缓存镜像"
    )
    
    local failed_images=()
    local successful_images=()
    
    for image_info in "${critical_images[@]}"; do
        local image=$(echo "$image_info" | cut -d'|' -f1)
        local description=$(echo "$image_info" | cut -d'|' -f2)
        
        log_info "测试拉取: $image ($description)"
        
        if timeout 60 docker pull "$image" > /dev/null 2>&1; then
            log_success "拉取成功: $image"
            successful_images+=("$image")
        else
            log_error "拉取失败: $image"
            failed_images+=("$image")
        fi
    done
    
    echo
    echo "=== 镜像拉取测试结果 ==="
    echo "成功: ${#successful_images[@]} 个镜像"
    echo "失败: ${#failed_images[@]} 个镜像"
    
    if [ ${#failed_images[@]} -eq 0 ]; then
        log_success "所有关键镜像拉取成功"
        return 0
    else
        log_warning "部分镜像拉取失败: ${failed_images[*]}"
        return 1
    fi
}

# 自动修复镜像问题
auto_fix_images() {
    log_info "自动修复镜像问题..."
    
    # 修复Python镜像问题
    if [ -f "scripts/fix_python_image_issue.sh" ]; then
        log_info "运行Python镜像修复脚本..."
        if ./scripts/fix_python_image_issue.sh; then
            log_success "Python镜像问题修复完成"
        else
            log_warning "Python镜像修复失败"
        fi
    fi
    
    # 修复Nginx镜像问题
    if [ -f "scripts/fix_nginx_image_issue.sh" ]; then
        log_info "运行Nginx镜像修复脚本..."
        if ./scripts/fix_nginx_image_issue.sh; then
            log_success "Nginx镜像问题修复完成"
        else
            log_warning "Nginx镜像修复失败"
        fi
    fi
}

# 验证配置文件
verify_configurations() {
    log_info "验证配置文件..."
    
    # 验证Docker Compose配置
    if [ -f "scripts/quick_validate_compose.sh" ]; then
        log_info "验证Docker Compose配置..."
        if ./scripts/quick_validate_compose.sh > /dev/null 2>&1; then
            log_success "Docker Compose配置验证通过"
        else
            log_warning "Docker Compose配置验证失败"
            return 1
        fi
    fi
    
    # 检查关键文件
    local critical_files=(
        "backend/Dockerfile.aliyun"
        "frontend/Dockerfile.aliyun"
        "nginx/Dockerfile.proxy"
        "docker-compose.aliyun.yml"
    )
    
    for file in "${critical_files[@]}"; do
        if [ -f "$file" ]; then
            log_success "配置文件存在: $file"
        else
            log_error "配置文件缺失: $file"
            return 1
        fi
    done
    
    return 0
}

# 测试构建
test_builds() {
    log_info "测试镜像构建..."
    
    # 测试后端构建
    if [ -f "scripts/smart_build_backend.sh" ]; then
        log_info "测试后端镜像构建..."
        if ./scripts/smart_build_backend.sh --test-only; then
            log_success "后端镜像构建测试通过"
        else
            log_warning "后端镜像构建测试失败"
        fi
    fi
    
    # 简单的构建测试
    log_info "执行简单构建测试..."
    if docker build -f backend/Dockerfile.aliyun -t ssl-backend-test ./backend > /dev/null 2>&1; then
        log_success "后端镜像构建成功"
        docker rmi ssl-backend-test > /dev/null 2>&1 || true
    else
        log_warning "后端镜像构建失败"
    fi
}

# 生成修复报告
generate_report() {
    local report_file="image_fix_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成修复报告: $report_file"
    
    {
        echo "SSL证书管理系统 - 镜像问题修复报告"
        echo "生成时间: $(date)"
        echo "========================================"
        echo
        
        echo "=== 系统环境 ==="
        uname -a
        echo "Docker版本: $(docker --version)"
        if docker compose version > /dev/null 2>&1; then
            echo "Docker Compose版本: $(docker compose version)"
        fi
        echo
        
        echo "=== 网络连接测试 ==="
        ping -c 1 registry-1.docker.io > /dev/null 2>&1 && echo "✅ Docker Hub连接正常" || echo "❌ Docker Hub连接失败"
        ping -c 1 registry.cn-hangzhou.aliyuncs.com > /dev/null 2>&1 && echo "✅ 阿里云镜像仓库连接正常" || echo "❌ 阿里云镜像仓库连接失败"
        echo
        
        echo "=== 镜像拉取测试 ==="
        docker pull python:3.10-slim > /dev/null 2>&1 && echo "✅ Python镜像拉取成功" || echo "❌ Python镜像拉取失败"
        docker pull nginx:alpine > /dev/null 2>&1 && echo "✅ Nginx镜像拉取成功" || echo "❌ Nginx镜像拉取失败"
        echo
        
        echo "=== 配置文件状态 ==="
        [ -f "backend/Dockerfile.aliyun" ] && echo "✅ backend/Dockerfile.aliyun" || echo "❌ backend/Dockerfile.aliyun"
        [ -f "docker-compose.aliyun.yml" ] && echo "✅ docker-compose.aliyun.yml" || echo "❌ docker-compose.aliyun.yml"
        echo
        
        echo "=== 修复建议 ==="
        echo "1. 如果镜像拉取失败，运行: ./scripts/fix_python_image_issue.sh"
        echo "2. 如果配置验证失败，运行: ./scripts/quick_validate_compose.sh"
        echo "3. 如果构建失败，运行: ./scripts/smart_build_backend.sh"
        echo "4. 完整部署命令: ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
        
    } > "$report_file"
    
    log_success "修复报告已生成: $report_file"
}

# 显示修复建议
show_fix_suggestions() {
    echo
    echo "=== 🔧 修复建议 ==="
    echo
    echo "根据检测结果，建议按以下顺序执行修复："
    echo
    echo "1. 修复Python镜像问题:"
    echo "   ./scripts/fix_python_image_issue.sh"
    echo
    echo "2. 修复Nginx镜像问题:"
    echo "   ./scripts/fix_nginx_image_issue.sh"
    echo
    echo "3. 验证配置文件:"
    echo "   ./scripts/quick_validate_compose.sh"
    echo
    echo "4. 智能构建后端:"
    echo "   ./scripts/smart_build_backend.sh"
    echo
    echo "5. 继续完整部署:"
    echo "   ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
    echo
}

# 主函数
main() {
    echo "🔍 SSL证书管理系统 - 镜像问题验证和修复工具"
    echo "================================================="
    echo
    
    local auto_fix=false
    local generate_report_flag=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-fix)
                auto_fix=true
                shift
                ;;
            --report)
                generate_report_flag=true
                shift
                ;;
            --help)
                echo "镜像问题验证和修复脚本"
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --auto-fix    自动修复发现的问题"
                echo "  --report      生成详细报告"
                echo "  --help        显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    local checks_passed=0
    local total_checks=4
    
    # 执行检查
    if check_docker_environment; then ((checks_passed++)); fi
    echo
    
    if check_network_connectivity; then ((checks_passed++)); fi
    echo
    
    if test_critical_images; then ((checks_passed++)); fi
    echo
    
    if verify_configurations; then ((checks_passed++)); fi
    echo
    
    # 可选的构建测试
    test_builds
    echo
    
    # 显示检查结果
    echo "=== 检查结果 ==="
    echo "通过检查: $checks_passed/$total_checks"
    
    if [ "$checks_passed" -eq "$total_checks" ]; then
        log_success "🎉 所有检查通过！系统已准备好进行部署"
        echo
        echo "可以继续执行完整部署:"
        echo "  ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
    elif [ "$checks_passed" -ge 2 ]; then
        log_warning "部分检查通过，建议先修复问题"
        
        if [ "$auto_fix" = "true" ]; then
            echo
            auto_fix_images
        else
            show_fix_suggestions
        fi
    else
        log_error "多项检查失败，需要修复问题"
        
        if [ "$auto_fix" = "true" ]; then
            echo
            auto_fix_images
        else
            show_fix_suggestions
        fi
    fi
    
    # 生成报告
    if [ "$generate_report_flag" = "true" ]; then
        echo
        generate_report
    fi
}

# 执行主函数
main "$@"
