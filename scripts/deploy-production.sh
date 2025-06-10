#!/bin/bash

# SSL证书管理器生产环境智能部署脚本
# 基于实际生产环境部署经验编写，支持配置保护和模块化部署
# 版本: 2.0
# 更新时间: 2025-01-10

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 全局变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"
ENV_BACKUP_FILE="$PROJECT_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
DOCKER_CONFIG_FILE="/etc/docker/daemon.json"
DOCKER_CONFIG_BACKUP="/etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)"

# 命令行参数
FORCE_OVERWRITE=false
SKIP_BUILD=false
ONLY_BUILD=false
SKIP_ENV_SETUP=false
INTERACTIVE_MODE=false
SKIP_DOCKER_CONFIG=false
SKIP_SYSTEM_CHECK=false

# 日志函数
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

log_debug() {
    echo -e "${CYAN}[DEBUG]${NC} $1"
}

log_prompt() {
    echo -e "${PURPLE}[PROMPT]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
SSL证书管理器生产环境智能部署脚本 v2.0

用法: $0 [选项]

选项:
  -h, --help              显示此帮助信息
  -f, --force-overwrite   强制覆盖现有配置文件
  -i, --interactive       交互式部署模式
  --skip-build           跳过Docker镜像构建步骤
  --only-build           仅执行Docker镜像构建
  --skip-env-setup       跳过环境变量配置
  --skip-docker-config   跳过Docker配置修改
  --skip-system-check    跳过系统要求检查

示例:
  $0                     # 标准部署
  $0 -i                  # 交互式部署
  $0 --skip-build        # 跳过镜像构建
  $0 --only-build        # 仅构建镜像
  $0 -f                  # 强制覆盖配置

EOF
}

# 解析命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--force-overwrite)
                FORCE_OVERWRITE=true
                shift
                ;;
            -i|--interactive)
                INTERACTIVE_MODE=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --only-build)
                ONLY_BUILD=true
                shift
                ;;
            --skip-env-setup)
                SKIP_ENV_SETUP=true
                shift
                ;;
            --skip-docker-config)
                SKIP_DOCKER_CONFIG=true
                shift
                ;;
            --skip-system-check)
                SKIP_SYSTEM_CHECK=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 交互式确认函数
confirm_action() {
    local message="$1"
    local default="${2:-n}"

    if [[ "$INTERACTIVE_MODE" == "false" ]]; then
        return 0
    fi

    while true; do
        if [[ "$default" == "y" ]]; then
            read -p "$message [Y/n]: " response
            response=${response:-y}
        else
            read -p "$message [y/N]: " response
            response=${response:-n}
        fi

        case $response in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "请输入 y 或 n";;
        esac
    done
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        exit 1
    fi
}

# 备份文件函数
backup_file() {
    local file_path="$1"
    local backup_path="$2"

    if [[ -f "$file_path" ]]; then
        log_info "备份文件: $file_path -> $backup_path"
        cp "$file_path" "$backup_path"
        return 0
    fi
    return 1
}

# 检查配置文件是否存在并处理
check_and_handle_env_file() {
    if [[ -f "$ENV_FILE" ]]; then
        log_warning "检测到现有的环境配置文件: $ENV_FILE"

        if [[ "$FORCE_OVERWRITE" == "true" ]]; then
            log_info "强制覆盖模式，备份现有配置..."
            backup_file "$ENV_FILE" "$ENV_BACKUP_FILE"
            return 0
        fi

        log_prompt "现有配置文件处理选项:"
        echo "  1) 保留现有配置 (推荐)"
        echo "  2) 备份并创建新配置"
        echo "  3) 合并配置 (保留现有值，添加缺失项)"
        echo "  4) 查看现有配置内容"

        while true; do
            read -p "请选择 [1-4]: " choice
            case $choice in
                1)
                    log_success "保留现有环境配置"
                    return 1
                    ;;
                2)
                    log_info "备份现有配置并创建新配置..."
                    backup_file "$ENV_FILE" "$ENV_BACKUP_FILE"
                    return 0
                    ;;
                3)
                    log_info "合并配置模式..."
                    merge_env_config
                    return 1
                    ;;
                4)
                    log_info "当前环境配置内容:"
                    echo "----------------------------------------"
                    cat "$ENV_FILE"
                    echo "----------------------------------------"
                    ;;
                *)
                    echo "请输入 1-4 之间的数字"
                    ;;
            esac
        done
    fi
    return 0
}

