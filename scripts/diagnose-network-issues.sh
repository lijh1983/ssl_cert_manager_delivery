#!/bin/bash

# 阿里云ECS Docker网络连接问题诊断脚本
# 用于诊断"Unable to connect to deb.debian.org:http"等网络连接问题

set -e

echo "=== 阿里云ECS Docker网络连接诊断工具 ==="
echo "诊断时间: $(date)"
echo "============================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 诊断结果统计
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 检查函数
check_item() {
    local name="$1"
    local command="$2"
    local expected="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -e "\n${BLUE}检查项目: $name${NC}"
    echo "执行命令: $command"
    
    if eval "$command" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name: 通过"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name: 失败"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# 详细检查函数
detailed_check() {
    local name="$1"
    local command="$2"
    
    echo -e "\n${BLUE}详细检查: $name${NC}"
    echo "执行命令: $command"
    echo "结果:"
    eval "$command" 2>&1 | head -10
}

echo -e "${BLUE}1. 基础网络连通性检查${NC}"

# 检查公网IP
detailed_check "ECS公网IP" "curl -s ifconfig.me || curl -s ipinfo.io/ip"

# 检查内网IP
detailed_check "ECS内网IP" "ip addr show | grep 'inet ' | grep -v '127.0.0.1'"

# 检查默认网关
detailed_check "默认网关" "ip route | grep default"

# 检查DNS配置
detailed_check "DNS配置" "cat /etc/resolv.conf"

echo -e "\n${BLUE}2. DNS解析测试${NC}"

# 测试关键域名解析
domains=(
    "deb.debian.org"
    "mirrors.aliyun.com"
    "registry.npmmirror.com"
    "pypi.tuna.tsinghua.edu.cn"
    "dl-cdn.alpinelinux.org"
)

for domain in "${domains[@]}"; do
    check_item "DNS解析: $domain" "nslookup $domain"
done

echo -e "\n${BLUE}3. 网络连接测试${NC}"

# 测试HTTP/HTTPS连接
test_urls=(
    "http://deb.debian.org"
    "https://mirrors.aliyun.com"
    "https://registry.npmmirror.com"
    "https://pypi.tuna.tsinghua.edu.cn/simple"
)

for url in "${test_urls[@]}"; do
    check_item "HTTP连接: $url" "curl -I --connect-timeout 10 $url"
done

echo -e "\n${BLUE}4. Docker网络配置检查${NC}"

# 检查Docker服务状态
check_item "Docker服务状态" "systemctl is-active docker"

# 检查Docker网络
detailed_check "Docker网络列表" "docker network ls"

# 检查Docker daemon配置
if [ -f /etc/docker/daemon.json ]; then
    detailed_check "Docker daemon配置" "cat /etc/docker/daemon.json"
else
    echo -e "${YELLOW}注意: /etc/docker/daemon.json 不存在${NC}"
fi

# 检查Docker默认网桥
detailed_check "Docker默认网桥" "docker network inspect bridge | jq '.[0].IPAM.Config' 2>/dev/null || docker network inspect bridge"

echo -e "\n${BLUE}5. 防火墙和安全组检查${NC}"

# 检查iptables规则
detailed_check "iptables规则" "iptables -L -n | head -20"

# 检查系统防火墙状态
if command -v ufw >/dev/null 2>&1; then
    detailed_check "UFW防火墙状态" "ufw status"
elif command -v firewall-cmd >/dev/null 2>&1; then
    detailed_check "firewalld状态" "firewall-cmd --state"
fi

echo -e "\n${BLUE}6. 容器内网络测试${NC}"

# 创建测试容器进行网络测试
echo "创建测试容器进行网络诊断..."
if docker run --rm --name network-test alpine:latest sh -c "
    echo '=== 容器内网络测试 ==='
    echo '1. 检查DNS配置:'
    cat /etc/resolv.conf
    echo '2. 测试DNS解析:'
    nslookup deb.debian.org || echo 'DNS解析失败'
    echo '3. 测试网络连接:'
    wget -T 10 -O /dev/null http://deb.debian.org 2>&1 || echo 'HTTP连接失败'
    echo '4. 测试阿里云镜像源:'
    wget -T 10 -O /dev/null https://mirrors.aliyun.com 2>&1 || echo '阿里云连接失败'
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} 容器网络测试完成"
else
    echo -e "${RED}✗${NC} 容器网络测试失败"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo -e "\n${BLUE}7. 阿里云ECS特定检查${NC}"

# 检查阿里云元数据服务
detailed_check "阿里云元数据服务" "curl -s --connect-timeout 5 http://100.100.100.200/latest/meta-data/instance-id"

# 检查阿里云DNS
detailed_check "阿里云DNS测试" "nslookup mirrors.aliyun.com 223.5.5.5"

echo -e "\n${BLUE}8. 系统资源检查${NC}"

# 检查磁盘空间
detailed_check "磁盘空间" "df -h /"

# 检查内存使用
detailed_check "内存使用" "free -h"

# 检查系统负载
detailed_check "系统负载" "uptime"

echo -e "\n============================================="
echo -e "${BLUE}诊断结果汇总:${NC}"
echo -e "总检查项: $TOTAL_CHECKS"
echo -e "${GREEN}通过: $PASSED_CHECKS${NC}"
echo -e "${RED}失败: $FAILED_CHECKS${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 网络诊断全部通过！${NC}"
    echo -e "${GREEN}网络连接正常，可以进行Docker构建。${NC}"
else
    echo -e "\n${RED}❌ 发现 $FAILED_CHECKS 个网络问题${NC}"
    
    echo -e "\n${BLUE}常见问题解决建议:${NC}"
    echo -e "${YELLOW}1. DNS解析问题:${NC}"
    echo "   - 检查 /etc/resolv.conf 配置"
    echo "   - 使用阿里云DNS: 223.5.5.5, 223.6.6.6"
    echo "   - 配置Docker daemon DNS"
    
    echo -e "${YELLOW}2. 网络连接问题:${NC}"
    echo "   - 检查ECS安全组规则"
    echo "   - 确认出站规则允许HTTP/HTTPS"
    echo "   - 检查VPC和子网配置"
    
    echo -e "${YELLOW}3. Docker网络问题:${NC}"
    echo "   - 重启Docker服务"
    echo "   - 配置Docker镜像加速器"
    echo "   - 使用阿里云镜像源"
    
    echo -e "${YELLOW}4. 防火墙问题:${NC}"
    echo "   - 检查iptables规则"
    echo "   - 确认系统防火墙配置"
    echo "   - 检查Docker网络规则"
fi

echo -e "\n${BLUE}下一步操作建议:${NC}"
echo "1. 运行网络修复脚本: ./scripts/fix-network-issues.sh"
echo "2. 配置阿里云镜像源: ./scripts/configure-aliyun-mirrors.sh"
echo "3. 重新构建Docker镜像"
echo "4. 如问题持续，请联系阿里云技术支持"
