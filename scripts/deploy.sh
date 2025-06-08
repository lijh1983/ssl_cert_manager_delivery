#!/bin/bash
# SSL证书管理系统部署脚本
# 用途: 一键部署到生产环境

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        log_error "Git未安装，请先安装Git"
        exit 1
    fi
    
    log_success "系统依赖检查完成"
}

# 创建系统用户
create_system_user() {
    log_info "创建系统用户..."
    
    if ! id "ssl-manager" &>/dev/null; then
        sudo useradd -r -s /bin/false -d /opt/ssl-manager ssl-manager
        log_success "系统用户 ssl-manager 创建成功"
    else
        log_info "系统用户 ssl-manager 已存在"
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    sudo mkdir -p /opt/ssl-manager
    sudo mkdir -p /opt/ssl-manager/data
    sudo mkdir -p /opt/ssl-manager/logs
    sudo mkdir -p /opt/ssl-manager/certs
    sudo mkdir -p /opt/ssl-manager/backups
    sudo mkdir -p /etc/ssl-manager
    sudo mkdir -p /var/log/ssl-manager
    
    # 设置权限
    sudo chown -R ssl-manager:ssl-manager /opt/ssl-manager
    sudo chown -R ssl-manager:ssl-manager /var/log/ssl-manager
    sudo chmod 755 /opt/ssl-manager
    sudo chmod 750 /opt/ssl-manager/data
    sudo chmod 750 /opt/ssl-manager/certs
    sudo chmod 755 /opt/ssl-manager/logs
    
    log_success "目录结构创建完成"
}

# 部署代码
deploy_code() {
    log_info "部署应用代码..."
    
    # 备份现有代码（如果存在）
    if [ -d "/opt/ssl-manager/app" ]; then
        log_info "备份现有代码..."
        sudo mv /opt/ssl-manager/app /opt/ssl-manager/app.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # 克隆或更新代码
    if [ -n "$GIT_REPO" ]; then
        log_info "从Git仓库部署: $GIT_REPO"
        sudo -u ssl-manager git clone "$GIT_REPO" /opt/ssl-manager/app
    else
        log_info "复制本地代码..."
        sudo cp -r . /opt/ssl-manager/app
        sudo chown -R ssl-manager:ssl-manager /opt/ssl-manager/app
    fi
    
    cd /opt/ssl-manager/app
    
    log_success "代码部署完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    # 创建生产环境配置文件
    sudo tee /opt/ssl-manager/.env > /dev/null <<EOF
# 生产环境配置
ENVIRONMENT=production
COMPOSE_PROJECT_NAME=ssl-manager

# 数据库配置
DB_HOST=postgres
DB_PORT=5432
DB_NAME=${DB_NAME:-ssl_manager}
DB_USER=${DB_USER:-ssl_user}
DB_PASSWORD=${DB_PASSWORD:-$(openssl rand -base64 32)}

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD:-$(openssl rand -base64 32)}

# 安全配置
SECRET_KEY=${SECRET_KEY:-$(openssl rand -base64 64)}
JWT_SECRET_KEY=${JWT_SECRET_KEY:-$(openssl rand -base64 64)}

# 域名配置
DOMAIN_NAME=${DOMAIN_NAME:-localhost}

# SSL配置
ACME_DIRECTORY_URL=${ACME_DIRECTORY_URL:-https://acme-v02.api.letsencrypt.org/directory}
ACME_EMAIL=${ACME_EMAIL:-admin@${DOMAIN_NAME}}

# 监控配置
ENABLE_METRICS=true
GRAFANA_USER=${GRAFANA_USER:-admin}
GRAFANA_PASSWORD=${GRAFANA_PASSWORD:-$(openssl rand -base64 16)}

# 端口配置
HTTP_PORT=${HTTP_PORT:-80}
HTTPS_PORT=${HTTPS_PORT:-443}
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}
PROMETHEUS_PORT=${PROMETHEUS_PORT:-9090}
GRAFANA_PORT=${GRAFANA_PORT:-3000}
EOF

    sudo chown ssl-manager:ssl-manager /opt/ssl-manager/.env
    sudo chmod 600 /opt/ssl-manager/.env
    
    log_success "环境变量配置完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    cd /opt/ssl-manager/app
    
    # 构建后端镜像
    sudo docker build -t ssl-manager-backend:latest ./backend
    
    # 构建前端镜像
    sudo docker build -t ssl-manager-frontend:latest ./frontend
    
    log_success "Docker镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    cd /opt/ssl-manager/app
    
    # 启动基础服务
    sudo docker-compose up -d postgres redis
    
    # 等待数据库就绪
    log_info "等待数据库就绪..."
    sleep 10
    
    # 启动应用服务
    sudo docker-compose up -d backend frontend
    
    # 启动监控服务（如果启用）
    if [ "$ENABLE_MONITORING" = "true" ]; then
        sudo docker-compose --profile monitoring up -d
    fi
    
    # 启动生产级nginx（如果启用）
    if [ "$ENABLE_NGINX" = "true" ]; then
        sudo docker-compose --profile production up -d nginx
    fi
    
    log_success "服务启动完成"
}

