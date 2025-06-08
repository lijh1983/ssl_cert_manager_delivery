#!/bin/bash
# SSL证书管理系统部署测试脚本
# 用途: 验证部署是否成功

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:80"
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3000"

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

# 检查Docker服务
check_docker_services() {
    log_info "检查Docker服务状态..."
    
    # 检查容器是否运行
    local containers=(
        "ssl-manager-postgres"
        "ssl-manager-redis"
        "ssl-manager-backend"
        "ssl-manager-frontend"
    )
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$container"; then
            log_success "容器 $container 正在运行"
        else
            log_error "容器 $container 未运行"
            return 1
        fi
    done
    
    log_success "所有核心容器都在运行"
}

# 检查健康状态
check_health_endpoints() {
    log_info "检查健康状态端点..."
    
    # 检查后端健康状态
    if curl -f -s "$BACKEND_URL/health" > /dev/null; then
        log_success "后端健康检查通过"
        
        # 获取健康状态详情
        local health_data=$(curl -s "$BACKEND_URL/health" | python3 -m json.tool 2>/dev/null || echo "无法解析JSON")
        echo "  健康状态详情: $health_data"
    else
        log_error "后端健康检查失败"
        return 1
    fi
    
    # 检查前端健康状态
    if curl -f -s "$FRONTEND_URL/health" > /dev/null; then
        log_success "前端健康检查通过"
    else
        log_warning "前端健康检查失败（可能正常，如果使用nginx代理）"
    fi
    
    # 检查就绪状态
    if curl -f -s "$BACKEND_URL/ready" > /dev/null; then
        log_success "后端就绪检查通过"
    else
        log_warning "后端就绪检查失败"
    fi
}

