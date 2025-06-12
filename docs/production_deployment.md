# SSL证书管理系统 - 生产环境部署指南

## 概述

本指南详细介绍如何在生产环境中部署SSL证书管理系统，包括MySQL数据库配置、Nginx负载均衡、SSL终止和安全配置。

## 系统架构

```
Internet
    ↓
[Nginx Load Balancer]
    ↓
[Backend Instances] × 3
    ↓
[MySQL 8.0.41 Cluster]
    ↓
[Redis Cache]
```

## 前置要求

### 硬件要求
- **CPU**: 4核心以上
- **内存**: 8GB以上（推荐16GB）
- **存储**: 100GB以上SSD
- **网络**: 1Gbps带宽

### 软件要求
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **域名**: 已解析到服务器IP

## 部署步骤

### 1. 环境准备

#### 1.1 创建部署目录
```bash
sudo mkdir -p /opt/ssl-manager
cd /opt/ssl-manager
git clone https://github.com/your-org/ssl-cert-manager.git .
```

#### 1.2 创建必要目录
```bash
sudo mkdir -p /opt/ssl-manager/{certs,backups,logs}
sudo mkdir -p /var/log/nginx
sudo mkdir -p /var/cache/nginx
sudo chown -R 1000:1000 /opt/ssl-manager
```

#### 1.3 配置防火墙
```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. SSL证书配置

#### 2.1 生成SSL证书（Let's Encrypt）
```bash
# 安装Certbot
sudo apt install certbot  # Ubuntu/Debian
sudo yum install certbot  # CentOS/RHEL

# 获取证书
sudo certbot certonly --standalone \
  -d ssl-manager.example.com \
  -d admin.ssl-manager.example.com \
  --email admin@example.com \
  --agree-tos \
  --non-interactive

# 复制证书到项目目录
sudo cp /etc/letsencrypt/live/ssl-manager.example.com/fullchain.pem \
  /opt/ssl-manager/nginx/ssl/ssl-manager.crt
sudo cp /etc/letsencrypt/live/ssl-manager.example.com/privkey.pem \
  /opt/ssl-manager/nginx/ssl/ssl-manager.key
```

#### 2.2 配置证书自动续期
```bash
# 添加续期任务到crontab
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### 3. 环境变量配置

#### 3.1 复制配置模板
```bash
cp .env.production.example .env.production
```

#### 3.2 编辑生产环境配置
```bash
nano .env.production
```

**关键配置项：**
```bash
# 域名配置
DOMAIN_NAME=ssl-manager.example.com

# MySQL配置
MYSQL_HOST=mysql
MYSQL_USERNAME=ssl_manager_prod
MYSQL_PASSWORD=your-secure-mysql-password
MYSQL_DATABASE=ssl_manager_prod

# 安全密钥（必须修改）
SECRET_KEY=your-very-secure-secret-key-minimum-32-characters
JWT_SECRET_KEY=your-jwt-secret-key-minimum-32-characters
CSRF_SECRET_KEY=your-csrf-secret-key-minimum-32-characters

# SSL证书路径
SSL_CERTIFICATE_PATH=/etc/nginx/ssl/ssl-manager.crt
SSL_CERTIFICATE_KEY_PATH=/etc/nginx/ssl/ssl-manager.key
```

#### 3.3 验证配置
```bash
python3 scripts/validate_config.py --env-file .env.production
```

### 4. 数据库配置

#### 4.1 MySQL SSL证书配置（可选但推荐）
```bash
# 生成MySQL SSL证书
sudo mkdir -p /opt/ssl-manager/mysql/ssl
cd /opt/ssl-manager/mysql/ssl

# 生成CA证书
openssl genrsa 2048 > ca-key.pem
openssl req -new -x509 -nodes -days 3600 \
  -key ca-key.pem -out ca.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=SSL Manager/CN=MySQL CA"

# 生成服务器证书
openssl req -newkey rsa:2048 -days 3600 \
  -nodes -keyout server-key.pem -out server-req.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=SSL Manager/CN=mysql"
openssl rsa -in server-key.pem -out server-key.pem
openssl x509 -req -in server-req.pem -days 3600 \
  -CA ca.pem -CAkey ca-key.pem -set_serial 01 \
  -out server-cert.pem

# 生成客户端证书
openssl req -newkey rsa:2048 -days 3600 \
  -nodes -keyout client-key.pem -out client-req.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=SSL Manager/CN=client"
openssl rsa -in client-key.pem -out client-key.pem
openssl x509 -req -in client-req.pem -days 3600 \
  -CA ca.pem -CAkey ca-key.pem -set_serial 01 \
  -out client-cert.pem

# 设置权限
chmod 600 *-key.pem
chmod 644 *.pem
```

