# 阿里云部署优化指南

本文档专门针对阿里云环境提供SSL证书管理系统的优化部署方案。

## 🚀 快速开始

### 一键优化部署

```bash
# 1. 下载优化脚本
wget https://raw.githubusercontent.com/lijh1983/ssl_cert_manager_delivery/main/scripts/setup_aliyun_docker.sh
chmod +x setup_aliyun_docker.sh

# 2. 配置Docker环境
sudo ./setup_aliyun_docker.sh

# 3. 快速部署
wget https://raw.githubusercontent.com/lijh1983/ssl_cert_manager_delivery/main/scripts/deploy_aliyun.sh
chmod +x deploy_aliyun.sh
sudo ./deploy_aliyun.sh --domain your-domain.com --enable-monitoring
```

## 🏗️ 阿里云ECS推荐配置

### 基础配置
- **实例规格**: ecs.c6.large (2vCPU 4GB)
- **操作系统**: Ubuntu 20.04 LTS
- **系统盘**: 40GB ESSD云盘
- **网络**: 专有网络VPC
- **安全组**: 开放80、443、22端口

### 生产环境配置
- **实例规格**: ecs.c6.xlarge (4vCPU 8GB)
- **操作系统**: Ubuntu 22.04 LTS
- **系统盘**: 100GB ESSD云盘
- **数据盘**: 200GB ESSD云盘（用于数据存储）
- **网络**: 专有网络VPC + 负载均衡SLB
- **安全组**: 精细化端口控制

### 高可用配置
- **实例规格**: ecs.c6.2xlarge (8vCPU 16GB)
- **部署方式**: 多可用区部署
- **数据库**: RDS PostgreSQL
- **缓存**: Redis企业版
- **存储**: NAS文件存储
- **监控**: 云监控 + 日志服务SLS

## 🔧 Docker优化配置

### 镜像加速器配置

```bash
# 配置阿里云Docker镜像加速器
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com"
    ],
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

### BuildKit优化

```bash
# 启用BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# 配置BuildKit
docker buildx create --name aliyun-builder --driver docker-container --use
docker buildx inspect --bootstrap
```

## 📦 软件源优化

### APT源配置（Ubuntu/Debian）

```bash
# 备份原始源
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup

# 配置阿里云源
sudo tee /etc/apt/sources.list > /dev/null <<EOF
deb http://mirrors.aliyun.com/ubuntu/ focal main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ focal-security main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ focal-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ focal-backports main restricted universe multiverse
EOF

sudo apt-get update
```

### NPM源配置

```bash
# 配置淘宝NPM镜像
npm config set registry https://registry.npmmirror.com
npm config set disturl https://npmmirror.com/dist

# 或使用pnpm（更快）
npm install -g pnpm
pnpm config set registry https://registry.npmmirror.com
```

### Python PIP源配置

```bash
# 创建pip配置目录
mkdir -p ~/.pip

# 配置清华大学镜像源
cat > ~/.pip/pip.conf <<EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

## 🐳 容器镜像服务（ACR）

### 配置ACR

```bash
# 登录阿里云容器镜像服务
docker login --username=your-username registry.cn-hangzhou.aliyuncs.com

# 推送镜像到ACR
docker tag ssl-manager-backend:latest registry.cn-hangzhou.aliyuncs.com/your-namespace/ssl-manager-backend:latest
docker push registry.cn-hangzhou.aliyuncs.com/your-namespace/ssl-manager-backend:latest
```

### 使用ACR镜像

```yaml
# docker-compose.yml中使用ACR镜像
services:
  backend:
    image: registry.cn-hangzhou.aliyuncs.com/your-namespace/ssl-manager-backend:latest
  frontend:
    image: registry.cn-hangzhou.aliyuncs.com/your-namespace/ssl-manager-frontend:latest
```

## 🚀 性能优化策略

### 1. 预构建镜像

```bash
# 运行预构建脚本
chmod +x scripts/prebuild_images.sh
./scripts/prebuild_images.sh --acr-namespace your-namespace
```

### 2. 并行构建

```bash
# 使用并行构建
docker build -f backend/Dockerfile.aliyun -t ssl-manager-backend:aliyun ./backend &
docker build -f frontend/Dockerfile.aliyun -t ssl-manager-frontend:aliyun ./frontend &
wait
```

### 3. 多阶段构建优化

```dockerfile
# 使用.dockerignore减少构建上下文
echo "node_modules" > frontend/.dockerignore
echo "*.log" >> frontend/.dockerignore
echo ".git" >> frontend/.dockerignore
```

### 4. 缓存优化

```bash
# 使用构建缓存
docker build --cache-from ssl-manager-backend:latest -t ssl-manager-backend:new ./backend
```

## 🌐 网络优化

### 安全组配置

```bash
# 创建安全组规则
# 入方向规则
22/tcp    SSH访问
80/tcp    HTTP访问
443/tcp   HTTPS访问
8000/tcp  API访问（可选，内网访问）

# 出方向规则
80/tcp    HTTP访问
443/tcp   HTTPS访问
53/udp    DNS解析
```

### 负载均衡配置

```bash
# 使用阿里云SLB进行负载均衡
# 后端服务器组：多个ECS实例
# 健康检查：HTTP /health
# 会话保持：基于Cookie
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

### 常见问题

#### 1. 镜像拉取慢
```bash
# 检查镜像加速器配置
docker info | grep -A 10 "Registry Mirrors"

# 手动拉取基础镜像
docker pull registry.cn-hangzhou.aliyuncs.com/library/node:18-alpine
```

#### 2. 构建超时
```bash
# 增加构建超时时间
export DOCKER_CLIENT_TIMEOUT=300
export COMPOSE_HTTP_TIMEOUT=300

# 使用预构建镜像
docker-compose -f docker-compose.fast.yml up -d
```

#### 3. 网络连接问题
```bash
# 检查安全组配置
# 检查DNS解析
nslookup registry.cn-hangzhou.aliyuncs.com

# 检查网络连通性
telnet registry.cn-hangzhou.aliyuncs.com 443
```

#### 4. 资源不足
```bash
# 检查系统资源
free -h
df -h
docker system df

# 清理Docker资源
docker system prune -a
```

## 📈 性能监控

### 关键指标

- **CPU使用率**: < 70%
- **内存使用率**: < 80%
- **磁盘使用率**: < 85%
- **网络延迟**: < 100ms
- **Docker镜像拉取时间**: < 5分钟
- **应用启动时间**: < 2分钟

### 监控命令

```bash
# 系统资源监控
htop
iotop
nethogs

# Docker监控
docker stats
docker system df
docker system events

# 应用监控
curl -s http://localhost:8000/health | jq
docker-compose logs -f --tail=100
```

## 🎯 最佳实践

1. **使用阿里云镜像源**: 显著提升下载速度
2. **预构建基础镜像**: 减少重复构建时间
3. **并行构建**: 充分利用多核CPU
4. **使用ACR**: 镜像分发更快
5. **配置监控**: 及时发现问题
6. **定期备份**: 保障数据安全
7. **安全加固**: 配置防火墙和访问控制
8. **性能调优**: 根据实际负载调整配置

通过以上优化配置，可以将Docker镜像构建时间从100分钟缩短到10-15分钟，显著提升部署效率。
