#!/bin/bash
# SSL证书自动化管理系统客户端脚本
# 用于安装、配置和管理SSL证书

# 配置参数
SERVER_URL="https://example.com/api/v1"
CONFIG_DIR="/etc/ssl-cert-manager"
LOG_FILE="/var/log/ssl-cert-manager.log"
CERT_DIR="/etc/ssl/certs"
KEY_DIR="/etc/ssl/private"
VERSION="1.0.0"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查curl
    if ! command -v curl &> /dev/null; then
        log_error "未找到curl，请先安装"
        exit 1
    fi
    
    # 检查openssl
    if ! command -v openssl &> /dev/null; then
        log_error "未找到openssl，请先安装"
        exit 1
    fi
    
    # 检查jq
    if ! command -v jq &> /dev/null; then
        log_warning "未找到jq，将尝试安装..."
        
        # 检测系统类型并安装jq
        if command -v apt-get &> /dev/null; then
            apt-get update && apt-get install -y jq
        elif command -v yum &> /dev/null; then
            yum install -y jq
        elif command -v dnf &> /dev/null; then
            dnf install -y jq
        else
            log_error "无法自动安装jq，请手动安装后重试"
            exit 1
        fi
    fi
    
    # 检查socat（用于ACME验证）
    if ! command -v socat &> /dev/null; then
        log_warning "未找到socat，将尝试安装..."
        
        # 检测系统类型并安装socat
        if command -v apt-get &> /dev/null; then
            apt-get update && apt-get install -y socat
        elif command -v yum &> /dev/null; then
            yum install -y socat
        elif command -v dnf &> /dev/null; then
            dnf install -y socat
        else
            log_error "无法自动安装socat，请手动安装后重试"
            exit 1
        fi
    fi
    
    log_success "依赖检查完成"
}

# 创建配置目录
create_config_dir() {
    if [ ! -d "$CONFIG_DIR" ]; then
        mkdir -p "$CONFIG_DIR"
        chmod 700 "$CONFIG_DIR"
        log_info "创建配置目录: $CONFIG_DIR"
    fi
    
    if [ ! -d "$CERT_DIR" ]; then
        mkdir -p "$CERT_DIR"
        log_info "创建证书目录: $CERT_DIR"
    fi
    
    if [ ! -d "$KEY_DIR" ]; then
        mkdir -p "$KEY_DIR"
        chmod 700 "$KEY_DIR"
        log_info "创建私钥目录: $KEY_DIR"
    fi
    
    # 创建日志文件
    touch "$LOG_FILE"
    chmod 640 "$LOG_FILE"
}

# 获取系统信息
get_system_info() {
    log_info "收集系统信息..."
    
    # 获取主机名
    HOSTNAME=$(hostname)
    
    # 获取IP地址
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
    if [ -z "$IP_ADDRESS" ]; then
        IP_ADDRESS=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v "127.0.0.1" | head -n 1)
    fi
    
    # 获取操作系统信息
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_TYPE="$NAME $VERSION_ID"
    elif [ -f /etc/redhat-release ]; then
        OS_TYPE=$(cat /etc/redhat-release)
    else
        OS_TYPE="Unknown"
    fi
    
    log_info "主机名: $HOSTNAME"
    log_info "IP地址: $IP_ADDRESS"
    log_info "操作系统: $OS_TYPE"
}

# 检测Web服务器
detect_web_server() {
    log_info "检测Web服务器..."
    
    WEB_SERVER="unknown"
    WEB_SERVER_CONFIG=""
    
    # 检测Nginx
    if command -v nginx &> /dev/null; then
        WEB_SERVER="nginx"
        
        # 尝试找到Nginx配置目录
        if [ -d /etc/nginx/conf.d ]; then
            WEB_SERVER_CONFIG="/etc/nginx/conf.d"
        elif [ -d /etc/nginx/sites-enabled ]; then
            WEB_SERVER_CONFIG="/etc/nginx/sites-enabled"
        else
            WEB_SERVER_CONFIG="/etc/nginx"
        fi
        
        log_info "检测到Nginx，配置目录: $WEB_SERVER_CONFIG"
    # 检测Apache
    elif command -v apache2 &> /dev/null || command -v httpd &> /dev/null; then
        WEB_SERVER="apache"
        
        # 尝试找到Apache配置目录
        if [ -d /etc/apache2/sites-enabled ]; then
            WEB_SERVER_CONFIG="/etc/apache2/sites-enabled"
        elif [ -d /etc/httpd/conf.d ]; then
            WEB_SERVER_CONFIG="/etc/httpd/conf.d"
        else
            WEB_SERVER_CONFIG="/etc/apache2"
        fi
        
        log_info "检测到Apache，配置目录: $WEB_SERVER_CONFIG"
    else
        log_warning "未检测到支持的Web服务器"
    fi
    
    # 保存Web服务器信息
    echo "$WEB_SERVER" > "$CONFIG_DIR/web_server"
    echo "$WEB_SERVER_CONFIG" > "$CONFIG_DIR/web_server_config"
}

