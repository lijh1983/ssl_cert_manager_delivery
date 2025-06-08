#!/bin/bash
# Docker Compose配置自动修复脚本

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

# 备份配置文件
backup_compose_file() {
    local compose_file="$1"
    local backup_file="${compose_file}.backup.$(date +%Y%m%d_%H%M%S)"
    
    log_info "备份配置文件: $compose_file -> $backup_file"
    cp "$compose_file" "$backup_file"
    log_success "配置文件已备份"
}

# 修复volumes配置错误
fix_volumes_config() {
    local compose_file="$1"
    
    log_info "修复volumes配置错误..."
    
    # 检查是否存在错误的volumes定义
    if grep -q "^  prometheus_data:" "$compose_file" || grep -q "^  grafana_data:" "$compose_file"; then
        log_warning "发现错误的volumes定义，正在修复..."
        
        # 移除错误的volumes定义
        sed -i '/^  prometheus_data:/,/^  grafana_data:/{/^  grafana_data:/!d;}' "$compose_file"
        sed -i '/^  grafana_data:/,/^$/d' "$compose_file"
        
        # 确保在正确的volumes部分添加定义
        if ! grep -q "prometheus_data:" "$compose_file"; then
            sed -i '/^volumes:/a\  prometheus_data:\n    driver: local\n  grafana_data:\n    driver: local' "$compose_file"
        fi
        
        log_success "volumes配置已修复"
    else
        log_info "volumes配置正常，无需修复"
    fi
}

# 修复服务依赖关系
fix_service_dependencies() {
    local compose_file="$1"
    
    log_info "检查服务依赖关系..."
    
    # 确保nginx-proxy依赖于其他服务
    if grep -A 20 "nginx-proxy:" "$compose_file" | grep -q "depends_on:"; then
        log_success "nginx-proxy依赖关系已配置"
    else
        log_warning "nginx-proxy缺少依赖关系配置"
        # 这里可以添加自动修复逻辑
    fi
}

# 修复网络配置
fix_network_config() {
    local compose_file="$1"
    
    log_info "检查网络配置..."
    
    # 确保网络配置正确
    if grep -q "ssl-manager-network:" "$compose_file"; then
        log_success "网络配置存在"
    else
        log_warning "网络配置缺失"
        # 可以添加自动修复逻辑
    fi
}

# 验证修复结果
validate_fix() {
    local compose_file="$1"
    
    log_info "验证修复结果..."
    
    if docker-compose -f "$compose_file" config > /dev/null 2>&1; then
        log_success "Docker Compose配置验证通过"
        return 0
    else
        log_error "配置验证仍然失败:"
        docker-compose -f "$compose_file" config 2>&1 | head -10
        return 1
    fi
}

# 显示修复摘要
show_fix_summary() {
    local compose_file="$1"
    
    echo
    log_success "🎉 Docker Compose配置修复完成！"
    echo
    echo "=== 修复摘要 ==="
    echo "✅ 修复了volumes配置错误"
    echo "✅ 验证了服务依赖关系"
    echo "✅ 检查了网络配置"
    echo "✅ 配置文件语法验证通过"
    echo
    echo "=== 下一步操作 ==="
    echo "现在可以继续执行nginx反向代理配置:"
    echo "  ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
    echo
    echo "或者先验证配置:"
    echo "  ./scripts/validate_docker_compose.sh $compose_file"
    echo
}

# 主函数
main() {
    echo "🔧 Docker Compose配置自动修复工具"
    echo "===================================="
    echo
    
    local compose_file="${1:-docker-compose.aliyun.yml}"
    
    # 检查文件是否存在
    if [ ! -f "$compose_file" ]; then
        log_error "Docker Compose文件不存在: $compose_file"
        exit 1
    fi
    
    # 备份原始文件
    backup_compose_file "$compose_file"
    
    # 执行修复
    fix_volumes_config "$compose_file"
    fix_service_dependencies "$compose_file"
    fix_network_config "$compose_file"
    
    # 验证修复结果
    if validate_fix "$compose_file"; then
        show_fix_summary "$compose_file"
    else
        log_error "修复失败，请手动检查配置"
        
        echo
        echo "=== 手动修复建议 ==="
        echo "1. 检查volumes部分的缩进是否正确"
        echo "2. 确保没有重复的服务或volumes定义"
        echo "3. 验证所有引用的镜像是否存在"
        echo "4. 检查环境变量是否正确设置"
        echo
        echo "可以恢复备份文件:"
        echo "  cp ${compose_file}.backup.* $compose_file"
        
        exit 1
    fi
}

# 执行主函数
main "$@"
