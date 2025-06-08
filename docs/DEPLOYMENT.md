# SSL证书管理系统部署指南

本文档详细介绍了SSL证书自动化管理系统的生产环境部署流程。

## 📋 目录

- [系统要求](#系统要求)
- [快速部署](#快速部署)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [监控和维护](#监控和维护)
- [故障排除](#故障排除)

## 🖥️ 系统要求

### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 20GB 可用空间
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **网络**: 公网IP（用于Let's Encrypt验证）

### 推荐配置
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB SSD
- **操作系统**: Ubuntu 22.04 LTS
- **网络**: 公网IP + 域名

### 软件依赖
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.0+
- Nginx（可选，用于反向代理）

## 🚀 快速部署

### 一键部署脚本

```bash
# 下载部署脚本
curl -fsSL https://raw.githubusercontent.com/lijh1983/ssl_cert_manager_delivery/main/scripts/deploy.sh -o deploy.sh
chmod +x deploy.sh

# 执行部署（替换为你的域名）
sudo ./deploy.sh --domain your-domain.com --enable-monitoring --enable-nginx
```

### 手动部署

```bash
# 1. 克隆代码
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 2. 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 3. 启动服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. 检查服务状态
docker-compose ps
```

## 📝 详细部署步骤

### 1. 环境准备

#### 安装Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# CentOS/RHEL
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable docker
sudo systemctl start docker
```

#### 安装Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 系统配置

#### 创建系统用户
```bash
sudo useradd -r -s /bin/false -d /opt/ssl-manager ssl-manager
sudo mkdir -p /opt/ssl-manager/{data,logs,certs,backups}
sudo chown -R ssl-manager:ssl-manager /opt/ssl-manager
```

#### 配置防火墙
```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 3. 应用部署

#### 下载代码
```bash
cd /opt/ssl-manager
sudo -u ssl-manager git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git app
cd app
```

#### 配置环境变量
```bash
sudo -u ssl-manager cp .env.example .env
sudo -u ssl-manager nano .env
```

关键配置项：
```env
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
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# SSL配置
ACME_EMAIL=admin@your-domain.com
ACME_DIRECTORY_URL=https://acme-v02.api.letsencrypt.org/directory

# 监控配置
GRAFANA_USER=admin
GRAFANA_PASSWORD=your-grafana-password
```

#### 构建和启动服务
```bash
# 构建镜像
sudo docker-compose build

# 启动基础服务
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres redis

# 等待数据库就绪
sleep 30

# 启动应用服务
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend frontend

# 启动监控服务
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile monitoring up -d

# 启动生产级nginx
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d
```

### 4. SSL证书配置

#### 获取Let's Encrypt证书
```bash
# 安装certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 设置自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 配置nginx SSL
```bash
# 复制证书到nginx目录
sudo mkdir -p /opt/ssl-manager/app/nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/ssl-manager/app/nginx/ssl/your-domain.com.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/ssl-manager/app/nginx/ssl/your-domain.com.key

# 重启nginx
sudo docker-compose restart nginx
```

### 5. 系统服务配置

#### 安装systemd服务
```bash
sudo cp /opt/ssl-manager/app/scripts/systemd/ssl-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ssl-manager.service
sudo systemctl start ssl-manager.service
```

#### 配置日志轮转
```bash
sudo cp /opt/ssl-manager/app/scripts/logrotate/ssl-manager /etc/logrotate.d/
sudo logrotate -d /etc/logrotate.d/ssl-manager
```

## ⚙️ 配置说明

### 环境变量配置

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `ENVIRONMENT` | 运行环境 | `production` | 是 |
| `DOMAIN_NAME` | 主域名 | `localhost` | 是 |
| `DB_PASSWORD` | 数据库密码 | - | 是 |
| `REDIS_PASSWORD` | Redis密码 | - | 是 |
| `SECRET_KEY` | 应用密钥 | - | 是 |
| `JWT_SECRET_KEY` | JWT密钥 | - | 是 |
| `ACME_EMAIL` | Let's Encrypt邮箱 | - | 是 |
| `GRAFANA_PASSWORD` | Grafana密码 | `admin` | 否 |

### 端口配置

| 服务 | 内部端口 | 外部端口 | 描述 |
|------|----------|----------|------|
| Frontend | 80 | 80 | 前端Web服务 |
| Backend | 8000 | 8000 | 后端API服务 |
| Nginx | 80/443 | 80/443 | 反向代理 |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存 |
| Prometheus | 9090 | 9090 | 监控 |
| Grafana | 3000 | 3000 | 可视化 |

### 数据卷配置

| 卷名 | 挂载点 | 描述 |
|------|--------|------|
| `postgres_data` | `/var/lib/postgresql/data` | 数据库数据 |
| `redis_data` | `/data` | Redis数据 |
| `ssl_certs` | `/app/certs` | SSL证书 |
| `app_logs` | `/app/logs` | 应用日志 |
| `nginx_logs` | `/var/log/nginx` | Nginx日志 |

## 📊 监控和维护

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health
curl http://localhost:80/health

# 检查容器状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 监控访问

- **Prometheus**: http://your-domain.com:9090
- **Grafana**: http://your-domain.com:3000
  - 用户名: admin
  - 密码: 查看 `.env` 文件中的 `GRAFANA_PASSWORD`

### 备份策略

#### 数据库备份
```bash
# 手动备份
docker-compose exec postgres pg_dump -U ssl_user ssl_manager > backup_$(date +%Y%m%d_%H%M%S).sql

# 自动备份脚本
sudo crontab -e
# 添加：0 2 * * * /opt/ssl-manager/app/scripts/backup.sh
```

#### 证书备份
```bash
# 备份证书目录
tar -czf certs_backup_$(date +%Y%m%d).tar.gz /opt/ssl-manager/certs/
```

### 更新部署

```bash
cd /opt/ssl-manager/app

# 拉取最新代码
sudo -u ssl-manager git pull

# 重新构建镜像
sudo docker-compose build

# 滚动更新
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps backend
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps frontend
```

## 🔧 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 查看容器日志
docker-compose logs container_name

# 检查资源使用
docker stats

# 重启服务
docker-compose restart service_name
```

#### 2. 数据库连接失败
```bash
# 检查数据库状态
docker-compose exec postgres pg_isready -U ssl_user

# 查看数据库日志
docker-compose logs postgres

# 重置数据库连接
docker-compose restart postgres backend
```

#### 3. SSL证书问题
```bash
# 检查证书有效性
openssl x509 -in /opt/ssl-manager/app/nginx/ssl/your-domain.com.crt -text -noout

# 重新获取证书
sudo certbot renew --force-renewal

# 更新nginx配置
docker-compose restart nginx
```

#### 4. 性能问题
```bash
# 检查系统资源
htop
df -h
free -h

# 检查容器资源使用
docker stats

# 优化配置
# 增加worker数量、调整内存限制等
```

### 日志位置

- **应用日志**: `/opt/ssl-manager/logs/`
- **Nginx日志**: `/var/log/nginx/`
- **系统日志**: `journalctl -u ssl-manager`
- **容器日志**: `docker-compose logs`

### 联系支持

如果遇到无法解决的问题，请：

1. 收集相关日志
2. 记录错误信息和复现步骤
3. 提交Issue到GitHub仓库
4. 或联系技术支持团队

---

## 📚 相关文档

- [用户手册](USER_GUIDE.md)
- [API文档](API.md)
- [开发指南](DEVELOPMENT.md)
- [安全指南](SECURITY.md)