# 检查API端点
check_api_endpoints() {
    log_info "检查API端点..."
    
    # 检查基本API端点
    local endpoints=(
        "/api/auth/login"
        "/api/servers"
        "/api/certificates"
        "/api/users"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="$BACKEND_URL$endpoint"
        local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
        
        if [[ "$status_code" =~ ^[2-4][0-9][0-9]$ ]]; then
            log_success "API端点 $endpoint 可访问 (状态码: $status_code)"
        else
            log_error "API端点 $endpoint 不可访问 (状态码: $status_code)"
        fi
    done
}

# 检查数据库连接
check_database_connection() {
    log_info "检查数据库连接..."
    
    # 通过Docker检查PostgreSQL
    if docker exec ssl-manager-postgres pg_isready -U ssl_user > /dev/null 2>&1; then
        log_success "PostgreSQL数据库连接正常"
    else
        log_error "PostgreSQL数据库连接失败"
        return 1
    fi
    
    # 检查Redis
    if docker exec ssl-manager-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis连接正常"
    else
        log_error "Redis连接失败"
        return 1
    fi
}

# 检查监控服务
check_monitoring_services() {
    log_info "检查监控服务..."
    
    # 检查Prometheus
    if curl -f -s "$PROMETHEUS_URL/-/healthy" > /dev/null 2>&1; then
        log_success "Prometheus服务正常"
        
        # 检查目标状态
        local targets=$(curl -s "$PROMETHEUS_URL/api/v1/targets" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    active_targets = [t for t in data['data']['activeTargets'] if t['health'] == 'up']
    print(f'活跃目标数量: {len(active_targets)}')
except:
    print('无法解析目标数据')
" 2>/dev/null || echo "无法获取目标信息")
        echo "  $targets"
    else
        log_warning "Prometheus服务不可用（可能未启用监控）"
    fi
    
    # 检查Grafana
    if curl -f -s "$GRAFANA_URL/api/health" > /dev/null 2>&1; then
        log_success "Grafana服务正常"
    else
        log_warning "Grafana服务不可用（可能未启用监控）"
    fi
}

# 检查系统资源
check_system_resources() {
    log_info "检查系统资源使用情况..."
    
    # 检查磁盘空间
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 80 ]; then
        log_success "磁盘使用率: ${disk_usage}%"
    else
        log_warning "磁盘使用率较高: ${disk_usage}%"
    fi
    
    # 检查内存使用
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$memory_usage" -lt 80 ]; then
        log_success "内存使用率: ${memory_usage}%"
    else
        log_warning "内存使用率较高: ${memory_usage}%"
    fi
    
    # 检查Docker资源使用
    log_info "Docker容器资源使用:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -10
}

# 检查日志
check_logs() {
    log_info "检查应用日志..."
    
    # 检查是否有错误日志
    local error_count=$(docker-compose logs --tail=100 2>/dev/null | grep -i error | wc -l || echo "0")
    if [ "$error_count" -eq 0 ]; then
        log_success "最近100行日志中无错误"
    else
        log_warning "最近100行日志中发现 $error_count 个错误"
        echo "  最近的错误日志:"
        docker-compose logs --tail=10 2>/dev/null | grep -i error | tail -3 || echo "  无法获取错误日志"
    fi
}

# 性能测试
performance_test() {
    log_info "执行基本性能测试..."
    
    # 测试API响应时间
    local start_time=$(date +%s%N)
    curl -s "$BACKEND_URL/health" > /dev/null
    local end_time=$(date +%s%N)
    local response_time=$(( (end_time - start_time) / 1000000 ))
    
    if [ "$response_time" -lt 1000 ]; then
        log_success "API响应时间: ${response_time}ms"
    else
        log_warning "API响应时间较慢: ${response_time}ms"
    fi
    
    # 测试并发请求
    log_info "测试并发请求处理能力..."
    local concurrent_requests=10
    local success_count=0
    
    for i in $(seq 1 $concurrent_requests); do
        if curl -f -s "$BACKEND_URL/health" > /dev/null &; then
            ((success_count++))
        fi
    done
    wait
    
    log_success "并发请求测试: $success_count/$concurrent_requests 成功"
}

# 生成测试报告
generate_report() {
    log_info "生成测试报告..."
    
    local report_file="deployment_test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
SSL证书管理系统部署测试报告
生成时间: $(date)
测试环境: $(uname -a)

=== 服务状态 ===
$(docker-compose ps 2>/dev/null || echo "无法获取服务状态")

=== 容器资源使用 ===
$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "无法获取资源使用情况")

=== 系统资源 ===
磁盘使用: $(df -h / | awk 'NR==2 {print $5}')
内存使用: $(free -h | awk 'NR==2{print $3"/"$2}')
CPU负载: $(uptime | awk -F'load average:' '{print $2}')

=== 网络连接 ===
$(netstat -tlnp | grep -E ':(80|443|8000|5432|6379|9090|3000)' 2>/dev/null || echo "无法获取网络连接信息")

=== 最近日志 ===
$(docker-compose logs --tail=20 2>/dev/null || echo "无法获取日志")

EOF
    
    log_success "测试报告已保存到: $report_file"
}

# 主函数
main() {
    echo "🧪 SSL证书管理系统部署测试"
    echo "================================"
    echo
    
    local test_passed=0
    local test_total=0
    
    # 执行测试
    local tests=(
        "check_docker_services"
        "check_database_connection"
        "check_health_endpoints"
        "check_api_endpoints"
        "check_monitoring_services"
        "check_system_resources"
        "check_logs"
        "performance_test"
    )
    
    for test in "${tests[@]}"; do
        ((test_total++))
        echo
        if $test; then
            ((test_passed++))
        fi
    done
    
    # 生成报告
    echo
    generate_report
    
    # 显示测试结果
    echo
    echo "=== 测试结果 ==="
    echo "通过: $test_passed/$test_total"
    
    if [ "$test_passed" -eq "$test_total" ]; then
        log_success "所有测试通过！部署成功 🎉"
        echo
        echo "🌐 访问地址:"
        echo "  前端: $FRONTEND_URL"
        echo "  后端API: $BACKEND_URL"
        echo "  健康检查: $BACKEND_URL/health"
        if curl -f -s "$PROMETHEUS_URL/-/healthy" > /dev/null 2>&1; then
            echo "  Prometheus: $PROMETHEUS_URL"
        fi
        if curl -f -s "$GRAFANA_URL/api/health" > /dev/null 2>&1; then
            echo "  Grafana: $GRAFANA_URL"
        fi
        exit 0
    else
        log_error "部分测试失败，请检查日志和配置"
        exit 1
    fi
}

# 执行主函数
main "$@"
