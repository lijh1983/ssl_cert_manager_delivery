#!/bin/bash
# SSL证书管理系统后端 - 健康检查脚本

set -e

# 配置
HEALTH_CHECK_URL="http://localhost:5000/api/health"
TIMEOUT=10
MAX_RETRIES=3

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[HEALTH]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[HEALTH]${NC} $1"
}

log_error() {
    echo -e "${RED}[HEALTH]${NC} $1"
}

# 检查HTTP健康端点
check_http_health() {
    local url="$1"
    local timeout="$2"
    
    # 使用curl检查健康端点
    response=$(curl -s -w "%{http_code}" -o /tmp/health_response --max-time "$timeout" "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        # 检查响应内容
        if grep -q "healthy" /tmp/health_response 2>/dev/null; then
            return 0
        else
            log_warn "健康端点返回200但内容异常"
            return 1
        fi
    else
        log_warn "健康端点返回状态码: $response"
        return 1
    fi
}

# 检查数据库连接
check_database() {
    python3 -c "
import sys
sys.path.append('/app/src')
try:
    from models.database import test_connection
    if test_connection():
        print('数据库连接正常')
        sys.exit(0)
    else:
        print('数据库连接失败')
        sys.exit(1)
except Exception as e:
    print(f'数据库检查异常: {e}')
    sys.exit(1)
" 2>/dev/null
    
    return $?
}

# 检查进程状态
check_process() {
    # 检查gunicorn进程
    if pgrep -f "gunicorn.*app:app" > /dev/null; then
        return 0
    else
        log_warn "Gunicorn进程未运行"
        return 1
    fi
}

# 检查内存使用
check_memory() {
    # 获取内存使用情况
    memory_usage=$(python3 -c "
import psutil
memory = psutil.virtual_memory()
print(f'{memory.percent:.1f}')
" 2>/dev/null || echo "0")
    
    # 检查内存使用是否超过90%
    if (( $(echo "$memory_usage > 90" | bc -l) )); then
        log_warn "内存使用率过高: ${memory_usage}%"
        return 1
    fi
    
    return 0
}

# 检查磁盘空间
check_disk() {
    # 检查根分区磁盘使用
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    # 检查磁盘使用是否超过90%
    if [ "$disk_usage" -gt 90 ]; then
        log_warn "磁盘使用率过高: ${disk_usage}%"
        return 1
    fi
    
    return 0
}

# 检查日志文件
check_logs() {
    local log_file="${LOG_FILE:-/app/logs/ssl_manager.log}"
    
    if [ -f "$log_file" ]; then
        # 检查最近是否有ERROR日志
        if tail -n 100 "$log_file" | grep -q "ERROR" 2>/dev/null; then
            log_warn "发现最近的错误日志"
            return 1
        fi
    fi
    
    return 0
}

# 综合健康检查
comprehensive_health_check() {
    local checks_passed=0
    local total_checks=6
    
    log_info "开始综合健康检查..."
    
    # 1. HTTP健康端点检查
    if check_http_health "$HEALTH_CHECK_URL" "$TIMEOUT"; then
        log_info "✓ HTTP健康端点正常"
        ((checks_passed++))
    else
        log_error "✗ HTTP健康端点异常"
    fi
    
    # 2. 数据库连接检查
    if check_database; then
        log_info "✓ 数据库连接正常"
        ((checks_passed++))
    else
        log_error "✗ 数据库连接异常"
    fi
    
    # 3. 进程状态检查
    if check_process; then
        log_info "✓ 应用进程正常"
        ((checks_passed++))
    else
        log_error "✗ 应用进程异常"
    fi
    
    # 4. 内存使用检查
    if check_memory; then
        log_info "✓ 内存使用正常"
        ((checks_passed++))
    else
        log_error "✗ 内存使用异常"
    fi
    
    # 5. 磁盘空间检查
    if check_disk; then
        log_info "✓ 磁盘空间正常"
        ((checks_passed++))
    else
        log_error "✗ 磁盘空间不足"
    fi
    
    # 6. 日志检查
    if check_logs; then
        log_info "✓ 日志状态正常"
        ((checks_passed++))
    else
        log_error "✗ 日志中发现错误"
    fi
    
    # 计算健康分数
    local health_score=$((checks_passed * 100 / total_checks))
    
    log_info "健康检查完成: $checks_passed/$total_checks 项通过 (${health_score}%)"
    
    # 如果关键检查（HTTP和数据库）都通过，则认为健康
    if check_http_health "$HEALTH_CHECK_URL" "$TIMEOUT" && check_database; then
        return 0
    else
        return 1
    fi
}

# 快速健康检查（Docker健康检查使用）
quick_health_check() {
    # 只检查HTTP端点和进程状态
    if check_http_health "$HEALTH_CHECK_URL" "$TIMEOUT" && check_process; then
        return 0
    else
        return 1
    fi
}

# 主函数
main() {
    local check_type="${1:-quick}"
    local retry_count=0
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        case "$check_type" in
            "quick")
                if quick_health_check; then
                    log_info "快速健康检查通过"
                    exit 0
                fi
                ;;
            "comprehensive")
                if comprehensive_health_check; then
                    log_info "综合健康检查通过"
                    exit 0
                fi
                ;;
            *)
                log_error "未知的检查类型: $check_type"
                exit 1
                ;;
        esac
        
        ((retry_count++))
        if [ $retry_count -lt $MAX_RETRIES ]; then
            log_warn "健康检查失败，重试 $retry_count/$MAX_RETRIES..."
            sleep 2
        fi
    done
    
    log_error "健康检查失败，已达到最大重试次数"
    exit 1
}

# 清理临时文件
cleanup() {
    rm -f /tmp/health_response
}

# 设置清理函数
trap cleanup EXIT

# 执行主函数
main "$@"