# 合并环境配置
merge_env_config() {
    local temp_env="/tmp/ssl_manager_env_new.tmp"

    log_info "生成新的环境配置模板..."
    generate_env_template "$temp_env"

    log_info "合并配置文件..."
    backup_file "$ENV_FILE" "$ENV_BACKUP_FILE"

    # 读取现有配置
    declare -A existing_config
    while IFS='=' read -r key value; do
        # 跳过注释和空行
        [[ $key =~ ^[[:space:]]*# ]] && continue
        [[ -z $key ]] && continue
        existing_config["$key"]="$value"
    done < "$ENV_FILE"

    # 合并配置
    {
        echo "# SSL证书管理器环境配置文件"
        echo "# 合并时间: $(date)"
        echo "# 备份文件: $ENV_BACKUP_FILE"
        echo ""

        while IFS='=' read -r key value; do
            if [[ $key =~ ^[[:space:]]*# ]] || [[ -z $key ]]; then
                echo "$key=$value"
            elif [[ -n "${existing_config[$key]}" ]]; then
                echo "$key=${existing_config[$key]}"
                log_debug "保留现有配置: $key=${existing_config[$key]}"
            else
                echo "$key=$value"
                log_debug "添加新配置: $key=$value"
            fi
        done < "$temp_env"
    } > "$ENV_FILE"

    rm -f "$temp_env"
    log_success "配置合并完成"
}

# 生成环境配置模板
generate_env_template() {
    local output_file="$1"

    cat > "$output_file" <<EOF
# 基础配置
DOMAIN_NAME=ssl.gzyggl.com
EMAIL=19822088@qq.com
ENVIRONMENT=production

# 数据库配置
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=$(openssl rand -base64 32)
DB_PORT="5432"

# Redis配置
REDIS_PASSWORD=$(openssl rand -base64 32)
REDIS_PORT="6379"

# 安全配置
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)

# API配置
VITE_API_BASE_URL=/api
BACKEND_WORKERS=2
LOG_LEVEL=INFO

# 监控配置
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 16)
PROMETHEUS_PORT=9090

# 功能开关
ENABLE_METRICS=true
ENABLE_MONITORING=true

# Let's Encrypt SSL证书配置
ACME_EMAIL=19822088@qq.com
ACME_DIRECTORY_URL=https://acme-v02.api.letsencrypt.org/directory
ACME_AGREE_TOS=true
ACME_CHALLENGE_TYPE=http-01
EOF
}

# 环境差异检测
detect_environment_differences() {
    log_info "检测系统环境差异..."

    local env_report="/tmp/ssl_manager_env_report.txt"
    {
        echo "=== SSL证书管理器环境兼容性报告 ==="
        echo "生成时间: $(date)"
        echo ""

        echo "=== 操作系统信息 ==="
        cat /etc/os-release
        echo ""

        echo "=== 内核信息 ==="
        uname -a
        echo ""

        echo "=== 内存信息 ==="
        free -h
        echo ""

        echo "=== 磁盘信息 ==="
        df -h
        echo ""

        echo "=== Docker信息 ==="
        if command -v docker &> /dev/null; then
            docker --version
            docker system info | grep -E "(Cgroup|Storage|Runtime)"
        else
            echo "Docker未安装"
        fi
        echo ""

        echo "=== cgroup信息 ==="
        mount | grep cgroup
        echo ""

        echo "=== 网络信息 ==="
        ip addr show | grep -E "(inet|mtu)" | head -5
        echo ""

    } > "$env_report"

    log_success "环境报告生成完成: $env_report"

    # 检查关键兼容性问题
    check_compatibility_issues
}

# 检查兼容性问题
check_compatibility_issues() {
    local issues_found=false

    log_info "检查关键兼容性问题..."

    # 检查操作系统
    if ! grep -q "Ubuntu 22.04" /etc/os-release; then
        log_warning "推荐使用Ubuntu 22.04.5 LTS，当前系统可能存在兼容性问题"
        issues_found=true
    fi

    # 检查cgroup v2 (cAdvisor已移除，但保留检查用于其他监控服务)
    if ! mount | grep -q "cgroup2"; then
        log_warning "系统不支持cgroup v2，部分监控功能可能受限"
        log_info "建议: 在/etc/default/grub中添加: systemd.unified_cgroup_hierarchy=1"
        # 不再作为错误，因为cAdvisor已移除
    fi

    # 检查Docker版本
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        local major_version=$(echo "$docker_version" | cut -d. -f1)
        local minor_version=$(echo "$docker_version" | cut -d. -f2)

        if [[ $major_version -lt 26 ]] || [[ $major_version -eq 26 && $minor_version -lt 1 ]]; then
            log_warning "Docker版本 $docker_version 可能存在兼容性问题，推荐使用 26.1.3+"
            issues_found=true
        fi
    fi

    # 检查内存
    local memory_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $memory_gb -lt 8 ]]; then
        log_error "内存不足！需要至少8GB内存，推荐16GB"
        issues_found=true
    fi

    if [[ "$issues_found" == "true" ]]; then
        log_warning "发现兼容性问题，建议查看环境报告并解决问题后再继续"
        if [[ "$INTERACTIVE_MODE" == "true" ]]; then
            if ! confirm_action "是否继续部署？"; then
                log_info "用户选择退出部署"
                exit 0
            fi
        fi
    else
        log_success "环境兼容性检查通过"
    fi
}

