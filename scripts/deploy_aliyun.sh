#!/bin/bash
# 阿里云快速部署脚本 - SSL证书管理系统

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

# 检查阿里云环境
check_aliyun_environment() {
    log_info "检查阿里云环境..."
    
    # 检查是否在阿里云ECS上
    if curl -s --connect-timeout 2 http://100.100.100.200/latest/meta-data/instance-id > /dev/null 2>&1; then
        log_success "检测到阿里云ECS环境"
        INSTANCE_ID=$(curl -s http://100.100.100.200/latest/meta-data/instance-id)
        REGION=$(curl -s http://100.100.100.200/latest/meta-data/region-id)
        log_info "实例ID: $INSTANCE_ID"
        log_info "区域: $REGION"
    else
        log_warning "未检测到阿里云ECS环境，将使用通用配置"
    fi
}

# 优化系统配置
optimize_system_for_aliyun() {
    log_info "优化阿里云系统配置..."
    
    # 更新软件源为阿里云镜像
    if [ -f /etc/apt/sources.list ]; then
        log_info "配置阿里云APT镜像源..."
        sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup
        sudo sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
        sudo sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
        sudo apt-get update
    elif [ -f /etc/yum.repos.d/CentOS-Base.repo ]; then
        log_info "配置阿里云YUM镜像源..."
        sudo wget -O /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo
        sudo yum clean all
        sudo yum makecache
    fi
    
    # 安装必要工具
    if command -v apt-get > /dev/null; then
        sudo apt-get install -y curl wget htop iotop nethogs
    elif command -v yum > /dev/null; then
        sudo yum install -y curl wget htop iotop nethogs
    fi
    
    log_success "系统配置优化完成"
}

# 配置Docker环境
setup_docker_environment() {
    log_info "配置Docker环境..."
    
    # 运行Docker优化脚本
    if [ -f "./scripts/setup_aliyun_docker.sh" ]; then
        chmod +x ./scripts/setup_aliyun_docker.sh
        ./scripts/setup_aliyun_docker.sh
    else
        log_warning "Docker优化脚本不存在，使用基础配置"
        
        # 基础Docker镜像加速器配置
        sudo mkdir -p /etc/docker
        sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn"
    ]
}
EOF
        sudo systemctl restart docker
    fi
    
    log_success "Docker环境配置完成"
}

# 预构建基础镜像
prebuild_base_images() {
    log_info "预构建基础镜像..."
    
    # 拉取阿里云镜像
    local images=(
        "registry.cn-hangzhou.aliyuncs.com/library/node:18-alpine"
        "registry.cn-hangzhou.aliyuncs.com/library/python:3.10-slim"
        "registry.cn-hangzhou.aliyuncs.com/library/nginx:1.24-alpine"
        "registry.cn-hangzhou.aliyuncs.com/library/postgres:15-alpine"
        "registry.cn-hangzhou.aliyuncs.com/library/redis:7-alpine"
    )
    
    for image in "${images[@]}"; do
        log_info "拉取镜像: $image"
        docker pull "$image" &
    done
    
    wait
    log_success "基础镜像预构建完成"
}

# 快速构建应用镜像
fast_build_images() {
    log_info "快速构建应用镜像..."
    
    # 使用BuildKit加速构建
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    # 并行构建前端和后端
    log_info "构建后端镜像..."
    docker build -f backend/Dockerfile.aliyun -t ssl-manager-backend:aliyun ./backend &
    BACKEND_PID=$!
    
    log_info "构建前端镜像..."
    docker build -f frontend/Dockerfile.aliyun -t ssl-manager-frontend:aliyun ./frontend &
    FRONTEND_PID=$!
    
    # 等待构建完成
    wait $BACKEND_PID
    log_success "后端镜像构建完成"
    
    wait $FRONTEND_PID
    log_success "前端镜像构建完成"
}

# 配置环境变量
setup_environment_variables() {
    log_info "配置环境变量..."
    
    # 创建.env文件
    if [ ! -f .env ]; then
        cat > .env <<EOF
# 阿里云环境配置
ENVIRONMENT=production
COMPOSE_PROJECT_NAME=ssl-manager

# 数据库配置
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=$(openssl rand -base64 32)

# Redis配置
REDIS_PASSWORD=$(openssl rand -base64 32)

# 安全配置
SECRET_KEY=$(openssl rand -base64 64)
JWT_SECRET_KEY=$(openssl rand -base64 64)

# 域名配置
DOMAIN_NAME=${DOMAIN_NAME:-localhost}

# SSL配置
ACME_DIRECTORY_URL=https://acme-v02.api.letsencrypt.org/directory
ACME_EMAIL=${ACME_EMAIL:-admin@${DOMAIN_NAME}}

# 监控配置
ENABLE_METRICS=true
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 16)

