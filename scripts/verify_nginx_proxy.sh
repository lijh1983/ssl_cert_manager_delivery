#!/bin/bash
# nginx反向代理验证脚本

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

# 获取域名
get_domain() {
    if [ -n "$DOMAIN_NAME" ]; then
        DOMAIN="$DOMAIN_NAME"
    elif [ -f ".env" ] && grep -q "DOMAIN_NAME" .env; then
        DOMAIN=$(grep "DOMAIN_NAME" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    else
        DOMAIN="ssl.gzyggl.com"
    fi
    
    log_info "使用域名: $DOMAIN"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    echo "=== Docker容器状态 ==="
    docker-compose -f docker-compose.aliyun.yml ps
    echo
    
    # 检查关键容器是否运行
    local containers=("ssl-manager-nginx-proxy" "ssl-manager-frontend" "ssl-manager-backend")
    local failed=0
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$container"; then
            log_success "容器 $container 正在运行"
        else
            log_error "容器 $container 未运行"
            failed=1
        fi
    done
    
    return $failed
}

# 检查端口监听
check_ports() {
    log_info "检查端口监听状态..."
    
    local ports=(80 443)
    local failed=0
    
    for port in "${ports[@]}"; do
        if ss -tlnp | grep ":$port " > /dev/null; then
            log_success "端口 $port 正在监听"
        else
            log_error "端口 $port 未监听"
            failed=1
        fi
    done
    
    return $failed
}

# 测试HTTP访问
test_http_access() {
    log_info "测试HTTP访问..."
    
    local failed=0
    
    # 测试前端主页
    log_info "测试前端主页..."
    if curl -f -s http://localhost/ > /dev/null; then
        log_success "前端主页访问正常: http://$DOMAIN/"
    else
        log_error "前端主页访问失败"
        failed=1
    fi
    
    # 测试API健康检查
    log_info "测试API健康检查..."
    if curl -f -s http://localhost/api/health > /dev/null; then
        log_success "API健康检查正常: http://$DOMAIN/api/health"
    else
        log_error "API健康检查失败"
        failed=1
    fi
    
    # 测试API接口
    log_info "测试API接口..."
    local api_response=$(curl -s -w "%{http_code}" http://localhost/api/servers -o /dev/null)
    if [ "$api_response" = "200" ] || [ "$api_response" = "401" ]; then
        log_success "API接口响应正常: http://$DOMAIN/api/"
    else
        log_warning "API接口响应异常，状态码: $api_response"
    fi
    
    # 测试监控面板（如果存在）
    if docker ps --format "table {{.Names}}" | grep -q "ssl-manager-grafana"; then
        log_info "测试监控面板..."
        if curl -f -s http://localhost/monitoring/ > /dev/null; then
            log_success "监控面板访问正常: http://$DOMAIN/monitoring/"
        else
            log_warning "监控面板访问失败"
        fi
    fi
    
    return $failed
}

# 测试响应时间
test_response_time() {
    log_info "测试响应时间..."
    
    # 创建curl格式文件
    cat > /tmp/curl-format.txt <<EOF
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
    
    echo "=== 前端响应时间 ==="
    curl -w "@/tmp/curl-format.txt" -o /dev/null -s http://localhost/
    
    echo "=== API响应时间 ==="
    curl -w "@/tmp/curl-format.txt" -o /dev/null -s http://localhost/api/health
    
    # 清理临时文件
    rm -f /tmp/curl-format.txt
}

# 检查nginx配置
check_nginx_config() {
    log_info "检查nginx配置..."
    
    # 测试nginx配置语法
    if docker-compose -f docker-compose.aliyun.yml exec -T nginx-proxy nginx -t > /dev/null 2>&1; then
        log_success "nginx配置语法正确"
    else
        log_error "nginx配置语法错误"
        docker-compose -f docker-compose.aliyun.yml exec nginx-proxy nginx -t
        return 1
    fi
    
    # 检查upstream配置
    log_info "检查upstream配置..."
    docker-compose -f docker-compose.aliyun.yml exec nginx-proxy nginx -T 2>/dev/null | grep -A 5 "upstream" || true
}

# 检查SSL配置
check_ssl_config() {
    log_info "检查SSL配置..."
    
    # 检查SSL证书文件
    if [ -f "nginx/ssl/$DOMAIN.crt" ]; then
        log_success "SSL证书文件存在: nginx/ssl/$DOMAIN.crt"
        
        # 检查证书有效期
        local expiry=$(openssl x509 -in "nginx/ssl/$DOMAIN.crt" -noout -enddate | cut -d= -f2)
        log_info "证书有效期至: $expiry"
    else
        log_warning "SSL证书文件不存在: nginx/ssl/$DOMAIN.crt"
    fi
    
    # 测试HTTPS访问（如果配置了）
    if ss -tlnp | grep ":443 " > /dev/null; then
        log_info "测试HTTPS访问..."
        if curl -k -f -s https://localhost/ > /dev/null; then
            log_success "HTTPS访问正常"
        else
            log_warning "HTTPS访问失败"
        fi
    else
        log_info "HTTPS端口未监听，跳过HTTPS测试"
    fi
}

# 检查日志
check_logs() {
    log_info "检查最近的错误日志..."
    
    echo "=== nginx错误日志 ==="
    docker-compose -f docker-compose.aliyun.yml logs --tail=10 nginx-proxy | grep -i error || echo "无错误日志"
    
    echo "=== 后端错误日志 ==="
    docker-compose -f docker-compose.aliyun.yml logs --tail=10 backend | grep -i error || echo "无错误日志"
    
    echo "=== 前端错误日志 ==="
    docker-compose -f docker-compose.aliyun.yml logs --tail=10 frontend | grep -i error || echo "无错误日志"
}

# 性能测试
performance_test() {
    log_info "执行简单性能测试..."
    
    if command -v ab > /dev/null; then
        echo "=== Apache Bench测试 (100请求，并发10) ==="
        ab -n 100 -c 10 http://localhost/ 2>/dev/null | grep -E "(Requests per second|Time per request|Transfer rate)"
    else
        log_warning "Apache Bench未安装，跳过性能测试"
    fi
}

# 生成报告
generate_report() {
    log_info "生成验证报告..."
    
    local report_file="nginx_proxy_verification_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "SSL证书管理系统 - nginx反向代理验证报告"
        echo "生成时间: $(date)"
        echo "域名: $DOMAIN"
        echo "========================================"
        echo
        
        echo "=== 服务状态 ==="
        docker-compose -f docker-compose.aliyun.yml ps
        echo
        
        echo "=== 端口监听 ==="
        ss -tlnp | grep -E ":(80|443|8000|3000|9090) "
        echo
        
        echo "=== 访问测试结果 ==="
        echo "前端主页: $(curl -s -w "%{http_code}" http://localhost/ -o /dev/null)"
        echo "API健康检查: $(curl -s -w "%{http_code}" http://localhost/api/health -o /dev/null)"
        echo "API接口: $(curl -s -w "%{http_code}" http://localhost/api/servers -o /dev/null)"
        if docker ps --format "table {{.Names}}" | grep -q "ssl-manager-grafana"; then
            echo "监控面板: $(curl -s -w "%{http_code}" http://localhost/monitoring/ -o /dev/null)"
        fi
        echo
        
        echo "=== nginx配置检查 ==="
        docker-compose -f docker-compose.aliyun.yml exec -T nginx-proxy nginx -t 2>&1
        echo
        
        echo "=== 最近错误日志 ==="
        docker-compose -f docker-compose.aliyun.yml logs --tail=5 nginx-proxy | grep -i error || echo "无错误日志"
        
    } > "$report_file"
    
    log_success "验证报告已生成: $report_file"
}

# 显示访问信息
show_access_info() {
    echo
    echo "=== 🎉 nginx反向代理验证完成 ==="
    echo
    echo "📱 访问地址:"
    echo "   前端主页:    http://$DOMAIN/"
    echo "   后端API:     http://$DOMAIN/api/"
    if docker ps --format "table {{.Names}}" | grep -q "ssl-manager-grafana"; then
        echo "   监控面板:    http://$DOMAIN/monitoring/"
    fi
    echo
    echo "🔍 健康检查:"
    echo "   前端健康:    http://$DOMAIN/health"
    echo "   API健康:     http://$DOMAIN/api/health"
    echo
    echo "🛠️ 管理命令:"
    echo "   查看状态:    ./scripts/restart_services.sh status"
    echo "   重启nginx:   ./scripts/restart_services.sh restart nginx"
    echo "   查看日志:    ./scripts/restart_services.sh logs nginx"
    echo "   健康检查:    ./scripts/restart_services.sh health"
    echo
}

# 主函数
main() {
    echo "🔍 SSL证书管理系统 - nginx反向代理验证"
    echo "========================================"
    echo
    
    get_domain
    
    local checks_passed=0
    local total_checks=4
    
    # 执行检查
    if check_services; then ((checks_passed++)); fi
    echo
    
    if check_ports; then ((checks_passed++)); fi
    echo
    
    if test_http_access; then ((checks_passed++)); fi
    echo
    
    check_nginx_config
    echo
    
    check_ssl_config
    echo
    
    test_response_time
    echo
    
    check_logs
    echo
    
    # 可选的性能测试
    if [ "$1" = "--performance" ]; then
        performance_test
        echo
    fi
    
    # 生成报告
    if [ "$1" = "--report" ]; then
        generate_report
    fi
    
    # 显示结果
    echo "=== 验证结果 ==="
    echo "关键检查通过: $checks_passed/$total_checks"
    
    if [ "$checks_passed" -eq "$total_checks" ]; then
        log_success "所有关键检查通过！nginx反向代理配置成功 🎉"
        show_access_info
    elif [ "$checks_passed" -ge 2 ]; then
        log_warning "部分检查通过，系统基本可用，但建议解决警告问题"
        show_access_info
    else
        log_error "多项检查失败，请检查配置和服务状态"
        exit 1
    fi
}

# 执行主函数
main "$@"
