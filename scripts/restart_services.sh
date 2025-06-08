#!/bin/bash
# 服务重启脚本

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

# 显示当前服务状态
show_current_status() {
    log_info "当前服务状态:"
    docker-compose -f docker-compose.aliyun.yml ps
    echo
}

# 重启指定服务
restart_service() {
    local service=$1
    log_info "重启服务: $service"
    
    case $service in
        "nginx"|"proxy")
            docker-compose -f docker-compose.aliyun.yml restart nginx-proxy
            ;;
        "frontend"|"web")
            docker-compose -f docker-compose.aliyun.yml restart frontend
            ;;
        "backend"|"api")
            docker-compose -f docker-compose.aliyun.yml restart backend
            ;;
        "database"|"db"|"postgres")
            docker-compose -f docker-compose.aliyun.yml restart postgres
            ;;
        "redis"|"cache")
            docker-compose -f docker-compose.aliyun.yml restart redis
            ;;
        "monitoring"|"grafana")
            docker-compose -f docker-compose.aliyun.yml restart grafana
            ;;
        "prometheus")
            docker-compose -f docker-compose.aliyun.yml restart prometheus
            ;;
        "all")
            restart_all_services
            return
            ;;
        *)
            log_error "未知服务: $service"
            show_help
            exit 1
            ;;
    esac
    
    log_success "服务 $service 重启完成"
}

# 重启所有服务
restart_all_services() {
    log_info "重启所有服务..."
    
    # 按依赖顺序重启
    log_info "重启基础服务..."
    docker-compose -f docker-compose.aliyun.yml restart postgres redis
    
    # 等待数据库就绪
    log_info "等待数据库就绪..."
    sleep 10
    timeout=30
    while ! docker-compose -f docker-compose.aliyun.yml exec -T postgres pg_isready -U ssl_user > /dev/null 2>&1; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_error "数据库启动超时"
            exit 1
        fi
    done
    
    log_info "重启应用服务..."
    docker-compose -f docker-compose.aliyun.yml restart backend frontend
    
    log_info "重启反向代理..."
    docker-compose -f docker-compose.aliyun.yml restart nginx-proxy
    
    # 重启监控服务（如果存在）
    if docker-compose -f docker-compose.aliyun.yml ps grafana | grep -q "Up"; then
        log_info "重启监控服务..."
        docker-compose -f docker-compose.aliyun.yml restart grafana prometheus
    fi
    
    log_success "所有服务重启完成"
}

# 优雅重启（零停机时间）
graceful_restart() {
    local service=$1
    log_info "优雅重启服务: $service"
    
    case $service in
        "nginx"|"proxy")
            # nginx支持优雅重启
            docker-compose -f docker-compose.aliyun.yml exec nginx-proxy nginx -s reload
            ;;
        "all")
            # 滚动重启所有服务
            log_info "执行滚动重启..."
            
            # 先重启后端
            docker-compose -f docker-compose.aliyun.yml restart backend
            sleep 5
            
            # 再重启前端
            docker-compose -f docker-compose.aliyun.yml restart frontend
            sleep 5
            
            # 最后重新加载nginx配置
            docker-compose -f docker-compose.aliyun.yml exec nginx-proxy nginx -s reload
            ;;
        *)
            log_warning "服务 $service 不支持优雅重启，使用普通重启"
            restart_service "$service"
            ;;
    esac
    
    log_success "服务 $service 优雅重启完成"
}

# 检查服务健康状态
check_health() {
    log_info "检查服务健康状态..."
    
    local failed=0
    
    # 检查前端
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_success "前端服务健康"
    else
        log_error "前端服务异常"
        failed=1
    fi
    
    # 检查API
    if curl -f http://localhost/api/health > /dev/null 2>&1; then
        log_success "API服务健康"
    else
        log_error "API服务异常"
        failed=1
    fi
    
    # 检查监控（如果存在）
    if docker-compose -f docker-compose.aliyun.yml ps grafana | grep -q "Up"; then
        if curl -f http://localhost/monitoring/ > /dev/null 2>&1; then
            log_success "监控服务健康"
        else
            log_warning "监控服务异常"
        fi
    fi
    
    if [ $failed -eq 0 ]; then
        log_success "所有服务健康检查通过"
    else
        log_error "部分服务健康检查失败"
        return 1
    fi
}

# 查看服务日志
show_logs() {
    local service=$1
    local lines=${2:-50}
    
    case $service in
        "nginx"|"proxy")
            docker-compose -f docker-compose.aliyun.yml logs --tail=$lines nginx-proxy
            ;;
        "frontend"|"web")
            docker-compose -f docker-compose.aliyun.yml logs --tail=$lines frontend
            ;;
        "backend"|"api")
            docker-compose -f docker-compose.aliyun.yml logs --tail=$lines backend
            ;;
        "database"|"db"|"postgres")
            docker-compose -f docker-compose.aliyun.yml logs --tail=$lines postgres
            ;;
        "redis"|"cache")
            docker-compose -f docker-compose.aliyun.yml logs --tail=$lines redis
            ;;
        "monitoring"|"grafana")
            docker-compose -f docker-compose.aliyun.yml logs --tail=$lines grafana
            ;;
        "all")
            docker-compose -f docker-compose.aliyun.yml logs --tail=$lines
            ;;
        *)
            log_error "未知服务: $service"
            show_help
            exit 1
            ;;
    esac
}

# 显示帮助信息
show_help() {
    echo "服务重启脚本"
    echo "用法: $0 [命令] [服务] [选项]"
    echo
    echo "命令:"
    echo "  restart [服务]        重启指定服务"
    echo "  graceful [服务]       优雅重启指定服务"
    echo "  status               显示服务状态"
    echo "  health               检查服务健康状态"
    echo "  logs [服务] [行数]    查看服务日志"
    echo "  help                 显示帮助信息"
    echo
    echo "服务名称:"
    echo "  nginx, proxy         nginx反向代理"
    echo "  frontend, web        前端服务"
    echo "  backend, api         后端API服务"
    echo "  database, db, postgres  数据库服务"
    echo "  redis, cache         Redis缓存"
    echo "  monitoring, grafana  监控服务"
    echo "  prometheus           Prometheus监控"
    echo "  all                  所有服务"
    echo
    echo "示例:"
    echo "  $0 restart nginx              # 重启nginx"
    echo "  $0 restart all                # 重启所有服务"
    echo "  $0 graceful nginx             # 优雅重启nginx"
    echo "  $0 logs backend 100           # 查看后端最近100行日志"
    echo "  $0 health                     # 检查服务健康状态"
}

# 主函数
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    local command=$1
    shift
    
    case $command in
        "restart")
            if [ $# -eq 0 ]; then
                log_error "请指定要重启的服务"
                show_help
                exit 1
            fi
            show_current_status
            restart_service "$1"
            echo
            check_health
            ;;
        "graceful")
            if [ $# -eq 0 ]; then
                log_error "请指定要优雅重启的服务"
                show_help
                exit 1
            fi
            show_current_status
            graceful_restart "$1"
            echo
            check_health
            ;;
        "status")
            show_current_status
            ;;
        "health")
            check_health
            ;;
        "logs")
            if [ $# -eq 0 ]; then
                log_error "请指定要查看日志的服务"
                show_help
                exit 1
            fi
            show_logs "$1" "$2"
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