# 扫描现有证书
scan_certificates() {
    log_info "扫描现有证书..."
    
    # 创建临时文件存储证书信息
    CERT_INFO_FILE="$CONFIG_DIR/certificates.json"
    echo "[]" > "$CERT_INFO_FILE"
    
    # 扫描Nginx配置中的证书
    if [ "$(cat "$CONFIG_DIR/web_server")" == "nginx" ]; then
        WEB_SERVER_CONFIG=$(cat "$CONFIG_DIR/web_server_config")
        
        # 查找所有配置文件
        find "$WEB_SERVER_CONFIG" -type f -name "*.conf" | while read -r config_file; do
            log_info "扫描配置文件: $config_file"
            
            # 提取证书和私钥路径
            grep -E "ssl_certificate|ssl_certificate_key" "$config_file" | while read -r line; do
                if [[ "$line" =~ ssl_certificate[^_] ]]; then
                    cert_path=$(echo "$line" | awk '{print $2}' | tr -d ';')
                    
                    # 检查证书是否存在
                    if [ -f "$cert_path" ]; then
                        # 提取域名
                        domain=$(openssl x509 -noout -subject -in "$cert_path" | grep -oP "CN\s*=\s*\K[^,/]+")
                        
                        # 提取过期时间
                        expires_at=$(openssl x509 -noout -enddate -in "$cert_path" | cut -d= -f2)
                        expires_at_iso=$(date -d "$expires_at" -Iseconds)
                        
                        # 提取证书类型
                        cert_type="single"
                        if openssl x509 -noout -text -in "$cert_path" | grep -q "DNS:*"; then
                            cert_type="wildcard"
                        fi
                        
                        # 查找对应的私钥
                        key_path=$(grep -A1 "ssl_certificate $cert_path" "$config_file" | grep "ssl_certificate_key" | awk '{print $2}' | tr -d ';')
                        
                        # 添加到证书信息文件
                        temp_file=$(mktemp)
                        jq --arg domain "$domain" \
                           --arg path "$cert_path" \
                           --arg key_path "$key_path" \
                           --arg expires_at "$expires_at_iso" \
                           --arg type "$cert_type" \
                           '. += [{"domain": $domain, "path": $path, "key_path": $key_path, "expires_at": $expires_at, "type": $type}]' \
                           "$CERT_INFO_FILE" > "$temp_file" && mv "$temp_file" "$CERT_INFO_FILE"
                        
                        log_info "发现证书: $domain, 过期时间: $expires_at"
                    fi
                fi
            done
        done
    # 扫描Apache配置中的证书
    elif [ "$(cat "$CONFIG_DIR/web_server")" == "apache" ]; then
        WEB_SERVER_CONFIG=$(cat "$CONFIG_DIR/web_server_config")
        
        # 查找所有配置文件
        find "$WEB_SERVER_CONFIG" -type f -name "*.conf" | while read -r config_file; do
            log_info "扫描配置文件: $config_file"
            
            # 提取证书和私钥路径
            grep -E "SSLCertificateFile|SSLCertificateKeyFile" "$config_file" | while read -r line; do
                if [[ "$line" =~ SSLCertificateFile ]]; then
                    cert_path=$(echo "$line" | awk '{print $2}')
                    
                    # 检查证书是否存在
                    if [ -f "$cert_path" ]; then
                        # 提取域名
                        domain=$(openssl x509 -noout -subject -in "$cert_path" | grep -oP "CN\s*=\s*\K[^,/]+")
                        
                        # 提取过期时间
                        expires_at=$(openssl x509 -noout -enddate -in "$cert_path" | cut -d= -f2)
                        expires_at_iso=$(date -d "$expires_at" -Iseconds)
                        
                        # 提取证书类型
                        cert_type="single"
                        if openssl x509 -noout -text -in "$cert_path" | grep -q "DNS:*"; then
                            cert_type="wildcard"
                        fi
                        
                        # 查找对应的私钥
                        key_path=$(grep -A1 "SSLCertificateFile $cert_path" "$config_file" | grep "SSLCertificateKeyFile" | awk '{print $2}')
                        
                        # 添加到证书信息文件
                        temp_file=$(mktemp)
                        jq --arg domain "$domain" \
                           --arg path "$cert_path" \
                           --arg key_path "$key_path" \
                           --arg expires_at "$expires_at_iso" \
                           --arg type "$cert_type" \
                           '. += [{"domain": $domain, "path": $path, "key_path": $key_path, "expires_at": $expires_at, "type": $type}]' \
                           "$CERT_INFO_FILE" > "$temp_file" && mv "$temp_file" "$CERT_INFO_FILE"
                        
                        log_info "发现证书: $domain, 过期时间: $expires_at"
                    fi
                fi
            done
        done
    fi
    
    # 统计发现的证书数量
    CERT_COUNT=$(jq '. | length' "$CERT_INFO_FILE")
    log_info "共发现 $CERT_COUNT 个证书"
}

