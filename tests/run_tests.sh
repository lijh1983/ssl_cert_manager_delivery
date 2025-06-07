#!/bin/bash
# 测试计划执行脚本
# 用于自动化测试SSL证书自动化管理系统的各个组件

# 配置参数
API_URL="http://localhost:5000/api/v1"
TEST_DIR="/home/ubuntu/ssl_project/tests"
REPORT_DIR="$TEST_DIR/reports"
LOG_FILE="$TEST_DIR/test.log"
TEST_TOKEN="test_token_123456"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 创建测试目录
mkdir -p "$REPORT_DIR"

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

# 测试API连接
test_api_connection() {
    log_info "测试API连接..."
    
    response=$(curl -s "$API_URL/auth/login" -w "\n%{http_code}")
    status_code=$(echo "$response" | tail -n1)
    
    if [[ "$status_code" == "400" ]]; then
        log_success "API连接成功，状态码: $status_code"
        return 0
    else
        log_error "API连接失败，状态码: $status_code"
        return 1
    fi
}

# 测试用户认证
test_user_auth() {
    log_info "测试用户认证..."
    
    # 测试登录 - 正确凭据
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' \
        "$API_URL/auth/login")
    
    if [[ $(echo "$response" | jq -r '.code') == "200" ]]; then
        token=$(echo "$response" | jq -r '.data.token')
        log_success "登录成功，获取到token"
        
        # 测试刷新令牌
        refresh_response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            "$API_URL/auth/refresh")
        
        if [[ $(echo "$refresh_response" | jq -r '.code') == "200" ]]; then
            log_success "令牌刷新成功"
        else
            log_error "令牌刷新失败"
        fi
        
        # 测试登出
        logout_response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            "$API_URL/auth/logout")
        
        if [[ $(echo "$logout_response" | jq -r '.code') == "200" ]]; then
            log_success "登出成功"
        else
            log_error "登出失败"
        fi
    else
        log_error "登录失败: $(echo "$response" | jq -r '.message')"
    fi
    
    # 测试登录 - 错误凭据
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "wrongpassword"}' \
        "$API_URL/auth/login")
    
    if [[ $(echo "$response" | jq -r '.code') == "401" ]]; then
        log_success "使用错误凭据登录失败，符合预期"
    else
        log_error "使用错误凭据登录测试失败"
    fi
}

# 测试服务器管理
test_server_management() {
    log_info "测试服务器管理..."
    
    # 先登录获取token
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' \
        "$API_URL/auth/login")
    
    token=$(echo "$response" | jq -r '.data.token')
    
    # 创建服务器
    create_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d '{"name": "测试服务器", "auto_renew": true}' \
        "$API_URL/servers")
    
    if [[ $(echo "$create_response" | jq -r '.code') == "200" ]]; then
        server_id=$(echo "$create_response" | jq -r '.data.id')
        server_token=$(echo "$create_response" | jq -r '.data.token')
        log_success "服务器创建成功，ID: $server_id, Token: ${server_token:0:8}..."
        
        # 获取服务器列表
        list_response=$(curl -s -X GET \
            -H "Authorization: Bearer $token" \
            "$API_URL/servers")
        
        if [[ $(echo "$list_response" | jq -r '.code') == "200" ]]; then
            server_count=$(echo "$list_response" | jq -r '.data.total')
            log_success "获取服务器列表成功，共 $server_count 个服务器"
        else
            log_error "获取服务器列表失败"
        fi
        
        # 获取服务器详情
        detail_response=$(curl -s -X GET \
            -H "Authorization: Bearer $token" \
            "$API_URL/servers/$server_id")
        
        if [[ $(echo "$detail_response" | jq -r '.code') == "200" ]]; then
            server_name=$(echo "$detail_response" | jq -r '.data.name')
            log_success "获取服务器详情成功，名称: $server_name"
        else
            log_error "获取服务器详情失败"
        fi
        
        # 更新服务器
        update_response=$(curl -s -X PUT \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            -d '{"name": "测试服务器-已更新", "auto_renew": false}' \
            "$API_URL/servers/$server_id")
        
        if [[ $(echo "$update_response" | jq -r '.code') == "200" ]]; then
            log_success "更新服务器成功"
        else
            log_error "更新服务器失败"
        fi
        
        # 测试服务器注册
        register_response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "X-Server-Token: $server_token" \
            -d '{"hostname": "test-host", "ip": "192.168.1.100", "os_type": "Ubuntu 22.04", "version": "1.0.0"}' \
            "$API_URL/servers/register")
        
        if [[ $(echo "$register_response" | jq -r '.code') == "200" ]]; then
            log_success "服务器注册成功"
        else
            log_error "服务器注册失败"
        fi
        
        # 测试服务器心跳
        heartbeat_response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "X-Server-Token: $server_token" \
            -d '{"version": "1.0.0", "timestamp": '$(date +%s)'}' \
            "$API_URL/servers/heartbeat")
        
        if [[ $(echo "$heartbeat_response" | jq -r '.code') == "200" ]]; then
            log_success "服务器心跳发送成功"
        else
            log_error "服务器心跳发送失败"
        fi
        
        # 删除服务器
        delete_response=$(curl -s -X DELETE \
            -H "Authorization: Bearer $token" \
            "$API_URL/servers/$server_id")
        
        if [[ $(echo "$delete_response" | jq -r '.code') == "200" ]]; then
            log_success "删除服务器成功"
        else
            log_error "删除服务器失败"
        fi
    else
        log_error "服务器创建失败: $(echo "$create_response" | jq -r '.message')"
    fi
}