# 检查系统要求
check_system_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if ! grep -q "Ubuntu 22.04" /etc/os-release; then
        log_warning "推荐使用Ubuntu 22.04.5 LTS，当前系统可能存在兼容性问题"
    fi
    
    # 检查内存
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$MEMORY_GB" -lt 8 ]; then
        log_error "内存不足！需要至少8GB内存，推荐16GB"
        exit 1
    fi
    
    # 检查磁盘空间
    DISK_SPACE=$(df / | awk 'NR==2 {print $4}')
    if [ "$DISK_SPACE" -lt 20971520 ]; then  # 20GB in KB
        log_error "磁盘空间不足！需要至少20GB可用空间"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 检查cgroup v2支持 (cAdvisor已移除，保留检查用于系统兼容性)
check_cgroup_v2() {
    log_info "检查cgroup v2支持..."

    if ! mount | grep -q "cgroup2"; then
        log_warning "系统不支持cgroup v2，部分监控功能可能受限"
        log_info "建议: 在/etc/default/grub中添加: systemd.unified_cgroup_hierarchy=1"
        log_info "然后执行: sudo update-grub && sudo reboot"
        # 不再强制退出，因为cAdvisor已移除
    else
        log_success "cgroup v2支持检查通过"
    fi
}

# 智能Docker安装
install_docker() {
    log_info "检查Docker安装状态..."

    if ! command -v docker &> /dev/null; then
        if [[ "$INTERACTIVE_MODE" == "true" ]]; then
            if ! confirm_action "Docker未安装，是否自动安装？" "y"; then
                log_error "Docker是必需的，无法继续部署"
                exit 1
            fi
        fi

        log_info "开始安装Docker..."
        install_docker_engine
    else
        log_info "Docker已安装"

        # 检查Docker版本兼容性
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        log_info "当前Docker版本: $docker_version"

        local major_version=$(echo "$docker_version" | cut -d. -f1)
        local minor_version=$(echo "$docker_version" | cut -d. -f2)

        if [[ $major_version -lt 26 ]] || [[ $major_version -eq 26 && $minor_version -lt 1 ]]; then
            log_warning "Docker版本较旧，推荐升级到26.1.3+"
            if [[ "$INTERACTIVE_MODE" == "true" ]]; then
                if confirm_action "是否升级Docker？"; then
                    install_docker_engine
                fi
            fi
        fi
    fi

    # 验证Docker配置
    verify_docker_installation
}

