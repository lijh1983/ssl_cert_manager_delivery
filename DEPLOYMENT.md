# SSL证书管理器部署指南

本指南提供SSL证书管理器在生产环境中的完整部署方案，基于实际生产环境部署经验编写。

## 📋 系统要求

### 推荐配置（基于生产环境验证）

- **操作系统**: Ubuntu 22.04.5 LTS (Jammy Jellyfish) - 已验证
- **架构**: x86_64
- **内核版本**: >= 6.0 (推荐 6.12+，支持cgroup v2)
- **Docker**: 26.1.3+ (必须支持cgroup v2)
- **Docker Compose**: v2.24.0+
- **内存**: 16GB (最低8GB)
- **CPU**: 4核心 (最低2核心)
- **磁盘**:
  - 系统盘: 40GB SSD
  - 数据盘: 20GB SSD (用于数据持久化)
- **网络**: 需要访问互联网，支持Docker镜像拉取

### 关键兼容性要求

**⚠️ 重要: cgroup v2支持**
```bash
# 验证cgroup v2 (必须!)
mount | grep cgroup
# 应该显示: cgroup on /sys/fs/cgroup type cgroup2

# 如果不是cgroup v2，需要配置内核参数
# 在/etc/default/grub中添加: systemd.unified_cgroup_hierarchy=1
```

**Docker配置要求**
```bash
# 验证Docker cgroup配置
docker system info | grep -E "(Cgroup|Version)"
# 必须显示:
# - Cgroup Driver: cgroupfs
# - Cgroup Version: 2
```

### 域名配置

确保域名 `ssl.gzyggl.com` 已正确解析到您的服务器IP地址：

```bash
# 检查域名解析
nslookup ssl.gzyggl.com

# 或使用dig命令
dig ssl.gzyggl.com
```

### 防火墙配置

开放必要的端口：

```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --reload
```

## 🚀 阿里云ECS部署配置

### 推荐的阿里云ECS实例配置

**实例规格建议:**
- **实例类型**: ecs.c6.xlarge 或更高
- **CPU**: 4核心
- **内存**: 16GB
- **系统盘**: 40GB SSD
- **数据盘**: 20GB SSD
- **操作系统**: Ubuntu 22.04.5 LTS
- **网络**: VPC网络，分配公网IP

**安全组配置:**
```bash
# 入站规则
80/tcp    0.0.0.0/0    HTTP访问
443/tcp   0.0.0.0/0    HTTPS访问
22/tcp    您的IP       SSH管理
8080/tcp  内网         cAdvisor监控 (可选)
9090/tcp  内网         Prometheus监控 (可选)
3000/tcp  内网         Grafana监控 (可选)
```

## 🚀 部署方法

### 方法1: 快速部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 2. 一键环境初始化和部署
./scripts/deploy-production.sh
```

### 方法2: 手动部署（详细步骤）

#### 步骤1: 系统环境初始化

**1.1 系统更新和基础软件安装**
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y curl wget git vim htop net-tools jq

# 配置时区
sudo timedatectl set-timezone Asia/Shanghai
```

**1.2 验证cgroup v2支持**
```bash
# 检查cgroup版本 (关键!)
mount | grep cgroup
# 必须显示: cgroup on /sys/fs/cgroup type cgroup2

# 如果不是cgroup v2，需要配置
if ! mount | grep -q "cgroup2"; then
    echo "配置cgroup v2支持..."
    sudo sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="systemd.unified_cgroup_hierarchy=1"/' /etc/default/grub
    sudo update-grub
    echo "需要重启系统以启用cgroup v2"
    # sudo reboot
fi
```

**1.3 安装Docker (版本26.1.3+)**
```bash
# 卸载旧版本
sudo apt remove -y docker docker-engine docker.io containerd runc

# 安装依赖
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
newgrp docker

# 验证安装
docker --version  # 应该 >= 26.1.3
docker compose version  # 应该 >= v2.24.0

# 验证cgroup v2支持
docker system info | grep -E "(Cgroup|Version)"
# 必须显示: Cgroup Version: 2
```

