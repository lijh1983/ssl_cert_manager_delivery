#!/bin/bash

# SSL证书管理系统 - 本地部署脚本
# 使用预构建镜像进行快速部署

set -e

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

# 检查Docker和Docker Compose
check_prerequisites() {
    log_info "检查系统前提条件..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在PATH中"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装或不在PATH中"
        exit 1
    fi
    
    log_success "Docker 和 Docker Compose 检查通过"
}

# 检查镜像是否存在
check_images() {
    log_info "检查必需的Docker镜像..."
    
    local required_images=(
        "ssl-manager-backend:latest"
        "ssl-manager-frontend:latest"
        "ssl-manager-nginx-proxy:latest"
        "postgres:15-alpine"
        "redis:7-alpine"
    )
    
    local missing_images=()
    
    for image in "${required_images[@]}"; do
        if ! docker image inspect "$image" &> /dev/null; then
            missing_images+=("$image")
        fi
    done
    
    if [ ${#missing_images[@]} -ne 0 ]; then
        log_error "以下镜像不存在："
        for image in "${missing_images[@]}"; do
            echo "  - $image"
        done
        log_error "请先构建所需的镜像"
        exit 1
    fi
    
    log_success "所有必需镜像检查通过"
}

# 设置环境变量
setup_environment() {
    log_info "设置环境变量..."
    
    if [ ! -f .env ]; then
        if [ -f .env.local ]; then
            cp .env.local .env
            log_success "已从 .env.local 复制环境变量配置"
        else
            log_warning ".env 文件不存在，将使用默认配置"
        fi
    else
        log_info "使用现有的 .env 配置文件"
    fi
}

# 启动服务
start_services() {
    local compose_file="docker-compose.local.yml"
    
    log_info "启动SSL证书管理系统服务..."
    
    # 检查compose文件是否存在
    if [ ! -f "$compose_file" ]; then
        log_error "Docker Compose 配置文件 $compose_file 不存在"
        exit 1
    fi
    
    # 停止现有服务（如果存在）
    log_info "停止现有服务..."
    docker-compose -f "$compose_file" down 2>/dev/null || true
    
    # 启动基础服务
    log_info "启动基础服务（数据库和缓存）..."
    docker-compose -f "$compose_file" up -d postgres redis
    
    # 等待基础服务就绪
    log_info "等待基础服务就绪..."
    sleep 10
    
    # 检查基础服务健康状态
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$compose_file" ps postgres | grep -q "healthy\|Up" && \
           docker-compose -f "$compose_file" ps redis | grep -q "healthy\|Up"; then
            log_success "基础服务已就绪"
            break
        fi
        
        log_info "等待基础服务启动... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "基础服务启动超时"
        docker-compose -f "$compose_file" logs postgres redis
        exit 1
    fi
    
    # 启动应用服务
    log_info "启动应用服务..."
    docker-compose -f "$compose_file" up -d backend frontend
    
    # 等待应用服务就绪
    log_info "等待应用服务就绪..."
    sleep 15
    
    # 启动代理服务
    log_info "启动代理服务..."
    docker-compose -f "$compose_file" up -d nginx
    
    log_success "所有服务启动完成"
}

# 验证服务
verify_services() {
    log_info "验证服务状态..."
    
    local compose_file="docker-compose.local.yml"
    
    # 显示服务状态
    echo
    log_info "服务状态："
    docker-compose -f "$compose_file" ps
    
    echo
    log_info "进行功能测试..."
    
    # 测试后端API
    local backend_url="http://localhost:8000"
    if curl -s -f "$backend_url/health" > /dev/null; then
        log_success "后端API服务正常 ($backend_url)"
    else
        log_warning "后端API服务可能未就绪 ($backend_url)"
    fi
    
    # 测试前端服务
    local frontend_url="http://localhost:3000"
    if curl -s -f "$frontend_url/health" > /dev/null; then
        log_success "前端服务正常 ($frontend_url)"
    else
        log_warning "前端服务可能未就绪 ($frontend_url)"
    fi
    
    # 测试代理服务
    local proxy_url="http://localhost"
    if curl -s -f "$proxy_url/health" > /dev/null; then
        log_success "代理服务正常 ($proxy_url)"
    else
        log_warning "代理服务可能未就绪 ($proxy_url)"
    fi
}

# 显示访问信息
show_access_info() {
    echo
    log_success "=== SSL证书管理系统部署完成 ==="
    echo
    echo "访问地址："
    echo "  前端应用:    http://localhost:3000"
    echo "  后端API:     http://localhost:8000"
    echo "  API文档:     http://localhost:8000/docs"
    echo "  代理服务:    http://localhost"
    echo
    echo "管理命令："
    echo "  查看状态:    docker-compose -f docker-compose.local.yml ps"
    echo "  查看日志:    docker-compose -f docker-compose.local.yml logs -f"
    echo "  停止服务:    docker-compose -f docker-compose.local.yml stop"
    echo "  重启服务:    docker-compose -f docker-compose.local.yml restart"
    echo "  清理服务:    docker-compose -f docker-compose.local.yml down"
    echo
    log_info "详细文档请参考: DEPLOYMENT_LOCAL.md"
}

# 主函数
main() {
    echo "=== SSL证书管理系统本地部署脚本 ==="
    echo
    
    check_prerequisites
    check_images
    setup_environment
    start_services
    verify_services
    show_access_info
    
    log_success "部署完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main "$@"