# Docker引擎安装
install_docker_engine() {
    log_info "安装Docker引擎..."

    # 卸载旧版本
    sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # 安装依赖
    sudo apt update
    sudo apt install -y ca-certificates curl gnupg lsb-release

    # 添加Docker官方GPG密钥
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # 添加Docker仓库
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # 配置用户权限
    sudo usermod -aG docker $USER

    log_success "Docker安装完成"
    log_warning "请注意：可能需要重新登录以使Docker用户组权限生效"
}

# 验证Docker安装
verify_docker_installation() {
    log_info "验证Docker安装..."

    # 检查Docker服务状态
    if ! sudo systemctl is-active --quiet docker; then
        log_info "启动Docker服务..."
        sudo systemctl start docker
        sudo systemctl enable docker
    fi

    # 验证Docker版本
    local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    log_info "Docker版本: $docker_version"

    # 验证Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose未正确安装"
        exit 1
    fi

    local compose_version=$(docker compose version | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    log_info "Docker Compose版本: $compose_version"

    # 验证cgroup v2支持 (cAdvisor已移除，保留检查用于系统兼容性)
    if ! docker system info | grep -q "Cgroup Version: 2"; then
        log_warning "Docker不支持cgroup v2，部分监控功能可能受限"
        # 不再强制确认，因为cAdvisor已移除
    else
        log_success "Docker cgroup v2支持验证通过"
    fi

    log_success "Docker安装验证完成"
}

# 智能Docker配置
configure_docker() {
    if [[ "$SKIP_DOCKER_CONFIG" == "true" ]]; then
        log_info "跳过Docker配置"
        return 0
    fi

    log_info "检查Docker配置..."

    # 检查现有配置
    if [[ -f "$DOCKER_CONFIG_FILE" ]]; then
        log_warning "检测到现有Docker配置文件"

        if [[ "$INTERACTIVE_MODE" == "true" ]]; then
            log_prompt "Docker配置处理选项:"
            echo "  1) 保留现有配置"
            echo "  2) 备份并应用推荐配置"
            echo "  3) 查看现有配置"

            while true; do
                read -p "请选择 [1-3]: " choice
                case $choice in
                    1)
                        log_success "保留现有Docker配置"
                        return 0
                        ;;
                    2)
                        break
                        ;;
                    3)
                        log_info "当前Docker配置:"
                        echo "----------------------------------------"
                        sudo cat "$DOCKER_CONFIG_FILE"
                        echo "----------------------------------------"
                        ;;
                    *)
                        echo "请输入 1-3 之间的数字"
                        ;;
                esac
            done
        elif [[ "$FORCE_OVERWRITE" != "true" ]]; then
            log_info "保留现有Docker配置"
            return 0
        fi

        # 备份现有配置
        log_info "备份现有Docker配置..."
        sudo cp "$DOCKER_CONFIG_FILE" "$DOCKER_CONFIG_BACKUP"
    fi

    log_info "应用推荐的Docker配置..."

    # 生成优化的Docker配置
    generate_docker_config

    # 重启Docker服务
    log_info "重启Docker服务..."
    sudo systemctl restart docker
    sudo systemctl enable docker

    # 验证配置
    sleep 5
    if sudo systemctl is-active --quiet docker; then
        log_success "Docker配置应用成功"
    else
        log_error "Docker配置应用失败，恢复备份配置"
        if [[ -f "$DOCKER_CONFIG_BACKUP" ]]; then
            sudo cp "$DOCKER_CONFIG_BACKUP" "$DOCKER_CONFIG_FILE"
            sudo systemctl restart docker
        fi
        exit 1
    fi
}