**1.4 Docker配置优化**
```bash
# 创建Docker配置文件
sudo mkdir -p /etc/docker
cat > /tmp/daemon.json <<EOF
{
  "exec-opts": ["native.cgroupdriver=cgroupfs"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
sudo mv /tmp/daemon.json /etc/docker/daemon.json

# 重启Docker服务
sudo systemctl restart docker
sudo systemctl enable docker

# 验证配置
docker system info | grep -E "(Storage|Cgroup|Registry)"
```

#### 步骤2: 克隆项目

```bash
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery
```

#### 步骤3: 配置环境变量

**完整的.env配置文件 (基于生产环境验证)**

```bash
cat > .env <<EOF
# 基础配置
DOMAIN_NAME=ssl.gzyggl.com
EMAIL=19822088@qq.com
ENVIRONMENT=production

# 数据库配置 (注意: 端口号必须使用字符串格式)
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=$(openssl rand -base64 32)
DB_PORT="5432"

# Redis配置 (注意: 端口号必须使用字符串格式)
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

# Let's Encrypt SSL证书配置 (新增 - 避免环境变量警告)
ACME_EMAIL=19822088@qq.com
ACME_DIRECTORY_URL=https://acme-v02.api.letsencrypt.org/directory
# 测试环境可使用: https://acme-staging-v02.api.letsencrypt.org/directory
ACME_AGREE_TOS=true
ACME_CHALLENGE_TYPE=http-01
EOF
```

**环境变量说明:**
- `DB_PORT` 和 `REDIS_PORT`: 必须使用字符串格式，避免Docker Compose解析错误
- `ACME_*`: SSL证书自动申请配置，避免启动时的环境变量警告
- `ACME_DIRECTORY_URL`: 生产环境使用正式API，测试时可切换到staging环境

#### 步骤4: 构建基础镜像

```bash
# 构建后端基础镜像
docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend

# 构建前端基础镜像
docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend
```

#### 步骤5: 启动服务

**开发环境部署:**
```bash
# 启动完整服务（包含监控）
docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d

# 或仅启动基础服务
docker-compose -f docker-compose.aliyun.yml up -d
```

**步骤5: 生产环境部署**

**5.1 创建数据目录结构**
```bash
# 创建生产环境目录结构
sudo mkdir -p /opt/ssl-manager/{data,logs,certs,backups}
sudo mkdir -p /opt/ssl-manager/data/{postgres,redis,prometheus,grafana}

# 设置正确的权限 (关键!)
sudo chown -R $USER:$USER /opt/ssl-manager
sudo chown -R 70:70 /opt/ssl-manager/data/postgres      # PostgreSQL用户
sudo chown -R 472:472 /opt/ssl-manager/data/grafana     # Grafana用户
sudo chown -R 65534:65534 /opt/ssl-manager/data/prometheus  # Prometheus用户
sudo chown -R 999:999 /opt/ssl-manager/data/redis       # Redis用户

# 验证目录结构
ls -la /opt/ssl-manager/
ls -la /opt/ssl-manager/data/
```

**5.2 启动生产环境服务**
```bash
# 启动完整生产环境（包含监控栈）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring up -d

# 或仅启动核心服务（不包含监控）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d

# 查看启动状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps
```

**5.3 等待服务启动完成**
```bash
# 等待所有服务健康检查通过
echo "等待服务启动..."
sleep 60

# 检查服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps

# 应该看到所有服务状态为 "healthy" 或 "Up"
```

## ✅ 部署验证

### 完整的生产环境验证清单

**1. 服务状态验证**
```bash
# 检查所有服务状态 (应该有9个服务)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps

# 预期结果: 所有服务状态为 "healthy" 或 "Up"
# - ssl-manager-postgres: healthy
# - ssl-manager-redis: healthy
# - ssl-manager-backend: healthy
# - ssl-manager-frontend: healthy
# - ssl-manager-nginx: healthy
# - ssl-manager-prometheus: Up
# - ssl-manager-grafana: Up
# - ssl-manager-node-exporter: Up
# - ssl-manager-cadvisor: healthy
```

