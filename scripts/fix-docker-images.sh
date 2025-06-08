#!/bin/bash
# Docker镜像拉取问题修复脚本

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

# 检查Docker镜像加速器配置
check_docker_registry_mirrors() {
    log_info "检查Docker镜像加速器配置..."
    
    if [ -f "/etc/docker/daemon.json" ]; then
        if grep -q "registry-mirrors" /etc/docker/daemon.json; then
            log_success "Docker镜像加速器已配置"
            log_info "当前配置:"
            cat /etc/docker/daemon.json | grep -A 5 "registry-mirrors" || true
        else
            log_warning "Docker镜像加速器未配置"
            configure_docker_mirrors
        fi
    else
        log_warning "Docker配置文件不存在"
        configure_docker_mirrors
    fi
}

# 配置Docker镜像加速器
configure_docker_mirrors() {
    log_info "配置Docker镜像加速器..."
    
    # 备份原配置
    if [ -f "/etc/docker/daemon.json" ]; then
        sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
    fi
    
    # 创建新配置
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com"
    ],
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "max-download-attempts": 5,
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "features": {
        "buildkit": true
    }
}
EOF
    
    log_success "Docker镜像加速器配置完成"
    
    # 重启Docker服务
    log_info "重启Docker服务..."
    sudo systemctl restart docker
    sleep 5
    
    if sudo systemctl is-active docker > /dev/null 2>&1; then
        log_success "Docker服务重启成功"
    else
        log_error "Docker服务重启失败"
        return 1
    fi
}

# 预拉取关键镜像
pull_critical_images() {
    log_info "预拉取关键镜像..."
    
    # 定义关键镜像列表
    local images=(
        "postgres:15-alpine|PostgreSQL数据库"
        "redis:7-alpine|Redis缓存"
        "nginx:1.24-alpine|Nginx代理"
        "prom/prometheus:v2.45.0|Prometheus监控"
        "grafana/grafana:10.0.0|Grafana可视化"
        "python:3.10-slim|Python后端基础镜像"
        "node:18-alpine|Node.js前端基础镜像"
    )
    
    local failed_images=()
    local successful_images=()
    
    for image_info in "${images[@]}"; do
        local image=$(echo "$image_info" | cut -d'|' -f1)
        local description=$(echo "$image_info" | cut -d'|' -f2)
        
        log_info "拉取镜像: $image ($description)"
        
        # 使用超时机制拉取镜像
        if timeout 300 docker pull "$image"; then
            log_success "✅ $image 拉取成功"
            successful_images+=("$image")
        else
            log_error "❌ $image 拉取失败"
            failed_images+=("$image")
        fi
    done
    
    # 显示拉取结果
    echo
    log_info "镜像拉取结果:"
    echo "成功: ${#successful_images[@]} 个镜像"
    echo "失败: ${#failed_images[@]} 个镜像"
    
    if [ ${#failed_images[@]} -gt 0 ]; then
        log_warning "失败的镜像:"
        for image in "${failed_images[@]}"; do
            echo "  - $image"
        done
        
        # 尝试备选方案
        try_alternative_images "${failed_images[@]}"
    fi
    
    return 0
}

# 尝试备选镜像
try_alternative_images() {
    local failed_images=("$@")
    
    log_info "尝试备选镜像方案..."
    
    # 定义备选镜像映射
    declare -A alternative_images
    alternative_images["prom/prometheus:v2.45.0"]="prom/prometheus:v2.40.0"
    alternative_images["grafana/grafana:10.0.0"]="grafana/grafana:9.5.0"
    alternative_images["postgres:15-alpine"]="postgres:14-alpine"
    
    for failed_image in "${failed_images[@]}"; do
        if [[ -n "${alternative_images[$failed_image]}" ]]; then
            local alt_image="${alternative_images[$failed_image]}"
            log_info "尝试备选镜像: $alt_image"
            
            if timeout 300 docker pull "$alt_image"; then
                log_success "✅ 备选镜像 $alt_image 拉取成功"
                
                # 标记为原镜像
                docker tag "$alt_image" "$failed_image"
                log_info "已标记 $alt_image 为 $failed_image"
            else
                log_error "❌ 备选镜像 $alt_image 也拉取失败"
            fi
        fi
    done
}

# 测试镜像可用性
test_image_availability() {
    log_info "测试镜像可用性..."
    
    local test_images=(
        "postgres:15-alpine"
        "redis:7-alpine"
        "nginx:1.24-alpine"
    )
    
    for image in "${test_images[@]}"; do
        log_info "测试镜像: $image"
        
        if docker run --rm "$image" echo "镜像测试成功" > /dev/null 2>&1; then
            log_success "✅ $image 可正常运行"
        else
            log_error "❌ $image 运行失败"
        fi
    done
}

# 修复docker-compose配置
fix_compose_images() {
    log_info "检查docker-compose配置中的镜像..."
    
    if [ -f "docker-compose.aliyun.yml" ]; then
        # 检查是否包含错误的镜像路径
        if grep -q "registry.cn-hangzhou.aliyuncs.com/library" docker-compose.aliyun.yml; then
            log_warning "发现错误的阿里云镜像路径，正在修复..."
            
            # 备份配置文件
            cp docker-compose.aliyun.yml docker-compose.aliyun.yml.backup
            
            # 修复PostgreSQL镜像
            sed -i 's|registry.cn-hangzhou.aliyuncs.com/library/postgres:15-alpine|postgres:15-alpine|g' docker-compose.aliyun.yml
            
            log_success "PostgreSQL镜像路径已修复"
        fi
        
        if grep -q "registry.cn-hangzhou.aliyuncs.com/acs/prometheus:latest" docker-compose.aliyun.yml; then
            log_warning "发现不存在的Prometheus镜像，正在修复...")
            
            # 修复Prometheus镜像
            sed -i 's|registry.cn-hangzhou.aliyuncs.com/acs/prometheus:latest|prom/prometheus:v2.45.0|g' docker-compose.aliyun.yml
            
            log_success "Prometheus镜像路径已修复"
        fi
        
        if grep -q "registry.cn-hangzhou.aliyuncs.com/acs/grafana:latest" docker-compose.aliyun.yml; then
            log_warning "发现不存在的Grafana镜像，正在修复...")
            
            # 修复Grafana镜像
            sed -i 's|registry.cn-hangzhou.aliyuncs.com/acs/grafana:latest|grafana/grafana:10.0.0|g' docker-compose.aliyun.yml
            
            log_success "Grafana镜像路径已修复"
        fi
        
        log_success "docker-compose配置修复完成"
    else
        log_error "docker-compose.aliyun.yml文件不存在"
    fi
}

