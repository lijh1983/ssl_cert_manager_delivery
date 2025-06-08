#!/bin/bash
# 阿里云部署验证脚本

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

# 检查系统环境
check_system() {
    log_info "检查系统环境..."
    
    echo "系统信息:"
    uname -a
    
    if [ -f /etc/os-release ]; then
        echo "操作系统:"
        cat /etc/os-release | grep -E "(NAME|VERSION)"
    fi
    
    echo "CPU信息:"
    lscpu | grep -E "(Model name|CPU\(s\)|Thread)"
    
    echo "内存信息:"
    free -h
    
    echo "磁盘信息:"
    df -h
    
    log_success "系统环境检查完成"
}

# 检查Docker环境
check_docker() {
    log_info "检查Docker环境..."
    
    # 检查Docker版本
    if command -v docker &> /dev/null; then
        log_success "Docker已安装: $(docker --version)"
    else
        log_error "Docker未安装"
        return 1
    fi
    
    # 检查Docker服务状态
    if systemctl is-active --quiet docker; then
        log_success "Docker服务运行正常"
    else
        log_error "Docker服务未运行"
        return 1
    fi
    
    # 检查Docker Compose
    if command -v docker-compose &> /dev/null; then
        log_success "Docker Compose已安装: $(docker-compose --version)"
    elif docker compose version &> /dev/null; then
        log_success "Docker Compose Plugin已安装: $(docker compose version)"
    else
        log_error "Docker Compose未安装"
        return 1
    fi
    
    # 检查Docker镜像加速器
    if docker info | grep -q "Registry Mirrors"; then
        log_success "Docker镜像加速器已配置"
        docker info | grep -A 5 "Registry Mirrors"
    else
        log_warning "Docker镜像加速器未配置"
    fi
    
    # 测试Docker镜像拉取
    log_info "测试Docker镜像拉取速度..."
    start_time=$(date +%s)
    if docker pull registry.cn-hangzhou.aliyuncs.com/library/hello-world:latest > /dev/null 2>&1; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        log_success "镜像拉取成功，耗时: ${duration}秒"
        docker rmi registry.cn-hangzhou.aliyuncs.com/library/hello-world:latest > /dev/null 2>&1
    else
        log_error "镜像拉取失败"
        return 1
    fi
    
    log_success "Docker环境检查完成"
}

# 检查网络连接
check_network() {
    log_info "检查网络连接..."
    
    # 检查基本网络连接
    if ping -c 3 8.8.8.8 > /dev/null 2>&1; then
        log_success "外网连接正常"
    else
        log_error "外网连接失败"
        return 1
    fi
    
    # 检查阿里云镜像源连接
    if curl -s --connect-timeout 5 https://registry.cn-hangzhou.aliyuncs.com > /dev/null; then
        log_success "阿里云Docker镜像源连接正常"
    else
        log_warning "阿里云Docker镜像源连接失败"
    fi
    
    # 检查GitHub连接
    if curl -s --connect-timeout 5 https://github.com > /dev/null; then
        log_success "GitHub连接正常"
    else
        log_warning "GitHub连接失败，可能影响代码下载"
    fi
    
    # 检查端口占用
    log_info "检查端口占用情况..."
    ports=(80 443 8000 3000 9090 5432 6379)
    for port in "${ports[@]}"; do
        if ss -tlnp | grep ":$port " > /dev/null; then
            log_warning "端口 $port 已被占用"
        else
            log_success "端口 $port 可用"
        fi
    done
    
    log_success "网络连接检查完成"
}

# 检查部署脚本
check_deployment_script() {
    log_info "检查部署脚本..."
    
    # 检查脚本是否存在
    if [ -f "scripts/deploy_aliyun.sh" ]; then
        log_success "阿里云部署脚本存在"
    else
        log_error "阿里云部署脚本不存在"
        return 1
    fi
    
    # 检查脚本权限
    if [ -x "scripts/deploy_aliyun.sh" ]; then
        log_success "部署脚本有执行权限"
    else
        log_warning "部署脚本没有执行权限，正在添加..."
        chmod +x scripts/deploy_aliyun.sh
    fi
    
    # 检查脚本参数支持
    if grep -q "enable-nginx" scripts/deploy_aliyun.sh; then
        log_success "部署脚本支持 --enable-nginx 参数"
    else
        log_error "部署脚本不支持 --enable-nginx 参数"
        return 1
    fi
    
    # 显示支持的参数
    log_info "支持的部署参数:"
    grep -A 10 "echo.*选项:" scripts/deploy_aliyun.sh | grep "echo.*--"
    
    log_success "部署脚本检查完成"
}