**2. 核心功能验证**
```bash
# Nginx反向代理健康检查
curl -f http://localhost/health
# 预期: "nginx-proxy healthy"

# 后端API健康检查
curl -f http://localhost/api/health
# 预期: {"database":"connected","status":"healthy","timestamp":"..."}

# 前端页面访问
curl -I http://localhost/
# 预期: HTTP/1.1 200 OK

# 数据库连接验证
docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "SELECT 1;"
# 预期: 返回 "1"

# Redis连接验证
docker exec ssl-manager-redis redis-cli ping
# 预期: "PONG"
```

**3. 监控系统验证**
```bash
# Prometheus监控面板
curl -f http://localhost/prometheus/
# 预期: 重定向到 /graph

# Grafana可视化面板
curl -I http://localhost/grafana/
# 预期: HTTP/1.1 302 Found, Location: /grafana/login

# cAdvisor容器监控 (关键验证!)
curl -f http://localhost:8080/metrics | head -5
# 预期: 返回监控指标数据

# Node Exporter系统监控
curl -f http://localhost:9100/metrics | head -5
# 预期: 返回系统监控指标

# Prometheus targets状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
# 预期: 所有target状态为 "up"
```

**4. 数据持久化验证**
```bash
# 验证数据目录挂载
ls -la /opt/ssl-manager/data/
# 预期: 看到 postgres, redis, prometheus, grafana 目录

# 验证数据库数据持久化
docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "\dt"
# 预期: 显示数据库表结构

# 验证权限设置
ls -la /opt/ssl-manager/data/postgres/ | head -3
# 预期: 所有者为 70:70 (postgres用户)

ls -la /opt/ssl-manager/data/grafana/ | head -3
# 预期: 所有者为 472:472 (grafana用户)
```

**5. 网络和安全验证**
```bash
# 验证端口监听
netstat -tlnp | grep -E ":80|:443|:8080|:9090|:3000"
# 预期: 看到相应端口被Docker进程监听

# 验证防火墙配置 (如果启用)
sudo ufw status
# 或
sudo iptables -L | grep -E "80|443"

# 验证域名解析 (如果配置了域名)
nslookup ssl.gzyggl.com
# 预期: 解析到服务器IP
```

**6. 性能和资源验证**
```bash
# 检查系统资源使用
free -h
# 预期: 内存使用合理，有足够可用内存

# 检查Docker容器资源使用
docker stats --no-stream
# 预期: 各容器CPU和内存使用正常

# 检查磁盘空间
df -h
# 预期: 有足够的磁盘空间
```

## 🔧 服务管理

### 常用管理命令

```bash
# 查看服务状态
docker-compose -f docker-compose.aliyun.yml ps

# 查看服务日志
docker-compose -f docker-compose.aliyun.yml logs -f

# 重启特定服务
docker-compose -f docker-compose.aliyun.yml restart backend

# 停止所有服务
docker-compose -f docker-compose.aliyun.yml down

# 重新构建并启动
docker-compose -f docker-compose.aliyun.yml up -d --build
```

### 数据备份

```bash
# 备份PostgreSQL数据库
docker exec ssl-manager-postgres pg_dump -U ssl_user ssl_manager > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份SSL证书
docker run --rm -v ssl_cert_manager_delivery_ssl_certs:/data -v $(pwd):/backup alpine tar czf /backup/ssl_certs_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# 备份应用日志
docker run --rm -v ssl_cert_manager_delivery_app_logs:/data -v $(pwd):/backup alpine tar czf /backup/app_logs_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

### 数据恢复

```bash
# 恢复PostgreSQL数据库
docker exec -i ssl-manager-postgres psql -U ssl_user -d ssl_manager < backup_20250109_120000.sql

