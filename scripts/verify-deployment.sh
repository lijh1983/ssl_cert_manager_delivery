#!/bin/bash

# SSL证书管理系统 - 部署验证脚本
# 验证所有服务是否正常运行

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
COMPOSE_FILE="docker-compose.local.yml"
TIMEOUT=30

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

# 检查服务状态
check_service_status() {
    log_info "检查Docker服务状态..."
    
    if ! docker ps &> /dev/null; then
        log_error "Docker服务未运行"
        return 1
    fi
    
    # 检查容器状态
    local containers=(
        "ssl-manager-postgres"
        "ssl-manager-redis"
        "ssl-manager-backend"
        "ssl-manager-frontend"
        "ssl-manager-nginx"
    )
    
    local failed_containers=()
    
    for container in "${containers[@]}"; do
        if ! docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container.*Up"; then
            failed_containers+=("$container")
        fi
    done
    
    if [ ${#failed_containers[@]} -ne 0 ]; then
        log_error "以下容器未正常运行："
        for container in "${failed_containers[@]}"; do
            echo "  - $container"
        done
        return 1
    fi
    
    log_success "所有容器状态正常"
    return 0
}

# 检查健康状态
check_health_status() {
    log_info "检查服务健康状态..."
    
    local services=(
        "postgres:5432"
        "redis:6379"
        "backend:8000"
        "frontend:3000"
        "nginx:80"
    )
    
    for service in "${services[@]}"; do
        local name="${service%:*}"
        local port="${service#*:}"
        local container="ssl-manager-$name"
        
        log_info "检查 $name 服务..."
        
        # 检查端口是否监听
        if docker exec "$container" netstat -tln 2>/dev/null | grep -q ":$port "; then
            log_success "$name 服务端口 $port 正常监听"
        else
            log_warning "$name 服务端口 $port 可能未就绪"
        fi
    done
}

# HTTP健康检查
check_http_endpoints() {
    log_info "检查HTTP端点..."
    
    local endpoints=(
        "http://localhost:8000/health:后端API健康检查"
        "http://localhost:3000/health:前端服务健康检查"
        "http://localhost/health:代理服务健康检查"
        "http://localhost/api/health:通过代理的API健康检查"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        local url="${endpoint_info%:*}"
        local description="${endpoint_info#*:}"
        
        log_info "测试: $description"
        
        if curl -s -f --max-time 10 "$url" > /dev/null 2>&1; then
            log_success "$description 正常"
        else
            log_warning "$description 失败或超时"
            # 尝试获取详细错误信息
            local response=$(curl -s --max-time 5 "$url" 2>&1 || echo "连接失败")
            echo "  响应: $response"
        fi
    done
}

# 检查数据库连接
check_database_connection() {
    log_info "检查数据库连接..."
    
    # PostgreSQL连接测试
    if docker exec ssl-manager-postgres pg_isready -U ssl_user -d ssl_manager &> /dev/null; then
        log_success "PostgreSQL连接正常"
    else
        log_error "PostgreSQL连接失败"
        return 1
    fi
    
    # Redis连接测试
    if docker exec ssl-manager-redis redis-cli -a redis_password ping 2>/dev/null | grep -q "PONG"; then
        log_success "Redis连接正常"
    else
        log_error "Redis连接失败"
        return 1
    fi
    
    return 0
}

# 检查日志错误
check_logs_for_errors() {
    log_info "检查服务日志中的错误..."
    
    local services=("backend" "frontend" "nginx")
    
    for service in "${services[@]}"; do
        log_info "检查 $service 服务日志..."
        
        # 获取最近的日志并检查错误
        local error_count=$(docker logs "ssl-manager-$service" --since="5m" 2>&1 | grep -i "error\|exception\|failed" | wc -l)
        
        if [ "$error_count" -gt 0 ]; then
            log_warning "$service 服务日志中发现 $error_count 个错误"
            echo "最近的错误日志："
            docker logs "ssl-manager-$service" --since="5m" 2>&1 | grep -i "error\|exception\|failed" | tail -5
        else
            log_success "$service 服务日志正常"
        fi
    done
}

# 性能检查
check_performance() {
    log_info "检查系统性能..."
    
    # 检查容器资源使用
    echo "容器资源使用情况："
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" | grep ssl-manager
    
    # 检查磁盘使用
    echo
    echo "Docker磁盘使用情况："
    docker system df
}

# 功能测试
run_functional_tests() {
    log_info "运行基本功能测试..."
    
    # 测试API文档访问
    if curl -s -f "http://localhost:8000/docs" > /dev/null; then
        log_success "API文档访问正常"
    else
        log_warning "API文档访问失败"
    fi
    
    # 测试前端页面
    if curl -s -f "http://localhost:3000/" > /dev/null; then
        log_success "前端页面访问正常"
    else
        log_warning "前端页面访问失败"
    fi
    
    # 测试代理转发
    if curl -s -f "http://localhost/" > /dev/null; then
        log_success "代理转发正常"
    else
        log_warning "代理转发失败"
    fi
}

# 生成报告
generate_report() {
    echo
    echo "=== 部署验证报告 ==="
    echo "验证时间: $(date)"
    echo
    
    # 服务状态摘要
    echo "服务状态摘要:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep ssl-manager
    
    echo
    echo "访问地址:"
    echo "  前端应用: http://localhost:3000"
    echo "  后端API:  http://localhost:8000"
    echo "  API文档:  http://localhost:8000/docs"
    echo "  代理服务: http://localhost"
    
    echo
    echo "管理命令:"
    echo "  查看日志: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  重启服务: docker-compose -f $COMPOSE_FILE restart"
    echo "  停止服务: docker-compose -f $COMPOSE_FILE stop"
}

# 主函数
main() {
    echo "=== SSL证书管理系统部署验证 ==="
    echo
    
    local exit_code=0
    
    # 执行各项检查
    check_service_status || exit_code=1
    echo
    
    check_health_status || exit_code=1
    echo
    
    check_http_endpoints || exit_code=1
    echo
    
    check_database_connection || exit_code=1
    echo
    
    check_logs_for_errors || exit_code=1
    echo
    
    check_performance || exit_code=1
    echo
    
    run_functional_tests || exit_code=1
    echo
    
    generate_report
    
    if [ $exit_code -eq 0 ]; then
        log_success "所有验证检查通过！"
    else
        log_warning "部分验证检查失败，请查看上述详细信息"
    fi
    
    return $exit_code
}

# 执行主函数
main "$@"
