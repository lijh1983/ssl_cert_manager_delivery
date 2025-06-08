#!/bin/bash
# 快速验证Docker Compose配置

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

# 检查文件结构
check_file_structure() {
    local compose_file="$1"
    
    log_info "检查Docker Compose文件结构..."
    
    # 检查必需的顶级部分
    local required_sections=("version:" "networks:" "volumes:" "services:")
    local missing_sections=()
    
    for section in "${required_sections[@]}"; do
        if grep -q "^$section" "$compose_file"; then
            log_success "发现必需部分: $section"
        else
            log_error "缺失必需部分: $section"
            missing_sections+=("$section")
        fi
    done
    
    if [ ${#missing_sections[@]} -eq 0 ]; then
        log_success "文件结构检查通过"
        return 0
    else
        log_error "文件结构检查失败，缺失: ${missing_sections[*]}"
        return 1
    fi
}

# 检查volumes配置
check_volumes_config() {
    local compose_file="$1"
    
    log_info "检查volumes配置..."
    
    # 检查volumes是否在正确位置
    if grep -A 20 "^volumes:" "$compose_file" | grep -q "prometheus_data:"; then
        log_success "prometheus_data在正确的volumes部分"
    else
        log_error "prometheus_data不在volumes部分"
        return 1
    fi
    
    if grep -A 20 "^volumes:" "$compose_file" | grep -q "grafana_data:"; then
        log_success "grafana_data在正确的volumes部分"
    else
        log_error "grafana_data不在volumes部分"
        return 1
    fi
    
    # 检查是否有错误的volumes定义（在services部分）
    if grep -A 100 "^services:" "$compose_file" | grep -q "^  prometheus_data:"; then
        log_error "发现错误的prometheus_data定义位置（在services部分）"
        return 1
    fi
    
    log_success "volumes配置检查通过"
    return 0
}

# 检查服务配置
check_services_config() {
    local compose_file="$1"
    
    log_info "检查services配置..."
    
    # 检查关键服务
    local required_services=("postgres" "redis" "backend" "frontend" "nginx-proxy")
    local missing_services=()
    
    for service in "${required_services[@]}"; do
        if grep -q "^  $service:" "$compose_file"; then
            log_success "发现服务: $service"
        else
            log_warning "缺失服务: $service"
            missing_services+=("$service")
        fi
    done
    
    # 检查监控服务（可选）
    if grep -q "^  prometheus:" "$compose_file"; then
        log_success "发现监控服务: prometheus"
    fi
    
    if grep -q "^  grafana:" "$compose_file"; then
        log_success "发现监控服务: grafana"
    fi
    
    if [ ${#missing_services[@]} -eq 0 ]; then
        log_success "所有关键服务都已定义"
        return 0
    else
        log_warning "缺失的服务: ${missing_services[*]}"
        return 1
    fi
}

# 检查网络配置
check_network_config() {
    local compose_file="$1"
    
    log_info "检查网络配置..."
    
    if grep -q "ssl-manager-network:" "$compose_file"; then
        log_success "ssl-manager-network网络已定义"
        
        # 检查子网配置
        if grep -A 5 "ssl-manager-network:" "$compose_file" | grep -q "subnet:"; then
            log_success "网络子网配置存在"
        else
            log_warning "网络子网配置缺失"
        fi
        
        return 0
    else
        log_error "ssl-manager-network网络未定义"
        return 1
    fi
}

# 生成修复建议
show_fix_suggestions() {
    echo
    echo "=== 🔧 修复建议 ==="
    echo
    echo "如果发现配置错误，可以："
    echo
    echo "1. 使用自动修复脚本:"
    echo "   ./scripts/fix_docker_compose.sh"
    echo
    echo "2. 手动检查以下内容:"
    echo "   - 确保prometheus_data和grafana_data在顶级volumes部分"
    echo "   - 检查YAML缩进是否正确（使用2个空格）"
    echo "   - 确保没有重复的服务或volumes定义"
    echo
    echo "3. 验证修复结果:"
    echo "   ./scripts/quick_validate_compose.sh"
    echo
}

# 主函数
main() {
    echo "🔍 Docker Compose配置快速验证"
    echo "==============================="
    echo
    
    local compose_file="${1:-docker-compose.aliyun.yml}"
    local validation_passed=true
    
    # 检查文件是否存在
    if [ ! -f "$compose_file" ]; then
        log_error "Docker Compose文件不存在: $compose_file"
        exit 1
    fi
    
    log_info "验证文件: $compose_file"
    echo
    
    # 执行各项检查
    if ! check_file_structure "$compose_file"; then
        validation_passed=false
    fi
    echo
    
    if ! check_volumes_config "$compose_file"; then
        validation_passed=false
    fi
    echo
    
    if ! check_services_config "$compose_file"; then
        validation_passed=false
    fi
    echo
    
    if ! check_network_config "$compose_file"; then
        validation_passed=false
    fi
    echo
    
    # 显示验证结果
    if [ "$validation_passed" = "true" ]; then
        log_success "🎉 Docker Compose配置验证通过！"
        echo
        echo "=== ✅ 验证结果 ==="
        echo "✓ 文件结构正确"
        echo "✓ volumes配置正确"
        echo "✓ services配置正确"
        echo "✓ 网络配置正确"
        echo
        echo "=== 🚀 下一步操作 ==="
        echo "现在可以继续执行nginx反向代理配置:"
        echo "  ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
        echo
    else
        log_error "❌ Docker Compose配置验证失败"
        show_fix_suggestions
        exit 1
    fi
}

# 执行主函数
main "$@"
