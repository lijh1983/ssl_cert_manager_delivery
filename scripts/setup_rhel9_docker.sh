#!/bin/bash
# RHEL/CentOS 9 Docker环境优化配置脚本

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

# 检测系统版本
detect_system() {
    log_info "检测系统版本..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        log_info "检测到系统: $OS $VER"
    else
        log_error "无法检测系统版本"
        exit 1
    fi
    
    # 检查是否为RHEL/CentOS 9
    if [[ "$OS" =~ "Red Hat" ]] || [[ "$OS" =~ "CentOS" ]] || [[ "$OS" =~ "Rocky" ]] || [[ "$OS" =~ "AlmaLinux" ]]; then
        if [[ "$VER" =~ ^9 ]]; then
            log_success "确认为RHEL/CentOS 9系列系统"
        else
            log_warning "系统版本为 $VER，本脚本针对9.x版本优化"
        fi
    else
        log_warning "系统不是RHEL/CentOS系列，可能需要调整配置"
    fi
}

# 配置阿里云软件源
setup_aliyun_repos() {
    log_info "配置阿里云软件源..."
    
    # 备份原始配置
    sudo cp /etc/dnf/dnf.conf /etc/dnf/dnf.conf.backup 2>/dev/null || true
    
    # 配置阿里云CentOS Stream 9镜像源
    sudo tee /etc/yum.repos.d/aliyun-centos.repo > /dev/null <<EOF
[aliyun-baseos]
name=AliyunLinux-BaseOS
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/BaseOS/x86_64/os/
gpgcheck=0
enabled=1
priority=1

[aliyun-appstream]
name=AliyunLinux-AppStream
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/AppStream/x86_64/os/
gpgcheck=0
enabled=1
priority=1

[aliyun-crb]
name=AliyunLinux-CRB
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/CRB/x86_64/os/
gpgcheck=0
enabled=1
priority=1
EOF
    
    # 配置阿里云EPEL源
    sudo tee /etc/yum.repos.d/aliyun-epel.repo > /dev/null <<EOF
[aliyun-epel]
name=Extra Packages for Enterprise Linux 9 - Aliyun
baseurl=https://mirrors.aliyun.com/epel/9/Everything/x86_64/
gpgcheck=0
enabled=1
priority=1

[aliyun-epel-next]
name=Extra Packages for Enterprise Linux 9 - Next - Aliyun
baseurl=https://mirrors.aliyun.com/epel/next/9/Everything/x86_64/
gpgcheck=0
enabled=1
priority=1
EOF
    
    # 清理并重建缓存
    sudo dnf clean all
    sudo dnf makecache
    
    log_success "阿里云软件源配置完成"
}

# 安装Docker
install_docker() {
    log_info "安装Docker..."
    
    # 卸载旧版本
    sudo dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine podman runc 2>/dev/null || true
    
    # 安装必要的包
    sudo dnf install -y dnf-plugins-core
    
    # 添加Docker官方仓库
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    
    # 安装Docker CE
    sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # 启动Docker服务
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # 添加当前用户到docker组
    sudo usermod -aG docker $USER
    
    log_success "Docker安装完成"
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
    },
    "exec-opts": ["native.cgroupdriver=systemd"],
    "live-restore": true
}
EOF
    
    # 重启Docker服务
    sudo systemctl daemon-reload
    sudo systemctl restart docker
    
    log_success "Docker镜像加速器配置完成"
}

# 安装必要工具
install_tools() {
    log_info "安装必要工具..."
    
    # 基础工具
    sudo dnf install -y curl wget git unzip tar
    
    # 系统监控工具
    sudo dnf install -y htop iotop net-tools
    
    # 尝试安装nethogs（可能需要EPEL）
    if ! sudo dnf install -y nethogs 2>/dev/null; then
        log_warning "nethogs安装失败，尝试从EPEL安装..."
        sudo dnf install -y epel-release
        sudo dnf install -y nethogs 2>/dev/null || log_warning "nethogs安装失败，请手动安装"
    fi
    
    # 安装Docker Compose（如果没有通过插件安装）
    if ! command -v docker-compose &> /dev/null; then
        log_info "安装Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    
    log_success "必要工具安装完成"
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

# 网络优化
net.core.somaxconn = 32768
net.core.netdev_max_backlog = 32768
net.ipv4.tcp_max_syn_backlog = 32768
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 32768
EOF
    
    # 应用内核参数
    sudo sysctl -p
    
    # 配置防火墙
    if systemctl is-active --quiet firewalld; then
        log_info "配置防火墙规则..."
        sudo firewall-cmd --permanent --add-port=80/tcp
        sudo firewall-cmd --permanent --add-port=443/tcp
        sudo firewall-cmd --permanent --add-port=8000/tcp
        sudo firewall-cmd --permanent --add-port=3000/tcp
        sudo firewall-cmd --permanent --add-port=9090/tcp
        sudo firewall-cmd --reload
    fi
    
    log_success "系统参数优化完成"
}

# 验证安装
verify_installation() {
    log_info "验证安装..."
    
    # 检查Docker
    if docker --version > /dev/null 2>&1; then
        log_success "Docker安装成功: $(docker --version)"
    else
        log_error "Docker安装失败"
        return 1
    fi
    
    # 检查Docker Compose
    if docker-compose --version > /dev/null 2>&1; then
        log_success "Docker Compose安装成功: $(docker-compose --version)"
    elif docker compose version > /dev/null 2>&1; then
        log_success "Docker Compose Plugin安装成功: $(docker compose version)"
    else
        log_error "Docker Compose安装失败"
        return 1
    fi
    
    # 检查Docker服务状态
    if systemctl is-active --quiet docker; then
        log_success "Docker服务运行正常"
    else
        log_error "Docker服务未运行"
        return 1
    fi
    
    # 测试Docker镜像拉取
    log_info "测试Docker镜像拉取..."
    if docker pull registry.cn-hangzhou.aliyuncs.com/library/hello-world:latest > /dev/null 2>&1; then
        log_success "Docker镜像拉取测试成功"
        docker rmi registry.cn-hangzhou.aliyuncs.com/library/hello-world:latest > /dev/null 2>&1
    else
        log_warning "Docker镜像拉取测试失败，请检查网络连接"
    fi
    
    log_success "安装验证完成"
}

# 主函数
main() {
    log_info "开始配置RHEL/CentOS 9 Docker环境..."
    
    # 检查是否为root用户或有sudo权限
    if [[ $EUID -eq 0 ]]; then
        log_warning "建议不要使用root用户运行此脚本"
    fi
    
    if ! sudo -n true 2>/dev/null; then
        log_error "需要sudo权限，请确保当前用户有sudo权限"
        exit 1
    fi
    
    # 执行配置步骤
    detect_system
    setup_aliyun_repos
    install_docker
    setup_docker_mirror
    install_tools
    optimize_system
    verify_installation
    
    log_success "RHEL/CentOS 9 Docker环境配置完成！"
    
    echo
    log_info "配置完成后的信息："
    echo "Docker版本: $(docker --version)"
    echo "Docker Compose版本: $(docker-compose --version 2>/dev/null || docker compose version)"
    echo
    log_warning "请注意："
    echo "1. 重新登录或运行 'newgrp docker' 以使docker组权限生效"
    echo "2. 如果是首次安装，建议重启系统以确保所有配置生效"
    echo "3. 可以运行 'docker run hello-world' 测试Docker是否正常工作"
}

# 执行主函数
main "$@"
