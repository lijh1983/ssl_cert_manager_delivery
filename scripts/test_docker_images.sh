#!/bin/bash
# Docker镜像拉取测试脚本

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

# 测试Docker连接
test_docker_connection() {
    log_info "测试Docker连接..."
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行或无权限访问"
        return 1
    fi
    
    log_success "Docker连接正常"
}

# 测试网络连接
test_network_connectivity() {
    log_info "测试网络连接..."
    
    local registries=(
        "registry-1.docker.io"
        "registry.cn-hangzhou.aliyuncs.com"
        "docker.mirrors.ustc.edu.cn"
        "dockerproxy.com"
    )
    
    for registry in "${registries[@]}"; do
        if ping -c 1 -W 3 "$registry" > /dev/null 2>&1; then
            log_success "网络连接正常: $registry"
        else
            log_warning "网络连接失败: $registry"
        fi
    done
}

# 测试镜像拉取
test_image_pull() {
    log_info "测试nginx镜像拉取..."
    
    # 定义要测试的镜像列表
    local images=(
        "nginx:1.24-alpine|官方Docker Hub"
        "nginx:alpine|官方Docker Hub (latest alpine)"
        "registry.cn-hangzhou.aliyuncs.com/acs/nginx:1.24-alpine|阿里云ACS"
        "registry.cn-hangzhou.aliyuncs.com/library/nginx:1.24-alpine|阿里云Library"
        "dockerproxy.com/library/nginx:1.24-alpine|Docker代理"
        "docker.mirrors.ustc.edu.cn/library/nginx:1.24-alpine|中科大镜像"
    )
    
    local successful_images=()
    local failed_images=()
    
    for image_info in "${images[@]}"; do
        local image=$(echo "$image_info" | cut -d'|' -f1)
        local description=$(echo "$image_info" | cut -d'|' -f2)
        
        log_info "测试拉取: $image ($description)"
        
        # 记录开始时间
        local start_time=$(date +%s)
        
        if timeout 60 docker pull "$image" > /dev/null 2>&1; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log_success "拉取成功: $image (耗时: ${duration}秒)"
            successful_images+=("$image")
            
            # 获取镜像信息
            local size=$(docker images --format "table {{.Size}}" "$image" | tail -n 1)
            log_info "镜像大小: $size"
        else
            log_error "拉取失败: $image"
            failed_images+=("$image")
        fi
        
        echo
    done
    
    # 显示测试结果
    echo "=== 镜像拉取测试结果 ==="
    echo "成功拉取的镜像 (${#successful_images[@]}):"
    for image in "${successful_images[@]}"; do
        echo "  ✅ $image"
    done
    
    echo
    echo "拉取失败的镜像 (${#failed_images[@]}):"
    for image in "${failed_images[@]}"; do
        echo "  ❌ $image"
    done
    
    # 返回结果
    if [ ${#successful_images[@]} -gt 0 ]; then
        log_success "至少有一个镜像拉取成功，可以继续部署"
        return 0
    else
        log_error "所有镜像拉取都失败了"
        return 1
    fi
}

# 清理测试镜像
cleanup_test_images() {
    log_info "清理测试镜像..."
    
    # 删除测试拉取的镜像（保留一个可用的）
    local images_to_keep=("nginx:1.24-alpine" "nginx:alpine")
    
    # 获取所有nginx镜像
    local all_nginx_images=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep nginx || true)
    
    for image in $all_nginx_images; do
        local keep_image=false
        for keep in "${images_to_keep[@]}"; do
            if [ "$image" = "$keep" ]; then
                keep_image=true
                break
            fi
        done
        
        if [ "$keep_image" = "false" ]; then
            log_info "删除测试镜像: $image"
            docker rmi "$image" > /dev/null 2>&1 || true
        fi
    done
    
    log_success "测试镜像清理完成"
}

# 推荐最佳镜像
recommend_best_image() {
    log_info "推荐最佳镜像..."
    
    # 检查哪些镜像可用
    local available_images=()
    
    if docker images nginx:1.24-alpine --format "{{.Repository}}" | grep -q nginx; then
        available_images+=("nginx:1.24-alpine")
    fi
    
    if docker images nginx:alpine --format "{{.Repository}}" | grep -q nginx; then
        available_images+=("nginx:alpine")
    fi
    
    if [ ${#available_images[@]} -gt 0 ]; then
        local recommended="${available_images[0]}"
        log_success "推荐使用镜像: $recommended"
        
        echo
        echo "=== 修改建议 ==="
        echo "请将 nginx/Dockerfile.proxy 中的 FROM 行修改为:"
        echo "FROM $recommended"
        echo
        echo "或者运行以下命令自动修改:"
        echo "sed -i 's|FROM.*nginx.*|FROM $recommended|' nginx/Dockerfile.proxy"
    else
        log_error "没有可用的nginx镜像"
        
        echo
        echo "=== 解决建议 ==="
        echo "1. 检查网络连接"
        echo "2. 配置Docker镜像加速器"
        echo "3. 尝试使用VPN或代理"
        echo "4. 联系系统管理员检查防火墙设置"
    fi
}

# 生成Dockerfile修复脚本
generate_dockerfile_fix() {
    log_info "生成Dockerfile修复脚本..."
    
    cat > fix_dockerfile.sh <<'EOF'
#!/bin/bash
# Dockerfile自动修复脚本

echo "修复nginx/Dockerfile.proxy..."

# 备份原文件
cp nginx/Dockerfile.proxy nginx/Dockerfile.proxy.backup

# 尝试不同的基础镜像
if docker pull nginx:1.24-alpine > /dev/null 2>&1; then
    sed -i 's|FROM.*nginx.*|FROM nginx:1.24-alpine|' nginx/Dockerfile.proxy
    echo "使用官方镜像: nginx:1.24-alpine"
elif docker pull nginx:alpine > /dev/null 2>&1; then
    sed -i 's|FROM.*nginx.*|FROM nginx:alpine|' nginx/Dockerfile.proxy
    echo "使用官方镜像: nginx:alpine"
elif docker pull registry.cn-hangzhou.aliyuncs.com/acs/nginx:1.24-alpine > /dev/null 2>&1; then
    sed -i 's|FROM.*nginx.*|FROM registry.cn-hangzhou.aliyuncs.com/acs/nginx:1.24-alpine|' nginx/Dockerfile.proxy
    echo "使用阿里云镜像: registry.cn-hangzhou.aliyuncs.com/acs/nginx:1.24-alpine"
else
    echo "错误: 无法拉取任何nginx镜像"
    exit 1
fi

echo "Dockerfile修复完成"
EOF
    
    chmod +x fix_dockerfile.sh
    log_success "修复脚本已生成: fix_dockerfile.sh"
}

# 主函数
main() {
    echo "🐳 Docker镜像拉取测试工具"
    echo "==============================="
    echo
    
    # 解析命令行参数
    local cleanup_after=false
    local auto_fix=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup)
                cleanup_after=true
                shift
                ;;
            --auto-fix)
                auto_fix=true
                shift
                ;;
            --help)
                echo "Docker镜像拉取测试脚本"
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --cleanup     测试后清理镜像"
                echo "  --auto-fix    自动修复Dockerfile"
                echo "  --help        显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行测试
    test_docker_connection
    echo
    
    test_network_connectivity
    echo
    
    if test_image_pull; then
        echo
        recommend_best_image
        
        if [ "$auto_fix" = "true" ]; then
            echo
            generate_dockerfile_fix
            ./fix_dockerfile.sh
        fi
        
        if [ "$cleanup_after" = "true" ]; then
            echo
            cleanup_test_images
        fi
        
        echo
        log_success "测试完成！可以继续部署nginx反向代理"
    else
        echo
        log_error "镜像拉取测试失败，请检查网络连接和Docker配置"
        
        echo
        echo "=== 故障排除建议 ==="
        echo "1. 检查Docker服务状态: systemctl status docker"
        echo "2. 检查网络连接: ping registry-1.docker.io"
        echo "3. 配置Docker镜像加速器: 参考阿里云文档"
        echo "4. 检查防火墙设置: firewall-cmd --list-all"
        echo "5. 尝试使用代理: export HTTP_PROXY=your-proxy"
        
        exit 1
    fi
}

# 执行主函数
main "$@"
