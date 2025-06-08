#!/bin/bash
# Alpine Linux镜像源优化工具 - 整合版
# 包含优化、测试、验证功能

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

# 显示帮助信息
show_help() {
    echo "Alpine Linux镜像源优化工具"
    echo "用法: $0 <命令> [选项]"
    echo
    echo "命令:"
    echo "  optimize        优化Alpine镜像源配置"
    echo "  test            测试Alpine构建速度"
    echo "  verify          验证Alpine优化效果"
    echo "  restore         恢复原始配置"
    echo
    echo "优化选项 (optimize):"
    echo "  --auto          自动选择最快镜像源"
    echo "  --aliyun        使用阿里云镜像源"
    echo "  --ustc          使用中科大镜像源"
    echo "  --tuna          使用清华镜像源"
    echo
    echo "测试选项 (test):"
    echo "  --build         测试构建速度"
    echo "  --mirrors       测试镜像源速度"
    echo "  --simple        简化测试"
    echo
    echo "示例:"
    echo "  $0 optimize --auto"
    echo "  $0 test --build"
    echo "  $0 verify"
}

# 检测Alpine版本
detect_alpine_version() {
    if [ -f /etc/alpine-release ]; then
        # 获取主版本号，例如 3.18.12 -> v3.18
        local full_version=$(cat /etc/alpine-release)
        local major_minor=$(echo "$full_version" | cut -d'.' -f1,2)
        echo "v$major_minor"
    else
        echo "v3.18"  # 默认版本
    fi
}

# 优化Alpine镜像源
optimize_alpine() {
    local mirror="auto"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto)
                mirror="auto"
                shift
                ;;
            --aliyun)
                mirror="mirrors.aliyun.com"
                shift
                ;;
            --ustc)
                mirror="mirrors.ustc.edu.cn"
                shift
                ;;
            --tuna)
                mirror="mirrors.tuna.tsinghua.edu.cn"
                shift
                ;;
            *)
                log_error "未知优化参数: $1"
                return 1
                ;;
        esac
    done
    
    log_info "开始Alpine镜像源优化..."
    
    # 检查是否在Alpine环境中
    if [ ! -f /etc/alpine-release ]; then
        log_warning "当前不在Alpine环境中，将在Docker容器中测试"
        test_in_container "$mirror"
        return $?
    fi
    
    local version=$(detect_alpine_version)
    log_info "检测到Alpine版本: $version"
    
    # 自动选择最快镜像源
    if [ "$mirror" = "auto" ]; then
        mirror=$(select_fastest_mirror "$version")
    fi
    
    log_info "使用镜像源: $mirror"
    
    # 备份原始配置
    if [ -f /etc/apk/repositories ]; then
        cp /etc/apk/repositories /etc/apk/repositories.backup
        log_info "已备份原始配置"
    fi
    
    # 配置新镜像源
    cat > /etc/apk/repositories <<EOF
https://$mirror/alpine/$version/main
https://$mirror/alpine/$version/community
EOF
    
    log_success "Alpine镜像源配置完成"
    
    # 更新包索引
    log_info "更新包索引..."
    if apk update; then
        log_success "包索引更新成功"
        
        # 测试安装速度
        test_package_install
    else
        log_error "包索引更新失败，恢复备份"
        if [ -f /etc/apk/repositories.backup ]; then
            mv /etc/apk/repositories.backup /etc/apk/repositories
        fi
        return 1
    fi
}

# 选择最快的镜像源
select_fastest_mirror() {
    local version=$1
    local mirrors=("mirrors.aliyun.com" "mirrors.ustc.edu.cn" "mirrors.tuna.tsinghua.edu.cn")
    local fastest_mirror="mirrors.aliyun.com"
    local fastest_time=999
    
    for mirror in "${mirrors[@]}"; do
        log_info "测试镜像源: $mirror"
        local start_time=$(date +%s)
        
        if timeout 10 curl -s -I "https://$mirror/alpine/$version/main/x86_64/APKINDEX.tar.gz" > /dev/null 2>&1; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log_success "$mirror 响应时间: ${duration}秒"
            
            if [ $duration -lt $fastest_time ]; then
                fastest_time=$duration
                fastest_mirror=$mirror
            fi
        else
            log_warning "$mirror 连接失败"
        fi
    done
    
    log_success "选择最快镜像源: $fastest_mirror"
    echo "$fastest_mirror"
}

