#!/bin/bash
# Nginx反向代理配置脚本

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

# 检查环境变量
check_environment() {
    log_info "检查环境变量..."
    
    if [ -z "$DOMAIN_NAME" ]; then
        log_warning "DOMAIN_NAME未设置，使用默认值: ssl.gzyggl.com"
        export DOMAIN_NAME="ssl.gzyggl.com"
    fi
    
    log_info "域名: $DOMAIN_NAME"
}

# 停止现有服务
stop_services() {
    log_info "停止现有服务..."
    
    # 停止可能冲突的服务
    docker-compose -f docker-compose.aliyun.yml down 2>/dev/null || true
    
    # 清理可能占用端口的容器
    docker ps -q --filter "publish=80" | xargs -r docker stop 2>/dev/null || true
    docker ps -q --filter "publish=443" | xargs -r docker stop 2>/dev/null || true
    
    log_success "现有服务已停止"
}

# 构建nginx代理镜像
build_nginx_proxy() {
    log_info "构建nginx反向代理镜像..."

    # 检查nginx配置文件
    if [ ! -f "nginx/nginx.conf" ]; then
        log_error "nginx配置文件不存在: nginx/nginx.conf"
        exit 1
    fi

    if [ ! -f "nginx/conf.d/ssl-manager.conf" ]; then
        log_error "nginx虚拟主机配置文件不存在: nginx/conf.d/ssl-manager.conf"
        exit 1
    fi

    # 尝试多种构建方案
    local build_success=false

    # 方案1: 使用官方Docker Hub镜像
    log_info "尝试使用官方Docker Hub镜像构建..."
    if docker build -f nginx/Dockerfile.proxy -t ssl-manager-nginx-proxy:latest ./nginx 2>/dev/null; then
        log_success "使用官方镜像构建成功"
        build_success=true
    else
        log_warning "官方镜像构建失败，尝试阿里云镜像..."

        # 方案2: 使用阿里云优化镜像
        if docker build -f nginx/Dockerfile.proxy.aliyun -t ssl-manager-nginx-proxy:latest ./nginx 2>/dev/null; then
            log_success "使用阿里云镜像构建成功"
            build_success=true
        else
            log_warning "阿里云镜像构建失败，尝试手动拉取基础镜像..."

            # 方案3: 手动拉取基础镜像
            pull_base_nginx_image
            if docker build -f nginx/Dockerfile.proxy -t ssl-manager-nginx-proxy:latest ./nginx; then
                log_success "手动拉取后构建成功"
                build_success=true
            fi
        fi
    fi

    if [ "$build_success" = "false" ]; then
        log_error "所有构建方案都失败了"
        exit 1
    fi

    log_success "nginx反向代理镜像构建完成"
}

# 手动拉取基础镜像
pull_base_nginx_image() {
    log_info "手动拉取nginx基础镜像..."

    # 尝试多个镜像源
    local images=(
        "nginx:1.24-alpine"
        "nginx:1.22-alpine"
        "nginx:alpine"
        "dockerproxy.com/library/nginx:1.24-alpine"
    )

    for image in "${images[@]}"; do
        log_info "尝试拉取: $image"
        if docker pull "$image" 2>/dev/null; then
            log_success "成功拉取: $image"

            # 标记为我们需要的镜像
            docker tag "$image" nginx:1.24-alpine 2>/dev/null || true
            return 0
        else
            log_warning "拉取失败: $image"
        fi
    done

    log_error "所有镜像源都无法拉取"
    return 1
}