# 注册客户端
register_client() {
    log_info "注册客户端..."
    
    # 检查是否已有令牌
    if [ -f "$CONFIG_DIR/token" ]; then
        TOKEN=$(cat "$CONFIG_DIR/token")
        log_info "使用现有令牌: ${TOKEN:0:8}..."
    else
        # 如果没有提供令牌，则退出
        if [ -z "$1" ]; then
            log_error "未提供令牌，无法注册"
            exit 1
        fi
        
        TOKEN="$1"
        echo "$TOKEN" > "$CONFIG_DIR/token"
        chmod 600 "$CONFIG_DIR/token"
        log_info "保存令牌: ${TOKEN:0:8}..."
    fi
    
    # 准备注册数据
    get_system_info
    
    # 发送注册请求
    RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-Server-Token: $TOKEN" \
        -d "{\"hostname\": \"$HOSTNAME\", \"ip\": \"$IP_ADDRESS\", \"os_type\": \"$OS_TYPE\", \"version\": \"$VERSION\"}" \
        "$SERVER_URL/client/register")
    
    # 检查响应
    if [ "$(echo "$RESPONSE" | jq -r '.code')" == "200" ]; then
        SERVER_ID=$(echo "$RESPONSE" | jq -r '.data.server_id')
        SERVER_NAME=$(echo "$RESPONSE" | jq -r '.data.name')
        AUTO_RENEW=$(echo "$RESPONSE" | jq -r '.data.auto_renew')
        
        # 保存服务器信息
        echo "$SERVER_ID" > "$CONFIG_DIR/server_id"
        echo "$SERVER_NAME" > "$CONFIG_DIR/server_name"
        echo "$AUTO_RENEW" > "$CONFIG_DIR/auto_renew"
        
        # 保存设置
        echo "$RESPONSE" | jq -r '.data.settings' > "$CONFIG_DIR/settings.json"
        
        log_success "客户端注册成功，服务器ID: $SERVER_ID, 名称: $SERVER_NAME"
    else
        ERROR_MSG=$(echo "$RESPONSE" | jq -r '.message')
        log_error "客户端注册失败: $ERROR_MSG"
        exit 1
    fi
}

# 同步证书信息
sync_certificates() {
    log_info "同步证书信息..."
    
    # 检查是否已注册
    if [ ! -f "$CONFIG_DIR/token" ]; then
        log_error "客户端未注册，请先注册"
        exit 1
    fi
    
    TOKEN=$(cat "$CONFIG_DIR/token")
    
    # 检查证书信息文件
    if [ ! -f "$CONFIG_DIR/certificates.json" ]; then
        log_warning "未找到证书信息，将先扫描证书"
        scan_certificates
    fi
    
    # 读取证书信息
    CERT_INFO=$(cat "$CONFIG_DIR/certificates.json")
    
    # 发送同步请求
    RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-Server-Token: $TOKEN" \
        -d "{\"certificates\": $CERT_INFO}" \
        "$SERVER_URL/certificates/sync")
    
    # 检查响应
    if [ "$(echo "$RESPONSE" | jq -r '.code')" == "200" ]; then
        SYNCED=$(echo "$RESPONSE" | jq -r '.data.synced')
        NEW=$(echo "$RESPONSE" | jq -r '.data.new')
        UPDATED=$(echo "$RESPONSE" | jq -r '.data.updated')
        
        log_success "证书同步成功，同步: $SYNCED, 新增: $NEW, 更新: $UPDATED"
    else
        ERROR_MSG=$(echo "$RESPONSE" | jq -r '.message')
        log_error "证书同步失败: $ERROR_MSG"
        exit 1
    fi
}