# 检查必要工具
check_tools() {
    log_info "检查必要工具..."
    
    tools=(curl wget git htop iotop)
    missing_tools=()
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_success "$tool 已安装"
        else
            log_warning "$tool 未安装"
            missing_tools+=("$tool")
        fi
    done
    
    # 检查nethogs（可能在RHEL 9中缺失）
    if command -v nethogs &> /dev/null; then
        log_success "nethogs 已安装"
    else
        log_warning "nethogs 未安装（在RHEL 9中可能需要EPEL仓库）"
        missing_tools+=("nethogs")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_warning "缺失工具: ${missing_tools[*]}"
        log_info "可以运行以下命令安装:"
        if command -v dnf &> /dev/null; then
            echo "sudo dnf install -y ${missing_tools[*]}"
        elif command -v yum &> /dev/null; then
            echo "sudo yum install -y ${missing_tools[*]}"
        elif command -v apt-get &> /dev/null; then
            echo "sudo apt-get install -y ${missing_tools[*]}"
        fi
    fi
    
    log_success "工具检查完成"
}

# 检查防火墙配置
check_firewall() {
    log_info "检查防火墙配置..."
    
    if systemctl is-active --quiet firewalld; then
        log_info "firewalld 正在运行"
        
        # 检查必要端口是否开放
        ports=(80 443 8000)
        for port in "${ports[@]}"; do
            if firewall-cmd --query-port=${port}/tcp > /dev/null 2>&1; then
                log_success "端口 $port/tcp 已开放"
            else
                log_warning "端口 $port/tcp 未开放"
            fi
        done
    elif systemctl is-active --quiet iptables; then
        log_info "iptables 正在运行"
        log_warning "请手动检查iptables规则"
    else
        log_info "防火墙服务未运行"
    fi
    
    log_success "防火墙检查完成"
}

# 生成部署建议
generate_recommendations() {
    log_info "生成部署建议..."
    
    echo
    echo "=== 部署建议 ==="
    
    # 系统资源建议
    mem_total=$(free -m | awk 'NR==2{print $2}')
    if [ "$mem_total" -lt 4096 ]; then
        log_warning "内存不足4GB，建议升级到至少4GB内存"
    else
        log_success "内存充足 (${mem_total}MB)"
    fi
    
    # 磁盘空间建议
    disk_avail=$(df / | awk 'NR==2{print $4}')
    if [ "$disk_avail" -lt 20971520 ]; then  # 20GB in KB
        log_warning "磁盘可用空间不足20GB，建议清理或扩容"
    else
        log_success "磁盘空间充足"
    fi
    
    # 部署命令建议
    echo
    echo "=== 推荐的部署命令 ==="
    echo "1. 基础部署:"
    echo "   ./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring"
    echo
    echo "2. 完整部署（包含nginx）:"
    echo "   ./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring --enable-nginx"
    echo
    echo "3. 快速部署（跳过构建）:"
    echo "   ./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring --skip-build"
    echo
    
    # 优化建议
    echo "=== 优化建议 ==="
    echo "1. 如果是首次部署，建议先运行: ./scripts/setup_rhel9_docker.sh"
    echo "2. 确保域名 ssl.gzyggl.com 已正确解析到此服务器"
    echo "3. 建议在部署前运行: docker system prune -a 清理Docker缓存"
    echo "4. 部署完成后可以通过以下地址访问:"
    echo "   - 前端: http://ssl.gzyggl.com"
    echo "   - 后端API: http://ssl.gzyggl.com:8000"
    echo "   - 监控: http://ssl.gzyggl.com:3000"
    echo
}

# 主函数
main() {
    echo "🔍 SSL证书管理系统 - 阿里云部署验证"
    echo "========================================"
    echo
    
    local checks_passed=0
    local total_checks=6
    
    # 执行检查
    if check_system; then ((checks_passed++)); fi
    echo
    
    if check_docker; then ((checks_passed++)); fi
    echo
    
    if check_network; then ((checks_passed++)); fi
    echo
    
    if check_deployment_script; then ((checks_passed++)); fi
    echo
    
    if check_tools; then ((checks_passed++)); fi
    echo
    
    if check_firewall; then ((checks_passed++)); fi
    echo
    
    # 显示检查结果
    echo "=== 检查结果 ==="
    echo "通过检查: $checks_passed/$total_checks"
    
    if [ "$checks_passed" -eq "$total_checks" ]; then
        log_success "所有检查通过！系统已准备好进行部署 🎉"
    elif [ "$checks_passed" -ge 4 ]; then
        log_warning "大部分检查通过，可以尝试部署，但建议先解决警告问题"
    else
        log_error "多项检查失败，建议先解决问题再进行部署"
    fi
    
    generate_recommendations
}

# 执行主函数
main "$@"
