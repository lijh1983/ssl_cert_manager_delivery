#!/bin/bash
# SSL证书管理系统问题诊断脚本

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

# 诊断系统环境
diagnose_system() {
    echo "🔍 系统环境诊断"
    echo "=================="
    
    # 操作系统信息
    log_info "操作系统信息:"
    cat /etc/os-release | grep -E "NAME|VERSION" || echo "无法获取系统信息"
    
    # 内核版本
    log_info "内核版本: $(uname -r)"
    
    # 系统资源
    log_info "系统资源:"
    echo "  CPU核心数: $(nproc)"
    echo "  内存大小: $(free -h | awk 'NR==2{print $2}')"
    echo "  磁盘空间: $(df -h / | awk 'NR==2{print $4}' | head -1) 可用"
    
    echo
}

# 诊断Docker环境
diagnose_docker() {
    echo "🐳 Docker环境诊断"
    echo "=================="
    
    # Docker服务状态
    if systemctl is-active docker > /dev/null 2>&1; then
        log_success "Docker服务正在运行"
    else
        log_error "Docker服务未运行"
        log_info "尝试启动Docker服务..."
        sudo systemctl start docker || log_error "无法启动Docker服务"
    fi
    
    # Docker版本
    if command -v docker > /dev/null 2>&1; then
        local docker_version=$(docker --version)
        log_info "Docker版本: $docker_version"
    else
        log_error "Docker命令不可用"
        return 1
    fi
    
    # Docker信息
    if docker info > /dev/null 2>&1; then
        log_success "Docker守护进程正常"
        
        # Docker存储信息
        local storage_driver=$(docker info --format '{{.Driver}}')
        log_info "存储驱动: $storage_driver"
        
        # Docker镜像数量
        local image_count=$(docker images -q | wc -l)
        log_info "本地镜像数量: $image_count"
        
        # 运行中容器
        local running_containers=$(docker ps -q | wc -l)
        log_info "运行中容器: $running_containers"
    else
        log_error "Docker守护进程异常"
        return 1
    fi
    
    echo
}

# 诊断网络连接
diagnose_network() {
    echo "🌐 网络连接诊断"
    echo "================"
    
    # 测试基本网络连接
    local test_hosts=(
        "8.8.8.8|Google DNS"
        "mirrors.aliyun.com|阿里云镜像源"
        "registry-1.docker.io|Docker Hub"
        "dl-cdn.alpinelinux.org|Alpine官方源"
    )
    
    for host_info in "${test_hosts[@]}"; do
        local host=$(echo "$host_info" | cut -d'|' -f1)
        local description=$(echo "$host_info" | cut -d'|' -f2)
        
        if ping -c 1 -W 3 "$host" > /dev/null 2>&1; then
            log_success "$description ($host) 连接正常"
        else
            log_error "$description ($host) 连接失败"
        fi
    done
    
    # DNS解析测试
    log_info "DNS解析测试:"
    if nslookup mirrors.aliyun.com > /dev/null 2>&1; then
        log_success "DNS解析正常"
    else
        log_error "DNS解析异常"
    fi
    
    echo
}

# 诊断Alpine镜像问题
diagnose_alpine() {
    echo "🏔️ Alpine镜像诊断"
    echo "=================="
    
    # 测试Alpine镜像拉取
    log_info "测试Alpine镜像拉取..."
    if docker pull alpine:3.18 > /dev/null 2>&1; then
        log_success "Alpine 3.18镜像拉取成功"
    else
        log_error "Alpine 3.18镜像拉取失败"
        return 1
    fi
    
    # 测试Alpine容器启动
    log_info "测试Alpine容器启动..."
    if docker run --rm alpine:3.18 echo "Alpine容器测试成功" > /dev/null 2>&1; then
        log_success "Alpine容器启动正常"
    else
        log_error "Alpine容器启动失败"
        return 1
    fi
    
    # 测试Alpine网络连接
    log_info "测试Alpine容器网络连接..."
    if docker run --rm alpine:3.18 ping -c 1 mirrors.aliyun.com > /dev/null 2>&1; then
        log_success "Alpine容器网络连接正常"
    else
        log_warning "Alpine容器网络连接异常"
    fi
    
    # 测试Alpine包管理器
    log_info "测试Alpine包管理器..."
    if docker run --rm alpine:3.18 apk update > /dev/null 2>&1; then
        log_success "Alpine包管理器正常"
    else
        log_error "Alpine包管理器异常"
    fi
    
    echo
}