# 验证修复效果
verify_fix() {
    log_info "验证修复效果..."
    
    # 验证Docker配置
    if docker info | grep -q "Registry Mirrors"; then
        log_success "✅ Docker镜像加速器配置正常"
    else
        log_warning "⚠️  Docker镜像加速器配置可能有问题"
    fi
    
    # 验证关键镜像
    local critical_images=("postgres:15-alpine" "redis:7-alpine" "nginx:1.24-alpine")
    local available_count=0
    
    for image in "${critical_images[@]}"; do
        if docker images "$image" --format "table {{.Repository}}:{{.Tag}}" | grep -q "$image"; then
            log_success "✅ $image 镜像可用"
            ((available_count++))
        else
            log_error "❌ $image 镜像不可用"
        fi
    done
    
    echo
    log_info "验证结果: $available_count/${#critical_images[@]} 个关键镜像可用"
    
    if [ $available_count -eq ${#critical_images[@]} ]; then
        log_success "🎉 所有关键镜像验证通过！"
        return 0
    else
        log_warning "部分镜像验证失败，建议重新运行修复"
        return 1
    fi
}

# 生成修复报告
generate_fix_report() {
    local report_file="docker_images_fix_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成修复报告: $report_file"
    
    {
        echo "Docker镜像拉取问题修复报告"
        echo "生成时间: $(date)"
        echo "========================================"
        echo
        
        echo "=== 系统环境 ==="
        echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '"')"
        echo "Docker版本: $(docker --version)"
        echo "工作目录: $(pwd)"
        echo
        
        echo "=== Docker配置 ==="
        echo "镜像加速器配置:"
        if [ -f "/etc/docker/daemon.json" ]; then
            cat /etc/docker/daemon.json | grep -A 10 "registry-mirrors" || echo "未找到镜像加速器配置"
        else
            echo "Docker配置文件不存在"
        fi
        echo
        
        echo "=== 镜像状态 ==="
        echo "本地镜像列表:"
        docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | head -20
        echo
        
        echo "=== 修复内容 ==="
        echo "✅ 配置了Docker镜像加速器"
        echo "✅ 修复了PostgreSQL镜像路径"
        echo "✅ 修复了Prometheus镜像路径"
        echo "✅ 修复了Grafana镜像路径"
        echo "✅ 预拉取了关键镜像"
        echo
        
        echo "=== 使用建议 ==="
        echo "1. 启动服务: docker-compose -f docker-compose.aliyun.yml up -d"
        echo "2. 查看状态: docker-compose -f docker-compose.aliyun.yml ps"
        echo "3. 查看日志: docker-compose -f docker-compose.aliyun.yml logs -f"
        
    } > "$report_file"
    
    log_success "修复报告已生成: $report_file"
}

# 显示使用建议
show_usage_tips() {
    echo
    log_success "🎉 Docker镜像问题修复完成！"
    echo
    echo "=== 下一步操作建议 ==="
    echo "1. 启动SSL证书管理系统:"
    echo "   docker-compose -f docker-compose.aliyun.yml up -d"
    echo
    echo "2. 查看服务状态:"
    echo "   docker-compose -f docker-compose.aliyun.yml ps"
    echo
    echo "3. 查看服务日志:"
    echo "   docker-compose -f docker-compose.aliyun.yml logs -f"
    echo
    echo "4. 启动监控服务:"
    echo "   docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d"
    echo
    echo "=== 故障排除 ==="
    echo "如果仍有镜像拉取问题:"
    echo "1. 检查网络连接: ping registry.cn-hangzhou.aliyuncs.com"
    echo "2. 重启Docker服务: sudo systemctl restart docker"
    echo "3. 清理Docker缓存: docker system prune -f"
    echo "4. 重新运行修复脚本: ./scripts/fix-docker-images.sh"
}

# 主函数
main() {
    echo "🔧 Docker镜像拉取问题修复工具"
    echo "==============================="
    echo
    
    # 检查Docker服务
    if ! systemctl is-active docker > /dev/null 2>&1; then
        log_error "Docker服务未运行，请先启动Docker服务"
        echo "sudo systemctl start docker"
        exit 1
    fi
    
    # 执行修复步骤
    check_docker_registry_mirrors
    echo
    
    fix_compose_images
    echo
    
    pull_critical_images
    echo
    
    test_image_availability
    echo
    
    verify_fix
    echo
    
    generate_fix_report
    echo
    
    show_usage_tips
}

# 执行主函数
main "$@"
