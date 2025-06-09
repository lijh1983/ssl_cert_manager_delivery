#!/bin/bash

# 阿里云ECS Docker网络问题修复脚本
# 解决"Unable to connect to deb.debian.org:http"等网络连接问题

set -e

echo "=== 阿里云ECS Docker网络问题修复工具 ==="
echo "修复时间: $(date)"
echo "============================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请使用root权限运行此脚本${NC}"
    echo "使用方法: sudo $0"
    exit 1
fi

echo -e "${BLUE}1. 配置系统DNS${NC}"

# 备份原始DNS配置
if [ ! -f /etc/resolv.conf.backup ]; then
    cp /etc/resolv.conf /etc/resolv.conf.backup
    echo "已备份原始DNS配置到 /etc/resolv.conf.backup"
fi

# 配置阿里云DNS
cat > /etc/resolv.conf <<EOF
# 阿里云DNS配置
nameserver 223.5.5.5
nameserver 223.6.6.6
nameserver 8.8.8.8
nameserver 8.8.4.4
options timeout:2 attempts:3 rotate single-request-reopen
EOF

echo -e "${GREEN}✓${NC} 已配置阿里云DNS"

echo -e "\n${BLUE}2. 配置Docker daemon${NC}"

# 创建Docker配置目录
mkdir -p /etc/docker

# 配置Docker daemon
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ],
  "dns": [
    "223.5.5.5",
    "223.6.6.6",
    "8.8.8.8"
  ],
  "dns-opts": [
    "timeout:2",
    "attempts:3"
  ],
  "dns-search": [
    "."
  ],
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 5,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "exec-opts": ["native.cgroupdriver=systemd"],
  "live-restore": true,
  "userland-proxy": false,
  "experimental": false,
  "icc": true,
  "default-address-pools": [
    {
      "base": "172.30.0.0/16",
      "size": 24
    }
  ]
}
EOF

echo -e "${GREEN}✓${NC} 已配置Docker daemon"

echo -e "\n${BLUE}3. 重启Docker服务${NC}"

# 重新加载systemd配置
systemctl daemon-reload

# 重启Docker服务
systemctl restart docker

# 等待Docker服务启动
sleep 5

# 检查Docker服务状态
if systemctl is-active --quiet docker; then
    echo -e "${GREEN}✓${NC} Docker服务重启成功"
else
    echo -e "${RED}✗${NC} Docker服务重启失败"
    systemctl status docker
    exit 1
fi

echo -e "\n${BLUE}4. 配置系统网络优化${NC}"

# 配置网络参数
cat > /etc/sysctl.d/99-docker-network.conf <<EOF
# Docker网络优化配置
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.conf.default.forwarding = 1

# 网络连接优化
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3

# DNS优化
net.ipv4.tcp_slow_start_after_idle = 0
EOF

# 应用网络参数
sysctl -p /etc/sysctl.d/99-docker-network.conf >/dev/null 2>&1

echo -e "${GREEN}✓${NC} 已配置网络优化参数"

echo -e "\n${BLUE}5. 配置防火墙规则${NC}"

# 确保Docker相关端口开放
if command -v ufw >/dev/null 2>&1; then
    # Ubuntu/Debian UFW配置
    ufw allow out 53 comment "DNS"
    ufw allow out 80 comment "HTTP"
    ufw allow out 443 comment "HTTPS"
    ufw allow out on docker0 comment "Docker bridge"
    echo -e "${GREEN}✓${NC} 已配置UFW防火墙规则"
elif command -v firewall-cmd >/dev/null 2>&1; then
    # CentOS/RHEL firewalld配置
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --permanent --add-service=dns
    firewall-cmd --permanent --add-masquerade
    firewall-cmd --reload
    echo -e "${GREEN}✓${NC} 已配置firewalld防火墙规则"
fi

echo -e "\n${BLUE}6. 测试网络连接${NC}"

# 测试DNS解析
echo "测试DNS解析..."
if nslookup deb.debian.org >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} DNS解析正常"
else
    echo -e "${RED}✗${NC} DNS解析失败"
fi

# 测试HTTP连接
echo "测试HTTP连接..."
if curl -I --connect-timeout 10 http://deb.debian.org >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} HTTP连接正常"
else
    echo -e "${RED}✗${NC} HTTP连接失败"
fi

# 测试阿里云镜像源
echo "测试阿里云镜像源..."
if curl -I --connect-timeout 10 https://mirrors.aliyun.com >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 阿里云镜像源连接正常"
else
    echo -e "${RED}✗${NC} 阿里云镜像源连接失败"
fi

echo -e "\n${BLUE}7. 测试Docker网络${NC}"

# 测试Docker网络连接
echo "测试Docker容器网络..."
if docker run --rm alpine:latest sh -c "wget -T 10 -O /dev/null https://mirrors.aliyun.com" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker容器网络正常"
else
    echo -e "${RED}✗${NC} Docker容器网络异常"
fi

echo -e "\n${BLUE}8. 创建网络测试脚本${NC}"

# 创建持续网络测试脚本
cat > /usr/local/bin/test-docker-network.sh <<'EOF'
#!/bin/bash
echo "=== Docker网络连接测试 ==="
echo "测试时间: $(date)"

# 测试项目
tests=(
    "DNS解析:nslookup deb.debian.org"
    "HTTP连接:curl -I --connect-timeout 5 http://deb.debian.org"
    "HTTPS连接:curl -I --connect-timeout 5 https://mirrors.aliyun.com"
    "Docker网络:docker run --rm alpine:latest wget -T 5 -O /dev/null https://mirrors.aliyun.com"
)

passed=0
total=${#tests[@]}

for test in "${tests[@]}"; do
    name=$(echo "$test" | cut -d: -f1)
    command=$(echo "$test" | cut -d: -f2-)
    
    echo -n "测试 $name ... "
    if eval "$command" >/dev/null 2>&1; then
        echo "通过"
        passed=$((passed + 1))
    else
        echo "失败"
    fi
done

echo "测试结果: $passed/$total 通过"
if [ $passed -eq $total ]; then
    echo "✓ 网络连接正常"
    exit 0
else
    echo "✗ 发现网络问题"
    exit 1
fi
EOF

chmod +x /usr/local/bin/test-docker-network.sh
echo -e "${GREEN}✓${NC} 已创建网络测试脚本: /usr/local/bin/test-docker-network.sh"

echo -e "\n============================================="
echo -e "${GREEN}🎉 网络问题修复完成！${NC}"

echo -e "\n${BLUE}修复内容汇总:${NC}"
echo "1. ✓ 配置阿里云DNS (223.5.5.5, 223.6.6.6)"
echo "2. ✓ 配置Docker daemon (镜像加速器 + DNS)"
echo "3. ✓ 重启Docker服务"
echo "4. ✓ 优化系统网络参数"
echo "5. ✓ 配置防火墙规则"
echo "6. ✓ 测试网络连接"
echo "7. ✓ 创建网络测试工具"

echo -e "\n${BLUE}下一步操作:${NC}"
echo "1. 运行网络测试: /usr/local/bin/test-docker-network.sh"
echo "2. 配置阿里云镜像源: ./scripts/configure-aliyun-mirrors.sh"
echo "3. 重新构建Docker镜像"

echo -e "\n${YELLOW}注意事项:${NC}"
echo "- 如果问题持续存在，请检查ECS安全组配置"
echo "- 确保出站规则允许HTTP(80)和HTTPS(443)端口"
echo "- 可以联系阿里云技术支持获取进一步帮助"
