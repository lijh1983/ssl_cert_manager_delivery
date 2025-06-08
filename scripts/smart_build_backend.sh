#!/bin/bash
# 智能后端镜像构建脚本 - 支持多镜像源自动切换

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

# 智能选择基础镜像
select_base_image() {
    log_info "智能选择最佳Python基础镜像..."
    
    local candidate_images=(
        "python:3.10-slim"
        "python:3.11-slim"
        "registry.cn-hangzhou.aliyuncs.com/acs/python:3.10-slim"
        "dockerproxy.com/library/python:3.10-slim"
    )
    
    for image in "${candidate_images[@]}"; do
        log_info "测试镜像: $image"
        
        if timeout 60 docker pull "$image" > /dev/null 2>&1; then
            log_success "选择基础镜像: $image"
            echo "$image"
            return 0
        else
            log_warning "镜像不可用: $image"
        fi
    done
    
    log_error "没有找到可用的Python基础镜像"
    return 1
}

# 构建后端镜像
build_backend() {
    local base_image="$1"
    local dockerfile="${2:-backend/Dockerfile.aliyun}"
    local tag="${3:-ssl-manager-backend:latest}"
    
    log_info "构建后端镜像..."
    log_info "基础镜像: $base_image"
    log_info "Dockerfile: $dockerfile"
    log_info "标签: $tag"
    
    # 使用多种构建策略
    local build_success=false
    
    # 策略1: 使用指定的基础镜像构建
    log_info "尝试策略1: 使用指定基础镜像构建"
    if docker build \
        --build-arg BASE_IMAGE="$base_image" \
        --cache-from "$base_image" \
        --cache-from "$tag" \
        -f "$dockerfile" \
        -t "$tag" \
        ./backend 2>/dev/null; then
        log_success "策略1构建成功"
        build_success=true
    else
        log_warning "策略1构建失败，尝试策略2"
        
        # 策略2: 使用多源Dockerfile
        if [ -f "backend/Dockerfile.aliyun.multi" ]; then
            log_info "尝试策略2: 使用多源Dockerfile"
            if docker build \
                --build-arg BASE_IMAGE="$base_image" \
                -f backend/Dockerfile.aliyun.multi \
                -t "$tag" \
                ./backend 2>/dev/null; then
                log_success "策略2构建成功"
                build_success=true
            else
                log_warning "策略2构建失败，尝试策略3"
            fi
        fi
        
        # 策略3: 使用标准Dockerfile
        if [ "$build_success" = "false" ] && [ -f "backend/Dockerfile" ]; then
            log_info "尝试策略3: 使用标准Dockerfile"
            if docker build \
                -f backend/Dockerfile \
                -t "$tag" \
                ./backend; then
                log_success "策略3构建成功"
                build_success=true
            fi
        fi
    fi
    
    if [ "$build_success" = "true" ]; then
        log_success "后端镜像构建完成: $tag"
        
        # 显示镜像信息
        local image_size=$(docker images --format "table {{.Size}}" "$tag" | tail -n 1)
        log_info "镜像大小: $image_size"
        
        return 0
    else
        log_error "所有构建策略都失败了"
        return 1
    fi
}

# 测试镜像
test_image() {
    local tag="$1"
    
    log_info "测试后端镜像..."
    
    # 创建测试容器
    local container_id
    if container_id=$(docker run -d --name ssl-backend-test "$tag" sleep 30 2>/dev/null); then
        log_success "镜像启动测试成功"
        
        # 检查Python版本
        local python_version
        if python_version=$(docker exec "$container_id" python --version 2>/dev/null); then
            log_info "Python版本: $python_version"
        fi
        
        # 检查依赖包
        local pip_list
        if pip_list=$(docker exec "$container_id" pip list 2>/dev/null | wc -l); then
            log_info "已安装包数量: $pip_list"
        fi
        
        # 清理测试容器
        docker stop "$container_id" > /dev/null 2>&1 || true
        docker rm "$container_id" > /dev/null 2>&1 || true
        
        log_success "镜像测试通过"
        return 0
    else
        log_error "镜像启动测试失败"
        return 1
    fi
}