# 生成Docker配置
generate_docker_config() {
    sudo mkdir -p /etc/docker

    # 检测系统特性并生成适配的配置
    local cgroup_driver="cgroupfs"
    if systemctl is-active --quiet systemd; then
        cgroup_driver="systemd"
    fi

    cat > /tmp/daemon.json <<EOF
{
  "exec-opts": ["native.cgroupdriver=$cgroup_driver"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ],
  "data-root": "/var/lib/docker",
  "live-restore": true,
  "userland-proxy": false,
  "experimental": false
}
EOF

    sudo mv /tmp/daemon.json "$DOCKER_CONFIG_FILE"
    log_debug "Docker配置已生成，使用cgroup驱动: $cgroup_driver"
}

# 创建数据目录
create_data_directories() {
    log_info "创建数据目录..."
    
    # 创建目录结构
    sudo mkdir -p /opt/ssl-manager/{data,logs,certs,backups}
    sudo mkdir -p /opt/ssl-manager/data/{postgres,redis,prometheus,grafana}
    
    # 设置权限
    sudo chown -R $USER:$USER /opt/ssl-manager
    sudo chown -R 70:70 /opt/ssl-manager/data/postgres      # PostgreSQL
    sudo chown -R 472:472 /opt/ssl-manager/data/grafana     # Grafana
    sudo chown -R 65534:65534 /opt/ssl-manager/data/prometheus  # Prometheus
    sudo chown -R 999:999 /opt/ssl-manager/data/redis       # Redis
    
    log_success "数据目录创建完成"
}

# 智能环境变量配置
configure_environment() {
    if [[ "$SKIP_ENV_SETUP" == "true" ]]; then
        log_info "跳过环境变量配置"
        return 0
    fi

    log_info "配置环境变量..."

    # 检查并处理现有配置文件
    if ! check_and_handle_env_file; then
        log_info "使用现有环境配置"
        return 0
    fi

    # 创建新的环境配置
    log_info "创建新的环境配置文件..."
    generate_env_template "$ENV_FILE"

    log_success "环境变量配置完成"

    # 显示重要配置信息
    if [[ "$INTERACTIVE_MODE" == "true" ]]; then
        show_env_summary
    fi
}

# 显示环境配置摘要
show_env_summary() {
    log_info "环境配置摘要:"
    echo "----------------------------------------"
    echo "域名: $(grep '^DOMAIN_NAME=' "$ENV_FILE" | cut -d'=' -f2)"
    echo "邮箱: $(grep '^EMAIL=' "$ENV_FILE" | cut -d'=' -f2)"
    echo "数据库用户: $(grep '^DB_USER=' "$ENV_FILE" | cut -d'=' -f2)"
    echo "Grafana用户: $(grep '^GRAFANA_USER=' "$ENV_FILE" | cut -d'=' -f2)"
    echo "Grafana密码: $(grep '^GRAFANA_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2)"
    echo "----------------------------------------"

    if confirm_action "是否需要修改任何配置？"; then
        log_info "请手动编辑 $ENV_FILE 文件"
        if confirm_action "是否现在打开编辑器？"; then
            ${EDITOR:-nano} "$ENV_FILE"
        fi
    fi
}

# 模块化部署服务
deploy_services() {
    if [[ "$ONLY_BUILD" == "true" ]]; then
        build_images_only
        return 0
    fi

    log_info "开始部署生产环境服务..."

    # 切换到项目目录
    cd "$PROJECT_DIR"

    # 构建或拉取镜像
    if [[ "$SKIP_BUILD" != "true" ]]; then
        build_and_pull_images
    else
        log_info "跳过镜像构建步骤"
    fi

    # 启动服务
    start_services

    log_success "服务部署完成"
}

