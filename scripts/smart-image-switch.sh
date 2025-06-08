#!/bin/bash
# 智能镜像源切换脚本

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

# 定义镜像源配置
declare -A MIRROR_CONFIGS
MIRROR_CONFIGS["aliyun"]="registry.cn-hangzhou.aliyuncs.com"
MIRROR_CONFIGS["ustc"]="docker.mirrors.ustc.edu.cn"
MIRROR_CONFIGS["163"]="hub-mirror.c.163.com"
MIRROR_CONFIGS["tencent"]="mirror.ccs.tencentyun.com"
MIRROR_CONFIGS["official"]="registry-1.docker.io"

# 定义镜像映射
declare -A IMAGE_MAPPINGS
IMAGE_MAPPINGS["postgres:15-alpine"]="postgres:15-alpine|postgres:14-alpine|postgres:13-alpine"
IMAGE_MAPPINGS["redis:7-alpine"]="redis:7-alpine|redis:6-alpine|redis:alpine"
IMAGE_MAPPINGS["nginx:1.24-alpine"]="nginx:1.24-alpine|nginx:1.22-alpine|nginx:alpine"
IMAGE_MAPPINGS["prom/prometheus:v2.45.0"]="prom/prometheus:v2.45.0|prom/prometheus:v2.40.0|prom/prometheus:latest"
IMAGE_MAPPINGS["grafana/grafana:10.0.0"]="grafana/grafana:10.0.0|grafana/grafana:9.5.0|grafana/grafana:latest"

# 测试镜像源速度
test_mirror_speed() {
    local mirror_name=$1
    local mirror_url=${MIRROR_CONFIGS[$mirror_name]}
    
    log_info "测试镜像源: $mirror_name ($mirror_url)"
    
    local start_time=$(date +%s%N)
    if timeout 10 curl -s -I "https://$mirror_url/v2/" > /dev/null 2>&1; then
        local end_time=$(date +%s%N)
        local duration=$(( (end_time - start_time) / 1000000 ))
        log_success "$mirror_name 响应时间: ${duration}ms"
        echo $duration
    else
        log_warning "$mirror_name 连接失败"
        echo 9999
    fi
}

# 选择最快的镜像源
select_fastest_mirror() {
    log_info "测试所有镜像源速度..."
    
    local fastest_mirror=""
    local fastest_time=9999
    
    for mirror_name in "${!MIRROR_CONFIGS[@]}"; do
        local time=$(test_mirror_speed "$mirror_name")
        if [ "$time" -lt "$fastest_time" ]; then
            fastest_time=$time
            fastest_mirror=$mirror_name
        fi
    done
    
    if [ -n "$fastest_mirror" ]; then
        log_success "选择最快镜像源: $fastest_mirror (${fastest_time}ms)"
        echo "$fastest_mirror"
    else
        log_warning "所有镜像源测试失败，使用官方源"
        echo "official"
    fi
}

# 配置Docker镜像加速器
configure_docker_mirrors() {
    local selected_mirror=$1
    
    log_info "配置Docker镜像加速器: $selected_mirror"
    
    # 备份原配置
    if [ -f "/etc/docker/daemon.json" ]; then
        sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # 根据选择的镜像源配置
    case "$selected_mirror" in
        "aliyun")
            sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com"
    ],
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    }
}
EOF
            ;;
        "ustc")
            sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn",
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://hub-mirror.c.163.com"
    ],
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    }
}
EOF
            ;;
        "163")
            sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://hub-mirror.c.163.com",
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn"
    ],
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    }
}
EOF
            ;;
        *)
            log_warning "使用默认配置"
            ;;
    esac
    
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

# 智能拉取镜像
smart_pull_image() {
    local image=$1
    local alternatives=${IMAGE_MAPPINGS[$image]}
    
    if [ -z "$alternatives" ]; then
        alternatives="$image"
    fi
    
    log_info "智能拉取镜像: $image"
    
    # 尝试拉取主镜像
    if timeout 300 docker pull "$image" > /dev/null 2>&1; then
        log_success "✅ $image 拉取成功"
        return 0
    fi
    
    # 尝试备选镜像
    log_warning "$image 拉取失败，尝试备选镜像..."
    
    IFS='|' read -ra alt_images <<< "$alternatives"
    for alt_image in "${alt_images[@]}"; do
        if [ "$alt_image" != "$image" ]; then
            log_info "尝试备选镜像: $alt_image"
            
            if timeout 300 docker pull "$alt_image" > /dev/null 2>&1; then
                log_success "✅ 备选镜像 $alt_image 拉取成功"
                
                # 标记为原镜像
                docker tag "$alt_image" "$image"
                log_info "已标记 $alt_image 为 $image"
                return 0
            fi
        fi
    done
    
    log_error "❌ 所有镜像拉取失败: $image"
    return 1
}