# 恢复SSL证书
docker run --rm -v ssl_cert_manager_delivery_ssl_certs:/data -v $(pwd):/backup alpine tar xzf /backup/ssl_certs_backup_20250109_120000.tar.gz -C /data
```

## 🔍 故障排除

### 常见问题

#### 1. 服务启动失败

```bash
# 检查Docker服务状态
sudo systemctl status docker

# 检查端口占用
netstat -tlnp | grep :80
netstat -tlnp | grep :443

# 查看详细错误日志
docker-compose -f docker-compose.aliyun.yml logs backend
```

#### 2. 数据库连接失败

```bash
# 检查PostgreSQL容器状态
docker ps | grep postgres

# 查看PostgreSQL日志
docker logs ssl-manager-postgres

# 重启PostgreSQL服务
docker-compose -f docker-compose.aliyun.yml restart postgres
```

#### 3. 网络连接问题

```bash
# 测试网络连接
ping 8.8.8.8

# 检查DNS配置
cat /etc/resolv.conf

# 测试阿里云镜像源
curl -I https://mirrors.aliyun.com
```

#### 4. Docker镜像拉取权限错误

```bash
# 检查Docker镜像拉取
docker pull python:3.10-slim

# 如果出现权限错误，检查网络连接
ping docker.io

# 配置阿里云Docker镜像加速器
sudo mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
sudo systemctl restart docker

# 重新拉取镜像
docker pull python:3.10-slim
```

#### 5. PostgreSQL版本兼容性问题

```bash
# 如果遇到PostgreSQL版本不兼容错误
# FATAL: database files are incompatible with server

# 停止服务并清理数据卷
docker-compose -f docker-compose.aliyun.yml down
docker volume rm workspace_postgres_data

# 重新启动服务（会重新初始化数据库）
docker-compose -f docker-compose.aliyun.yml up -d postgres

# 检查PostgreSQL版本
docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "SELECT version();"
```

#### 6. 生产环境部署常见问题

**网络配置冲突**
```bash
# 错误: Pool overlaps with other one on this address space
# 解决方案: 使用默认网络，移除自定义网络配置

# 检查现有网络
docker network ls

# 清理冲突网络
docker network prune -f

# 使用简化的网络配置重新部署
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d
```

**端口占用冲突**
```bash
# 错误: Bind for 0.0.0.0:80 failed: port is already allocated
# 检查端口占用
netstat -tlnp | grep :80
lsof -i :80

# 停止占用端口的服务
sudo systemctl stop apache2  # 如果是Apache
sudo systemctl stop nginx    # 如果是系统nginx

# 或者修改配置使用不同端口
```

**环境变量格式错误**
```bash
# 错误: nc: port number invalid: %!s(int=5432)
# 解决方案: 确保端口号为字符串格式

# 检查.env文件中的端口配置
grep -E "(PORT|port)" .env

# 确保端口号使用引号
DB_PORT="5432"
REDIS_PORT="6379"
```

**数据库密码认证失败**
```bash
# 错误: password authentication failed for user "ssl_user"
# 解决方案: 重新初始化数据库

# 停止服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 删除数据库数据卷
docker volume rm workspace_postgres_data

# 重新启动数据库服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres

# 等待数据库初始化完成
sleep 30

# 测试数据库连接
docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "SELECT 1;"
```

**Nginx配置冲突**
```bash
# 错误: duplicate default server for 0.0.0.0:80
# 解决方案: 使用简化的nginx配置

# 检查nginx配置
docker exec ssl-manager-nginx nginx -t

# 如果配置有误，重新创建容器
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