# 仅构建镜像
build_images_only() {
    log_info "仅执行镜像构建..."
    cd "$PROJECT_DIR"

    # 构建自定义镜像
    if [[ -f "docker-compose.yml" ]]; then
        log_info "构建自定义镜像..."
        docker-compose -f docker-compose.yml build
    fi

    # 拉取外部镜像
    log_info "拉取外部镜像..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

    log_success "镜像构建完成"
}

# 构建和拉取镜像
build_and_pull_images() {
    log_info "构建和拉取Docker镜像..."

    # 检查网络连接
    if ! ping -c 1 docker.io &> /dev/null; then
        log_warning "无法连接到Docker Hub，可能影响镜像拉取"
        if [[ "$INTERACTIVE_MODE" == "true" ]]; then
            if ! confirm_action "是否继续？"; then
                exit 1
            fi
        fi
    fi

    # 拉取外部镜像
    log_info "拉取外部镜像..."
    if ! docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull; then
        log_warning "部分镜像拉取失败，尝试使用本地镜像"
    fi

    # 构建自定义镜像
    if [[ -f "docker-compose.yml" ]]; then
        log_info "构建自定义镜像..."
        docker-compose -f docker-compose.yml build
    fi

    log_success "镜像准备完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    # 检查端口占用
    check_port_conflicts

    # 启动服务
    if [[ "$INTERACTIVE_MODE" == "true" ]]; then
        log_prompt "启动模式选择:"
        echo "  1) 启动核心服务 (不包含监控)"
        echo "  2) 启动完整服务 (包含监控)"

        while true; do
            read -p "请选择 [1-2]: " choice
            case $choice in
                1)
                    log_info "启动核心服务..."
                    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d
                    break
                    ;;
                2)
                    log_info "启动完整服务..."
                    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring up -d
                    break
                    ;;
                *)
                    echo "请输入 1 或 2"
                    ;;
            esac
        done
    else
        log_info "启动完整服务..."
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring up -d
    fi

    log_success "服务启动完成"
}

