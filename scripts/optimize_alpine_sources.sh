#!/bin/bash
# Alpine Linux镜像源优化脚本

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

# 检测Alpine版本
detect_alpine_version() {
    if [ -f /etc/alpine-release ]; then
        cat /etc/alpine-release
    else
        echo "v3.18"  # 默认版本
    fi
}

# 测试镜像源速度
test_mirror_speed() {
    local mirror=$1
    local version=$2

    log_info "测试镜像源: $mirror"

    local start_time=$(date +%s)
    if timeout 10 wget -q --spider "https://$mirror/alpine/$version/main/x86_64/APKINDEX.tar.gz" 2>/dev/null || \
       timeout 10 curl -s -I "https://$mirror/alpine/$version/main/x86_64/APKINDEX.tar.gz" > /dev/null 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "$mirror 响应时间: ${duration}秒"
        echo $duration
    else
        log_warning "$mirror 连接失败"
        echo 9999
    fi
}

# 选择最快的镜像源
select_fastest_mirror() {
    local version=$(detect_alpine_version)
    log_info "检测到Alpine版本: $version"
    
    # 候选镜像源
    local mirrors=(
        "mirrors.aliyun.com"
        "mirrors.ustc.edu.cn"
        "mirrors.tuna.tsinghua.edu.cn"
        "dl-cdn.alpinelinux.org"
    )
    
    local fastest_mirror=""
    local fastest_time=9999
    
    for mirror in "${mirrors[@]}"; do
        local time=$(test_mirror_speed "$mirror" "$version")
        if [ "$time" -lt "$fastest_time" ]; then
            fastest_time=$time
            fastest_mirror=$mirror
        fi
    done
    
    if [ -n "$fastest_mirror" ]; then
        log_success "选择最快镜像源: $fastest_mirror (${fastest_time}ms)"
        echo "$fastest_mirror"
    else
        log_warning "所有镜像源测试失败，使用默认源"
        echo "dl-cdn.alpinelinux.org"
    fi
}

# 配置Alpine镜像源
configure_alpine_sources() {
    local mirror=${1:-$(select_fastest_mirror)}
    local version=$(detect_alpine_version)
    
    log_info "配置Alpine镜像源: $mirror"
    
    # 备份原始配置
    if [ -f /etc/apk/repositories ]; then
        cp /etc/apk/repositories /etc/apk/repositories.backup
        log_info "已备份原始配置: /etc/apk/repositories.backup"
    fi
    
    # 配置新的镜像源
    cat > /etc/apk/repositories <<EOF
https://$mirror/alpine/$version/main
https://$mirror/alpine/$version/community
EOF
    
    log_success "Alpine镜像源配置完成"
    
    # 显示配置内容
    log_info "当前配置的镜像源:"
    cat /etc/apk/repositories
    
    # 更新包索引
    log_info "更新包索引..."
    if apk update; then
        log_success "包索引更新成功"
        return 0
    else
        log_error "包索引更新失败，恢复备份"
        if [ -f /etc/apk/repositories.backup ]; then
            mv /etc/apk/repositories.backup /etc/apk/repositories
            log_info "已恢复原始配置"
        fi
        return 1
    fi
}

# 测试包安装速度
test_package_install_speed() {
    log_info "测试包安装速度..."
    
    # 测试安装curl包
    local start_time=$(date +%s)
    
    if apk add --no-cache curl > /dev/null 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "curl包安装耗时: ${duration}秒"
        
        # 清理测试包
        apk del curl > /dev/null 2>&1 || true
        
        return 0
    else
        log_error "curl包安装失败"
        return 1
    fi
}

# 生成镜像源配置脚本
generate_config_script() {
    local mirror=$1
    local version=$2
    
    log_info "生成镜像源配置脚本..."
    
    cat > configure_alpine_mirror.sh <<EOF
#!/bin/sh
# Alpine镜像源配置脚本 - 自动生成
# 生成时间: $(date)
# 优化镜像源: $mirror
# Alpine版本: $version

set -e

echo "配置Alpine镜像源: $mirror"

# 备份原始配置
if [ -f /etc/apk/repositories ]; then
    cp /etc/apk/repositories /etc/apk/repositories.backup
fi

# 配置镜像源
cat > /etc/apk/repositories <<'REPOS'
https://$mirror/alpine/$version/main
https://$mirror/alpine/$version/community
REPOS

# 更新包索引
echo "更新包索引..."
apk update

echo "Alpine镜像源配置完成"
EOF
    
    chmod +x configure_alpine_mirror.sh
    log_success "配置脚本已生成: configure_alpine_mirror.sh"
}