# 创建SSL证书目录
setup_ssl_directory() {
    log_info "设置SSL证书目录..."
    
    # 创建SSL证书目录
    mkdir -p nginx/ssl
    
    # 创建自签名证书（用于测试）
    if [ ! -f "nginx/ssl/${DOMAIN_NAME}.crt" ]; then
        log_info "创建自签名SSL证书..."
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "nginx/ssl/${DOMAIN_NAME}.key" \
            -out "nginx/ssl/${DOMAIN_NAME}.crt" \
            -subj "/C=CN/ST=Guangdong/L=Guangzhou/O=SSL Manager/CN=${DOMAIN_NAME}"
        
        # 创建证书链文件
        cp "nginx/ssl/${DOMAIN_NAME}.crt" "nginx/ssl/${DOMAIN_NAME}-chain.crt"
        
        log_success "自签名SSL证书创建完成"
    else
        log_info "SSL证书已存在，跳过创建"
    fi
    
    # 创建默认证书
    if [ ! -f "nginx/ssl/default.crt" ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "nginx/ssl/default.key" \
            -out "nginx/ssl/default.crt" \
            -subj "/C=CN/ST=Default/L=Default/O=Default/CN=default"
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 设置环境变量
    export DOMAIN_NAME="${DOMAIN_NAME}"
    
    # 启动基础服务
    log_info "启动数据库和缓存服务..."
    docker-compose -f docker-compose.aliyun.yml up -d postgres redis
    
    # 等待数据库就绪
    log_info "等待数据库就绪..."
    timeout=60
    while ! docker-compose -f docker-compose.aliyun.yml exec -T postgres pg_isready -U ssl_user > /dev/null 2>&1; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_error "数据库启动超时"
            exit 1
        fi
    done
    
    # 启动应用服务
    log_info "启动应用服务..."
    docker-compose -f docker-compose.aliyun.yml up -d backend frontend
    
    # 启动监控服务（如果启用）
    if [ "$ENABLE_MONITORING" = "true" ]; then
        log_info "启动监控服务..."
        docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d
    fi
    
    # 启动nginx反向代理
    log_info "启动nginx反向代理..."
    docker-compose -f docker-compose.aliyun.yml up -d nginx-proxy
    
    log_success "所有服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    # 等待后端API就绪
    log_info "等待后端API就绪..."
    timeout=120
    while ! curl -f http://localhost/api/health > /dev/null 2>&1; do
        sleep 3
        timeout=$((timeout-3))
        if [ $timeout -le 0 ]; then
            log_error "后端API启动超时"
            return 1
        fi
    done
    
    # 等待前端就绪
    log_info "等待前端就绪..."
    timeout=60
    while ! curl -f http://localhost/health > /dev/null 2>&1; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_error "前端启动超时"
            return 1
        fi
    done
    
    # 检查监控服务（如果启用）
    if [ "$ENABLE_MONITORING" = "true" ]; then
        log_info "等待监控服务就绪..."
        timeout=60
        while ! curl -f http://localhost/monitoring/ > /dev/null 2>&1; do
            sleep 2
            timeout=$((timeout-2))
            if [ $timeout -le 0 ]; then
                log_warning "监控服务启动超时，但不影响主要功能"
                break
            fi
        done
    fi
    
    log_success "所有服务就绪"
}

# 验证配置
verify_setup() {
    log_info "验证nginx反向代理配置..."
    
    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose -f docker-compose.aliyun.yml ps
    
    # 测试访问
    log_info "测试服务访问..."
    
    # 测试前端
    if curl -f http://localhost/ > /dev/null 2>&1; then
        log_success "前端访问正常: http://${DOMAIN_NAME}/"
    else
        log_error "前端访问失败"
        return 1
    fi
    
    # 测试API
    if curl -f http://localhost/api/health > /dev/null 2>&1; then
        log_success "API访问正常: http://${DOMAIN_NAME}/api/"
    else
        log_error "API访问失败"
        return 1
    fi
    
    # 测试监控（如果启用）
    if [ "$ENABLE_MONITORING" = "true" ]; then
        if curl -f http://localhost/monitoring/ > /dev/null 2>&1; then
            log_success "监控访问正常: http://${DOMAIN_NAME}/monitoring/"
        else
            log_warning "监控访问失败，请检查Grafana配置"
        fi
    fi
    
    log_success "nginx反向代理配置验证完成"
}

# 显示访问信息
show_access_info() {
    log_success "nginx反向代理配置完成！"
    echo
    echo "=== 服务访问地址 ==="
    echo "🌐 前端主页:    http://${DOMAIN_NAME}/"
    echo "🔌 后端API:     http://${DOMAIN_NAME}/api/"
    if [ "$ENABLE_MONITORING" = "true" ]; then
        echo "📊 监控面板:    http://${DOMAIN_NAME}/monitoring/"
        echo "   (用户名: ${GRAFANA_USER:-admin}, 密码: ${GRAFANA_PASSWORD:-admin})"
    fi
    echo
    echo "=== 健康检查地址 ==="
    echo "前端健康检查:   http://${DOMAIN_NAME}/health"
    echo "API健康检查:    http://${DOMAIN_NAME}/api/health"
    echo
    echo "=== 管理命令 ==="
    echo "查看服务状态:   docker-compose -f docker-compose.aliyun.yml ps"
    echo "查看nginx日志:  docker-compose -f docker-compose.aliyun.yml logs nginx-proxy"
    echo "重启nginx:      docker-compose -f docker-compose.aliyun.yml restart nginx-proxy"
    echo "停止所有服务:   docker-compose -f docker-compose.aliyun.yml down"
    echo
}

# 主函数
main() {
    log_info "开始配置nginx反向代理..."
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            --enable-monitoring)
                ENABLE_MONITORING="true"
                shift
                ;;
            --help)
                echo "nginx反向代理配置脚本"
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --domain DOMAIN       设置域名"
                echo "  --enable-monitoring   启用监控服务"
                echo "  --help               显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行配置步骤
    check_environment
    stop_services
    setup_ssl_directory
    build_nginx_proxy
    start_services
    wait_for_services
    
    # 验证配置
    if verify_setup; then
        show_access_info
    else
        log_error "配置验证失败，请检查日志"
        exit 1
    fi
}

# 执行主函数
main "$@"