# 测试证书管理
test_certificate_management() {
    log_info "测试证书管理..."
    
    # 先登录获取token
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' \
        "$API_URL/auth/login")
    
    token=$(echo "$response" | jq -r '.data.token')
    
    # 创建服务器
    create_server_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d '{"name": "证书测试服务器", "auto_renew": true}' \
        "$API_URL/servers")
    
    server_id=$(echo "$create_server_response" | jq -r '.data.id')
    server_token=$(echo "$create_server_response" | jq -r '.data.token')
    
    # 创建证书
    create_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d '{"domain": "test.example.com", "server_id": '$server_id', "type": "single", "ca_type": "letsencrypt", "validation_method": "dns"}' \
        "$API_URL/certificates")
    
    if [[ $(echo "$create_response" | jq -r '.code') == "200" ]]; then
        cert_id=$(echo "$create_response" | jq -r '.data.id')
        log_success "证书创建成功，ID: $cert_id"
        
        # 获取证书列表
        list_response=$(curl -s -X GET \
            -H "Authorization: Bearer $token" \
            "$API_URL/certificates")
        
        if [[ $(echo "$list_response" | jq -r '.code') == "200" ]]; then
            cert_count=$(echo "$list_response" | jq -r '.data.total')
            log_success "获取证书列表成功，共 $cert_count 个证书"
        else
            log_error "获取证书列表失败"
        fi
        
        # 获取证书详情
        detail_response=$(curl -s -X GET \
            -H "Authorization: Bearer $token" \
            "$API_URL/certificates/$cert_id")
        
        if [[ $(echo "$detail_response" | jq -r '.code') == "200" ]]; then
            cert_domain=$(echo "$detail_response" | jq -r '.data.domain')
            log_success "获取证书详情成功，域名: $cert_domain"
        else
            log_error "获取证书详情失败"
        fi
        
        # 更新证书
        update_response=$(curl -s -X PUT \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            -d '{"auto_renew": false}' \
            "$API_URL/certificates/$cert_id")
        
        if [[ $(echo "$update_response" | jq -r '.code') == "200" ]]; then
            log_success "更新证书成功"
        else
            log_error "更新证书失败"
        fi
        
        # 续期证书
        renew_response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            "$API_URL/certificates/$cert_id/renew")
        
        if [[ $(echo "$renew_response" | jq -r '.code') == "200" ]]; then
            log_success "证书续期请求成功"
        else
            log_error "证书续期请求失败"
        fi
        
        # 测试证书同步
        sync_response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "X-Server-Token: $server_token" \
            -d '{"certificates": [{"domain": "test.example.com", "path": "/etc/nginx/certs/test.example.com.crt", "key_path": "/etc/nginx/certs/test.example.com.key", "expires_at": "'$(date -d "+90 days" -Iseconds)'", "type": "single"}]}' \
            "$API_URL/certificates/sync")
        
        if [[ $(echo "$sync_response" | jq -r '.code') == "200" ]]; then
            log_success "证书同步成功"
        else
            log_error "证书同步失败"
        fi
        
        # 删除证书
        delete_response=$(curl -s -X DELETE \
            -H "Authorization: Bearer $token" \
            "$API_URL/certificates/$cert_id")
        
        if [[ $(echo "$delete_response" | jq -r '.code') == "200" ]]; then
            log_success "删除证书成功"
        else
            log_error "删除证书失败"
        fi
    else
        log_error "证书创建失败: $(echo "$create_response" | jq -r '.message')"
    fi
    
    # 清理服务器
    curl -s -X DELETE \
        -H "Authorization: Bearer $token" \
        "$API_URL/servers/$server_id"
}

