# SSL证书管理系统 - 本地部署指南

## 概述

本文档提供SSL证书管理系统的本地部署指南，采用两阶段部署模式：
- **阶段1**：镜像构建（已完成）
- **阶段2**：服务启动（本文档重点）

## 前提条件

### 已完成的镜像构建
确保以下Docker镜像已在本地构建完成：
```bash
# 验证镜像是否存在
docker images | grep ssl-manager

# 应该看到以下镜像：
ssl-manager-frontend:latest
ssl-manager-backend:latest
ssl-manager-nginx-proxy:latest
```

### 系统要求
- Docker Engine 20.10+
- Docker Compose 2.0+ 或 docker-compose 1.29+
- 可用内存：至少 2GB
- 可用磁盘空间：至少 5GB

## 部署配置

### 1. 环境变量配置

复制环境变量模板：
```bash
cp .env.local .env
```

根据需要修改 `.env` 文件中的配置：
```bash
# 编辑环境变量
nano .env

# 重要配置项：
# - DB_PASSWORD: 数据库密码
# - REDIS_PASSWORD: Redis密码
# - SECRET_KEY: 应用密钥
# - DOMAIN_NAME: 域名（本地测试可用localhost）
```

### 2. 选择部署模式

#### 模式1：本地开发模式（推荐）
```bash
# 使用本地优化配置
docker-compose -f docker-compose.local.yml up -d
```

#### 模式2：标准模式
```bash
# 使用标准配置
docker-compose up -d
```

#### 模式3：开发模式
```bash
# 使用开发环境配置
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## 服务启动

### 完整启动流程

1. **启动基础服务**（数据库和缓存）：
```bash
docker-compose -f docker-compose.local.yml up -d postgres redis
```

2. **等待基础服务就绪**：
```bash
# 检查服务状态
docker-compose -f docker-compose.local.yml ps

# 查看健康检查状态
docker-compose -f docker-compose.local.yml logs postgres
docker-compose -f docker-compose.local.yml logs redis
```

3. **启动应用服务**：
```bash
docker-compose -f docker-compose.local.yml up -d backend frontend
```

4. **启动代理服务**：
```bash
docker-compose -f docker-compose.local.yml up -d nginx
```

5. **验证所有服务**：
```bash
docker-compose -f docker-compose.local.yml ps
```

### 一键启动（推荐）
```bash
# 一次性启动所有服务
docker-compose -f docker-compose.local.yml up -d

# 查看启动日志
docker-compose -f docker-compose.local.yml logs -f
```

## 服务验证

### 1. 健康检查
```bash
# 检查所有服务状态
docker-compose -f docker-compose.local.yml ps

# 检查特定服务日志
docker-compose -f docker-compose.local.yml logs backend
docker-compose -f docker-compose.local.yml logs frontend
docker-compose -f docker-compose.local.yml logs nginx
```

### 2. 功能测试

#### 后端API测试
```bash
# 健康检查
curl http://localhost:8000/health

# API文档
curl http://localhost:8000/docs
```

#### 前端服务测试
```bash
# 前端健康检查
curl http://localhost:3000/health

# 访问前端应用
curl http://localhost:3000/
```

#### 代理服务测试
```bash
# Nginx代理健康检查
curl http://localhost/health

# 通过代理访问API
curl http://localhost/api/health

# 通过代理访问前端
curl http://localhost/
```

### 3. 数据库连接测试
```bash
# 连接PostgreSQL
docker exec -it ssl-manager-postgres psql -U ssl_user -d ssl_manager

# 连接Redis
docker exec -it ssl-manager-redis redis-cli -a redis_password
```

## 服务管理

### 启动服务
```bash
docker-compose -f docker-compose.local.yml start
```

### 停止服务
```bash
docker-compose -f docker-compose.local.yml stop
```

### 重启服务
```bash
docker-compose -f docker-compose.local.yml restart
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose -f docker-compose.local.yml logs

# 查看特定服务日志
docker-compose -f docker-compose.local.yml logs backend

# 实时查看日志
docker-compose -f docker-compose.local.yml logs -f
```

### 清理服务
```bash
# 停止并删除容器
docker-compose -f docker-compose.local.yml down

# 停止并删除容器、网络、卷
docker-compose -f docker-compose.local.yml down -v
```

## 访问地址

### 本地开发模式
- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **代理服务**: http://localhost (端口80)

### 标准模式（通过代理访问）
- **应用首页**: http://localhost
- **API接口**: http://localhost/api
- **健康检查**: http://localhost/health

## 故障排除

### 常见问题

#### 1. 端口冲突
```bash
# 检查端口占用
netstat -tulpn | grep :80
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# 修改端口配置
# 编辑 .env 文件中的端口配置
```

#### 2. 服务启动失败
```bash
# 查看详细错误信息
docker-compose -f docker-compose.local.yml logs [service_name]

# 检查镜像是否存在
docker images | grep ssl-manager

# 重新构建镜像（如果需要）
docker build -t ssl-manager-backend:latest -f backend/Dockerfile ./backend
```

#### 3. 数据库连接失败
```bash
# 检查数据库服务状态
docker-compose -f docker-compose.local.yml ps postgres

# 查看数据库日志
docker-compose -f docker-compose.local.yml logs postgres

# 重置数据库
docker-compose -f docker-compose.local.yml down -v
docker-compose -f docker-compose.local.yml up -d postgres
```

#### 4. 健康检查失败
```bash
# 手动测试健康检查
docker exec ssl-manager-backend curl -f http://localhost:8000/health
docker exec ssl-manager-frontend curl -f http://localhost/health
docker exec ssl-manager-nginx curl -f http://localhost/health
```

### 调试命令
```bash
# 进入容器调试
docker exec -it ssl-manager-backend bash
docker exec -it ssl-manager-frontend sh
docker exec -it ssl-manager-nginx sh

# 查看容器资源使用
docker stats

# 查看网络配置
docker network ls
docker network inspect ssl_cert_manager_delivery_ssl-manager-network
```

## 性能优化

### 资源配置
根据系统资源调整以下配置：

```bash
# .env 文件中的配置
BACKEND_WORKERS=2          # 后端工作进程数
DB_MAX_CONNECTIONS=100     # 数据库最大连接数
REDIS_MAXMEMORY=512mb      # Redis最大内存
```

### 监控建议
```bash
# 监控容器状态
watch docker-compose -f docker-compose.local.yml ps

# 监控资源使用
watch docker stats
```

## 备份和恢复

### 数据备份
```bash
# 备份数据库
docker exec ssl-manager-postgres pg_dump -U ssl_user ssl_manager > backup.sql

# 备份Redis数据
docker exec ssl-manager-redis redis-cli -a redis_password BGSAVE
```

### 数据恢复
```bash
# 恢复数据库
docker exec -i ssl-manager-postgres psql -U ssl_user ssl_manager < backup.sql
```

## 总结

本地部署已完成镜像构建阶段，现在只需要：
1. 配置环境变量
2. 选择合适的部署模式
3. 启动服务
4. 验证功能

推荐使用 `docker-compose.local.yml` 配置进行本地部署，该配置已针对本地环境进行优化。
