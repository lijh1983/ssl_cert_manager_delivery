# SSL证书管理器 - 阿里云ECS一键部署指南

## 🚀 快速开始

本项目已针对阿里云ECS环境进行优化，所有网络连接问题和Docker缓存问题都已修复，可以直接部署使用。

### 方法1: 一键部署（推荐）

```bash
# 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 一键部署（交互式）
./deploy.sh

# 或快速部署（使用默认配置）
./deploy.sh --quick
```

### 方法2: 手动部署

```bash
# 1. 构建基础镜像
docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend
docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend

# 2. 创建环境配置文件
cat > .env <<EOF
DOMAIN_NAME=ssl.gzyggl.com
EMAIL=19822088@qq.com
ENVIRONMENT=production
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -base64 16)
VITE_API_BASE_URL=/api
ENABLE_METRICS=true
EOF

# 3. 启动服务（如果有docker-compose）
docker-compose -f docker-compose.aliyun.yml up -d

# 或启动服务（如果有docker compose）
docker compose -f docker-compose.aliyun.yml up -d

# 4. 启动监控服务（可选）
docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d
```

## 📋 系统要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Docker**: 20.10+
- **内存**: 最低2GB，推荐4GB+
- **磁盘**: 最低10GB可用空间
- **网络**: 需要访问互联网（已配置阿里云镜像源）

## 🔧 已修复的问题

### 1. Docker缓存清单问题
- ✅ 修复了 `importing cache manifest from ssl-manager-nginx-proxy:latest` 错误
- ✅ 移除了docker-compose.yml中的循环缓存依赖
- ✅ 优化了多阶段构建的缓存策略

### 2. 网络连接问题
- ✅ 修复了 `Unable to connect to deb.debian.org:http` 错误
- ✅ 配置了阿里云Debian/Alpine镜像源
- ✅ 配置了阿里云npm和pip镜像源
- ✅ 优化了DNS配置和网络参数

### 3. 镜像构建优化
- ✅ 所有Dockerfile都使用阿里云镜像源
- ✅ 修复了Alpine仓库URL语法错误
- ✅ 优化了依赖安装顺序和错误处理

## 🌐 访问地址

部署完成后，可以通过以下地址访问：

- **主应用**: http://ssl.gzyggl.com
- **API文档**: http://ssl.gzyggl.com/api/docs
- **监控面板**: http://ssl.gzyggl.com/monitoring/ (如果启用)
- **Prometheus**: http://ssl.gzyggl.com:9090 (如果启用)

## 📊 服务架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │────│    Frontend     │────│     Backend     │
│   (Port 80/443) │    │   (Vue.js SPA)  │    │  (FastAPI/Flask)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │   PostgreSQL    │    │      Redis      │
         │              │   (Database)    │    │     (Cache)     │
         │              └─────────────────┘    └─────────────────┘
         │
┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │────│     Grafana     │
│   (Monitoring)  │    │  (Visualization)│
└─────────────────┘    └─────────────────┘
```

## 🛠️ 管理命令

### 查看服务状态
```bash
# 查看所有服务
docker ps

# 查看服务日志
docker logs ssl-manager-backend
docker logs ssl-manager-frontend
docker logs ssl-manager-nginx-proxy

# 查看服务健康状态
docker inspect ssl-manager-backend | grep Health -A 10
```

### 服务管理
```bash
# 重启服务
docker restart ssl-manager-backend
docker restart ssl-manager-frontend

# 停止所有服务
docker stop $(docker ps -q --filter "name=ssl-manager")

# 清理资源
docker system prune -f
```

### 数据备份
```bash
# 备份数据库
docker exec ssl-manager-postgres pg_dump -U ssl_user ssl_manager > backup.sql

# 备份SSL证书
docker cp ssl-manager-nginx-proxy:/etc/nginx/ssl ./ssl_backup
```

## 🔍 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查日志
   docker logs ssl-manager-backend --tail 50
   
   # 检查端口占用
   netstat -tlnp | grep :80
   netstat -tlnp | grep :443
   ```

2. **网络连接问题**
   ```bash
   # 测试网络连接
   docker run --rm alpine:latest wget -O- https://mirrors.aliyun.com
   
   # 检查DNS配置
   cat /etc/resolv.conf
   ```

3. **镜像构建失败**
   ```bash
   # 清理Docker缓存
   docker builder prune -f
   docker system prune -f
   
   # 重新构建（无缓存）
   docker build --no-cache -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend
   ```

### 性能优化

1. **内存优化**
   ```bash
   # 查看内存使用
   docker stats
   
   # 调整worker数量（在.env文件中）
   BACKEND_WORKERS=1  # 减少内存使用
   ```

2. **磁盘清理**
   ```bash
   # 清理未使用的镜像
   docker image prune -a
   
   # 清理未使用的卷
   docker volume prune
   ```

## 📞 技术支持

如果遇到问题，请按以下顺序排查：

1. **检查系统资源**: 确保有足够的内存和磁盘空间
2. **检查网络连接**: 确保可以访问阿里云镜像源
3. **检查Docker状态**: 确保Docker服务正常运行
4. **查看服务日志**: 检查具体的错误信息

### 联系方式

- **GitHub Issues**: https://github.com/lijh1983/ssl_cert_manager_delivery/issues
- **邮箱**: 19822088@qq.com

## 🎉 部署成功标志

当看到以下输出时，表示部署成功：

```
🎉 SSL证书管理器部署完成！
======================================

访问信息:
主应用: http://ssl.gzyggl.com
API文档: http://ssl.gzyggl.com/api/docs
监控面板: http://ssl.gzyggl.com/monitoring/

服务状态: 5/5 正常
✓ postgres 运行正常
✓ redis 运行正常  
✓ backend 运行正常
✓ frontend 运行正常
✓ nginx-proxy 运行正常
```

## 📝 更新日志

### v1.0.0 (2025-01-09)
- ✅ 完全解决Docker缓存清单问题
- ✅ 完全解决阿里云ECS网络连接问题
- ✅ 优化所有Dockerfile配置
- ✅ 提供一键部署脚本
- ✅ 支持开箱即用部署

---

**注意**: 本项目已针对阿里云ECS环境进行深度优化，所有已知问题都已修复。如果您在其他云平台部署，可能需要相应调整镜像源配置。