# 测试告警管理
test_alert_management() {
    log_info "测试告警管理..."
    
    # 先登录获取token
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' \
        "$API_URL/auth/login")
    
    token=$(echo "$response" | jq -r '.data.token')
    
    # 获取告警列表
    list_response=$(curl -s -X GET \
        -H "Authorization: Bearer $token" \
        "$API_URL/alerts")
    
    if [[ $(echo "$list_response" | jq -r '.code') == "200" ]]; then
        alert_count=$(echo "$list_response" | jq -r '.data.total')
        log_success "获取告警列表成功，共 $alert_count 个告警"
        
        # 如果有告警，测试更新告警状态
        if [[ "$alert_count" -gt 0 ]]; then
            alert_id=$(echo "$list_response" | jq -r '.data.items[0].id')
            
            update_response=$(curl -s -X PUT \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $token" \
                -d '{"status": "resolved"}' \
                "$API_URL/alerts/$alert_id")
            
            if [[ $(echo "$update_response" | jq -r '.code') == "200" ]]; then
                log_success "更新告警状态成功"
            else
                log_error "更新告警状态失败"
            fi
        else
            log_warning "没有告警记录，跳过告警状态更新测试"
        fi
    else
        log_error "获取告警列表失败"
    fi
}

# 测试系统设置
test_system_settings() {
    log_info "测试系统设置..."
    
    # 先登录获取token
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' \
        "$API_URL/auth/login")
    
    token=$(echo "$response" | jq -r '.data.token')
    
    # 获取系统设置
    get_response=$(curl -s -X GET \
        -H "Authorization: Bearer $token" \
        "$API_URL/settings")
    
    if [[ $(echo "$get_response" | jq -r '.code') == "200" ]]; then
        log_success "获取系统设置成功"
        
        # 更新系统设置
        update_response=$(curl -s -X PUT \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            -d '{"renew_before_days": 20, "alert_before_days": 25, "default_ca": "letsencrypt"}' \
            "$API_URL/settings")
        
        if [[ $(echo "$update_response" | jq -r '.code') == "200" ]]; then
            log_success "更新系统设置成功"
        else
            log_error "更新系统设置失败"
        fi
    else
        log_error "获取系统设置失败"
    fi
}

# 测试客户端任务
test_client_tasks() {
    log_info "测试客户端任务..."
    
    # 先创建服务器获取token
    login_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' \
        "$API_URL/auth/login")
    
    token=$(echo "$login_response" | jq -r '.data.token')
    
    create_server_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d '{"name": "任务测试服务器", "auto_renew": true}' \
        "$API_URL/servers")
    
    server_id=$(echo "$create_server_response" | jq -r '.data.id')
    server_token=$(echo "$create_server_response" | jq -r '.data.token')
    
    # 客户端注册
    register_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-Server-Token: $server_token" \
        -d '{"hostname": "task-test-host", "ip": "192.168.1.200", "os_type": "CentOS 7", "version": "1.0.0"}' \
        "$API_URL/client/register")
    
    if [[ $(echo "$register_response" | jq -r '.code') == "200" ]]; then
        log_success "客户端注册成功"
        
        # 获取客户端任务
        tasks_response=$(curl -s -X GET \
            -H "X-Server-Token: $server_token" \
            "$API_URL/client/tasks")
        
        if [[ $(echo "$tasks_response" | jq -r '.code') == "200" ]]; then
            task_count=$(echo "$tasks_response" | jq -r '.data.tasks | length')
            log_success "获取客户端任务成功，共 $task_count 个任务"
            
            # 如果有任务，测试更新任务状态
            if [[ "$task_count" -gt 0 ]]; then
                task_id=$(echo "$tasks_response" | jq -r '.data.tasks[0].id')
                
                update_task_response=$(curl -s -X PUT \
                    -H "Content-Type: application/json" \
                    -H "X-Server-Token: $server_token" \
                    -d '{"status": "completed", "result": {"success": true, "message": "任务完成"}}' \
                    "$API_URL/client/tasks/$task_id")
                
                if [[ $(echo "$update_task_response" | jq -r '.code') == "200" ]]; then
                    log_success "更新任务状态成功"
                else
                    log_error "更新任务状态失败"
                fi
            else
                log_warning "没有任务，跳过任务状态更新测试"
            fi
        else
            log_error "获取客户端任务失败"
        fi
    else
        log_error "客户端注册失败"
    fi
    
    # 清理服务器
    curl -s -X DELETE \
        -H "Authorization: Bearer $token" \
        "$API_URL/servers/$server_id"
}