# 优化镜像
optimize_image() {
    local tag="$1"
    
    log_info "优化镜像..."
    
    # 创建优化后的镜像
    local optimized_tag="${tag}-optimized"
    
    # 使用multi-stage build的结果已经是优化的
    log_info "镜像已通过multi-stage构建优化"
    
    # 显示镜像层信息
    log_info "镜像层信息:"
    docker history "$tag" --format "table {{.CreatedBy}}\t{{.Size}}" | head -10
}

# 推送到镜像仓库（可选）
push_image() {
    local tag="$1"
    local registry="${2:-}"
    
    if [ -n "$registry" ]; then
        log_info "推送镜像到仓库: $registry"
        
        local remote_tag="$registry/$tag"
        docker tag "$tag" "$remote_tag"
        
        if docker push "$remote_tag"; then
            log_success "镜像推送成功: $remote_tag"
        else
            log_warning "镜像推送失败"
        fi
    fi
}

# 显示构建结果
show_build_result() {
    local tag="$1"
    local base_image="$2"
    
    echo
    log_success "🎉 后端镜像构建完成！"
    echo
    echo "=== 构建详情 ==="
    echo "✅ 基础镜像: $base_image"
    echo "✅ 构建标签: $tag"
    echo "✅ 镜像测试通过"
    echo
    echo "=== 镜像信息 ==="
    docker images "$tag" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo
    echo "=== 下一步操作 ==="
    echo "1. 启动完整服务:"
    echo "   docker-compose -f docker-compose.aliyun.yml up -d"
    echo
    echo "2. 或继续nginx代理配置:"
    echo "   ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
    echo
    echo "3. 测试后端服务:"
    echo "   docker run --rm -p 8000:8000 $tag"
    echo
}

# 主函数
main() {
    echo "🚀 智能后端镜像构建工具"
    echo "=========================="
    echo
    
    # 解析命令行参数
    local dockerfile="backend/Dockerfile.aliyun"
    local tag="ssl-manager-backend:latest"
    local registry=""
    local test_only=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dockerfile)
                dockerfile="$2"
                shift 2
                ;;
            --tag)
                tag="$2"
                shift 2
                ;;
            --registry)
                registry="$2"
                shift 2
                ;;
            --test-only)
                test_only=true
                shift
                ;;
            --help)
                echo "智能后端镜像构建脚本"
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --dockerfile FILE    指定Dockerfile路径"
                echo "  --tag TAG           指定镜像标签"
                echo "  --registry URL      推送到指定镜像仓库"
                echo "  --test-only         仅测试镜像拉取，不构建"
                echo "  --help              显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 检查Docker服务
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行，请先启动Docker"
        exit 1
    fi
    
    # 选择基础镜像
    local base_image
    if base_image=$(select_base_image); then
        log_success "基础镜像选择完成: $base_image"
        
        if [ "$test_only" = "true" ]; then
            log_info "仅测试模式，跳过构建"
            exit 0
        fi
        
        # 构建镜像
        if build_backend "$base_image" "$dockerfile" "$tag"; then
            # 测试镜像
            if test_image "$tag"; then
                # 优化镜像
                optimize_image "$tag"
                
                # 推送镜像（如果指定了仓库）
                if [ -n "$registry" ]; then
                    push_image "$tag" "$registry"
                fi
                
                # 显示结果
                show_build_result "$tag" "$base_image"
            else
                log_error "镜像测试失败"
                exit 1
            fi
        else
            log_error "镜像构建失败"
            exit 1
        fi
    else
        log_error "无法选择合适的基础镜像"
        exit 1
    fi
}

# 执行主函数
main "$@"