# 诊断脚本文件
diagnose_scripts() {
    echo "📜 脚本文件诊断"
    echo "================"
    
    # 检查关键脚本文件
    local scripts=(
        "scripts/ssl-manager.sh"
        "scripts/alpine-optimizer.sh"
        "scripts/setup_nginx_proxy.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ]; then
            if [ -x "$script" ]; then
                log_success "$script 存在且可执行"
            else
                log_warning "$script 存在但不可执行"
                chmod +x "$script"
                log_info "已修复 $script 执行权限"
            fi
        else
            log_error "$script 不存在"
        fi
    done
    
    # 检查配置文件
    local configs=(
        "docker-compose.aliyun.yml"
        "docker-compose.yml"
    )
    
    for config in "${configs[@]}"; do
        if [ -f "$config" ]; then
            log_success "$config 存在"
        else
            log_warning "$config 不存在"
        fi
    done
    
    echo
}

# 运行修复测试
run_fix_tests() {
    echo "🧪 修复效果测试"
    echo "================"
    
    # 测试ssl-manager.sh验证功能
    log_info "测试ssl-manager.sh验证功能..."
    if ./scripts/ssl-manager.sh verify --docker > /dev/null 2>&1; then
        log_success "ssl-manager.sh Docker验证功能正常"
    else
        log_error "ssl-manager.sh Docker验证功能异常"
    fi
    
    # 测试alpine-optimizer.sh
    log_info "测试alpine-optimizer.sh功能..."
    if ./scripts/alpine-optimizer.sh verify > /dev/null 2>&1; then
        log_success "alpine-optimizer.sh验证功能正常"
    else
        log_warning "alpine-optimizer.sh验证功能异常"
    fi
    
    echo
}

# 生成诊断报告
generate_report() {
    local report_file="diagnosis_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成诊断报告: $report_file"
    
    {
        echo "SSL证书管理系统问题诊断报告"
        echo "生成时间: $(date)"
        echo "========================================"
        echo
        
        echo "=== 系统环境 ==="
        cat /etc/os-release | grep -E "NAME|VERSION" || echo "无法获取系统信息"
        echo "内核版本: $(uname -r)"
        echo "CPU核心数: $(nproc)"
        echo "内存大小: $(free -h | awk 'NR==2{print $2}')"
        echo
        
        echo "=== Docker环境 ==="
        docker --version || echo "Docker未安装"
        systemctl is-active docker || echo "Docker服务未运行"
        docker info --format '{{.Driver}}' 2>/dev/null || echo "Docker信息获取失败"
        echo
        
        echo "=== 网络连接 ==="
        ping -c 1 mirrors.aliyun.com > /dev/null 2>&1 && echo "✅ 阿里云镜像源连接正常" || echo "❌ 阿里云镜像源连接失败"
        ping -c 1 registry-1.docker.io > /dev/null 2>&1 && echo "✅ Docker Hub连接正常" || echo "❌ Docker Hub连接失败"
        echo
        
        echo "=== 脚本状态 ==="
        [ -f "scripts/ssl-manager.sh" ] && echo "✅ ssl-manager.sh存在" || echo "❌ ssl-manager.sh缺失"
        [ -f "scripts/alpine-optimizer.sh" ] && echo "✅ alpine-optimizer.sh存在" || echo "❌ alpine-optimizer.sh缺失"
        [ -f "docker-compose.aliyun.yml" ] && echo "✅ docker-compose.aliyun.yml存在" || echo "❌ docker-compose.aliyun.yml缺失"
        echo
        
        echo "=== 修复建议 ==="
        echo "1. 如果Docker服务异常: sudo systemctl restart docker"
        echo "2. 如果网络连接失败: 检查防火墙和DNS设置"
        echo "3. 如果脚本权限问题: chmod +x scripts/*.sh"
        echo "4. 如果Alpine测试失败: 检查容器网络配置"
        
    } > "$report_file"
    
    log_success "诊断报告已生成: $report_file"
}

# 主函数
main() {
    echo "🔧 SSL证书管理系统问题诊断工具"
    echo "================================="
    echo
    
    # 执行诊断
    diagnose_system
    diagnose_docker
    diagnose_network
    diagnose_alpine
    diagnose_scripts
    run_fix_tests
    
    # 生成报告
    generate_report
    
    echo
    log_success "🎉 诊断完成！"
    echo
    echo "=== 下一步操作建议 ==="
    echo "1. 查看诊断报告了解详细信息"
    echo "2. 根据报告中的建议进行修复"
    echo "3. 重新运行验证命令测试修复效果"
    echo "4. 如果问题持续，请联系技术支持"
}

# 执行主函数
main "$@"
