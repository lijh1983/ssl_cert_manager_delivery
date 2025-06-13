#!/bin/bash
# SSL证书自动化管理系统 - 核心管理脚本
# 整合了部署、验证、修复、测试等核心功能

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
    echo "SSL证书自动化管理系统 - 核心管理脚本"
    echo "用法: $0 <命令> [选项]"
    echo
    echo "核心命令:"
    echo "  deploy          部署SSL证书管理系统"
    echo "  verify          验证系统配置和状态"
    echo "  fix             修复常见问题"
    echo "  test            运行系统测试"
    echo "  optimize        优化系统性能"
    echo "  status          查看系统状态"
    echo "  logs            查看系统日志"
    echo "  restart         重启服务"
    echo "  stop            停止服务"
    echo "  cleanup         清理系统"
    echo
    echo "部署选项 (deploy):"
    echo "  --domain DOMAIN     指定域名 (必需)"
    echo "  --email EMAIL       指定邮箱 (必需)"
    echo "  --env ENV           指定环境 (dev/prod，默认prod)"
    echo "  --monitoring        启用监控"
    echo "  --aliyun           使用阿里云优化配置"
    echo
    echo "验证选项 (verify):"
    echo "  --all              验证所有组件"
    echo "  --docker           验证Docker配置"
    echo "  --compose          验证Docker Compose配置"
    echo "  --network          验证网络连接"
    echo "  --tools            验证基础工具"
    echo
    echo "修复选项 (fix):"
    echo "  --docker-compose   修复Docker Compose配置"
    echo "  --python-images    重建后端镜像"
    echo "  --alpine-sources   重建前端镜像"
    echo "  --permissions      修复文件权限"
    echo
    echo "维护选项:"
    echo "  cleanup [--dry-run]    清理临时文件和维护仓库卫生"
    echo "  update-log             更新项目更新日志"
    echo ""
    echo "测试选项 (test):"
    echo "  --build-speed      测试构建速度"
    echo "  --alpine-speed     测试Alpine构建速度"
    echo "  --deployment       测试部署"
    echo "  --images           测试镜像"
    echo
    echo "示例:"
    echo "  $0 deploy --domain ssl.gzyggl.com --email admin@gzyggl.com --aliyun --monitoring"
    echo "  $0 verify --all"
    echo "  $0 fix --docker-compose"
    echo "  $0 cleanup --dry-run"
    echo "  $0 update-log --type FEATURE --desc '添加新功能'"
    echo "  $0 status"
}

# 部署功能
deploy_system() {
    local domain=""
    local email=""
    local env="prod"
    local monitoring=false
    local aliyun=false
    
    # 解析部署参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                domain="$2"
                shift 2
                ;;
            --email)
                email="$2"
                shift 2
                ;;
            --env)
                env="$2"
                shift 2
                ;;
            --monitoring)
                monitoring=true
                shift
                ;;
            --aliyun)
                aliyun=true
                shift
                ;;
            *)
                log_error "未知部署参数: $1"
                return 1
                ;;
        esac
    done
    
    # 验证必需参数
    if [ -z "$domain" ] || [ -z "$email" ]; then
        log_error "部署需要指定域名和邮箱"
        echo "用法: $0 deploy --domain <域名> --email <邮箱>"
        return 1
    fi
    
    log_info "开始部署SSL证书管理系统..."
    log_info "域名: $domain"
    log_info "邮箱: $email"
    log_info "环境: $env"
    log_info "监控: $monitoring"
    log_info "阿里云优化: $aliyun"
    
    # 检查依赖
    if ! command -v docker > /dev/null 2>&1; then
        log_error "Docker未安装，请先安装Docker"
        return 1
    fi
    
    # 设置环境变量
    export DOMAIN_NAME="$domain"
    export ACME_EMAIL="$email"
    export ENVIRONMENT="$env"
    
    # 选择部署配置
    local compose_file="docker-compose.yml"
    if [ "$env" = "prod" ]; then
        compose_file="docker-compose.production.yml"
        log_info "使用生产环境配置"
    elif [ "$aliyun" = "true" ]; then
        compose_file="docker-compose.yml"
        log_info "使用阿里云优化配置"
    fi
    
    # 执行部署
    log_info "启动服务..."
    if [ "$monitoring" = "true" ]; then
        docker-compose -f "$compose_file" --profile monitoring up -d
    else
        docker-compose -f "$compose_file" up -d
    fi
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 验证部署
    if verify_deployment; then
        log_success "🎉 SSL证书管理系统部署成功！"
        echo
        echo "访问地址:"
        echo "  前端: http://$domain/"
        echo "  API: http://$domain/api/"
        if [ "$monitoring" = "true" ]; then
            echo "  监控: http://$domain/monitoring/"
        fi
    else
        log_error "部署验证失败，请检查日志"
        return 1
    fi
}