# 安装systemd服务
install_systemd_service() {
    log_info "安装systemd服务..."
    
    # 复制服务文件
    sudo cp /opt/ssl-manager/app/scripts/systemd/ssl-manager.service /etc/systemd/system/
    
    # 更新服务文件中的路径
    sudo sed -i "s|/opt/ssl-manager|/opt/ssl-manager/app|g" /etc/systemd/system/ssl-manager.service
    
    # 重新加载systemd
    sudo systemctl daemon-reload
    
    # 启用服务
    sudo systemctl enable ssl-manager.service
    
    log_success "systemd服务安装完成"
}

# 配置日志轮转
setup_log_rotation() {
    log_info "配置日志轮转..."
    
    sudo cp /opt/ssl-manager/app/scripts/logrotate/ssl-manager /etc/logrotate.d/
    
    # 测试日志轮转配置
    sudo logrotate -d /etc/logrotate.d/ssl-manager
    
    log_success "日志轮转配置完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 等待服务启动
    sleep 30
    
    # 检查后端健康状态
    if curl -f http://localhost:${BACKEND_PORT:-8000}/health > /dev/null 2>&1; then
        log_success "后端服务健康检查通过"
    else
        log_error "后端服务健康检查失败"
        return 1
    fi
    
    # 检查前端健康状态
    if curl -f http://localhost:${FRONTEND_PORT:-80}/health > /dev/null 2>&1; then
        log_success "前端服务健康检查通过"
    else
        log_error "前端服务健康检查失败"
        return 1
    fi
    
    log_success "所有服务健康检查通过"
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo
    echo "=== 部署信息 ==="
    echo "应用目录: /opt/ssl-manager/app"
    echo "数据目录: /opt/ssl-manager/data"
    echo "日志目录: /opt/ssl-manager/logs"
    echo "证书目录: /opt/ssl-manager/certs"
    echo
    echo "=== 服务地址 ==="
    echo "前端地址: http://localhost:${FRONTEND_PORT:-80}"
    echo "后端API: http://localhost:${BACKEND_PORT:-8000}"
    echo "健康检查: http://localhost:${BACKEND_PORT:-8000}/health"
    
    if [ "$ENABLE_MONITORING" = "true" ]; then
        echo "Prometheus: http://localhost:${PROMETHEUS_PORT:-9090}"
        echo "Grafana: http://localhost:${GRAFANA_PORT:-3000}"
        echo "Grafana用户名: ${GRAFANA_USER:-admin}"
        echo "Grafana密码: 请查看 /opt/ssl-manager/.env 文件"
    fi
    
    echo
    echo "=== 管理命令 ==="
    echo "启动服务: sudo systemctl start ssl-manager"
    echo "停止服务: sudo systemctl stop ssl-manager"
    echo "重启服务: sudo systemctl restart ssl-manager"
    echo "查看状态: sudo systemctl status ssl-manager"
    echo "查看日志: sudo journalctl -u ssl-manager -f"
    echo
    echo "=== Docker命令 ==="
    echo "查看容器: sudo docker-compose ps"
    echo "查看日志: sudo docker-compose logs -f"
    echo "重启服务: sudo docker-compose restart"
    echo
}

# 主函数
main() {
    log_info "开始部署SSL证书管理系统..."
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --git-repo)
                GIT_REPO="$2"
                shift 2
                ;;
            --domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            --enable-monitoring)
                ENABLE_MONITORING="true"
                shift
                ;;
            --enable-nginx)
                ENABLE_NGINX="true"
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --git-repo URL        从Git仓库部署"
                echo "  --domain DOMAIN       设置域名"
                echo "  --enable-monitoring   启用监控服务"
                echo "  --enable-nginx        启用生产级nginx"
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
    check_dependencies
    create_system_user
    create_directories
    deploy_code
    setup_environment
    build_images
    start_services
    install_systemd_service
    setup_log_rotation
    
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