### 5. Nginx配置

#### 5.1 更新Nginx配置
```bash
# 编辑Nginx配置文件
nano nginx/conf.d/ssl-manager-production.conf

# 更新域名
sed -i 's/ssl-manager.example.com/your-domain.com/g' \
  nginx/conf.d/ssl-manager-production.conf
```

#### 5.2 生成DH参数（提高安全性）
```bash
sudo openssl dhparam -out nginx/ssl/dhparam.pem 2048
```

#### 5.3 创建基本认证文件（管理后台）
```bash
sudo apt install apache2-utils  # Ubuntu/Debian
sudo yum install httpd-tools     # CentOS/RHEL

# 创建管理员用户
sudo htpasswd -c nginx/.htpasswd admin
```

### 6. 部署应用

#### 6.1 构建Docker镜像
```bash
# 构建后端镜像
docker build -t ssl-manager-backend:latest ./backend

# 构建前端镜像
docker build -t ssl-manager-frontend:latest ./frontend
```

#### 6.2 启动服务
```bash
# 启动所有服务
docker-compose -f docker-compose.production.yml up -d

# 查看服务状态
docker-compose -f docker-compose.production.yml ps

# 查看日志
docker-compose -f docker-compose.production.yml logs -f
```

#### 6.3 初始化数据库
```bash
# 等待MySQL启动完成
sleep 30

# 初始化数据库
docker-compose -f docker-compose.production.yml exec backend1 \
  python3 -c "from models.database import init_db; init_db()"
```

### 7. 健康检查和验证

#### 7.1 检查服务状态
```bash
# 检查所有容器状态
docker-compose -f docker-compose.production.yml ps

# 检查健康状态
curl -f http://localhost:8080/health
curl -f https://ssl-manager.example.com/api/health
```

#### 7.2 验证负载均衡
```bash
# 多次请求API，检查负载均衡
for i in {1..10}; do
  curl -s https://ssl-manager.example.com/api/health | grep -o '"instance_id":"[^"]*"'
done
```

#### 7.3 验证SSL配置
```bash
# 检查SSL证书
openssl s_client -connect ssl-manager.example.com:443 -servername ssl-manager.example.com

# 检查SSL评级
curl -s "https://api.ssllabs.com/api/v3/analyze?host=ssl-manager.example.com"
```

### 8. 监控配置（可选）

#### 8.1 启动监控服务
```bash
# 启动Prometheus和Grafana
docker-compose -f docker-compose.production.yml --profile monitoring up -d

# 访问监控界面
# Prometheus: http://your-server:9090
# Grafana: http://your-server:3001 (admin/your-grafana-password)
```

#### 8.2 配置告警
```bash
# 编辑Prometheus告警规则
nano monitoring/prometheus/alerts.yml

# 重启Prometheus
docker-compose -f docker-compose.production.yml restart prometheus
```

### 9. 备份配置

#### 9.1 数据库备份
```bash
# 创建备份脚本
cat > /opt/ssl-manager/scripts/backup_mysql.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/ssl-manager/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="ssl_manager_backup_${DATE}.sql"

mkdir -p $BACKUP_DIR

docker-compose -f /opt/ssl-manager/docker-compose.production.yml exec -T mysql \
  mysqldump -u ssl_manager_prod -p${MYSQL_PASSWORD} ssl_manager_prod > $BACKUP_DIR/$BACKUP_FILE

gzip $BACKUP_DIR/$BACKUP_FILE
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
EOF

chmod +x /opt/ssl-manager/scripts/backup_mysql.sh

# 添加到crontab
echo "0 2 * * * /opt/ssl-manager/scripts/backup_mysql.sh" | crontab -
```

#### 9.2 证书备份
```bash
# 创建证书备份脚本
cat > /opt/ssl-manager/scripts/backup_certs.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/ssl-manager/backups/certs"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

tar -czf $BACKUP_DIR/certs_backup_${DATE}.tar.gz \
  -C /opt/ssl-manager certs/

find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Certificate backup completed: certs_backup_${DATE}.tar.gz"
EOF

chmod +x /opt/ssl-manager/scripts/backup_certs.sh

# 添加到crontab
echo "0 3 * * * /opt/ssl-manager/scripts/backup_certs.sh" | crontab -
```