# 端口配置
HTTP_PORT=80
HTTPS_PORT=443
BACKEND_PORT=8000
FRONTEND_PORT=80
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# 阿里云特定配置
ALIYUN_REGION=${REGION:-cn-hangzhou}
ALIYUN_INSTANCE_ID=${INSTANCE_ID:-unknown}
EOF
        log_success "环境变量配置完成"
    else
        log_info "环境变量文件已存在，跳过创建"
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 使用阿里云优化的compose文件
    export COMPOSE_FILE="docker-compose.aliyun.yml"
    
    # 启动基础服务
    log_info "启动数据库和缓存服务..."
    docker-compose up -d postgres redis
    
    # 等待数据库就绪
    log_info "等待数据库就绪..."
    timeout=60
    while ! docker-compose exec -T postgres pg_isready -U ssl_user > /dev/null 2>&1; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_error "数据库启动超时"
            exit 1
        fi
    done
    
    # 启动应用服务
    log_info "启动应用服务..."
    docker-compose up -d backend frontend
    
    # 等待应用就绪
    log_info "等待应用就绪..."
    timeout=120
    while ! curl -f http://localhost:8000/health > /dev/null 2>&1; do
        sleep 3
        timeout=$((timeout-3))
        if [ $timeout -le 0 ]; then
            log_error "应用启动超时"
            exit 1
        fi
    done
    
    log_success "服务启动完成"
}

# 启动监控服务
start_monitoring() {
    if [ "$ENABLE_MONITORING" = "true" ]; then
        log_info "启动监控服务..."
        docker-compose --profile monitoring up -d
        log_success "监控服务启动完成"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查服务状态
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "后端服务健康"
    else
        log_error "后端服务异常"
        return 1
    fi
    
    if curl -f http://localhost:80/health > /dev/null 2>&1; then
        log_success "前端服务健康"
    else
        log_error "前端服务异常"
        return 1
    fi
    
    log_success "所有服务健康检查通过"
}

# 显示部署信息
show_deployment_info() {
    log_success "阿里云部署完成！"
    echo
    echo "=== 服务访问地址 ==="
    echo "前端地址: http://$(curl -s http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || echo 'localhost')"
    echo "后端API: http://$(curl -s http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || echo 'localhost'):8000"
    echo "健康检查: http://$(curl -s http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || echo 'localhost'):8000/health"
    
    if [ "$ENABLE_MONITORING" = "true" ]; then
        echo "Prometheus: http://$(curl -s http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || echo 'localhost'):9090"
        echo "Grafana: http://$(curl -s http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || echo 'localhost'):3000"
    fi
    
    echo
    echo "=== 管理命令 ==="
    echo "查看服务状态: docker-compose -f docker-compose.aliyun.yml ps"
    echo "查看日志: docker-compose -f docker-compose.aliyun.yml logs -f"
    echo "重启服务: docker-compose -f docker-compose.aliyun.yml restart"
    echo "停止服务: docker-compose -f docker-compose.aliyun.yml down"
    echo
    echo "=== 性能监控 ==="
    echo "系统资源: htop"
    echo "网络监控: nethogs"
    echo "磁盘IO: iotop"
    echo
}

# 主函数
main() {
    log_info "开始阿里云快速部署..."
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            --email)
                ACME_EMAIL="$2"
                shift 2
                ;;
            --enable-monitoring)
                ENABLE_MONITORING="true"
                shift
                ;;
            --skip-build)
                SKIP_BUILD="true"
                shift
                ;;
            --help)
                echo "阿里云快速部署脚本"
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --domain DOMAIN       设置域名"
                echo "  --email EMAIL         设置ACME邮箱"
                echo "  --enable-monitoring   启用监控服务"
                echo "  --skip-build          跳过镜像构建"
                echo "  --help               显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行部署步骤
    check_aliyun_environment
    optimize_system_for_aliyun
    setup_docker_environment
    setup_environment_variables
    
    if [ "$SKIP_BUILD" != "true" ]; then
        prebuild_base_images
        fast_build_images
    else
        log_info "跳过镜像构建"
    fi
    
    start_services
    start_monitoring
    
    # 健康检查
    if health_check; then
        show_deployment_info
    else
        log_error "部署失败，请检查日志"
        exit 1
    fi
}

# 执行主函数
main "$@"