# 显示优化结果
show_optimization_result() {
    local mirror=$1
    local version=$2
    
    echo
    log_success "🎉 Alpine镜像源优化完成！"
    echo
    echo "=== 优化详情 ==="
    echo "✅ Alpine版本: $version"
    echo "✅ 选择镜像源: $mirror"
    echo "✅ 配置文件: /etc/apk/repositories"
    echo "✅ 备份文件: /etc/apk/repositories.backup"
    echo
    echo "=== 使用方法 ==="
    echo "现在可以使用以下命令快速安装包:"
    echo "  apk add --no-cache <package_name>"
    echo
    echo "常用包安装示例:"
    echo "  apk add --no-cache curl wget bash"
    echo "  apk add --no-cache openssl ca-certificates"
    echo "  apk add --no-cache tzdata"
    echo
    echo "=== 验证命令 ==="
    echo "检查配置: cat /etc/apk/repositories"
    echo "更新索引: apk update"
    echo "搜索包:   apk search curl"
    echo "安装测试: time apk add --no-cache curl"
    echo
    echo "=== 恢复方法 ==="
    echo "如需恢复原始配置:"
    echo "  mv /etc/apk/repositories.backup /etc/apk/repositories"
    echo "  apk update"
    echo
}

# 显示帮助信息
show_help() {
    echo "Alpine Linux镜像源优化脚本"
    echo "用法: $0 [选项] [镜像源]"
    echo
    echo "选项:"
    echo "  --auto          自动选择最快的镜像源"
    echo "  --test          仅测试镜像源速度，不修改配置"
    echo "  --restore       恢复原始配置"
    echo "  --generate      生成配置脚本"
    echo "  --help          显示帮助信息"
    echo
    echo "镜像源选项:"
    echo "  aliyun          阿里云镜像源 (mirrors.aliyun.com)"
    echo "  ustc            中科大镜像源 (mirrors.ustc.edu.cn)"
    echo "  tuna            清华镜像源 (mirrors.tuna.tsinghua.edu.cn)"
    echo "  official        官方镜像源 (dl-cdn.alpinelinux.org)"
    echo
    echo "示例:"
    echo "  $0 --auto                    # 自动选择最快镜像源"
    echo "  $0 aliyun                    # 使用阿里云镜像源"
    echo "  $0 --test                    # 测试所有镜像源速度"
    echo "  $0 --restore                 # 恢复原始配置"
}

# 恢复原始配置
restore_original_config() {
    log_info "恢复原始Alpine镜像源配置..."
    
    if [ -f /etc/apk/repositories.backup ]; then
        mv /etc/apk/repositories.backup /etc/apk/repositories
        log_success "已恢复原始配置"
        
        # 更新包索引
        if apk update; then
            log_success "包索引更新成功"
        else
            log_warning "包索引更新失败"
        fi
    else
        log_error "备份文件不存在: /etc/apk/repositories.backup"
        return 1
    fi
}

# 主函数
main() {
    echo "🔧 Alpine Linux镜像源优化工具"
    echo "==============================="
    echo
    
    # 检查是否为Alpine系统
    if [ ! -f /etc/alpine-release ]; then
        log_error "当前系统不是Alpine Linux"
        exit 1
    fi
    
    # 解析命令行参数
    case "${1:-}" in
        --auto)
            configure_alpine_sources
            ;;
        --test)
            local version=$(detect_alpine_version)
            log_info "测试所有镜像源速度..."
            select_fastest_mirror
            ;;
        --restore)
            restore_original_config
            ;;
        --generate)
            local mirror=$(select_fastest_mirror)
            local version=$(detect_alpine_version)
            generate_config_script "$mirror" "$version"
            ;;
        --help|-h)
            show_help
            ;;
        aliyun)
            configure_alpine_sources "mirrors.aliyun.com"
            ;;
        ustc)
            configure_alpine_sources "mirrors.ustc.edu.cn"
            ;;
        tuna)
            configure_alpine_sources "mirrors.tuna.tsinghua.edu.cn"
            ;;
        official)
            configure_alpine_sources "dl-cdn.alpinelinux.org"
            ;;
        "")
            # 默认自动选择
            configure_alpine_sources
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
    
    # 如果配置成功，显示结果
    if [ $? -eq 0 ] && [ "${1:-}" != "--test" ] && [ "${1:-}" != "--help" ] && [ "${1:-}" != "--restore" ]; then
        local version=$(detect_alpine_version)
        local current_mirror=$(head -1 /etc/apk/repositories | sed 's|https://||' | sed 's|/alpine/.*||')
        
        # 测试安装速度
        test_package_install_speed
        
        # 生成配置脚本
        generate_config_script "$current_mirror" "$version"
        
        # 显示结果
        show_optimization_result "$current_mirror" "$version"
    fi
}

# 执行主函数
main "$@"