### 10. 安全加固

#### 10.1 系统安全
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
sudo yum update -y                       # CentOS/RHEL

# 配置自动安全更新
sudo apt install unattended-upgrades    # Ubuntu/Debian
sudo dpkg-reconfigure unattended-upgrades

# 禁用不必要的服务
sudo systemctl disable bluetooth
sudo systemctl disable cups
```

#### 10.2 Docker安全
```bash
# 配置Docker daemon
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true
}
EOF

sudo systemctl restart docker
```

#### 10.3 网络安全
```bash
# 配置fail2ban
sudo apt install fail2ban  # Ubuntu/Debian
sudo yum install fail2ban  # CentOS/RHEL

# 配置fail2ban规则
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 维护和故障排除

### 日常维护

#### 1. 检查服务状态
```bash
# 每日检查脚本
cat > /opt/ssl-manager/scripts/daily_check.sh << 'EOF'
#!/bin/bash
echo "=== SSL Manager Daily Check $(date) ==="

# 检查容器状态
echo "Container Status:"
docker-compose -f /opt/ssl-manager/docker-compose.production.yml ps

# 检查磁盘空间
echo -e "\nDisk Usage:"
df -h

# 检查内存使用
echo -e "\nMemory Usage:"
free -h

# 检查SSL证书过期时间
echo -e "\nSSL Certificate Expiry:"
openssl x509 -in /opt/ssl-manager/nginx/ssl/ssl-manager.crt -noout -dates

# 检查数据库连接
echo -e "\nDatabase Connection:"
docker-compose -f /opt/ssl-manager/docker-compose.production.yml exec -T mysql \
  mysql -u ssl_manager_prod -p${MYSQL_PASSWORD} -e "SELECT 1" ssl_manager_prod

echo "=== Check Completed ==="
EOF

chmod +x /opt/ssl-manager/scripts/daily_check.sh
```

#### 2. 日志轮转
```bash
# 配置日志轮转
sudo tee /etc/logrotate.d/ssl-manager << 'EOF'
/opt/ssl-manager/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/ssl-manager/docker-compose.production.yml restart nginx
    endscript
}
EOF
```

### 故障排除

#### 常见问题

1. **服务无法启动**
   ```bash
   # 检查Docker日志
   docker-compose -f docker-compose.production.yml logs
   
   # 检查配置文件
   python3 scripts/validate_config.py
   ```

2. **数据库连接失败**
   ```bash
   # 检查MySQL状态
   docker-compose -f docker-compose.production.yml exec mysql mysqladmin status
   
   # 检查网络连接
   docker-compose -f docker-compose.production.yml exec backend1 ping mysql
   ```

3. **SSL证书问题**
   ```bash
   # 检查证书有效性
   openssl x509 -in nginx/ssl/ssl-manager.crt -text -noout
   
   # 重新获取证书
   sudo certbot renew --force-renewal
   ```

4. **性能问题**
   ```bash
   # 检查资源使用
   docker stats
   
   # 检查慢查询
   docker-compose -f docker-compose.production.yml exec mysql \
     mysql -u root -p -e "SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;"
   ```

## 升级指南

### 应用升级
```bash
# 1. 备份数据
/opt/ssl-manager/scripts/backup_mysql.sh
/opt/ssl-manager/scripts/backup_certs.sh

# 2. 拉取最新代码
git pull origin main

# 3. 重新构建镜像
docker-compose -f docker-compose.production.yml build

# 4. 滚动更新
docker-compose -f docker-compose.production.yml up -d --no-deps backend1
sleep 30
docker-compose -f docker-compose.production.yml up -d --no-deps backend2
sleep 30
docker-compose -f docker-compose.production.yml up -d --no-deps backend3

# 5. 验证服务
curl -f https://ssl-manager.example.com/api/health
```

### 数据库升级
```bash
# MySQL版本升级
docker-compose -f docker-compose.production.yml stop mysql
docker-compose -f docker-compose.production.yml pull mysql
docker-compose -f docker-compose.production.yml up -d mysql
```

## 联系支持

如果在部署过程中遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 运行配置验证脚本
3. 检查系统资源使用情况
4. 联系技术支持团队

---

**注意**: 在生产环境部署前，请务必在测试环境中完整验证所有功能和配置。
