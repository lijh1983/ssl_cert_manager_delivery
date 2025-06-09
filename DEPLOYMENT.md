# SSL证书管理器部署指南

本指南提供SSL证书管理器在阿里云ECS环境中的详细部署步骤。

## 📋 部署前准备

### 系统要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Docker**: 20.10+
- **内存**: 最低2GB，推荐4GB+
- **磁盘**: 最低10GB可用空间
- **网络**: 需要访问互联网

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

## 🚀 部署方法

### 方法1: 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 2. 执行一键部署
./deploy.sh --quick
```

### 方法2: 手动部署

#### 步骤1: 安装Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker

# 验证安装
docker --version
docker-compose --version
```

#### 步骤2: 克隆项目

```bash
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery
```

#### 步骤3: 配置环境变量

```bash
cat > .env <<EOF
# 基础配置
DOMAIN_NAME=ssl.gzyggl.com
EMAIL=19822088@qq.com
ENVIRONMENT=production

# 数据库配置
DB_NAME=ssl_manager
DB_USER=ssl_user
DB_PASSWORD=$(openssl rand -base64 32)
DB_PORT=5432

# Redis配置
REDIS_PASSWORD=$(openssl rand -base64 32)
REDIS_PORT=6379

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
EOF
```

#### 步骤4: 构建基础镜像

```bash
# 构建后端基础镜像
docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend

# 构建前端基础镜像
docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend
```

#### 步骤5: 启动服务

```bash
# 启动完整服务（包含监控）
docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d

# 或仅启动基础服务
docker-compose -f docker-compose.aliyun.yml up -d
```

## ✅ 部署验证

### 检查服务状态

```bash
# 查看所有服务状态
docker-compose -f docker-compose.aliyun.yml ps

# 检查服务健康状态
docker-compose -f docker-compose.aliyun.yml ps | grep "healthy\|Up"
```

### 验证数据库连接

```bash
# 测试PostgreSQL连接
docker exec ssl-manager-postgres pg_isready -U ssl_user -d ssl_manager

# 查看数据库表
docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "\dt"
```

### 测试Web访问

```bash
# 测试本地访问
curl -I http://localhost

# 测试域名访问
curl -I http://ssl.gzyggl.com
```

### 验证API接口

```bash
# 测试API健康检查
curl http://ssl.gzyggl.com/api/health

# 查看API文档
curl http://ssl.gzyggl.com/api/docs
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

#### 4. 内存不足

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