# 测试包安装速度
test_package_install() {
    log_info "测试包安装速度..."
    
    local start_time=$(date +%s)
    if apk add --no-cache curl > /dev/null 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "curl包安装耗时: ${duration}秒"
        
        # 清理测试包
        apk del curl > /dev/null 2>&1 || true
    else
        log_error "curl包安装失败"
    fi
}

# 在容器中测试
test_in_container() {
    local mirror=$1

    log_info "在Alpine容器中测试镜像源优化..."

    # 确定使用的镜像源
    local selected_mirror
    if [ "$mirror" = "auto" ]; then
        selected_mirror="mirrors.aliyun.com"
    else
        selected_mirror="$mirror"
    fi

    log_info "使用镜像源: $selected_mirror"

    # 创建测试脚本（修复变量替换问题）
    cat > test_alpine_in_container.sh <<EOF
#!/bin/sh
set -e

echo "=== Alpine镜像源优化测试 ==="
echo "Alpine版本: \$(cat /etc/alpine-release)"

# 配置镜像源
ALPINE_FULL_VERSION=\$(cat /etc/alpine-release)
ALPINE_VERSION="v\$(echo \$ALPINE_FULL_VERSION | cut -d'.' -f1,2)"
MIRROR="$selected_mirror"

echo "配置镜像源: \$MIRROR"

# 备份原始配置
cp /etc/apk/repositories /etc/apk/repositories.backup

# 配置新的镜像源
echo "https://\$MIRROR/alpine/\$ALPINE_VERSION/main" > /etc/apk/repositories
echo "https://\$MIRROR/alpine/\$ALPINE_VERSION/community" >> /etc/apk/repositories

echo "当前镜像源配置:"
cat /etc/apk/repositories

# 测试网络连接
echo "测试网络连接..."
if ping -c 1 \$MIRROR > /dev/null 2>&1; then
    echo "✅ 网络连接正常"
else
    echo "⚠️  网络连接可能有问题，但继续测试..."
fi

# 测试更新和安装
echo "测试包索引更新..."
start_time=\$(date +%s)
if apk update; then
    end_time=\$(date +%s)
    update_duration=\$((end_time - start_time))
    echo "✅ 包索引更新成功，耗时: \${update_duration}秒"

    echo "测试包安装..."
    start_time=\$(date +%s)
    if apk add --no-cache curl; then
        end_time=\$(date +%s)
        install_duration=\$((end_time - start_time))
        echo "✅ curl包安装成功，耗时: \${install_duration}秒"
        echo "✅ Alpine镜像源优化测试完成"
        echo "总耗时: \$((update_duration + install_duration))秒"
    else
        echo "❌ curl包安装失败"
        exit 1
    fi
else
    echo "❌ 包索引更新失败"
    echo "尝试恢复原始配置..."
    mv /etc/apk/repositories.backup /etc/apk/repositories
    echo "原始配置:"
    cat /etc/apk/repositories
    echo "使用原始配置重试..."
    if apk update; then
        echo "✅ 原始配置可用"
    else
        echo "❌ 原始配置也失败"
    fi
    exit 1
fi
EOF

    chmod +x test_alpine_in_container.sh

    # 在Alpine容器中运行测试（增加详细输出）
    log_info "启动Alpine容器进行测试..."
    if docker run --rm -v "$(pwd)/test_alpine_in_container.sh:/test.sh" alpine:3.18 sh /test.sh; then
        log_success "Alpine容器测试完成"
        return 0
    else
        log_error "Alpine容器测试失败"

        # 提供故障排除信息
        echo
        log_info "故障排除建议:"
        echo "1. 检查网络连接: ping $selected_mirror"
        echo "2. 检查Docker网络: docker network ls"
        echo "3. 尝试手动测试: docker run --rm -it alpine:3.18 sh"
        echo "4. 检查DNS解析: nslookup $selected_mirror"

        return 1
    fi

    # 清理测试脚本
    rm -f test_alpine_in_container.sh
}

