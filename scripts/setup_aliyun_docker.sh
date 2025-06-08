#!/bin/bash
# 阿里云Docker环境优化配置脚本

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

# 配置阿里云Docker镜像加速器
setup_docker_mirror() {
    log_info "配置阿里云Docker镜像加速器..."
    
    # 创建Docker配置目录
    sudo mkdir -p /etc/docker
    
    # 配置镜像加速器
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com"
    ],
    "insecure-registries": [],
    "debug": false,
    "experimental": false,
    "features": {
        "buildkit": true
    },
    "builder": {
        "gc": {
            "enabled": true,
            "defaultKeepStorage": "20GB"
        }
    },
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "storage-driver": "overlay2",
    "storage-opts": [
        "overlay2.override_kernel_check=true"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    }
}
EOF
    
    # 重启Docker服务
    sudo systemctl daemon-reload
    sudo systemctl restart docker
    
    log_success "Docker镜像加速器配置完成"
}

# 配置Docker Buildx
setup_docker_buildx() {
    log_info "配置Docker Buildx..."
    
    # 创建新的builder实例
    docker buildx create --name aliyun-builder --driver docker-container --use
    docker buildx inspect --bootstrap
    
    log_success "Docker Buildx配置完成"
}

# 预拉取基础镜像
pull_base_images() {
    log_info "预拉取基础镜像..."
    
    # 基础镜像列表
    local base_images=(
        "node:18-alpine"
        "python:3.10-slim"
        "nginx:1.24-alpine"
        "postgres:15-alpine"
        "redis:7-alpine"
        "prom/prometheus:latest"
        "grafana/grafana:latest"
    )
    
    for image in "${base_images[@]}"; do
        log_info "拉取镜像: $image"
        docker pull "$image" &
    done
    
    # 等待所有拉取完成
    wait
    log_success "基础镜像拉取完成"
}

# 清理Docker缓存
cleanup_docker() {
    log_info "清理Docker缓存..."
    
    # 清理未使用的镜像
    docker image prune -f
    
    # 清理构建缓存
    docker builder prune -f
    
    # 清理未使用的容器
    docker container prune -f
    
    # 清理未使用的网络
    docker network prune -f
    
    # 清理未使用的数据卷
    docker volume prune -f
    
    log_success "Docker缓存清理完成"
}

# 优化系统参数
optimize_system() {
    log_info "优化系统参数..."
    
    # 增加文件描述符限制
    echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
    echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
    
    # 优化内核参数
    sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# Docker优化参数
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
vm.max_map_count = 262144
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
EOF
    
    # 应用内核参数
    sudo sysctl -p
    
    log_success "系统参数优化完成"
}

# 主函数
main() {
    log_info "开始配置阿里云Docker环境..."
    
    # 检查是否为root用户或有sudo权限
    if [[ $EUID -eq 0 ]]; then
        log_warning "建议不要使用root用户运行此脚本"
    fi
    
    if ! sudo -n true 2>/dev/null; then
        log_error "需要sudo权限，请确保当前用户有sudo权限"
        exit 1
    fi
    
    # 执行优化步骤
    cleanup_docker
    setup_docker_mirror
    setup_docker_buildx
    optimize_system
    pull_base_images
    
    log_success "阿里云Docker环境配置完成！"
    
    echo
    log_info "配置验证："
    echo "Docker版本: $(docker --version)"
    echo "Docker Compose版本: $(docker-compose --version)"
    echo "可用镜像："
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
}

# 执行主函数
main "$@"