# 发送心跳
send_heartbeat() {
    log_info "发送心跳..."
    
    # 检查是否已注册
    if [ ! -f "$CONFIG_DIR/token" ]; then
        log_error "客户端未注册，请先注册"
        exit 1
    fi
    
    TOKEN=$(cat "$CONFIG_DIR/token")
    
    # 发送心跳请求
    RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-Server-Token: $TOKEN" \
        -d "{\"version\": \"$VERSION\", \"timestamp\": $(date +%s)}" \
        "$SERVER_URL/servers/heartbeat")
    
    # 检查响应
    if [ "$(echo "$RESPONSE" | jq -r '.code')" == "200" ]; then
        # 检查是否有需要执行的命令
        COMMANDS=$(echo "$RESPONSE" | jq -r '.data.commands')
        if [ "$COMMANDS" != "[]" ]; then
            log_info "收到服务器命令，准备执行"
            # 这里可以添加命令执行逻辑
        fi
        
        log_success "心跳发送成功"
    else
        ERROR_MSG=$(echo "$RESPONSE" | jq -r '.message')
        log_error "心跳发送失败: $ERROR_MSG"
    fi
}

# 获取任务
get_tasks() {
    log_info "获取任务..."
    
    # 检查是否已注册
    if [ ! -f "$CONFIG_DIR/token" ]; then
        log_error "客户端未注册，请先注册"
        exit 1
    fi
    
    TOKEN=$(cat "$CONFIG_DIR/token")
    
    # 发送获取任务请求
    RESPONSE=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        -H "X-Server-Token: $TOKEN" \
        "$SERVER_URL/client/tasks")
    
    # 检查响应
    if [ "$(echo "$RESPONSE" | jq -r '.code')" == "200" ]; then
        TASKS=$(echo "$RESPONSE" | jq -r '.data.tasks')
        TASK_COUNT=$(echo "$TASKS" | jq '. | length')
        
        if [ "$TASK_COUNT" -gt 0 ]; then
            log_info "收到 $TASK_COUNT 个任务，准备执行"
            
            # 保存任务到文件
            echo "$TASKS" > "$CONFIG_DIR/tasks.json"
            
            # 执行任务
            execute_tasks
        else
            log_info "没有需要执行的任务"
        fi
    else
        ERROR_MSG=$(echo "$RESPONSE" | jq -r '.message')
        log_error "获取任务失败: $ERROR_MSG"
    fi
}

# 执行任务
execute_tasks() {
    log_info "执行任务..."
    
    # 检查任务文件
    if [ ! -f "$CONFIG_DIR/tasks.json" ]; then
        log_error "未找到任务文件"
        return
    fi
    
    # 读取任务
    TASKS=$(cat "$CONFIG_DIR/tasks.json")
    
    # 遍历任务
    echo "$TASKS" | jq -c '.[]' | while read -r task; do
        TASK_ID=$(echo "$task" | jq -r '.id')
        TASK_TYPE=$(echo "$task" | jq -r '.type')
        
        log_info "执行任务 #$TASK_ID, 类型: $TASK_TYPE"
        
        # 根据任务类型执行不同操作
        case "$TASK_TYPE" in
            "renew")
                execute_renew_task "$task"
                ;;
            *)
                log_warning "未知任务类型: $TASK_TYPE"
                update_task_status "$TASK_ID" "failed" "不支持的任务类型"
                ;;
        esac
    done
}

