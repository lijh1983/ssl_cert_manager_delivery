#!/bin/bash

# SSL证书管理器一键部署脚本
# 专为阿里云ECS环境优化，开箱即用

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 默认配置
DEFAULT_DOMAIN="ssl.gzyggl.com"
DEFAULT_EMAIL="19822088@qq.com"
DEFAULT_ENVIRONMENT="production"

echo "=== SSL证书管理器一键部署工具 ==="
echo "专为阿里云ECS环境优化"
echo "部署时间: $(date)"
echo "======================================="

# 检查Docker和Docker Compose
check_prerequisites() {
    echo -e "${BLUE}1. 检查系统环境${NC}"
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker未安装${NC}"
        echo "请先安装Docker: https://docs.docker.com/engine/install/"
        exit 1
    fi
    
    # 检查Docker服务
    if ! systemctl is-active --quiet docker; then
        echo -e "${YELLOW}启动Docker服务...${NC}"
        sudo systemctl start docker
    fi
    
    # 检查Docker Compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        echo -e "${YELLOW}警告: Docker Compose未安装，将使用Docker命令手动部署${NC}"
        COMPOSE_CMD=""
    fi
    
    echo -e "${GREEN}✓ Docker环境检查通过${NC}"
    echo "Docker版本: $(docker --version)"
    echo "Compose命令: $COMPOSE_CMD"
}

# 设置环境变量
setup_environment() {
    echo -e "\n${BLUE}2. 配置环境变量${NC}"
    
    # 读取用户输入或使用默认值
    read -p "请输入域名 (默认: $DEFAULT_DOMAIN): " DOMAIN_NAME
    DOMAIN_NAME=${DOMAIN_NAME:-$DEFAULT_DOMAIN}
    
    read -p "请输入邮箱 (默认: $DEFAULT_EMAIL): " EMAIL
    EMAIL=${EMAIL:-$DEFAULT_EMAIL}
    
    read -p "请输入环境 (默认: $DEFAULT_ENVIRONMENT): " ENVIRONMENT
    ENVIRONMENT=${ENVIRONMENT:-$DEFAULT_ENVIRONMENT}
    
    # 创建.env文件
    cat > .env <<EOF
# SSL证书管理器环境配置
DOMAIN_NAME=$DOMAIN_NAME
EMAIL=$EMAIL
ENVIRONMENT=$ENVIRONMENT

# 数据库配置
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=$(openssl rand -base64 32)
DB_PORT=5432

# Redis配置
REDIS_PASSWORD=$(openssl rand -base64 32)

# 监控配置
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 16)
PROMETHEUS_PORT=9090

# API配置
VITE_API_BASE_URL=/api
BACKEND_WORKERS=2
LOG_LEVEL=INFO

# 启用功能
ENABLE_METRICS=true
ENABLE_MONITORING=true
EOF
    
    echo -e "${GREEN}✓ 环境配置完成${NC}"
    echo "域名: $DOMAIN_NAME"
    echo "邮箱: $EMAIL"
    echo "环境: $ENVIRONMENT"
}

# 构建基础镜像
build_base_images() {
    echo -e "\n${BLUE}3. 构建基础镜像${NC}"
    
    # 构建后端基础镜像
    if [ -f "backend/Dockerfile.base" ]; then
        echo "构建后端基础镜像..."
        docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend
        echo -e "${GREEN}✓ 后端基础镜像构建完成${NC}"
    fi
    
    # 构建前端基础镜像
    if [ -f "frontend/Dockerfile.base" ]; then
        echo "构建前端基础镜像..."
        docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend
        echo -e "${GREEN}✓ 前端基础镜像构建完成${NC}"
    fi
}

# 部署应用
deploy_application() {
    echo -e "\n${BLUE}4. 部署应用${NC}"
    
    # 构建应用镜像
    echo "构建应用镜像..."
    $COMPOSE_CMD -f docker-compose.aliyun.yml build
    
    # 启动服务
    echo "启动服务..."
    $COMPOSE_CMD -f docker-compose.aliyun.yml up -d
    
    echo -e "${GREEN}✓ 应用部署完成${NC}"
}

# 启动监控服务
deploy_monitoring() {
    echo -e "\n${BLUE}5. 部署监控服务${NC}"
    
    read -p "是否启用监控服务? (y/N): " ENABLE_MONITORING
    if [[ $ENABLE_MONITORING =~ ^[Yy]$ ]]; then
        echo "启动监控服务..."
        $COMPOSE_CMD -f docker-compose.aliyun.yml --profile monitoring up -d
        echo -e "${GREEN}✓ 监控服务部署完成${NC}"
    else
        echo "跳过监控服务部署"
    fi
}