# 批量智能拉取镜像
batch_smart_pull() {
    log_info "批量智能拉取关键镜像..."
    
    local images=(
        "postgres:15-alpine"
        "redis:7-alpine"
        "nginx:1.24-alpine"
        "python:3.10-slim"
        "node:18-alpine"
        "prom/prometheus:v2.45.0"
        "grafana/grafana:10.0.0"
    )
    
    local failed_images=()
    local successful_images=()
    
    for image in "${images[@]}"; do
        if smart_pull_image "$image"; then
            successful_images+=("$image")
        else
            failed_images+=("$image")
        fi
    done
    
    echo
    log_info "批量拉取结果:"
    echo "成功: ${#successful_images[@]} 个镜像"
    echo "失败: ${#failed_images[@]} 个镜像"
    
    if [ ${#failed_images[@]} -gt 0 ]; then
        log_warning "失败的镜像:"
        for image in "${failed_images[@]}"; do
            echo "  - $image"
        done
    fi
    
    return 0
}

# 生成镜像切换报告
generate_switch_report() {
    local selected_mirror=$1
    local report_file="image_switch_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成镜像切换报告: $report_file"
    
    {
        echo "Docker镜像源智能切换报告"
        echo "生成时间: $(date)"
        echo "========================================"
        echo
        
        echo "=== 选择的镜像源 ==="
        echo "镜像源: $selected_mirror"
        echo "地址: ${MIRROR_CONFIGS[$selected_mirror]}"
        echo
        
        echo "=== Docker配置 ==="
        if [ -f "/etc/docker/daemon.json" ]; then
            cat /etc/docker/daemon.json
        else
            echo "Docker配置文件不存在"
        fi
        echo
        
        echo "=== 本地镜像 ==="
        docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | head -15
        echo
        
        echo "=== 使用建议 ==="
        echo "1. 启动服务: docker-compose -f docker-compose.aliyun.yml up -d"
        echo "2. 如果仍有问题: ./scripts/fix-docker-images.sh"
        echo "3. 备选配置: docker-compose -f docker-compose.aliyun.backup.yml up -d"
        
    } > "$report_file"
    
    log_success "镜像切换报告已生成: $report_file"
}

# 显示使用建议
show_usage_tips() {
    echo
    log_success "🎉 智能镜像源切换完成！"
    echo
    echo "=== 下一步操作 ==="
    echo "1. 验证镜像拉取:"
    echo "   docker pull nginx:alpine"
    echo
    echo "2. 启动SSL证书管理系统:"
    echo "   docker-compose -f docker-compose.aliyun.yml up -d"
    echo
    echo "3. 查看服务状态:"
    echo "   docker-compose -f docker-compose.aliyun.yml ps"
    echo
    echo "=== 故障排除 ==="
    echo "如果仍有镜像拉取问题:"
    echo "1. 重新运行智能切换: ./scripts/smart-image-switch.sh"
    echo "2. 手动修复镜像: ./scripts/fix-docker-images.sh"
    echo "3. 使用备选配置: docker-compose -f docker-compose.aliyun.backup.yml up -d"
}

# 主函数
main() {
    echo "🔄 Docker镜像源智能切换工具"
    echo "============================="
    echo
    
    # 检查Docker服务
    if ! systemctl is-active docker > /dev/null 2>&1; then
        log_error "Docker服务未运行，请先启动Docker服务"
        echo "sudo systemctl start docker"
        exit 1
    fi
    
    # 选择最快的镜像源
    local selected_mirror
    if [ -n "$1" ]; then
        selected_mirror="$1"
        log_info "使用指定的镜像源: $selected_mirror"
    else
        selected_mirror=$(select_fastest_mirror)
    fi
    echo
    
    # 配置Docker镜像加速器
    configure_docker_mirrors "$selected_mirror"
    echo
    
    # 批量智能拉取镜像
    batch_smart_pull
    echo
    
    # 生成报告
    generate_switch_report "$selected_mirror"
    echo
    
    # 显示使用建议
    show_usage_tips
}

# 显示帮助信息
show_help() {
    echo "Docker镜像源智能切换工具"
    echo "用法: $0 [镜像源]"
    echo
    echo "可用的镜像源:"
    echo "  aliyun    - 阿里云镜像源 (推荐)"
    echo "  ustc      - 中科大镜像源"
    echo "  163       - 网易镜像源"
    echo "  tencent   - 腾讯云镜像源"
    echo "  official  - 官方镜像源"
    echo
    echo "示例:"
    echo "  $0           # 自动选择最快的镜像源"
    echo "  $0 aliyun    # 使用阿里云镜像源"
    echo "  $0 ustc      # 使用中科大镜像源"
}

# 检查参数
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

# 执行主函数
main "$@"