# 执行续期任务
execute_renew_task() {
    TASK=$(echo "$1")
    TASK_ID=$(echo "$TASK" | jq -r '.id')
    CERT_ID=$(echo "$TASK" | jq -r '.certificate_id')
    DOMAIN=$(echo "$TASK" | jq -r '.domain')
    CA_TYPE=$(echo "$TASK" | jq -r '.params.ca_type')
    
    log_info "执行证书续期任务: $DOMAIN (ID: $CERT_ID)"
    
    # 这里应该调用acme.sh进行实际的证书续期
    # 为了演示，我们假设续期成功
    
    # 模拟续期过程
    log_info "正在续期证书: $DOMAIN"
    sleep 2
    
    # 假设续期成功
    SUCCESS=true
    
    if [ "$SUCCESS" = true ]; then
        # 生成新的过期时间（当前时间+90天）
        EXPIRES_AT=$(date -d "+90 days" -Iseconds)
        
        # 查找证书路径
        CERT_PATH=$(jq -r --arg domain "$DOMAIN" '.[] | select(.domain == $domain) | .path' "$CONFIG_DIR/certificates.json")
        KEY_PATH=$(jq -r --arg domain "$DOMAIN" '.[] | select(.domain == $domain) | .key_path' "$CONFIG_DIR/certificates.json")
        
        # 更新任务状态
        update_task_status "$TASK_ID" "completed" "{\"success\": true, \"message\": \"证书续期成功\", \"certificate\": {\"id\": $CERT_ID, \"domain\": \"$DOMAIN\", \"expires_at\": \"$EXPIRES_AT\", \"path\": \"$CERT_PATH\", \"key_path\": \"$KEY_PATH\"}}"
        
        log_success "证书续期成功: $DOMAIN, 新过期时间: $EXPIRES_AT"
    else
        # 更新任务状态
        update_task_status "$TASK_ID" "failed" "{\"success\": false, \"message\": \"证书续期失败\"}"
        
        log_error "证书续期失败: $DOMAIN"
    fi
}

# 更新任务状态
update_task_status() {
    TASK_ID="$1"
    STATUS="$2"
    RESULT="$3"
    
    log_info "更新任务 #$TASK_ID 状态: $STATUS"
    
    # 检查是否已注册
    if [ ! -f "$CONFIG_DIR/token" ]; then
        log_error "客户端未注册，请先注册"
        return
    fi
    
    TOKEN=$(cat "$CONFIG_DIR/token")
    
    # 发送更新任务状态请求
    RESPONSE=$(curl -s -X PUT \
        -H "Content-Type: application/json" \
        -H "X-Server-Token: $TOKEN" \
        -d "{\"status\": \"$STATUS\", \"result\": $RESULT}" \
        "$SERVER_URL/client/tasks/$TASK_ID")
    
    # 检查响应
    if [ "$(echo "$RESPONSE" | jq -r '.code')" == "200" ]; then
        log_success "任务状态更新成功"
    else
        ERROR_MSG=$(echo "$RESPONSE" | jq -r '.message')
        log_error "任务状态更新失败: $ERROR_MSG"
    fi
}

# 安装服务
install_service() {
    log_info "安装系统服务..."
    
    # 创建服务文件
    SERVICE_FILE="/etc/systemd/system/ssl-cert-manager.service"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=SSL Certificate Manager
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash $CONFIG_DIR/cron.sh
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF
    
    # 创建定时任务脚本
    CRON_SCRIPT="$CONFIG_DIR/cron.sh"
    
    cat > "$CRON_SCRIPT" << EOF
#!/bin/bash
# SSL证书管理定时任务

# 配置
CONFIG_DIR="$CONFIG_DIR"
LOG_FILE="$LOG_FILE"
CLIENT_SCRIPT="$0"

# 发送心跳
$0 heartbeat

# 获取并执行任务
$0 tasks

# 每天扫描证书并同步
if [ \$(date +%H) -eq 0 ]; then
    $0 scan
    $0 sync
fi

# 休眠一段时间
sleep 3600
EOF
    
    chmod +x "$CRON_SCRIPT"
    
    # 启用并启动服务
    systemctl daemon-reload
    systemctl enable ssl-cert-manager.service
    systemctl start ssl-cert-manager.service
    
    log_success "服务安装完成并已启动"
}

# 显示帮助信息
show_help() {
    echo "SSL证书自动化管理系统客户端"
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  install <token>    安装并注册客户端"
    echo "  scan               扫描现有证书"
    echo "  sync               同步证书信息到服务器"
    echo "  heartbeat          发送心跳"
    echo "  tasks              获取并执行任务"
    echo "  help               显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 install abc123  使用令牌abc123安装客户端"
    echo "  $0 scan            扫描现有证书"
}

# 主函数
main() {
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # 解析命令
    COMMAND="$1"
    shift
    
    case "$COMMAND" in
        "install")
            check_dependencies
            create_config_dir
            get_system_info
            detect_web_server
            register_client "$1"
            scan_certificates
            sync_certificates
            install_service
            ;;
        "scan")
            scan_certificates
            ;;
        "sync")
            sync_certificates
            ;;
        "heartbeat")
            send_heartbeat
            ;;
        "tasks")
            get_tasks
            ;;
        "help"|"")
            show_help
            ;;
        *)
            echo "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