# 验证部署
verify_deployment() {
    echo -e "\n${BLUE}6. 验证部署${NC}"
    
    # 等待服务启动
    echo "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    echo "检查服务状态..."
    $COMPOSE_CMD -f docker-compose.aliyun.yml ps
    
    # 检查健康状态
    echo -e "\n检查服务健康状态..."
    local healthy_count=0
    local total_count=0
    
    for service in postgres redis backend frontend nginx-proxy; do
        total_count=$((total_count + 1))
        if $COMPOSE_CMD -f docker-compose.aliyun.yml ps $service | grep -q "healthy\|Up"; then
            echo -e "${GREEN}✓ $service 运行正常${NC}"
            healthy_count=$((healthy_count + 1))
        else
            echo -e "${RED}✗ $service 运行异常${NC}"
        fi
    done
    
    echo -e "\n服务状态: $healthy_count/$total_count 正常"
    
    if [ $healthy_count -eq $total_count ]; then
        echo -e "${GREEN}🎉 所有服务部署成功！${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  部分服务可能需要更多时间启动${NC}"
        return 1
    fi
}

# 显示访问信息
show_access_info() {
    echo -e "\n======================================="
    echo -e "${GREEN}🎉 SSL证书管理器部署完成！${NC}"
    echo "======================================="
    
    echo -e "\n${BLUE}访问信息:${NC}"
    echo "主应用: http://$DOMAIN_NAME"
    echo "API文档: http://$DOMAIN_NAME/api/docs"
    
    if [[ $ENABLE_MONITORING =~ ^[Yy]$ ]]; then
        echo "监控面板: http://$DOMAIN_NAME/monitoring/"
        echo "Prometheus: http://$DOMAIN_NAME:9090"
    fi
    
    echo -e "\n${BLUE}管理命令:${NC}"
    echo "查看日志: $COMPOSE_CMD -f docker-compose.aliyun.yml logs -f"
    echo "停止服务: $COMPOSE_CMD -f docker-compose.aliyun.yml down"
    echo "重启服务: $COMPOSE_CMD -f docker-compose.aliyun.yml restart"
    
    echo -e "\n${BLUE}配置文件:${NC}"
    echo "环境配置: .env"
    echo "Docker配置: docker-compose.aliyun.yml"
    
    echo -e "\n${YELLOW}注意事项:${NC}"
    echo "1. 请确保域名 $DOMAIN_NAME 已正确解析到此服务器"
    echo "2. 请确保防火墙已开放80和443端口"
    echo "3. SSL证书将自动申请和续期"
    echo "4. 数据库密码等敏感信息已保存在.env文件中"
}

# 错误处理
handle_error() {
    echo -e "\n${RED}部署过程中发生错误！${NC}"
    echo "请检查错误信息并重试"
    echo "如需帮助，请查看日志: $COMPOSE_CMD -f docker-compose.aliyun.yml logs"
    exit 1
}

# 主函数
main() {
    # 设置错误处理
    trap handle_error ERR
    
    # 执行部署步骤
    check_prerequisites
    setup_environment
    build_base_images
    deploy_application
    deploy_monitoring
    
    # 验证部署
    if verify_deployment; then
        show_access_info
    else
        echo -e "\n${YELLOW}部署可能需要更多时间完成${NC}"
        echo "请稍后运行以下命令检查状态:"
        echo "$COMPOSE_CMD -f docker-compose.aliyun.yml ps"
        show_access_info
    fi
}

# 检查参数
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  --quick        快速部署（使用默认配置）"
    echo ""
    echo "示例:"
    echo "  $0              # 交互式部署"
    echo "  $0 --quick      # 快速部署"
    exit 0
fi

if [ "$1" = "--quick" ]; then
    # 快速部署模式
    DOMAIN_NAME=$DEFAULT_DOMAIN
    EMAIL=$DEFAULT_EMAIL
    ENVIRONMENT=$DEFAULT_ENVIRONMENT
    ENABLE_MONITORING="y"
    
    echo "快速部署模式"
    echo "域名: $DOMAIN_NAME"
    echo "邮箱: $EMAIL"
    
    check_prerequisites
    
    # 创建默认.env文件
    cat > .env <<EOF
DOMAIN_NAME=$DOMAIN_NAME
EMAIL=$EMAIL
ENVIRONMENT=$ENVIRONMENT
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -base64 16)
VITE_API_BASE_URL=/api
ENABLE_METRICS=true
EOF
    
    build_base_images
    deploy_application
    $COMPOSE_CMD -f docker-compose.aliyun.yml --profile monitoring up -d
    verify_deployment
    show_access_info
else
    # 交互式部署
    main
fi