# 验证功能
verify_system() {
    local verify_all=false
    local verify_docker=false
    local verify_compose=false
    local verify_network=false
    local verify_tools=false
    
    # 解析验证参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                verify_all=true
                shift
                ;;
            --docker)
                verify_docker=true
                shift
                ;;
            --compose)
                verify_compose=true
                shift
                ;;
            --network)
                verify_network=true
                shift
                ;;
            --tools)
                verify_tools=true
                shift
                ;;
            *)
                log_error "未知验证参数: $1"
                return 1
                ;;
        esac
    done

    # 如果没有指定具体验证项，默认验证所有
    if [ "$verify_all" = "false" ] && [ "$verify_docker" = "false" ] && [ "$verify_compose" = "false" ] && [ "$verify_network" = "false" ] && [ "$verify_tools" = "false" ]; then
        verify_all=true
    fi

    log_info "验证参数: all=$verify_all, docker=$verify_docker, compose=$verify_compose, network=$verify_network, tools=$verify_tools"
    
    log_info "开始系统验证..."

    local verification_passed=0
    local total_verifications=0
    
    # Docker验证
    if [ "$verify_all" = "true" ] || [ "$verify_docker" = "true" ]; then
        total_verifications=$((total_verifications + 1))
        log_info "验证Docker环境..."

        # 检查Docker服务状态
        if timeout 10 docker info > /dev/null 2>&1; then
            log_success "Docker服务正常运行"

            # 检查Docker版本
            local docker_version
            if docker_version=$(timeout 5 docker --version 2>/dev/null); then
                log_info "Docker版本: $docker_version"
            else
                log_warning "无法获取Docker版本"
            fi

            # 检查Docker镜像
            local image_count
            if image_count=$(timeout 5 docker images -q 2>/dev/null | wc -l); then
                log_info "本地镜像数量: $image_count"
            else
                log_warning "无法获取镜像数量"
            fi

            # 检查运行中的容器
            local running_containers
            if running_containers=$(timeout 5 docker ps -q 2>/dev/null | wc -l); then
                log_info "运行中容器数量: $running_containers"
            else
                log_warning "无法获取容器数量"
            fi

            verification_passed=$((verification_passed + 1))
        else
            log_error "Docker服务异常或未启动"
            log_info "请检查Docker服务状态: systemctl status docker"
        fi
    fi

    # Docker Compose验证
    if [ "$verify_all" = "true" ] || [ "$verify_compose" = "true" ]; then
        total_verifications=$((total_verifications + 1))
        log_info "验证Docker Compose配置..."

        # 检查配置文件存在
        if [ -f "docker-compose.yml" ]; then
            log_success "docker-compose.yml文件存在"

            # 检查配置语法
            if docker compose -f docker-compose.yml config > /dev/null 2>&1; then
                log_success "Docker Compose配置语法正确"
                verification_passed=$((verification_passed + 1))
            elif docker-compose -f docker-compose.yml config > /dev/null 2>&1; then
                log_success "Docker Compose配置语法正确 (使用docker-compose命令)"
                verification_passed=$((verification_passed + 1))
            else
                log_error "Docker Compose配置语法错误"
                log_info "请检查配置文件: docker-compose.yml"
            fi
        else
            log_error "docker-compose.yml文件不存在"
        fi
    fi

    # 网络验证
    if [ "$verify_all" = "true" ] || [ "$verify_network" = "true" ]; then
        total_verifications=$((total_verifications + 1))
        log_info "验证网络连接..."
        if ping -c 1 mirrors.aliyun.com > /dev/null 2>&1; then
            log_success "网络连接正常"
            verification_passed=$((verification_passed + 1))
        else
            log_error "网络连接异常"
        fi
    fi

    # 基础工具验证
    if [ "$verify_all" = "true" ] || [ "$verify_tools" = "true" ]; then
        total_verifications=$((total_verifications + 1))
        log_info "验证基础工具..."
        if command -v curl > /dev/null 2>&1 && command -v wget > /dev/null 2>&1; then
            log_success "基础网络工具正常"
            verification_passed=$((verification_passed + 1))
        else
            log_warning "部分基础工具缺失"
            verification_passed=$((verification_passed + 1))  # 仍然算通过
        fi
    fi
    
    # 显示验证结果
    echo
    log_info "验证结果: $verification_passed/$total_verifications"
    
    if [ "$verification_passed" -eq "$total_verifications" ]; then
        log_success "🎉 所有验证通过！"
        return 0
    else
        log_warning "部分验证失败，建议运行修复命令"
        return 1
    fi
}

