#!/bin/bash

# SSL证书管理器生产环境一键部署脚本
# 基于实际生产环境部署经验编写
# 版本: 1.0
# 更新时间: 2025-01-10

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        exit 1
    fi
}

# 检查系统要求
check_system_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if ! grep -q "Ubuntu 22.04" /etc/os-release; then
        log_warning "推荐使用Ubuntu 22.04.5 LTS，当前系统可能存在兼容性问题"
    fi
    
    # 检查内存
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$MEMORY_GB" -lt 8 ]; then
        log_error "内存不足！需要至少8GB内存，推荐16GB"
        exit 1
    fi
    
    # 检查磁盘空间
    DISK_SPACE=$(df / | awk 'NR==2 {print $4}')
    if [ "$DISK_SPACE" -lt 20971520 ]; then  # 20GB in KB
        log_error "磁盘空间不足！需要至少20GB可用空间"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 检查cgroup v2支持
check_cgroup_v2() {
    log_info "检查cgroup v2支持..."
    
    if ! mount | grep -q "cgroup2"; then
        log_error "系统不支持cgroup v2！这是运行cAdvisor的必要条件"
        log_info "请在/etc/default/grub中添加: systemd.unified_cgroup_hierarchy=1"
        log_info "然后执行: sudo update-grub && sudo reboot"
        exit 1
    fi
    
    log_success "cgroup v2支持检查通过"
}

# 安装Docker
install_docker() {
    log_info "检查Docker安装..."
    
    if ! command -v docker &> /dev/null; then
        log_info "安装Docker..."
        
        # 卸载旧版本
        sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
        
        # 安装依赖
        sudo apt update
        sudo apt install -y ca-certificates curl gnupg lsb-release
        
        # 添加Docker官方GPG密钥
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        
        # 添加Docker仓库
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # 安装Docker
        sudo apt update
        sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # 配置用户权限
        sudo usermod -aG docker $USER
        
        log_success "Docker安装完成"
    else
        log_info "Docker已安装"
    fi
    
    # 验证Docker版本
    DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    log_info "Docker版本: $DOCKER_VERSION"
    
    # 验证cgroup v2支持
    if ! docker system info | grep -q "Cgroup Version: 2"; then
        log_error "Docker不支持cgroup v2！请检查Docker配置"
        exit 1
    fi
    
    log_success "Docker配置验证通过"
}

# 配置Docker
configure_docker() {
    log_info "配置Docker..."
    
    # 创建Docker配置文件
    sudo mkdir -p /etc/docker
    cat > /tmp/daemon.json <<EOF
{
  "exec-opts": ["native.cgroupdriver=cgroupfs"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
    sudo mv /tmp/daemon.json /etc/docker/daemon.json
    
    # 重启Docker服务
    sudo systemctl restart docker
    sudo systemctl enable docker
    
    log_success "Docker配置完成"
}

# 创建数据目录
create_data_directories() {
    log_info "创建数据目录..."
    
    # 创建目录结构
    sudo mkdir -p /opt/ssl-manager/{data,logs,certs,backups}
    sudo mkdir -p /opt/ssl-manager/data/{postgres,redis,prometheus,grafana}
    
    # 设置权限
    sudo chown -R $USER:$USER /opt/ssl-manager
    sudo chown -R 70:70 /opt/ssl-manager/data/postgres      # PostgreSQL
    sudo chown -R 472:472 /opt/ssl-manager/data/grafana     # Grafana
    sudo chown -R 65534:65534 /opt/ssl-manager/data/prometheus  # Prometheus
    sudo chown -R 999:999 /opt/ssl-manager/data/redis       # Redis
    
    log_success "数据目录创建完成"
}

# 配置环境变量
configure_environment() {
    log_info "配置环境变量..."
    
    if [ ! -f .env ]; then
        log_info "创建.env配置文件..."
        cat > .env <<EOF
# 基础配置
DOMAIN_NAME=ssl.gzyggl.com
EMAIL=19822088@qq.com
ENVIRONMENT=production

# 数据库配置
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=$(openssl rand -base64 32)
DB_PORT="5432"

# Redis配置
REDIS_PASSWORD=$(openssl rand -base64 32)
REDIS_PORT="6379"

# 安全配置
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)

# API配置
VITE_API_BASE_URL=/api
BACKEND_WORKERS=2
LOG_LEVEL=INFO

# 监控配置
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 16)
PROMETHEUS_PORT=9090

# 功能开关
ENABLE_METRICS=true
ENABLE_MONITORING=true

# Let's Encrypt SSL证书配置
ACME_EMAIL=19822088@qq.com
ACME_DIRECTORY_URL=https://acme-v02.api.letsencrypt.org/directory
ACME_AGREE_TOS=true
ACME_CHALLENGE_TYPE=http-01
EOF
        log_success "环境变量配置文件创建完成"
    else
        log_info "环境变量配置文件已存在"
    fi
}

# 部署服务
deploy_services() {
    log_info "部署生产环境服务..."
    
    # 拉取最新镜像
    log_info "拉取Docker镜像..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
    
    # 启动服务
    log_info "启动服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring up -d
    
    log_success "服务部署完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 等待服务启动
    log_info "等待服务启动完成..."
    sleep 60
    
    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps
    
    # 验证核心功能
    log_info "验证核心功能..."
    
    # Nginx健康检查
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_success "Nginx健康检查通过"
    else
        log_error "Nginx健康检查失败"
        return 1
    fi
    
    # API健康检查
    if curl -f http://localhost/api/health > /dev/null 2>&1; then
        log_success "API健康检查通过"
    else
        log_error "API健康检查失败"
        return 1
    fi
    
    # 数据库连接检查
    if docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "数据库连接检查通过"
    else
        log_error "数据库连接检查失败"
        return 1
    fi
    
    # Redis连接检查
    if docker exec ssl-manager-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis连接检查通过"
    else
        log_error "Redis连接检查失败"
        return 1
    fi
    
    log_success "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    log_success "🎉 SSL证书管理器生产环境部署成功！"
    echo ""
    echo "访问信息:"
    echo "  前端页面: http://localhost/"
    echo "  API接口: http://localhost/api/"
    echo "  Prometheus: http://localhost/prometheus/"
    echo "  Grafana: http://localhost/grafana/"
    echo "  cAdvisor: http://localhost:8080/"
    echo ""
    echo "管理命令:"
    echo "  查看服务状态: docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps"
    echo "  查看日志: docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring logs -f"
    echo "  停止服务: docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring down"
    echo ""
    echo "数据目录: /opt/ssl-manager/"
    echo "配置文件: .env"
}

# 主函数
main() {
    log_info "开始SSL证书管理器生产环境部署..."
    
    check_root
    check_system_requirements
    check_cgroup_v2
    install_docker
    configure_docker
    create_data_directories
    configure_environment
    deploy_services
    verify_deployment
    show_deployment_info
    
    log_success "部署完成！"
}

# 执行主函数
main "$@"
