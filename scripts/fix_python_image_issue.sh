#!/bin/bash
# Python镜像拉取问题修复脚本

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

# 测试Python镜像拉取
test_python_images() {
    log_info "测试Python基础镜像拉取..."
    
    # 定义候选镜像列表
    local images=(
        "python:3.10-slim|官方Docker Hub镜像"
        "python:3.11-slim|官方Docker Hub镜像(新版本)"
        "registry.cn-hangzhou.aliyuncs.com/acs/python:3.10-slim|阿里云ACS镜像"
        "dockerproxy.com/library/python:3.10-slim|Docker代理镜像"
        "docker.mirrors.ustc.edu.cn/library/python:3.10-slim|中科大镜像"
    )
    
    local successful_images=()
    local failed_images=()
    
    for image_info in "${images[@]}"; do
        local image=$(echo "$image_info" | cut -d'|' -f1)
        local description=$(echo "$image_info" | cut -d'|' -f2)
        
        log_info "测试拉取: $image ($description)"
        
        # 记录开始时间
        local start_time=$(date +%s)
        
        if timeout 120 docker pull "$image" > /dev/null 2>&1; then
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
    echo "=== Python镜像拉取测试结果 ==="
    echo "成功拉取的镜像 (${#successful_images[@]}):"
    for image in "${successful_images[@]}"; do
        echo "  ✅ $image"
    done
    
    echo
    echo "拉取失败的镜像 (${#failed_images[@]}):"
    for image in "${failed_images[@]}"; do
        echo "  ❌ $image"
    done
    
    # 返回最佳镜像
    if [ ${#successful_images[@]} -gt 0 ]; then
        echo "${successful_images[0]}"
        return 0
    else
        return 1
    fi
}

# 修复Dockerfile
fix_dockerfile() {
    local best_image="$1"
    
    log_info "修复backend/Dockerfile.aliyun..."
    
    # 备份原文件
    if [ -f "backend/Dockerfile.aliyun" ]; then
        cp backend/Dockerfile.aliyun backend/Dockerfile.aliyun.backup.$(date +%Y%m%d_%H%M%S)
        log_success "已备份原始Dockerfile"
    fi
    
    # 修复FROM行
    sed -i "s|FROM.*python.*AS base|FROM $best_image AS base|" backend/Dockerfile.aliyun
    
    log_success "Dockerfile修复完成，使用镜像: $best_image"
}

# 更新docker-compose配置
update_docker_compose() {
    local best_image="$1"
    
    log_info "更新docker-compose.aliyun.yml配置..."
    
    # 备份原文件
    if [ -f "docker-compose.aliyun.yml" ]; then
        cp docker-compose.aliyun.yml docker-compose.aliyun.yml.backup.$(date +%Y%m%d_%H%M%S)
        log_success "已备份原始docker-compose文件"
    fi
    
    # 更新cache_from配置
    if grep -q "cache_from:" docker-compose.aliyun.yml; then
        # 更新现有的cache_from配置
        sed -i "/cache_from:/,/^[[:space:]]*[^-]/ {
            /cache_from:/!{
                /^[[:space:]]*[^-]/!d
            }
        }" docker-compose.aliyun.yml
        
        # 添加新的cache_from配置
        sed -i "/cache_from:/a\\        - $best_image" docker-compose.aliyun.yml
    fi
    
    log_success "docker-compose配置更新完成"
}

# 测试构建
test_build() {
    log_info "测试后端镜像构建..."
    
    if docker build -f backend/Dockerfile.aliyun -t ssl-manager-backend:test ./backend; then
        log_success "后端镜像构建测试成功"
        
        # 清理测试镜像
        docker rmi ssl-manager-backend:test > /dev/null 2>&1 || true
        
        return 0
    else
        log_error "后端镜像构建测试失败"
        return 1
    fi
}

# 配置Docker镜像加速器
setup_docker_mirror() {
    log_info "检查Docker镜像加速器配置..."
    
    if [ -f "/etc/docker/daemon.json" ]; then
        if grep -q "registry-mirrors" /etc/docker/daemon.json; then
            log_success "Docker镜像加速器已配置"
            return 0
        fi
    fi
    
    log_warning "Docker镜像加速器未配置，正在配置..."
    
    sudo mkdir -p /etc/docker
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
    
    sudo systemctl restart docker
    sleep 5
    
    log_success "Docker镜像加速器配置完成"
}

# 显示修复结果
show_fix_result() {
    local best_image="$1"
    
    echo
    log_success "🎉 Python镜像问题修复完成！"
    echo
    echo "=== 修复详情 ==="
    echo "✅ 使用的Python基础镜像: $best_image"
    echo "✅ backend/Dockerfile.aliyun已修复"
    echo "✅ docker-compose.aliyun.yml已更新"
    echo "✅ 构建测试通过"
    echo
    echo "=== 下一步操作 ==="
    echo "现在可以继续执行完整的部署："
    echo "  ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
    echo
    echo "或者单独构建后端镜像："
    echo "  docker build -f backend/Dockerfile.aliyun -t ssl-manager-backend:latest ./backend"
    echo
}

# 主函数
main() {
    echo "🔧 Python镜像拉取问题修复工具"
    echo "================================="
    echo
    
    # 检查Docker服务
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行，请先启动Docker"
        exit 1
    fi
    
    # 配置镜像加速器
    setup_docker_mirror
    
    # 测试Python镜像拉取
    local best_image
    if best_image=$(test_python_images); then
        echo
        log_success "找到可用的Python镜像: $best_image"
        
        # 修复配置文件
        fix_dockerfile "$best_image"
        update_docker_compose "$best_image"
        
        # 测试构建
        if test_build; then
            show_fix_result "$best_image"
        else
            log_error "构建测试失败，请检查配置"
            exit 1
        fi
    else
        log_error "无法找到可用的Python基础镜像"
        
        echo
        echo "=== 故障排除建议 ==="
        echo "1. 检查网络连接:"
        echo "   ping registry-1.docker.io"
        echo "   ping registry.cn-hangzhou.aliyuncs.com"
        echo
        echo "2. 检查Docker配置:"
        echo "   docker info"
        echo "   systemctl status docker"
        echo
        echo "3. 尝试手动拉取镜像:"
        echo "   docker pull python:3.10-slim"
        echo
        echo "4. 配置代理（如果需要）:"
        echo "   export HTTP_PROXY=your-proxy-server"
        echo "   export HTTPS_PROXY=your-proxy-server"
        echo
        
        exit 1
    fi
}

# 执行主函数
main "$@"
