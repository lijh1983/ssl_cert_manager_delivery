#!/bin/bash
# 简化的验证测试脚本

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

# 测试Docker验证
test_docker_verification() {
    log_info "开始Docker验证测试..."
    
    local verification_passed=0
    local total_verifications=1
    
    # Docker验证
    log_info "验证Docker环境..."
    
    # 检查Docker服务状态
    if docker info > /dev/null 2>&1; then
        log_success "Docker服务正常运行"
        
        # 检查Docker版本
        local docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        log_info "Docker版本: $docker_version"
        
        # 检查Docker镜像
        local image_count=$(docker images -q | wc -l)
        log_info "本地镜像数量: $image_count"
        
        # 检查运行中的容器
        local running_containers=$(docker ps -q | wc -l)
        log_info "运行中容器数量: $running_containers"
        
        ((verification_passed++))
    else
        log_error "Docker服务异常或未启动"
        log_info "请检查Docker服务状态: systemctl status docker"
    fi
    
    # 显示验证结果
    echo
    log_info "验证结果: $verification_passed/$total_verifications"
    
    if [ "$verification_passed" -eq "$total_verifications" ]; then
        log_success "🎉 Docker验证通过！"
        return 0
    else
        log_warning "Docker验证失败"
        return 1
    fi
}

# 测试Alpine验证
test_alpine_verification() {
    log_info "开始Alpine验证测试..."
    
    # 检查Alpine优化工具
    if [ -f "scripts/alpine-optimizer.sh" ]; then
        log_success "Alpine优化工具存在"
        
        # 测试Alpine优化工具功能
        log_info "测试Alpine优化工具功能..."
        if timeout 30 ./scripts/alpine-optimizer.sh verify > /dev/null 2>&1; then
            log_success "Alpine优化工具功能正常"
        else
            log_warning "Alpine优化工具功能异常"
        fi
    else
        log_error "Alpine优化工具缺失"
    fi
}

# 测试Docker Compose验证
test_compose_verification() {
    log_info "开始Docker Compose验证测试..."
    
    # 检查配置文件存在
    if [ -f "docker-compose.aliyun.yml" ]; then
        log_success "docker-compose.aliyun.yml文件存在"
        
        # 检查配置语法
        log_info "检查Docker Compose配置语法..."
        if docker compose -f docker-compose.aliyun.yml config > /dev/null 2>&1; then
            log_success "Docker Compose配置语法正确"
        elif docker-compose -f docker-compose.aliyun.yml config > /dev/null 2>&1; then
            log_success "Docker Compose配置语法正确 (使用docker-compose命令)"
        else
            log_error "Docker Compose配置语法错误"
            log_info "请检查配置文件: docker-compose.aliyun.yml"
        fi
    else
        log_error "docker-compose.aliyun.yml文件不存在"
    fi
}

# 测试网络验证
test_network_verification() {
    log_info "开始网络验证测试..."
    
    local test_hosts=(
        "mirrors.aliyun.com"
        "registry-1.docker.io"
        "8.8.8.8"
    )
    
    for host in "${test_hosts[@]}"; do
        log_info "测试连接: $host"
        if ping -c 1 -W 3 "$host" > /dev/null 2>&1; then
            log_success "$host 连接正常"
        else
            log_error "$host 连接失败"
        fi
    done
}

# 主函数
main() {
    echo "🧪 SSL证书管理系统验证功能测试"
    echo "==============================="
    echo
    
    case "${1:-all}" in
        docker)
            test_docker_verification
            ;;
        alpine)
            test_alpine_verification
            ;;
        compose)
            test_compose_verification
            ;;
        network)
            test_network_verification
            ;;
        all)
            test_docker_verification
            echo
            test_alpine_verification
            echo
            test_compose_verification
            echo
            test_network_verification
            ;;
        *)
            echo "用法: $0 [docker|alpine|compose|network|all]"
            exit 1
            ;;
    esac
    
    echo
    log_success "验证测试完成"
}

# 执行主函数
main "$@"