# 性能测试
test_performance() {
    log_info "执行性能测试..."
    
    # 先登录获取token
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' \
        "$API_URL/auth/login")
    
    token=$(echo "$response" | jq -r '.data.token')
    
    # 测试API响应时间
    log_info "测试API响应时间..."
    
    # 测试登录接口响应时间
    start_time=$(date +%s.%N)
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' \
        "$API_URL/auth/login" > /dev/null
    end_time=$(date +%s.%N)
    login_time=$(echo "$end_time - $start_time" | bc)
    log_info "登录接口响应时间: ${login_time}s"
    
    # 测试获取服务器列表接口响应时间
    start_time=$(date +%s.%N)
    curl -s -X GET \
        -H "Authorization: Bearer $token" \
        "$API_URL/servers" > /dev/null
    end_time=$(date +%s.%N)
    servers_time=$(echo "$end_time - $start_time" | bc)
    log_info "获取服务器列表接口响应时间: ${servers_time}s"
    
    # 测试获取证书列表接口响应时间
    start_time=$(date +%s.%N)
    curl -s -X GET \
        -H "Authorization: Bearer $token" \
        "$API_URL/certificates" > /dev/null
    end_time=$(date +%s.%N)
    certs_time=$(echo "$end_time - $start_time" | bc)
    log_info "获取证书列表接口响应时间: ${certs_time}s"
    
    # 测试并发请求
    log_info "测试并发请求..."
    
    # 使用ab工具进行并发测试
    if command -v ab &> /dev/null; then
        # 创建临时文件存储请求数据
        echo '{"username": "admin", "password": "admin123"}' > /tmp/login_data.json
        
        # 测试登录接口并发性能
        ab -n 100 -c 10 -T 'application/json' -p /tmp/login_data.json "$API_URL/auth/login" > "$REPORT_DIR/login_concurrency.txt"
        log_success "登录接口并发测试完成，报告已保存至 $REPORT_DIR/login_concurrency.txt"
        
        # 清理临时文件
        rm /tmp/login_data.json
    else
        log_warning "未找到ab工具，跳过并发测试"
    fi
    
    # 生成性能测试报告
    cat > "$REPORT_DIR/performance_summary.txt" << EOF
性能测试摘要
============

API响应时间:
- 登录接口: ${login_time}s
- 获取服务器列表: ${servers_time}s
- 获取证书列表: ${certs_time}s

并发测试:
- 登录接口: 100个请求，10个并发
EOF
    
    log_success "性能测试完成，摘要已保存至 $REPORT_DIR/performance_summary.txt"
}