# 测试Alpine构建速度
test_alpine_build() {
    local test_type="simple"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                test_type="build"
                shift
                ;;
            --mirrors)
                test_type="mirrors"
                shift
                ;;
            --simple)
                test_type="simple"
                shift
                ;;
            *)
                log_error "未知测试参数: $1"
                return 1
                ;;
        esac
    done
    
    log_info "开始Alpine构建速度测试..."
    
    case "$test_type" in
        "build")
            test_nginx_build_speed
            ;;
        "mirrors")
            test_mirror_speeds
            ;;
        "simple")
            test_in_container "auto"
            ;;
        *)
            log_error "未知测试类型: $test_type"
            return 1
            ;;
    esac
}

# 测试nginx构建速度
test_nginx_build_speed() {
    log_info "测试nginx构建速度对比..."
    
    # 创建优化Dockerfile
    cat > test_nginx_optimized.dockerfile <<EOF
FROM nginx:1.24-alpine

# 配置阿里云Alpine镜像源
RUN ALPINE_VERSION=\$(cat /etc/alpine-release) && \\
    echo "https://mirrors.aliyun.com/alpine/\$ALPINE_VERSION/main" > /etc/apk/repositories && \\
    echo "https://mirrors.aliyun.com/alpine/\$ALPINE_VERSION/community" >> /etc/apk/repositories && \\
    apk update

# 安装包
RUN apk add --no-cache curl wget openssl ca-certificates

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
    
    # 测试优化构建
    log_info "测试优化构建速度..."
    local start_time=$(date +%s)
    if docker build -f test_nginx_optimized.dockerfile -t test-nginx-optimized . > /dev/null 2>&1; then
        local end_time=$(date +%s)
        local optimized_time=$((end_time - start_time))
        log_success "优化构建耗时: ${optimized_time}秒"
        docker rmi test-nginx-optimized > /dev/null 2>&1 || true
    else
        log_error "优化构建失败"
    fi
    
    # 清理测试文件
    rm test_nginx_optimized.dockerfile
}

# 测试镜像源速度
test_mirror_speeds() {
    log_info "测试不同镜像源速度..."
    
    local mirrors=(
        "mirrors.aliyun.com|阿里云镜像源"
        "mirrors.ustc.edu.cn|中科大镜像源"
        "mirrors.tuna.tsinghua.edu.cn|清华镜像源"
        "dl-cdn.alpinelinux.org|官方镜像源"
    )
    
    for mirror_info in "${mirrors[@]}"; do
        local mirror=$(echo "$mirror_info" | cut -d'|' -f1)
        local description=$(echo "$mirror_info" | cut -d'|' -f2)
        
        log_info "测试 $description ($mirror)..."
        
        local start_time=$(date +%s)
        if timeout 10 curl -s -I "https://$mirror/alpine/v3.18/main/x86_64/APKINDEX.tar.gz" > /dev/null 2>&1; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log_success "$description 响应时间: ${duration}秒"
        else
            log_warning "$description 连接失败"
        fi
    done
}

# 验证Alpine优化
verify_alpine() {
    log_info "验证Alpine优化效果..."
    
    # 检查配置文件
    local files=(
        "nginx/Dockerfile.proxy"
        "nginx/Dockerfile.proxy.alpine"
        "docker-compose.aliyun.yml"
    )
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            log_success "✅ $file 存在"
            
            if grep -q "mirrors.aliyun.com" "$file" 2>/dev/null; then
                log_success "  包含阿里云镜像源配置"
            else
                log_warning "  未包含阿里云镜像源配置"
            fi
        else
            log_error "❌ $file 不存在"
        fi
    done
    
    # 测试容器中的优化效果
    test_in_container "mirrors.aliyun.com"
}

# 恢复原始配置
restore_alpine() {
    log_info "恢复Alpine原始配置..."
    
    if [ -f /etc/apk/repositories.backup ]; then
        mv /etc/apk/repositories.backup /etc/apk/repositories
        log_success "已恢复原始配置"
        
        if apk update; then
            log_success "包索引更新成功"
        fi
    else
        log_warning "备份文件不存在"
    fi
}

# 主函数
main() {
    echo "🔧 Alpine Linux镜像源优化工具"
    echo "==============================="
    echo
    
    if [ $# -eq 0 ]; then
        show_help
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        optimize)
            optimize_alpine "$@"
            ;;
        test)
            test_alpine_build "$@"
            ;;
        verify)
            verify_alpine
            ;;
        restore)
            restore_alpine
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