# 检查端口冲突
check_port_conflicts() {
    log_info "检查端口冲突..."

    local ports=(80 443 9090 3000)  # 移除8080端口(cAdvisor已移除)
    local conflicts=()

    for port in "${ports[@]}"; do
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            local process=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | head -1)
            conflicts+=("端口 $port 被占用 (进程: $process)")
        fi
    done

    if [[ ${#conflicts[@]} -gt 0 ]]; then
        log_warning "发现端口冲突:"
        for conflict in "${conflicts[@]}"; do
            echo "  - $conflict"
        done

        if [[ "$INTERACTIVE_MODE" == "true" ]]; then
            if ! confirm_action "是否继续部署？"; then
                exit 1
            fi
        fi
    else
        log_success "端口检查通过"
    fi
}

# 智能部署验证
verify_deployment() {
    if [[ "$ONLY_BUILD" == "true" ]]; then
        log_info "仅构建模式，跳过部署验证"
        return 0
    fi

    log_info "开始部署验证..."

    # 等待服务启动
    wait_for_services

    # 检查服务状态
    check_service_status

    # 验证核心功能
    verify_core_functions

    # 生成验证报告
    generate_verification_report

    log_success "部署验证完成"
}

# 等待服务启动
wait_for_services() {
    log_info "等待服务启动完成..."

    local max_wait=300  # 最大等待5分钟
    local wait_time=0
    local check_interval=10

    while [[ $wait_time -lt $max_wait ]]; do
        local healthy_count=$(docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps | grep -c "healthy\|Up" || true)
        local total_count=$(docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps | grep -c "ssl-manager" || true)

        log_debug "服务状态: $healthy_count/$total_count 健康"

        if [[ $healthy_count -ge 6 ]]; then  # 至少6个服务健康 (cAdvisor已移除)
            log_success "服务启动完成"
            return 0
        fi

        sleep $check_interval
        wait_time=$((wait_time + check_interval))

        if [[ $((wait_time % 30)) -eq 0 ]]; then
            log_info "等待中... ($wait_time/${max_wait}s)"
        fi
    done

    log_warning "服务启动超时，继续验证..."
}

# 检查服务状态
check_service_status() {
    log_info "检查服务状态..."

    cd "$PROJECT_DIR"
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps

    # 检查失败的服务
    local failed_services=$(docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps | grep -E "(Exit|Restarting)" | awk '{print $1}' || true)

    if [[ -n "$failed_services" ]]; then
        log_warning "发现失败的服务:"
        echo "$failed_services"

        if [[ "$INTERACTIVE_MODE" == "true" ]]; then
            if confirm_action "是否查看失败服务的日志？"; then
                for service in $failed_services; do
                    log_info "查看 $service 日志:"
                    docker logs "$service" --tail 20
                    echo "----------------------------------------"
                done
            fi
        fi
    fi
}

# 验证核心功能
verify_core_functions() {
    log_info "验证核心功能..."

    local tests=(
        "curl -f http://localhost/health:Nginx健康检查"
        "curl -f http://localhost/api/health:API健康检查"
        "curl -I http://localhost/:前端页面访问"
    )

    local passed=0
    local total=${#tests[@]}

    for test in "${tests[@]}"; do
        local command=$(echo "$test" | cut -d':' -f1)
        local description=$(echo "$test" | cut -d':' -f2)

        if eval "$command" > /dev/null 2>&1; then
            log_success "$description 通过"
            ((passed++))
        else
            log_error "$description 失败"
        fi
    done

    # 数据库连接检查
    if docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "数据库连接检查通过"
        ((passed++))
        ((total++))
    else
        log_error "数据库连接检查失败"
        ((total++))
    fi

    # Redis连接检查
    if docker exec ssl-manager-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis连接检查通过"
        ((passed++))
        ((total++))
    else
        log_error "Redis连接检查失败"
        ((total++))
    fi

    log_info "功能验证结果: $passed/$total 通过"

    if [[ $passed -lt $total ]]; then
        log_warning "部分功能验证失败，请检查服务状态"
    fi
}

# 生成验证报告
generate_verification_report() {
    local report_file="/tmp/ssl_manager_verification_report.txt"

    {
        echo "=== SSL证书管理器部署验证报告 ==="
        echo "生成时间: $(date)"
        echo ""

        echo "=== 服务状态 ==="
        cd "$PROJECT_DIR"
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps
        echo ""

        echo "=== 系统资源使用 ==="
        docker stats --no-stream
        echo ""

        echo "=== 磁盘使用 ==="
        df -h
        echo ""

        echo "=== 网络端口 ==="
        netstat -tlnp | grep -E ":80|:443|:9090|:3000"  # 移除8080端口(cAdvisor已移除)
        echo ""

    } > "$report_file"

    log_success "验证报告生成: $report_file"
}

# 显示部署信息
show_deployment_info() {
    log_success "🎉 SSL证书管理器生产环境部署成功！"
    echo ""
    echo "访问信息:"
    echo "  前端页面: http://localhost/"
    echo "  API接口: http://localhost/api/"
    echo "  Prometheus: http://localhost/prometheus/"
    echo "  Grafana: http://localhost/grafana/"
    echo "  # cAdvisor已移除 (原因: cgroup v2兼容性问题)"
    echo ""
    echo "管理命令:"
    echo "  查看服务状态: docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps"
    echo "  查看日志: docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring logs -f"
    echo "  停止服务: docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring down"
    echo ""
    echo "数据目录: /opt/ssl-manager/"
    echo "配置文件: .env"
}

# 主函数
main() {
    # 解析命令行参数
    parse_arguments "$@"

    log_info "开始SSL证书管理器生产环境智能部署..."
    log_info "部署模式: $(get_deployment_mode)"

    # 基础检查
    check_root

    # 系统检查
    if [[ "$SKIP_SYSTEM_CHECK" != "true" ]]; then
        check_system_requirements
        detect_environment_differences
    fi

    # 仅构建模式
    if [[ "$ONLY_BUILD" == "true" ]]; then
        deploy_services
        log_success "镜像构建完成！"
        exit 0
    fi

    # Docker安装和配置
    install_docker
    configure_docker

    # 数据目录创建
    create_data_directories

    # 环境变量配置
    configure_environment

    # 服务部署
    deploy_services

    # 部署验证
    verify_deployment

    # 显示部署信息
    show_deployment_info

    log_success "🎉 SSL证书管理器部署完成！"
}

# 获取部署模式描述
get_deployment_mode() {
    local mode="标准部署"

    if [[ "$INTERACTIVE_MODE" == "true" ]]; then
        mode="$mode (交互式)"
    fi

    if [[ "$ONLY_BUILD" == "true" ]]; then
        mode="仅构建镜像"
    elif [[ "$SKIP_BUILD" == "true" ]]; then
        mode="$mode (跳过构建)"
    fi

    if [[ "$SKIP_ENV_SETUP" == "true" ]]; then
        mode="$mode (跳过环境配置)"
    fi

    if [[ "$FORCE_OVERWRITE" == "true" ]]; then
        mode="$mode (强制覆盖)"
    fi

    echo "$mode"
}

# 显示部署信息
show_deployment_info() {
    log_success "🎉 SSL证书管理器生产环境部署成功！"
    echo ""
    echo "📋 部署信息摘要:"
    echo "  部署时间: $(date)"
    echo "  项目目录: $PROJECT_DIR"
    echo "  环境配置: $ENV_FILE"
    echo "  数据目录: /opt/ssl-manager/"
    echo ""
    echo "🌐 服务访问地址:"
    echo "  前端页面: http://localhost/"
    echo "  API接口: http://localhost/api/"
    echo "  API文档: http://localhost/api/docs"
    echo "  Prometheus: http://localhost/prometheus/"
    echo "  Grafana: http://localhost/grafana/"
    echo "  # cAdvisor已移除 (原因: cgroup v2兼容性问题)"
    echo ""
    echo "🔑 登录信息:"
    if [[ -f "$ENV_FILE" ]]; then
        local grafana_user=$(grep '^GRAFANA_USER=' "$ENV_FILE" | cut -d'=' -f2)
        local grafana_pass=$(grep '^GRAFANA_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2)
        echo "  Grafana用户: $grafana_user"
        echo "  Grafana密码: $grafana_pass"
    fi
    echo ""
    echo "🛠️ 管理命令:"
    echo "  查看服务状态:"
    echo "    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps"
    echo ""
    echo "  查看服务日志:"
    echo "    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring logs -f"
    echo ""
    echo "  重启服务:"
    echo "    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring restart"
    echo ""
    echo "  停止服务:"
    echo "    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring down"
    echo ""
    echo "📞 获取帮助:"
    echo "  脚本帮助: $0 --help"
    echo "  部署文档: DEPLOYMENT.md"
    echo "  快速指南: QUICKSTART.md"
    echo ""

    if [[ -f "$ENV_BACKUP_FILE" ]]; then
        echo "💾 配置备份: $ENV_BACKUP_FILE"
    fi

    if [[ -f "$DOCKER_CONFIG_BACKUP" ]]; then
        echo "💾 Docker配置备份: $DOCKER_CONFIG_BACKUP"
    fi

    echo ""
    log_info "部署完成！请访问 http://localhost/ 开始使用SSL证书管理器"
}

# 执行主函数
main "$@"