# 生成测试报告
generate_report() {
    log_info "生成测试报告..."
    
    # 统计测试结果
    success_count=$(grep -c "\[SUCCESS\]" "$LOG_FILE")
    error_count=$(grep -c "\[ERROR\]" "$LOG_FILE")
    warning_count=$(grep -c "\[WARNING\]" "$LOG_FILE")
    total_count=$((success_count + error_count + warning_count))
    
    # 计算成功率
    success_rate=$(echo "scale=2; $success_count * 100 / $total_count" | bc)
    
    # 生成HTML报告
    cat > "$REPORT_DIR/test_report.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SSL证书自动化管理系统测试报告</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1, h2 {
            color: #2c3e50;
        }
        .summary {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .success {
            color: #28a745;
        }
        .error {
            color: #dc3545;
        }
        .warning {
            color: #ffc107;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 10px;
            border: 1px solid #ddd;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        .progress-bar {
            height: 20px;
            background-color: #e9ecef;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .progress {
            height: 100%;
            border-radius: 5px;
            background-color: #28a745;
            width: ${success_rate}%;
        }
    </style>
</head>
<body>
    <h1>SSL证书自动化管理系统测试报告</h1>
    <p>测试时间: $(date '+%Y-%m-%d %H:%M:%S')</p>
    
    <div class="summary">
        <h2>测试摘要</h2>
        <p>总测试数: $total_count</p>
        <p class="success">成功: $success_count</p>
        <p class="error">错误: $error_count</p>
        <p class="warning">警告: $warning_count</p>
        <p>成功率: ${success_rate}%</p>
        
        <div class="progress-bar">
            <div class="progress"></div>
        </div>
    </div>
    
    <h2>测试模块结果</h2>
    <table>
        <tr>
            <th>模块</th>
            <th>状态</th>
            <th>备注</th>
        </tr>
        <tr>
            <td>API连接</td>
            <td class="$(grep -q "API连接成功" "$LOG_FILE" && echo "success" || echo "error")">
                $(grep -q "API连接成功" "$LOG_FILE" && echo "通过" || echo "失败")
            </td>
            <td>测试API服务是否可访问</td>
        </tr>
        <tr>
            <td>用户认证</td>
            <td class="$(grep -q "登录成功" "$LOG_FILE" && echo "success" || echo "error")">
                $(grep -q "登录成功" "$LOG_FILE" && echo "通过" || echo "失败")
            </td>
            <td>测试登录、令牌刷新和登出功能</td>
        </tr>
        <tr>
            <td>服务器管理</td>
            <td class="$(grep -q "服务器创建成功" "$LOG_FILE" && echo "success" || echo "error")">
                $(grep -q "服务器创建成功" "$LOG_FILE" && echo "通过" || echo "失败")
            </td>
            <td>测试服务器的创建、查询、更新和删除</td>
        </tr>
        <tr>
            <td>证书管理</td>
            <td class="$(grep -q "证书创建成功" "$LOG_FILE" && echo "success" || echo "error")">
                $(grep -q "证书创建成功" "$LOG_FILE" && echo "通过" || echo "失败")
            </td>
            <td>测试证书的创建、查询、更新、续期和删除</td>
        </tr>
        <tr>
            <td>告警管理</td>
            <td class="$(grep -q "获取告警列表成功" "$LOG_FILE" && echo "success" || echo "error")">
                $(grep -q "获取告警列表成功" "$LOG_FILE" && echo "通过" || echo "失败")
            </td>
            <td>测试告警的查询和状态更新</td>
        </tr>
        <tr>
            <td>系统设置</td>
            <td class="$(grep -q "获取系统设置成功" "$LOG_FILE" && echo "success" || echo "error")">
                $(grep -q "获取系统设置成功" "$LOG_FILE" && echo "通过" || echo "失败")
            </td>
            <td>测试系统设置的查询和更新</td>
        </tr>
        <tr>
            <td>客户端任务</td>
            <td class="$(grep -q "客户端注册成功" "$LOG_FILE" && echo "success" || echo "error")">
                $(grep -q "客户端注册成功" "$LOG_FILE" && echo "通过" || echo "失败")
            </td>
            <td>测试客户端注册和任务管理</td>
        </tr>
        <tr>
            <td>性能测试</td>
            <td class="success">通过</td>
            <td>测试API响应时间和并发性能</td>
        </tr>
    </table>
    
    <h2>详细日志</h2>
    <pre>$(cat "$LOG_FILE")</pre>
</body>
</html>
EOF
    
    log_success "测试报告已生成: $REPORT_DIR/test_report.html"
}

# 主函数
main() {
    log_info "开始执行SSL证书自动化管理系统测试..."
    
    # 执行各项测试
    test_api_connection
    test_user_auth
    test_server_management
    test_certificate_management
    test_alert_management
    test_system_settings
    test_client_tasks
    test_performance
    
    # 生成测试报告
    generate_report
    
    log_info "测试执行完成"
}

# 执行主函数
main
