#!/bin/bash
# SSL证书管理系统后端 - Docker入口脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [[ "${LOG_LEVEL}" == "DEBUG" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# 显示启动信息
show_banner() {
    echo "=================================================="
    echo "SSL证书管理系统后端服务"
    echo "版本: $(cat /app/version.txt | grep VERSION | cut -d'=' -f2)"
    echo "构建时间: $(cat /app/version.txt | grep BUILD_DATE | cut -d'=' -f2)"
    echo "实例ID: ${INSTANCE_ID:-backend}"
    echo "环境: ${FLASK_ENV:-production}"
    echo "=================================================="
}

# 等待MySQL数据库就绪
wait_for_mysql() {
    log_info "等待MySQL数据库连接..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python3 -c "
import sys
sys.path.append('/app/src')
from models.database import DatabaseConfig, test_connection
try:
    if test_connection():
        print('MySQL连接成功')
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    print(f'MySQL连接失败: {e}')
    sys.exit(1)
" 2>/dev/null; then
            log_info "MySQL数据库连接成功"
            return 0
        fi
        
        log_warn "MySQL连接失败，重试 $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    log_error "MySQL数据库连接超时"
    return 1
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."
    
    python3 -c "
import sys
sys.path.append('/app/src')
from models.database import init_db
try:
    init_db()
    print('数据库初始化成功')
except Exception as e:
    print(f'数据库初始化失败: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_info "数据库初始化完成"
    else
        log_error "数据库初始化失败"
        exit 1
    fi
}

# 检查配置
check_config() {
    log_info "检查配置..."
    
    # 检查必需的环境变量
    required_vars=(
        "MYSQL_HOST"
        "MYSQL_USERNAME"
        "MYSQL_PASSWORD"
        "MYSQL_DATABASE"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "缺少必需的环境变量: $var"
            exit 1
        fi
    done
    
    # 检查密钥长度
    if [ ${#SECRET_KEY} -lt 32 ]; then
        log_warn "SECRET_KEY长度不足32位，建议使用更长的密钥"
    fi
    
    if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
        log_warn "JWT_SECRET_KEY长度不足32位，建议使用更长的密钥"
    fi
    
    log_info "配置检查完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p /app/logs
    mkdir -p /app/certs
    mkdir -p /app/temp
    
    # 设置权限
    chmod 755 /app/logs
    chmod 700 /app/certs
    chmod 755 /app/temp
    
    log_info "目录创建完成"
}

# 设置日志配置
setup_logging() {
    log_info "配置日志..."
    
    # 创建日志配置文件
    cat > /app/logging.conf << EOF
[loggers]
keys=root,ssl_manager

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter,detailedFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_ssl_manager]
level=${LOG_LEVEL:-INFO}
handlers=consoleHandler,fileHandler
qualname=ssl_manager
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=${LOG_LEVEL:-INFO}
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=handlers.RotatingFileHandler
level=${LOG_LEVEL:-INFO}
formatter=detailedFormatter
args=('${LOG_FILE:-/app/logs/ssl_manager.log}', 'a', 10485760, 5)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s

[formatter_detailedFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s
EOF
    
    log_info "日志配置完成"
}

# 运行数据库迁移
run_migrations() {
    log_info "检查数据库迁移..."
    
    # 这里可以添加数据库迁移逻辑
    # python3 -c "from migrations import run_migrations; run_migrations()"
    
    log_info "数据库迁移检查完成"
}

# 启动前检查
pre_start_checks() {
    log_info "执行启动前检查..."
    
    # 检查Python模块
    python3 -c "
import sys
sys.path.append('/app/src')
try:
    import app
    print('应用模块导入成功')
except Exception as e:
    print(f'应用模块导入失败: {e}')
    sys.exit(1)
"
    
    if [ $? -ne 0 ]; then
        log_error "应用模块检查失败"
        exit 1
    fi
    
    # 检查端口
    if netstat -tuln | grep -q ":5000 "; then
        log_warn "端口5000已被占用"
    fi
    
    log_info "启动前检查完成"
}

# 信号处理
cleanup() {
    log_info "接收到停止信号，正在清理..."
    
    # 停止后台进程
    if [ ! -z "$GUNICORN_PID" ]; then
        kill -TERM $GUNICORN_PID 2>/dev/null || true
        wait $GUNICORN_PID 2>/dev/null || true
    fi
    
    log_info "清理完成"
    exit 0
}

# 设置信号处理
trap cleanup SIGTERM SIGINT

# 主函数
main() {
    show_banner
    
    # 执行初始化步骤
    check_config
    create_directories
    setup_logging
    
    # 等待依赖服务
    wait_for_mysql
    
    # 初始化数据库
    if [ "${SKIP_DB_INIT:-false}" != "true" ]; then
        init_database
    fi
    
    # 运行迁移
    if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
        run_migrations
    fi
    
    # 启动前检查
    pre_start_checks
    
    log_info "启动应用服务..."
    
    # 执行传入的命令
    if [ $# -eq 0 ]; then
        log_error "未指定启动命令"
        exit 1
    fi
    
    # 启动应用
    exec "$@" &
    GUNICORN_PID=$!
    
    log_info "应用服务已启动 (PID: $GUNICORN_PID)"
    
    # 等待进程结束
    wait $GUNICORN_PID
}

# 如果直接运行此脚本
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
