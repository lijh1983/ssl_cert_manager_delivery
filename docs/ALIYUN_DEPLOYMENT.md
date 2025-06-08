# SSL证书管理系统 - 阿里云部署优化指南

本文档专门针对阿里云环境提供SSL证书管理系统的优化部署方案，解决Docker镜像构建速度慢、网络连接问题等常见问题。

## 📋 目录

- [快速开始](#快速开始)
- [阿里云ECS环境准备](#阿里云ecs环境准备)
- [Docker环境优化](#docker环境优化)
- [快速部署指南](#快速部署指南)
- [性能优化方案](#性能优化方案)
- [阿里云特定服务集成](#阿里云特定服务集成)
- [故障排除](#故障排除)
- [性能监控](#性能监控)

## 🚀 快速开始

### 一键优化部署

```bash
# 1. 克隆项目代码
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 2. 配置Docker环境
chmod +x scripts/setup_aliyun_docker.sh
sudo ./scripts/setup_aliyun_docker.sh

# 3. 快速部署
chmod +x scripts/deploy_aliyun.sh
sudo ./scripts/deploy_aliyun.sh --domain your-domain.com --enable-monitoring
```

### 预期部署时间

| 部署方式 | 预期时间 | 说明 |
|---------|----------|------|
| 标准部署 | 90-120分钟 | 使用官方镜像源 |
| 阿里云优化部署 | 10-15分钟 | 使用阿里云镜像加速 |
| 预构建镜像部署 | 3-5分钟 | 使用预构建镜像 |

## 🏗️ 阿里云ECS环境准备

### 推荐实例配置

#### 开发测试环境
```
实例规格: ecs.c6.large (2vCPU 4GB内存)
操作系统: Ubuntu 22.04 LTS 64位
系统盘: 40GB ESSD云盘
网络带宽: 3Mbps
预估费用: ¥200-300/月
```

#### 生产环境
```
实例规格: ecs.c6.xlarge (4vCPU 8GB内存)
操作系统: Ubuntu 22.04 LTS 64位
系统盘: 100GB ESSD云盘
数据盘: 200GB ESSD云盘
网络带宽: 10Mbps
预估费用: ¥800-1200/月
```

#### 高可用环境
```
实例规格: ecs.c6.2xlarge (8vCPU 16GB内存)
部署方式: 多可用区部署（至少2台）
数据库: RDS PostgreSQL 高可用版
缓存: Redis企业版
存储: NAS文件存储
负载均衡: SLB应用型负载均衡
预估费用: ¥3000-5000/月
```

### 安全组配置

#### 入方向规则
```bash
# SSH访问
22/tcp    源地址: 0.0.0.0/0 (建议限制为特定IP)

# HTTP/HTTPS访问
80/tcp    源地址: 0.0.0.0/0
443/tcp   源地址: 0.0.0.0/0

# API访问（可选，建议仅内网）
8000/tcp  源地址: 172.16.0.0/12

# 监控访问（仅内网）
9090/tcp  源地址: 172.16.0.0/12  # Prometheus
3000/tcp  源地址: 172.16.0.0/12  # Grafana
```

#### 出方向规则
```bash
# HTTP/HTTPS访问（用于下载软件包）
80/tcp    目标地址: 0.0.0.0/0
443/tcp   目标地址: 0.0.0.0/0

# DNS解析
53/udp    目标地址: 0.0.0.0/0

# NTP时间同步
123/udp   目标地址: 0.0.0.0/0
```

### 网络配置

#### VPC配置
```bash
# 创建专有网络
VPC网段: 172.16.0.0/12
可用区: 建议选择多个可用区
子网规划:
  - Web层: 172.16.1.0/24
  - 应用层: 172.16.2.0/24
  - 数据层: 172.16.3.0/24
```

#### 域名和SSL配置
```bash
# 域名解析（推荐使用阿里云DNS）
A记录: your-domain.com -> ECS公网IP
CNAME: www.your-domain.com -> your-domain.com

# SSL证书（推荐使用阿里云SSL证书服务）
证书类型: DV SSL证书（免费）或 OV/EV SSL证书（付费）
自动续期: 开启
```

## 🔧 Docker环境优化

### 自动化Docker环境配置

使用我们提供的自动化脚本来配置Docker环境：

```bash
# 下载并运行Docker优化脚本
wget https://raw.githubusercontent.com/lijh1983/ssl_cert_manager_delivery/main/scripts/setup_aliyun_docker.sh
chmod +x setup_aliyun_docker.sh
sudo ./setup_aliyun_docker.sh
```

### 手动Docker配置（可选）

如果需要手动配置，请按以下步骤操作：

#### 1. 配置阿里云Docker镜像加速器

```bash
# 创建Docker配置目录
sudo mkdir -p /etc/docker

# 配置镜像加速器和优化参数
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com"
    ],
    "insecure-registries": [],
    "debug": false,
    "experimental": false,
    "features": {
        "buildkit": true
    },
    "builder": {
        "gc": {
            "enabled": true,
            "defaultKeepStorage": "20GB"
        }
    },
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "storage-driver": "overlay2",
    "storage-opts": [
        "overlay2.override_kernel_check=true"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    }
}
EOF

# 重启Docker服务
sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 2. 配置Docker BuildKit

```bash
# 启用BuildKit环境变量
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# 创建新的builder实例
docker buildx create --name aliyun-builder --driver docker-container --use
docker buildx inspect --bootstrap

# 验证配置
docker buildx ls
```

#### 3. 优化系统参数

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化内核参数
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# Docker优化参数
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
vm.max_map_count = 262144
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
EOF

# 应用内核参数
sudo sysctl -p
```

### 软件源优化配置

#### APT源配置（Ubuntu 22.04）

```bash
# 备份原始源
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup

# 配置阿里云Ubuntu 22.04源
sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 阿里云Ubuntu 22.04 LTS源
deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse

# 源码包（可选）
# deb-src http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
EOF

# 更新软件包列表
sudo apt-get update
```

#### NPM源配置

```bash
# 方法1: 使用npm配置
npm config set registry https://registry.npmmirror.com
npm config set disturl https://npmmirror.com/dist
npm config set electron_mirror https://npmmirror.com/mirrors/electron/
npm config set sass_binary_site https://npmmirror.com/mirrors/node-sass/

# 方法2: 使用pnpm（推荐，速度更快）
npm install -g pnpm
pnpm config set registry https://registry.npmmirror.com

# 验证配置
npm config get registry
```

#### Python PIP源配置

```bash
# 全局配置
sudo mkdir -p /etc/pip
sudo tee /etc/pip/pip.conf > /dev/null <<EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
EOF

# 用户配置
mkdir -p ~/.pip
cat > ~/.pip/pip.conf <<EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
EOF

# 验证配置
pip config list
```

#### 其他软件源配置

```bash
# Docker CE源（如果需要安装最新版Docker）
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Node.js源
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
```

## 🚀 快速部署指南

### 方案一：一键自动部署（推荐）

这是最简单的部署方式，适合大多数用户：

```bash
# 1. 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 2. 运行一键部署脚本
chmod +x scripts/deploy_aliyun.sh
sudo ./scripts/deploy_aliyun.sh --domain your-domain.com --email admin@your-domain.com --enable-monitoring

# 部署完成后访问
# 前端: http://your-domain.com
# 后端API: http://your-domain.com:8000
# Grafana: http://your-domain.com:3000
```

### 方案二：分步部署

如果需要更多控制，可以分步执行：

#### 步骤1: 环境准备

```bash
# 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 配置Docker环境
chmod +x scripts/setup_aliyun_docker.sh
sudo ./scripts/setup_aliyun_docker.sh
```

#### 步骤2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

关键环境变量配置：

```bash
# 基础配置
ENVIRONMENT=production
DOMAIN_NAME=your-domain.com

# 数据库配置
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=your-secure-password

# Redis配置
REDIS_PASSWORD=your-redis-password

# 安全配置
SECRET_KEY=your-secret-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars

# SSL配置
ACME_EMAIL=admin@your-domain.com
ACME_DIRECTORY_URL=https://acme-v02.api.letsencrypt.org/directory

# 监控配置
GRAFANA_USER=admin
GRAFANA_PASSWORD=your-grafana-password
```

#### 步骤3: 启动服务

```bash
# 使用阿里云优化配置启动
docker-compose -f docker-compose.aliyun.yml up -d

# 查看服务状态
docker-compose -f docker-compose.aliyun.yml ps

# 查看日志
docker-compose -f docker-compose.aliyun.yml logs -f
```

### 方案三：预构建镜像部署（最快）

如果需要最快的部署速度：

```bash
# 1. 预构建镜像
chmod +x scripts/prebuild_images.sh
./scripts/prebuild_images.sh

# 2. 使用快速配置部署
docker-compose -f docker-compose.fast.yml up -d

# 预期部署时间: 3-5分钟
```

### 部署验证

部署完成后，执行以下命令验证：

```bash
# 检查服务状态
curl -f http://localhost:8000/health

# 检查前端
curl -f http://localhost:80/health

# 查看所有容器状态
docker ps

# 检查资源使用
docker stats
```

### 环境变量详细说明

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `DOMAIN_NAME` | 是 | localhost | 主域名 |
| `DB_PASSWORD` | 是 | - | 数据库密码 |
| `REDIS_PASSWORD` | 是 | - | Redis密码 |
| `SECRET_KEY` | 是 | - | 应用密钥（至少32字符） |
| `JWT_SECRET_KEY` | 是 | - | JWT密钥（至少32字符） |
| `ACME_EMAIL` | 是 | - | Let's Encrypt邮箱 |
| `GRAFANA_PASSWORD` | 否 | admin | Grafana密码 |
| `BACKEND_WORKERS` | 否 | 2 | 后端工作进程数 |
| `ENABLE_MONITORING` | 否 | true | 是否启用监控 |

## ⚡ 性能优化方案

### 构建时间优化

#### 1. 镜像加速器优化

```bash
# 验证镜像加速器配置
docker info | grep -A 10 "Registry Mirrors"

# 测试拉取速度
time docker pull registry.cn-hangzhou.aliyuncs.com/library/node:18-alpine
```

#### 2. 预构建基础镜像

```bash
# 预构建基础镜像，减少重复构建时间
chmod +x scripts/prebuild_images.sh
./scripts/prebuild_images.sh --acr-namespace your-namespace

# 预期效果：减少80%的构建时间
```

#### 3. 并行构建策略

```bash
# 启用BuildKit并行构建
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# 并行构建前端和后端
docker build -f backend/Dockerfile.aliyun -t ssl-manager-backend:aliyun ./backend &
BACKEND_PID=$!

docker build -f frontend/Dockerfile.aliyun -t ssl-manager-frontend:aliyun ./frontend &
FRONTEND_PID=$!

# 等待构建完成
wait $BACKEND_PID && echo "后端构建完成"
wait $FRONTEND_PID && echo "前端构建完成"
```

#### 4. 构建缓存优化

```bash
# 创建.dockerignore文件减少构建上下文
cat > frontend/.dockerignore <<EOF
node_modules
*.log
.git
.gitignore
README.md
.env
.env.local
.env.*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
EOF

cat > backend/.dockerignore <<EOF
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
EOF
```

### 运行时性能优化

#### 1. 容器资源限制

```yaml
# docker-compose.aliyun.yml中的资源配置
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'

  frontend:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
        reservations:
          memory: 128M
          cpus: '0.1'
```

#### 2. 数据库性能优化

```bash
# PostgreSQL性能参数
docker run -d \
  --name ssl-manager-postgres \
  -e POSTGRES_DB=ssl_manager \
  -e POSTGRES_USER=ssl_user \
  -e POSTGRES_PASSWORD=your-password \
  registry.cn-hangzhou.aliyuncs.com/library/postgres:15-alpine \
  postgres \
  -c shared_buffers=256MB \
  -c effective_cache_size=1GB \
  -c maintenance_work_mem=64MB \
  -c checkpoint_completion_target=0.9 \
  -c wal_buffers=16MB \
  -c default_statistics_target=100 \
  -c random_page_cost=1.1 \
  -c effective_io_concurrency=200 \
  -c work_mem=4MB
```

#### 3. Redis性能优化

```bash
# Redis性能参数
docker run -d \
  --name ssl-manager-redis \
  registry.cn-hangzhou.aliyuncs.com/library/redis:7-alpine \
  redis-server \
  --appendonly yes \
  --maxmemory 512mb \
  --maxmemory-policy allkeys-lru \
  --save 900 1 \
  --save 300 10 \
  --save 60 10000
```

### 网络性能优化

#### 1. 使用阿里云内网

```bash
# 配置内网DNS
echo "nameserver 100.100.2.136" | sudo tee /etc/resolv.conf
echo "nameserver 100.100.2.138" | sudo tee -a /etc/resolv.conf

# 验证内网连通性
ping registry-vpc.cn-hangzhou.aliyuncs.com
```

#### 2. CDN加速（可选）

```bash
# 如果使用阿里云CDN，配置静态资源加速
# 在nginx配置中添加CDN域名
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    # 可选：重定向到CDN
    # return 301 https://cdn.your-domain.com$request_uri;
}
```

## 🌐 阿里云特定服务集成

### 容器镜像服务（ACR）

#### 配置ACR

```bash
# 1. 登录阿里云容器镜像服务
docker login --username=your-username registry.cn-hangzhou.aliyuncs.com

# 2. 创建命名空间（在阿里云控制台或使用CLI）
# 命名空间名称: ssl-manager

# 3. 推送镜像到ACR
docker tag ssl-manager-backend:aliyun registry.cn-hangzhou.aliyuncs.com/ssl-manager/backend:latest
docker tag ssl-manager-frontend:aliyun registry.cn-hangzhou.aliyuncs.com/ssl-manager/frontend:latest

docker push registry.cn-hangzhou.aliyuncs.com/ssl-manager/backend:latest
docker push registry.cn-hangzhou.aliyuncs.com/ssl-manager/frontend:latest
```

#### 使用ACR镜像部署

```yaml
# docker-compose.acr.yml
version: '3.8'
services:
  backend:
    image: registry.cn-hangzhou.aliyuncs.com/ssl-manager/backend:latest
    # 其他配置...

  frontend:
    image: registry.cn-hangzhou.aliyuncs.com/ssl-manager/frontend:latest
    # 其他配置...
```

### 负载均衡器（SLB）

#### 应用型负载均衡配置

```bash
# 1. 创建应用型负载均衡实例
# 实例类型: 应用型负载均衡ALB
# 网络类型: 公网
# IP版本: IPv4

# 2. 配置监听器
# 协议: HTTPS
# 端口: 443
# SSL证书: 选择已有证书或上传新证书

# 3. 配置后端服务器组
# 后端协议: HTTP
# 后端端口: 80
# 健康检查路径: /health
# 健康检查间隔: 30秒
```

#### SLB配置示例

```json
{
  "LoadBalancerName": "ssl-manager-alb",
  "LoadBalancerSpec": "slb.s2.small",
  "AddressType": "internet",
  "VSwitchId": "vsw-xxxxxxxxx",
  "Listeners": [
    {
      "Protocol": "HTTPS",
      "LoadBalancerPort": 443,
      "BackendServerPort": 80,
      "Bandwidth": 10,
      "HealthCheck": "on",
      "HealthCheckURI": "/health",
      "HealthCheckInterval": 30
    }
  ]
}
```

### RDS数据库服务

#### 高可用RDS配置

```bash
# 1. 创建RDS PostgreSQL实例
# 数据库类型: PostgreSQL 15
# 实例规格: pg.n2.medium.1 (1核2GB)
# 存储类型: ESSD云盘
# 存储空间: 100GB
# 可用区: 多可用区部署

# 2. 配置数据库
# 数据库名: ssl_manager
# 用户名: ssl_user
# 密码: 强密码
```

#### 连接RDS数据库

```bash
# 修改环境变量
DB_HOST=rm-xxxxxxxxx.mysql.rds.aliyuncs.com
DB_PORT=5432
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=your-rds-password

# 配置白名单
# 在RDS控制台添加ECS内网IP到白名单
```

### Redis企业版

#### 配置Redis企业版

```bash
# 1. 创建Redis企业版实例
# 实例类型: Redis企业版
# 版本: Redis 7.0
# 实例规格: redis.master.micro.default (1GB)
# 网络类型: 专有网络VPC

# 2. 配置连接信息
REDIS_HOST=r-xxxxxxxxx.redis.rds.aliyuncs.com
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
```

### 对象存储（OSS）

#### 配置OSS存储

```bash
# 1. 创建OSS Bucket
# Bucket名称: ssl-manager-storage
# 地域: 华东1（杭州）
# 存储类型: 标准存储
# 读写权限: 私有

# 2. 配置访问密钥
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_BUCKET=ssl-manager-storage
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

#### OSS集成代码示例

```python
# backend/src/utils/oss_client.py
import oss2

class OSSClient:
    def __init__(self):
        auth = oss2.Auth(
            os.getenv('OSS_ACCESS_KEY_ID'),
            os.getenv('OSS_ACCESS_KEY_SECRET')
        )
        self.bucket = oss2.Bucket(
            auth,
            os.getenv('OSS_ENDPOINT'),
            os.getenv('OSS_BUCKET')
        )

    def upload_certificate(self, cert_id, cert_data):
        key = f"certificates/{cert_id}/cert.pem"
        return self.bucket.put_object(key, cert_data)
```

### 日志服务（SLS）

#### 配置日志收集

```bash
# 1. 创建日志项目
# 项目名称: ssl-manager-logs
# 地域: 华东1（杭州）

# 2. 创建日志库
# 日志库名称: application-logs
# 数据保存时间: 30天
# 分片数: 2
```

#### Logtail配置

```json
{
  "configName": "ssl-manager-config",
  "inputType": "file",
  "inputDetail": {
    "logType": "json_log",
    "logPath": "/opt/ssl-manager/logs",
    "filePattern": "*.log",
    "dockerFile": true,
    "dockerIncludeLabel": {
      "com.docker.compose.service": "backend"
    }
  },
  "outputType": "LogService",
  "outputDetail": {
    "projectName": "ssl-manager-logs",
    "logstoreName": "application-logs"
  }
}
```

### 云监控服务

#### 配置自定义监控

```bash
# 1. 安装云监控Agent
wget http://cms-download.aliyun.com/cms-go-agent/1.3.7/cms-go-agent-linux-amd64.tar.gz
tar -xzf cms-go-agent-linux-amd64.tar.gz
sudo ./cms-go-agent-linux-amd64/install.sh

# 2. 配置自定义监控指标
curl -X POST http://localhost:8000/metrics | \
  curl -X POST "http://metrichub-cn-hangzhou.aliyun.com/metric/custom/upload" \
  -H "Authorization: your-access-key" \
  -d @-
```

## 📊 监控和日志

### 云监控配置

```bash
# 安装云监控Agent
wget http://cms-download.aliyun.com/cms-go-agent/1.3.7/cms-go-agent-linux-amd64.tar.gz
tar -xzf cms-go-agent-linux-amd64.tar.gz
sudo ./cms-go-agent-linux-amd64/install.sh
```

### 日志服务SLS

```bash
# 安装Logtail
wget http://logtail-release-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/linux64/logtail.sh
sudo sh logtail.sh install cn-hangzhou
```

## 🔒 安全配置

### SSL证书配置

```bash
# 使用阿里云SSL证书服务
# 或配置Let's Encrypt
certbot --nginx -d your-domain.com
```

### 访问控制

```bash
# 配置WAF（Web应用防火墙）
# 配置DDoS防护
# 配置安全组规则
```

## 💾 数据备份

### 自动备份脚本

```bash
#!/bin/bash
# 数据备份到OSS
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
docker exec ssl-manager-postgres pg_dump -U ssl_user ssl_manager > backup_${DATE}.sql

# 上传到OSS
ossutil cp backup_${DATE}.sql oss://your-bucket/backups/

# 清理本地备份
find . -name "backup_*.sql" -mtime +7 -delete
```

## 🔧 故障排除

### 常见问题及解决方案

#### 1. Docker镜像构建/拉取问题

**问题**: 镜像拉取速度极慢或超时
```bash
# 诊断步骤
# 1. 检查镜像加速器配置
docker info | grep -A 10 "Registry Mirrors"

# 2. 测试网络连通性
ping registry.cn-hangzhou.aliyuncs.com
telnet registry.cn-hangzhou.aliyuncs.com 443

# 3. 检查DNS解析
nslookup registry.cn-hangzhou.aliyuncs.com

# 解决方案
# 重新配置镜像加速器
sudo ./scripts/setup_aliyun_docker.sh

# 手动拉取基础镜像
docker pull registry.cn-hangzhou.aliyuncs.com/library/node:18-alpine
docker pull registry.cn-hangzhou.aliyuncs.com/library/python:3.10-slim
```

**问题**: 构建超时或失败
```bash
# 增加构建超时时间
export DOCKER_CLIENT_TIMEOUT=600
export COMPOSE_HTTP_TIMEOUT=600

# 使用预构建镜像
./scripts/prebuild_images.sh
docker-compose -f docker-compose.fast.yml up -d

# 清理构建缓存
docker builder prune -a
docker system prune -a
```

#### 2. 网络连接问题

**问题**: 容器间网络不通
```bash
# 检查网络配置
docker network ls
docker network inspect ssl-manager-network

# 检查容器IP
docker inspect ssl-manager-backend | grep IPAddress

# 测试容器间连通性
docker exec ssl-manager-backend ping ssl-manager-postgres
```

**问题**: 外网访问问题
```bash
# 检查安全组配置
# 确保开放80、443、8000端口

# 检查防火墙
sudo ufw status
sudo iptables -L

# 检查服务绑定
netstat -tlnp | grep -E ':(80|443|8000)'
```

#### 3. 资源不足问题

**问题**: 内存不足
```bash
# 检查系统资源
free -h
df -h
docker stats

# 清理系统资源
# 清理Docker资源
docker system prune -a
docker volume prune
docker image prune -a

# 清理系统缓存
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# 调整容器资源限制
# 编辑docker-compose.aliyun.yml中的resources配置
```

**问题**: 磁盘空间不足
```bash
# 检查磁盘使用
df -h
du -sh /var/lib/docker

# 清理Docker数据
docker system df
docker system prune -a --volumes

# 清理日志文件
sudo find /var/log -name "*.log" -type f -size +100M -delete
sudo journalctl --vacuum-time=7d
```

#### 4. 服务启动问题

**问题**: 数据库连接失败
```bash
# 检查数据库状态
docker logs ssl-manager-postgres
docker exec ssl-manager-postgres pg_isready -U ssl_user

# 检查网络连通性
docker exec ssl-manager-backend nc -zv postgres 5432

# 重置数据库
docker-compose down
docker volume rm ssl_manager_postgres_data
docker-compose up -d postgres
```

**问题**: 应用启动失败
```bash
# 查看应用日志
docker logs ssl-manager-backend
docker logs ssl-manager-frontend

# 检查环境变量
docker exec ssl-manager-backend env | grep -E '(DB_|REDIS_|SECRET_)'

# 手动启动调试
docker exec -it ssl-manager-backend bash
python src/app.py
```

#### 5. 性能问题

**问题**: 响应速度慢
```bash
# 检查系统负载
htop
iotop
nethogs

# 检查容器资源使用
docker stats

# 优化建议
# 1. 增加ECS实例规格
# 2. 使用SSD磁盘
# 3. 配置Redis缓存
# 4. 启用CDN加速
```

### 调试工具和命令

#### 系统诊断
```bash
# 系统信息
uname -a
lsb_release -a
free -h
df -h
lscpu

# 网络诊断
ss -tlnp
netstat -rn
ping -c 4 8.8.8.8
curl -I http://www.baidu.com
```

#### Docker诊断
```bash
# Docker信息
docker version
docker info
docker system df
docker system events --since 1h

# 容器诊断
docker ps -a
docker logs --tail 100 container_name
docker exec -it container_name bash
docker inspect container_name
```

#### 应用诊断
```bash
# 健康检查
curl -f http://localhost:8000/health
curl -f http://localhost:80/health

# API测试
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# 数据库连接测试
docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "SELECT version();"
```

## 📈 性能监控

### 关键性能指标（KPI）

#### 系统级指标
| 指标 | 正常范围 | 警告阈值 | 严重阈值 | 监控方法 |
|------|----------|----------|----------|----------|
| CPU使用率 | < 70% | 70-85% | > 85% | `htop`, `top` |
| 内存使用率 | < 80% | 80-90% | > 90% | `free -h` |
| 磁盘使用率 | < 85% | 85-95% | > 95% | `df -h` |
| 磁盘IO等待 | < 10% | 10-20% | > 20% | `iotop` |
| 网络延迟 | < 50ms | 50-100ms | > 100ms | `ping` |
| 负载均衡 | < 核心数 | 核心数-2倍 | > 2倍核心数 | `uptime` |

#### 应用级指标
| 指标 | 正常范围 | 警告阈值 | 严重阈值 | 监控方法 |
|------|----------|----------|----------|----------|
| API响应时间 | < 200ms | 200-500ms | > 500ms | `/health` 端点 |
| 数据库连接时间 | < 100ms | 100-300ms | > 300ms | 连接池监控 |
| 证书检查时间 | < 5s | 5-10s | > 10s | 应用日志 |
| 错误率 | < 1% | 1-5% | > 5% | 错误日志统计 |
| 并发连接数 | < 100 | 100-500 | > 500 | Nginx状态 |

#### 部署相关指标
| 指标 | 目标值 | 优化后 | 说明 |
|------|--------|--------|------|
| Docker镜像拉取时间 | < 5分钟 | < 1分钟 | 使用阿里云镜像加速 |
| 应用构建时间 | < 15分钟 | < 3分钟 | 预构建镜像 |
| 应用启动时间 | < 2分钟 | < 30秒 | 优化启动脚本 |
| 健康检查响应 | < 3秒 | < 1秒 | 轻量级检查 |

### 监控工具和命令

#### 实时系统监控
```bash
# 系统资源实时监控
htop                    # 进程和CPU监控
iotop                   # 磁盘IO监控
nethogs                 # 网络流量监控
vmstat 1                # 系统统计信息
iostat -x 1             # 磁盘IO统计

# 网络监控
ss -tuln                # 网络连接状态
netstat -i              # 网络接口统计
iftop                   # 网络流量实时监控
```

#### Docker容器监控
```bash
# 容器资源监控
docker stats                              # 实时资源使用
docker stats --no-stream                  # 一次性资源快照
docker system df                          # Docker磁盘使用
docker system events --since 1h           # Docker事件日志

# 容器详细信息
docker inspect ssl-manager-backend        # 容器详细配置
docker logs --tail 100 ssl-manager-backend # 容器日志
docker exec ssl-manager-backend ps aux    # 容器内进程
```

#### 应用性能监控
```bash
# 健康检查监控
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# 创建curl格式文件
cat > curl-format.txt <<EOF
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF

# API性能测试
ab -n 100 -c 10 http://localhost:8000/health
wrk -t12 -c400 -d30s http://localhost:8000/health

# 数据库性能监控
docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public';"
```

### 自动化监控脚本

#### 系统监控脚本
```bash
#!/bin/bash
# 创建监控脚本
cat > monitor.sh <<'EOF'
#!/bin/bash

LOG_FILE="/var/log/ssl-manager-monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 系统资源检查
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
MEM_USAGE=$(free | grep Mem | awk '{printf("%.1f"), $3/$2 * 100.0}')
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

# 应用健康检查
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80/health)

# 记录日志
echo "[$DATE] CPU: ${CPU_USAGE}%, MEM: ${MEM_USAGE}%, DISK: ${DISK_USAGE}%, BACKEND: $BACKEND_STATUS, FRONTEND: $FRONTEND_STATUS" >> $LOG_FILE

# 告警检查
if (( $(echo "$CPU_USAGE > 85" | bc -l) )); then
    echo "[$DATE] ALERT: High CPU usage: ${CPU_USAGE}%" >> $LOG_FILE
fi

if (( $(echo "$MEM_USAGE > 90" | bc -l) )); then
    echo "[$DATE] ALERT: High memory usage: ${MEM_USAGE}%" >> $LOG_FILE
fi

if [ "$BACKEND_STATUS" != "200" ]; then
    echo "[$DATE] ALERT: Backend health check failed: $BACKEND_STATUS" >> $LOG_FILE
fi
EOF

chmod +x monitor.sh

# 添加到crontab（每分钟执行一次）
(crontab -l 2>/dev/null; echo "* * * * * /path/to/monitor.sh") | crontab -
```

#### 性能报告生成
```bash
#!/bin/bash
# 性能报告生成脚本
cat > performance_report.sh <<'EOF'
#!/bin/bash

REPORT_FILE="performance_report_$(date +%Y%m%d_%H%M%S).txt"

echo "SSL证书管理系统性能报告" > $REPORT_FILE
echo "生成时间: $(date)" >> $REPORT_FILE
echo "======================================" >> $REPORT_FILE

# 系统信息
echo "" >> $REPORT_FILE
echo "系统信息:" >> $REPORT_FILE
uname -a >> $REPORT_FILE
lscpu | grep -E "(Model name|CPU\(s\)|Thread)" >> $REPORT_FILE
free -h >> $REPORT_FILE
df -h >> $REPORT_FILE

# Docker信息
echo "" >> $REPORT_FILE
echo "Docker信息:" >> $REPORT_FILE
docker version --format '{{.Server.Version}}' >> $REPORT_FILE
docker system df >> $REPORT_FILE

# 容器状态
echo "" >> $REPORT_FILE
echo "容器状态:" >> $REPORT_FILE
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" >> $REPORT_FILE

# 应用性能
echo "" >> $REPORT_FILE
echo "应用性能测试:" >> $REPORT_FILE
curl -w "后端响应时间: %{time_total}s\n" -o /dev/null -s http://localhost:8000/health >> $REPORT_FILE
curl -w "前端响应时间: %{time_total}s\n" -o /dev/null -s http://localhost:80/health >> $REPORT_FILE

# 资源使用
echo "" >> $REPORT_FILE
echo "资源使用情况:" >> $REPORT_FILE
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" >> $REPORT_FILE

echo "报告生成完成: $REPORT_FILE"
EOF

chmod +x performance_report.sh
```

### Prometheus + Grafana监控

#### 启用监控服务
```bash
# 启动监控服务
docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d

# 访问监控界面
# Prometheus: http://your-server-ip:9090
# Grafana: http://your-server-ip:3000 (admin/admin)
```

#### 自定义监控指标
```bash
# 添加自定义指标到应用
curl http://localhost:8000/metrics

# 示例输出:
# ssl_manager_certificates_total 150
# ssl_manager_certificates_expired 5
# ssl_manager_servers_total 10
# ssl_manager_api_requests_total 1000
```

### 性能优化建议

#### 基于监控结果的优化
1. **CPU使用率高**: 增加ECS实例规格或启用负载均衡
2. **内存使用率高**: 优化应用内存使用或增加内存
3. **磁盘IO高**: 使用SSD磁盘或优化数据库查询
4. **网络延迟高**: 使用CDN或优化网络配置
5. **应用响应慢**: 启用缓存或优化代码逻辑

#### 持续优化策略
```bash
# 定期性能测试
./scripts/test_deployment.sh

# 定期清理资源
docker system prune -a
sudo journalctl --vacuum-time=7d

# 定期更新镜像
docker-compose pull
docker-compose up -d
```

## 🎯 最佳实践总结

### 部署优化最佳实践

#### 1. 镜像和构建优化
- ✅ **使用阿里云镜像源**: 显著提升下载速度（50-70%提升）
- ✅ **预构建基础镜像**: 减少重复构建时间（80%时间节省）
- ✅ **并行构建**: 充分利用多核CPU（40-60%时间节省）
- ✅ **使用ACR**: 镜像分发更快，支持内网传输
- ✅ **优化Dockerfile**: 合理分层，减少镜像大小

#### 2. 网络和连接优化
- ✅ **配置专有网络VPC**: 提高安全性和性能
- ✅ **使用内网连接**: 降低延迟和成本
- ✅ **配置负载均衡**: 提高可用性和性能
- ✅ **启用CDN**: 加速静态资源访问

#### 3. 监控和运维
- ✅ **配置全面监控**: 及时发现和解决问题
- ✅ **设置告警规则**: 主动监控关键指标
- ✅ **定期性能测试**: 确保系统性能稳定
- ✅ **自动化运维**: 减少人工干预和错误

#### 4. 安全和备份
- ✅ **定期数据备份**: 保障数据安全
- ✅ **安全组配置**: 最小权限原则
- ✅ **SSL证书管理**: 自动续期和监控
- ✅ **访问控制**: 强密码和多因素认证

#### 5. 性能调优
- ✅ **资源合理配置**: 根据实际负载调整
- ✅ **数据库优化**: 索引和查询优化
- ✅ **缓存策略**: 减少重复计算和查询
- ✅ **代码优化**: 异步处理和性能优化

### 部署时间对比

| 部署方式 | 构建时间 | 启动时间 | 总时间 | 优化效果 |
|---------|----------|----------|--------|----------|
| 标准部署 | 90-120分钟 | 5-10分钟 | 95-130分钟 | 基准 |
| 阿里云优化 | 10-15分钟 | 2-3分钟 | 12-18分钟 | 85%提升 |
| 预构建镜像 | 2-3分钟 | 1-2分钟 | 3-5分钟 | 95%提升 |

### 成本优化建议

#### 1. 计算资源优化
```bash
# 开发环境: ecs.c6.large (2vCPU 4GB) - ¥200-300/月
# 生产环境: ecs.c6.xlarge (4vCPU 8GB) - ¥800-1200/月
# 高可用环境: ecs.c6.2xlarge (8vCPU 16GB) × 2 - ¥3000-5000/月
```

#### 2. 存储成本优化
```bash
# 使用ESSD云盘提高性能
# 配置自动快照策略
# 定期清理无用数据和日志
```

#### 3. 网络成本优化
```bash
# 使用内网传输减少公网流量
# 配置CDN减少源站带宽消耗
# 合理配置带宽规格
```

### 故障恢复策略

#### 1. 数据备份策略
```bash
# 数据库备份: 每日自动备份，保留30天
# 文件备份: 每周备份到OSS，保留3个月
# 配置备份: 版本控制，随时可恢复
```

#### 2. 灾难恢复计划
```bash
# RTO (恢复时间目标): < 1小时
# RPO (恢复点目标): < 24小时
# 多可用区部署: 自动故障转移
# 备用环境: 快速切换能力
```

### 扩展性规划

#### 1. 水平扩展
```bash
# 使用负载均衡器分发请求
# 数据库读写分离
# 微服务架构拆分
# 容器编排（Kubernetes）
```

#### 2. 垂直扩展
```bash
# 根据监控数据调整实例规格
# 优化数据库配置参数
# 增加缓存容量
# 升级存储性能
```

### 联系和支持

#### 技术支持
- **GitHub Issues**: https://github.com/lijh1983/ssl_cert_manager_delivery/issues
- **文档更新**: 定期更新部署文档和最佳实践
- **社区支持**: 欢迎提交PR和改进建议

#### 阿里云技术支持
- **工单系统**: 阿里云控制台提交工单
- **技术论坛**: 阿里云开发者社区
- **文档中心**: https://help.aliyun.com/

---

## 📚 相关文档

- [主要部署文档](DEPLOYMENT.md) - 通用部署指南
- [用户手册](USER_GUIDE.md) - 系统使用说明
- [API文档](API.md) - 接口文档
- [开发指南](DEVELOPMENT.md) - 开发环境配置
- [安全指南](SECURITY.md) - 安全配置说明

---

**通过本指南的优化配置，您可以将Docker镜像构建时间从100分钟缩短到10-15分钟，显著提升部署效率和用户体验。**