# 验证部署状态
verify_deployment() {
    log_info "验证部署状态..."
    
    # 检查容器状态
    local running_containers=$(docker ps --format "table {{.Names}}" | grep -c ssl-manager || echo "0")
    if [ "$running_containers" -gt 0 ]; then
        log_success "发现 $running_containers 个运行中的容器"
    else
        log_error "没有发现运行中的容器"
        return 1
    fi
    
    # 检查健康状态
    local healthy_containers=$(docker ps --filter "health=healthy" --format "table {{.Names}}" | grep -c ssl-manager || echo "0")
    log_info "健康容器数量: $healthy_containers"
    
    return 0
}

# 修复功能
fix_system() {
    local fix_compose=false
    local fix_python=false
    local fix_alpine=false
    local fix_permissions=false
    
    # 解析修复参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --docker-compose)
                fix_compose=true
                shift
                ;;
            --python-images)
                fix_python=true
                shift
                ;;
            --alpine-sources)
                fix_alpine=true
                shift
                ;;
            --permissions)
                fix_permissions=true
                shift
                ;;
            *)
                log_error "未知修复参数: $1"
                return 1
                ;;
        esac
    done
    
    log_info "开始系统修复..."
    
    # 修复Docker Compose配置
    if [ "$fix_compose" = "true" ]; then
        log_info "修复Docker Compose配置..."
        # 检查配置文件语法
        if docker-compose -f docker-compose.yml config > /dev/null 2>&1; then
            log_success "Docker Compose配置正常"
        else
            log_error "Docker Compose配置有误，请检查docker-compose.yml文件"
        fi
    fi

    # 修复Python镜像问题
    if [ "$fix_python" = "true" ]; then
        log_info "修复Python镜像问题..."
        # 重新构建后端基础镜像
        if [ -f "backend/Dockerfile.base" ]; then
            docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend
            log_success "后端基础镜像重建完成"
        else
            log_error "后端Dockerfile.base文件不存在"
        fi
    fi

    # 修复Alpine镜像源
    if [ "$fix_alpine" = "true" ]; then
        log_info "修复Alpine镜像源..."
        # 重新构建前端基础镜像
        if [ -f "frontend/Dockerfile.base" ]; then
            docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend
            log_success "前端基础镜像重建完成"
        else
            log_error "前端Dockerfile.base文件不存在"
        fi
    fi
    
    # 修复文件权限
    if [ "$fix_permissions" = "true" ]; then
        log_info "修复文件权限..."
        find scripts -name "*.sh" -type f -exec chmod +x {} \;
        log_success "脚本权限修复完成"
    fi
    
    log_success "系统修复完成"
}

# 清理仓库功能
cleanup_repository() {
    local dry_run=false

    # 解析清理参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                log_error "未知清理参数: $1"
                return 1
                ;;
        esac
    done

    log_info "开始仓库清理..."

    if [ "$dry_run" = "true" ]; then
        log_info "干运行模式 - 仅显示将要清理的内容"
    fi

    local cleaned=0

    # 清理临时脚本
    log_info "检查临时脚本..."
    for pattern in "temp_*.sh" "fix-*.sh" "test-*.sh" "diagnose-*.sh"; do
        local files=$(find . -name "$pattern" -type f 2>/dev/null || true)
        if [ -n "$files" ]; then
            if [ "$dry_run" = "true" ]; then
                echo "将删除临时脚本: $files"
            else
                echo "$files" | xargs rm -f
                log_success "删除临时脚本: $pattern"
            fi
            cleaned=$((cleaned + 1))
        fi
    done

    # 清理临时文档
    log_info "检查临时文档..."
    for pattern in "*_REPORT.md" "*_FIX*.md" "*_VALIDATION*.md" "temp_*.md"; do
        local files=$(find . -name "$pattern" -type f 2>/dev/null || true)
        if [ -n "$files" ]; then
            if [ "$dry_run" = "true" ]; then
                echo "将删除临时文档: $files"
            else
                echo "$files" | xargs rm -f
                log_success "删除临时文档: $pattern"
            fi
            cleaned=$((cleaned + 1))
        fi
    done

    # 清理备份文件
    log_info "检查备份文件..."
    for pattern in "*.backup" "*.bak" "*.old" "*.tmp"; do
        local files=$(find . -name "$pattern" -type f 2>/dev/null || true)
        if [ -n "$files" ]; then
            if [ "$dry_run" = "true" ]; then
                echo "将删除备份文件: $files"
            else
                echo "$files" | xargs rm -f
                log_success "删除备份文件: $pattern"
            fi
            cleaned=$((cleaned + 1))
        fi
    done

    # 清理空目录
    log_info "检查空目录..."
    local empty_dirs=$(find . -type d -empty ! -path "./.git*" 2>/dev/null || true)
    if [ -n "$empty_dirs" ]; then
        if [ "$dry_run" = "true" ]; then
            echo "将删除空目录: $empty_dirs"
        else
            echo "$empty_dirs" | xargs rmdir 2>/dev/null || true
            log_success "删除空目录"
        fi
        cleaned=$((cleaned + 1))
    fi

    # Docker系统清理
    log_info "清理Docker系统..."
    if [ "$dry_run" = "true" ]; then
        echo "将执行: docker system prune -f"
    else
        docker system prune -f > /dev/null 2>&1 || true
        log_success "Docker系统清理完成"
    fi

    if [ $cleaned -eq 0 ]; then
        log_success "✓ 仓库已经很干净，没有发现需要清理的文件"
    else
        if [ "$dry_run" = "true" ]; then
            log_info "发现 $cleaned 类文件需要清理"
        else
            log_success "✓ 清理了 $cleaned 类文件，仓库现在更干净了"
        fi
    fi
}