**Docker镜像拉取超时**
```bash
# 错误: Get "https://gcr.io/v2/": net/http: request canceled while waiting for connection
# 解决方案: 使用国内镜像源或Docker Hub替代

# 检查网络连接
curl -I --connect-timeout 10 https://gcr.io/v2/

# 使用Docker Hub替代gcr.io镜像
# 在docker-compose.prod.yml中修改:
# image: gcr.io/cadvisor/cadvisor:latest
# 改为:
# image: google/cadvisor:latest

# 使用阿里云镜像源（如果可用）
# image: registry.cn-hangzhou.aliyuncs.com/google_containers/prometheus:v2.45.0

# 重新拉取镜像
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
```

**ACME环境变量未设置警告**
```bash
# 警告: The "ACME_EMAIL" variable is not set
# 解决方案: 在.env文件中添加SSL证书相关配置

# 添加到.env文件
echo "# Let's Encrypt SSL证书配置" >> .env
echo "ACME_EMAIL=your-email@example.com" >> .env
echo "ACME_DIRECTORY_URL=https://acme-v02.api.letsencrypt.org/directory" >> .env
echo "ACME_AGREE_TOS=true" >> .env
echo "ACME_CHALLENGE_TYPE=http-01" >> .env

# 测试环境可使用staging URL
# ACME_DIRECTORY_URL=https://acme-staging-v02.api.letsencrypt.org/directory
```

**cAdvisor容器监控问题**
```bash
# 错误: Failed to create a Container Manager: mountpoint for cpu not found
# 解决方案: 优化cAdvisor配置或暂时禁用

# 方案1: 优化配置（在docker-compose.prod.yml中）
volumes:
  - /sys/fs/cgroup:/sys/fs/cgroup:ro
command:
  - '--housekeeping_interval=10s'
  - '--docker_only=true'

# 方案2: 暂时禁用cAdvisor
docker-compose -f docker-compose.yml -f docker-compose.prod.yml stop cadvisor

# 检查其他监控服务是否正常
curl http://localhost:9090/targets  # Prometheus targets
curl http://localhost:9100/metrics  # Node Exporter metrics
```

#### 6. 内存不足

```bash
# 查看内存使用情况
free -h
docker stats

# 调整服务配置（在.env文件中）
BACKEND_WORKERS=1
```

### 性能优化

#### 1. 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化内核参数
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65535" >> /etc/sysctl.conf
sysctl -p
```

#### 2. Docker优化

```bash
# 清理未使用的资源
docker system prune -a

# 优化Docker daemon配置
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

## 🎯 生产环境配置

### 安全加固

```bash
# 修改默认密码
# 1. 登录管理界面修改admin密码
# 2. 修改.env文件中的数据库密码
# 3. 重启服务使配置生效

# 配置SSL证书（Let's Encrypt会自动配置）
# 系统会自动为ssl.gzyggl.com申请SSL证书

# 配置防火墙规则
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 监控配置

```bash
# 访问监控面板
# Grafana: http://ssl.gzyggl.com/monitoring/
# Prometheus: http://ssl.gzyggl.com:9090

# 配置告警（在Grafana中配置）
# 1. 证书过期告警
# 2. 服务状态告警
# 3. 系统资源告警
```

### 定期维护

```bash
# 创建定期备份脚本
cat > /etc/cron.daily/ssl-manager-backup <<EOF
#!/bin/bash
cd /path/to/ssl_cert_manager_delivery
docker exec ssl-manager-postgres pg_dump -U ssl_user ssl_manager > /backup/ssl_manager_\$(date +%Y%m%d).sql
find /backup -name "ssl_manager_*.sql" -mtime +7 -delete
EOF

chmod +x /etc/cron.daily/ssl-manager-backup
```

## 📞 技术支持

如果在部署过程中遇到问题，请：

1. 查看相关日志文件
2. 检查系统资源使用情况
3. 确认网络连接正常
4. 联系技术支持：19822088@qq.com

## 🎉 部署成功

部署成功后，您可以：

1. 访问 http://ssl.gzyggl.com 使用SSL证书管理器
2. 使用默认账户 admin / admin123 登录
3. 在监控面板查看系统状态
4. 开始管理您的SSL证书

**注意**: 请及时修改默认密码并配置适当的安全策略。
