#!/bin/bash
# Docker Compose配置验证脚本

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

# 验证Docker Compose文件语法
validate_compose_syntax() {
    local compose_file="$1"
    
    log_info "验证Docker Compose文件语法: $compose_file"
    
    if [ ! -f "$compose_file" ]; then
        log_error "Docker Compose文件不存在: $compose_file"
        return 1
    fi
    
    # 检查YAML语法
    if command -v yamllint > /dev/null 2>&1; then
        log_info "使用yamllint检查YAML语法..."
        if yamllint "$compose_file" > /dev/null 2>&1; then
            log_success "YAML语法检查通过"
        else
            log_warning "YAML语法检查发现问题:"
            yamllint "$compose_file" || true
        fi
    else
        log_info "yamllint未安装，跳过YAML语法检查"
    fi
    
    # 使用docker-compose验证配置
    log_info "使用docker-compose验证配置..."
    if docker-compose -f "$compose_file" config > /dev/null 2>&1; then
        log_success "Docker Compose配置验证通过"
        return 0
    else
        log_error "Docker Compose配置验证失败:"
        docker-compose -f "$compose_file" config 2>&1 | head -20
        return 1
    fi
}

# 检查服务定义
check_services() {
    local compose_file="$1"
    
    log_info "检查服务定义..."
    
    # 获取所有服务名称
    local services=$(docker-compose -f "$compose_file" config --services 2>/dev/null || echo "")
    
    if [ -z "$services" ]; then
        log_error "无法获取服务列表"
        return 1
    fi
    
    log_info "发现的服务:"
    for service in $services; do
        echo "  ✓ $service"
    done
    
    # 检查关键服务
    local required_services=("postgres" "redis" "backend" "frontend" "nginx-proxy")
    local missing_services=()
    
    for required in "${required_services[@]}"; do
        if echo "$services" | grep -q "^$required$"; then
            log_success "关键服务存在: $required"
        else
            log_warning "关键服务缺失: $required"
            missing_services+=("$required")
        fi
    done
    
    if [ ${#missing_services[@]} -eq 0 ]; then
        log_success "所有关键服务都已定义"
        return 0
    else
        log_warning "缺失的关键服务: ${missing_services[*]}"
        return 1
    fi
}

# 检查数据卷定义
check_volumes() {
    local compose_file="$1"
    
    log_info "检查数据卷定义..."
    
    # 获取所有数据卷
    local volumes=$(docker-compose -f "$compose_file" config --volumes 2>/dev/null || echo "")
    
    if [ -z "$volumes" ]; then
        log_warning "没有发现数据卷定义"
        return 1
    fi
    
    log_info "发现的数据卷:"
    for volume in $volumes; do
        echo "  ✓ $volume"
    done
    
    # 检查关键数据卷
    local required_volumes=("postgres_data" "redis_data" "ssl_certs" "nginx_proxy_logs")
    local missing_volumes=()
    
    for required in "${required_volumes[@]}"; do
        if echo "$volumes" | grep -q "^$required$"; then
            log_success "关键数据卷存在: $required"
        else
            log_warning "关键数据卷缺失: $required"
            missing_volumes+=("$required")
        fi
    done
    
    if [ ${#missing_volumes[@]} -eq 0 ]; then
        log_success "所有关键数据卷都已定义"
        return 0
    else
        log_warning "缺失的关键数据卷: ${missing_volumes[*]}"
        return 1
    fi
}

# 检查网络定义
check_networks() {
    local compose_file="$1"
    
    log_info "检查网络定义..."
    
    # 检查网络配置
    if docker-compose -f "$compose_file" config | grep -q "networks:"; then
        log_success "网络配置存在"
        
        # 检查特定网络
        if docker-compose -f "$compose_file" config | grep -q "ssl-manager-network"; then
            log_success "ssl-manager-network网络已定义"
        else
            log_warning "ssl-manager-network网络未定义"
        fi
    else
        log_warning "没有发现网络配置"
    fi
}

# 检查环境变量
check_environment() {
    local compose_file="$1"
    
    log_info "检查环境变量配置..."
    
    # 检查.env文件
    if [ -f ".env" ]; then
        log_success ".env文件存在"
        
        # 检查关键环境变量
        local required_vars=("DOMAIN_NAME" "DB_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY")
        local missing_vars=()
        
        for var in "${required_vars[@]}"; do
            if grep -q "^$var=" .env; then
                log_success "环境变量存在: $var"
            else
                log_warning "环境变量缺失: $var"
                missing_vars+=("$var")
            fi
        done
        
        if [ ${#missing_vars[@]} -gt 0 ]; then
            log_warning "建议在.env文件中设置: ${missing_vars[*]}"
        fi
    else
        log_warning ".env文件不存在，将使用默认值"
    fi
}

# 生成修复建议
generate_fix_suggestions() {
    local compose_file="$1"
    
    log_info "生成修复建议..."
    
    echo
    echo "=== 常见问题修复建议 ==="
    echo
    echo "1. 如果遇到volumes配置错误:"
    echo "   - 确保所有volumes定义在顶级volumes部分"
    echo "   - 检查缩进是否正确（使用2个空格）"
    echo "   - 确保没有重复的volumes定义"
    echo
    echo "2. 如果遇到services配置错误:"
    echo "   - 检查服务名称是否唯一"
    echo "   - 确保所有必需的字段都已定义"
    echo "   - 检查镜像名称是否正确"
    echo
    echo "3. 如果遇到网络配置错误:"
    echo "   - 确保网络名称在整个文件中一致"
    echo "   - 检查IP地址分配是否冲突"
    echo "   - 确保子网配置正确"
    echo
    echo "4. 环境变量配置:"
    echo "   - 复制.env.example到.env"
    echo "   - 设置所有必需的环境变量"
    echo "   - 使用强密码和安全的密钥"
    echo
}

# 主函数
main() {
    echo "🔍 Docker Compose配置验证工具"
    echo "================================"
    echo
    
    local compose_file="${1:-docker-compose.aliyun.yml}"
    local validation_passed=true
    
    # 执行各项检查
    if ! validate_compose_syntax "$compose_file"; then
        validation_passed=false
    fi
    echo
    
    if ! check_services "$compose_file"; then
        validation_passed=false
    fi
    echo
    
    if ! check_volumes "$compose_file"; then
        validation_passed=false
    fi
    echo
    
    check_networks "$compose_file"
    echo
    
    check_environment "$compose_file"
    echo
    
    # 显示验证结果
    if [ "$validation_passed" = "true" ]; then
        log_success "🎉 Docker Compose配置验证通过！"
        echo
        echo "可以继续执行部署:"
        echo "  ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
    else
        log_error "❌ Docker Compose配置验证失败"
        generate_fix_suggestions "$compose_file"
        exit 1
    fi
}

# 执行主函数
main "$@"