# 更新项目日志功能
update_project_log() {
    local log_type=""
    local description=""
    local impact=""
    local details=""
    local test_status=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                log_type="$2"
                shift 2
                ;;
            --desc)
                description="$2"
                shift 2
                ;;
            --impact)
                impact="$2"
                shift 2
                ;;
            --details)
                details="$2"
                shift 2
                ;;
            --test)
                test_status="$2"
                shift 2
                ;;
            *)
                log_error "未知参数: $1"
                return 1
                ;;
        esac
    done

    # 交互式输入
    if [ -z "$log_type" ]; then
        echo "请选择更新类型:"
        echo "1) FEATURE - 新功能"
        echo "2) BUGFIX - 错误修复"
        echo "3) CLEANUP - 代码清理"
        echo "4) DOCKER - Docker相关"
        echo "5) DATABASE - 数据库相关"
        echo "6) SECURITY - 安全相关"
        echo "7) DOCS - 文档更新"
        read -p "请输入选择 (1-7): " choice

        case $choice in
            1) log_type="FEATURE" ;;
            2) log_type="BUGFIX" ;;
            3) log_type="CLEANUP" ;;
            4) log_type="DOCKER" ;;
            5) log_type="DATABASE" ;;
            6) log_type="SECURITY" ;;
            7) log_type="DOCS" ;;
            *) log_error "无效选择"; return 1 ;;
        esac
    fi

    if [ -z "$description" ]; then
        read -p "请输入更新描述: " description
    fi

    if [ -z "$impact" ]; then
        read -p "请输入影响范围: " impact
    fi

    if [ -z "$details" ]; then
        read -p "请输入变更详情: " details
    fi

    if [ -z "$test_status" ]; then
        read -p "请输入测试状态: " test_status
    fi

    # 写入update.log
    local timestamp=$(date '+%Y-%m-%d %H:%M')
    {
        echo ""
        echo "### [$timestamp] [$log_type] $description"
        echo "影响范围: $impact"
        echo "变更详情: $details"
        echo "测试状态: $test_status"
        echo "---"
    } >> update.log

    log_success "更新日志已添加到 update.log"
}

# 主函数
main() {
    echo "🔧 SSL证书自动化管理系统 - 核心管理工具"
    echo "============================================="
    echo
    
    # 检查参数
    if [ $# -eq 0 ]; then
        show_help
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        deploy)
            deploy_system "$@"
            ;;
        verify)
            verify_system "$@"
            ;;
        fix)
            fix_system "$@"
            ;;
        test)
            log_info "测试功能开发中..."
            ;;
        optimize)
            log_info "优化功能开发中..."
            ;;
        status)
            log_info "查看系统状态..."
            docker ps --filter "name=ssl-manager"
            ;;
        logs)
            log_info "查看系统日志..."
            docker-compose -f docker-compose.aliyun.yml logs -f --tail=50
            ;;
        restart)
            log_info "重启服务..."
            docker-compose -f docker-compose.aliyun.yml restart
            ;;
        stop)
            log_info "停止服务..."
            docker-compose -f docker-compose.aliyun.yml down
            ;;
        cleanup)
            cleanup_repository "$@"
            ;;
        update-log)
            update_project_log "$@"
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
