#!/bin/bash

# PostgreSQL问题快速修复脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=== PostgreSQL问题快速修复工具 ==="
echo "修复时间: $(date)"
echo "=================================="

# 检查Docker Compose命令
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${RED}错误: Docker Compose未安装${NC}"
    exit 1
fi

echo -e "${BLUE}1. 停止所有服务${NC}"
$COMPOSE_CMD -f docker-compose.aliyun.yml down

echo -e "\n${BLUE}2. 清理PostgreSQL相关资源${NC}"
# 删除PostgreSQL容器和卷
docker rm -f ssl-manager-postgres 2>/dev/null || true
docker volume rm ssl_cert_manager_delivery_postgres_data 2>/dev/null || true

echo -e "\n${BLUE}3. 验证数据库初始化文件${NC}"
if [ ! -f "database/init/01-init-database.sql" ]; then
    echo -e "${RED}错误: 数据库初始化文件不存在${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: .env文件不存在，使用默认配置${NC}"
    cp .env.example .env
fi

echo -e "${GREEN}✓ 数据库初始化文件检查通过${NC}"

echo -e "\n${BLUE}4. 重新启动PostgreSQL服务${NC}"
$COMPOSE_CMD -f docker-compose.aliyun.yml up -d postgres

echo -e "\n${BLUE}5. 等待PostgreSQL启动${NC}"
echo "等待PostgreSQL服务启动..."
for i in {1..60}; do
    if docker exec ssl-manager-postgres pg_isready -U ssl_user -d ssl_manager >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL服务启动成功${NC}"
        break
    fi
    
    if [ $i -eq 60 ]; then
        echo -e "${RED}✗ PostgreSQL启动超时${NC}"
        echo "查看PostgreSQL日志:"
        docker logs ssl-manager-postgres --tail 20
        exit 1
    fi
    
    echo -n "."
    sleep 2
done

echo -e "\n${BLUE}6. 验证数据库连接${NC}"
if docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "SELECT version();" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ 数据库连接正常${NC}"
else
    echo -e "${RED}✗ 数据库连接失败${NC}"
    docker logs ssl-manager-postgres --tail 20
    exit 1
fi

echo -e "\n${BLUE}7. 启动Redis服务${NC}"
$COMPOSE_CMD -f docker-compose.aliyun.yml up -d redis

echo -e "\n${BLUE}8. 等待Redis启动${NC}"
for i in {1..30}; do
    if docker exec ssl-manager-redis redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis服务启动成功${NC}"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Redis启动超时${NC}"
        docker logs ssl-manager-redis --tail 20
        exit 1
    fi
    
    echo -n "."
    sleep 1
done

echo -e "\n${BLUE}9. 检查服务状态${NC}"
echo "当前运行的服务:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n=================================="
echo -e "${GREEN}🎉 PostgreSQL修复完成！${NC}"

echo -e "\n${BLUE}下一步操作:${NC}"
echo "1. 启动所有服务:"
echo "   $COMPOSE_CMD -f docker-compose.aliyun.yml up -d"
echo ""
echo "2. 启动包含监控的完整服务:"
echo "   $COMPOSE_CMD -f docker-compose.aliyun.yml --profile monitoring up -d"
echo ""
echo "3. 查看服务状态:"
echo "   $COMPOSE_CMD -f docker-compose.aliyun.yml ps"
echo ""
echo "4. 查看日志:"
echo "   docker logs ssl-manager-postgres"
echo "   docker logs ssl-manager-redis"

echo -e "\n${YELLOW}注意事项:${NC}"
echo "- PostgreSQL默认密码已设置为: ssl_password_123"
echo "- Redis默认密码已设置为: redis_password_123"
echo "- 请在生产环境中修改这些默认密码"
echo "- 数据库已创建默认管理员账户: admin / admin123"
