# SSL证书自动化管理系统部署指南

## 1. 系统要求

### 1.1 服务端要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **CPU**: 2核+
- **内存**: 4GB+
- **存储**: 50GB+
- **软件环境**:
  - Python 3.11+
  - MySQL 8.0+ 或 SQLite 3.35+
  - Nginx 1.18+
  - Node.js 16+

### 1.2 客户端要求

- **操作系统**: 支持主流Linux发行版（Ubuntu/Debian/CentOS/RHEL/TencentOS）
- **最小磁盘空间**: 100MB
- **依赖软件**:
  - curl
  - openssl
  - socat
  - jq

## 2. 服务端部署

### 2.1 准备环境

#### 2.1.1 安装基础软件包

**Ubuntu/Debian**:
```bash
# 更新软件包列表
apt-get update

# 安装基础软件包
apt-get install -y python3 python3-pip python3-venv nginx supervisor git curl

# 安装数据库（MySQL）
apt-get install -y mysql-server

# 安装Node.js
curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
apt-get install -y nodejs
```

**CentOS/RHEL**:
```bash
# 更新软件包列表
yum update -y

# 安装基础软件包
yum install -y python3 python3-pip nginx supervisor git curl

# 安装数据库（MySQL）
yum install -y mysql-server
systemctl enable mysqld
systemctl start mysqld

# 安装Node.js
curl -fsSL https://rpm.nodesource.com/setup_16.x | bash -
yum install -y nodejs
```

#### 2.1.2 创建系统用户

```bash
# 创建系统用户
useradd -m -s /bin/bash sslcert

# 添加到www-data组（Ubuntu/Debian）
usermod -a -G www-data sslcert

# 添加到nginx组（CentOS/RHEL）
usermod -a -G nginx sslcert
```

### 2.2 获取源代码

```bash
# 切换到系统用户
su - sslcert

# 克隆代码仓库
git clone https://github.com/example/ssl-cert-manager.git
cd ssl-cert-manager
```

### 2.3 后端部署

#### 2.3.1 创建虚拟环境

```bash
# 创建Python虚拟环境
cd backend
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn
```

#### 2.3.2 配置数据库

**MySQL**:
```bash
# 登录MySQL
mysql -u root -p

# 创建数据库和用户
CREATE DATABASE ssl_cert_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sslcert'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON ssl_cert_manager.* TO 'sslcert'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 2.3.3 配置应用

```bash
# 复制配置文件模板
cp config.example.py config.py

# 编辑配置文件
nano config.py
```

修改以下配置项:
```python
# 数据库配置
DB_TYPE = 'mysql'  # 或 'sqlite'
DB_HOST = 'localhost'
DB_PORT = 3306
DB_NAME = 'ssl_cert_manager'
DB_USER = 'sslcert'
DB_PASSWORD = 'your_secure_password'

# 安全配置
SECRET_KEY = 'generate_a_secure_random_key'  # 生成随机密钥
JWT_EXPIRATION = 3600  # Token有效期（秒）

# 应用配置
DEBUG = False
ALLOWED_HOSTS = ['api.yourdomain.com']
```

#### 2.3.4 初始化数据库

```bash
# 初始化数据库
python init_db.py

# 创建管理员用户
python create_admin.py
```

#### 2.3.5 配置Gunicorn

创建Gunicorn配置文件:
```bash
# 退出虚拟环境
deactivate

# 切换到root用户
exit

# 创建Gunicorn配置文件
cat > /etc/supervisor/conf.d/ssl-cert-api.conf << EOF
[program:ssl-cert-api]
command=/home/sslcert/ssl-cert-manager/backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
directory=/home/sslcert/ssl-cert-manager/backend
user=sslcert
autostart=true
autorestart=true
stderr_logfile=/var/log/ssl-cert-api.err.log
stdout_logfile=/var/log/ssl-cert-api.out.log
environment=PATH="/home/sslcert/ssl-cert-manager/backend/venv/bin"
EOF
```

#### 2.3.6 配置Nginx

创建Nginx配置文件:
```bash
cat > /etc/nginx/sites-available/ssl-cert-api << EOF
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 启用站点配置
ln -s /etc/nginx/sites-available/ssl-cert-api /etc/nginx/sites-enabled/
```

### 2.4 前端部署

#### 2.4.1 构建前端

```bash
# 切换到系统用户
su - sslcert

# 进入前端目录
cd ssl-cert-manager/frontend

# 安装依赖
npm install

# 配置API地址
cat > .env.production << EOF
VUE_APP_API_URL=https://api.yourdomain.com
EOF

# 构建生产版本
npm run build
```

#### 2.4.2 配置Nginx

```bash
# 切换到root用户
exit

# 创建Nginx配置文件
cat > /etc/nginx/sites-available/ssl-cert-frontend << EOF
server {
    listen 80;
    server_name console.yourdomain.com;
    
    root /home/sslcert/ssl-cert-manager/frontend/dist;
    index index.html;
    
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    
    # 缓存静态资源
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
EOF

# 启用站点配置
ln -s /etc/nginx/sites-available/ssl-cert-frontend /etc/nginx/sites-enabled/
```

### 2.5 启动服务

```bash
# 重新加载Supervisor配置
supervisorctl reread
supervisorctl update

# 启动API服务
supervisorctl start ssl-cert-api

# 检查Nginx配置
nginx -t

# 重启Nginx
systemctl restart nginx
```

### 2.6 配置HTTPS

建议使用Let's Encrypt为API和控制台配置HTTPS:

```bash
# 安装Certbot
apt-get install -y certbot python3-certbot-nginx

# 获取证书并配置Nginx
certbot --nginx -d api.yourdomain.com -d console.yourdomain.com
```

### 2.7 安装客户端安装脚本

```bash
# 创建安装脚本目录
mkdir -p /var/www/html/install

# 复制客户端安装脚本
cp /home/sslcert/ssl-cert-manager/client/install.sh /var/www/html/install/

# 设置权限
chmod 644 /var/www/html/install/install.sh
```

## 3. 客户端部署

### 3.1 通过Web控制台部署

1. 登录Web控制台
2. 导航到"服务器管理"页面
3. 点击"添加服务器"按钮
4. 输入服务器名称，点击"确定"
5. 系统会生成一个安装命令，复制该命令
6. 在目标服务器上执行该命令:

```bash
curl -s https://console.yourdomain.com/install.sh | bash -s YOUR_TOKEN
```

### 3.2 手动部署

如果无法通过Web控制台部署，可以手动部署客户端:

1. 从Web控制台获取服务器令牌
2. 在目标服务器上执行以下命令:

```bash
# 下载客户端脚本
curl -s -o client.sh https://console.yourdomain.com/install.sh

# 设置执行权限
chmod +x client.sh

# 安装客户端
./client.sh install YOUR_TOKEN
```

## 4. 系统配置

### 4.1 初始设置

首次部署后，需要进行以下初始设置:

1. 登录Web控制台 (默认用户名: admin, 密码: 安装时设置)
2. 导航到"系统设置"页面
3. 配置以下参数:
   - 默认CA提供商 (Let's Encrypt/ZeroSSL)
   - 证书续期提前天数 (建议15天)
   - 证书过期告警提前天数 (建议30天)
   - 告警通知设置

### 4.2 添加用户

如需添加更多用户:

1. 导航到"用户管理"页面
2. 点击"添加用户"按钮
3. 填写用户信息 (用户名、邮箱、密码、角色)
4. 点击"确定"保存

### 4.3 配置备份

建议定期备份系统数据:

```bash
# 创建备份目录
mkdir -p /backup/ssl-cert-manager

# 备份数据库
mysqldump -u sslcert -p ssl_cert_manager > /backup/ssl-cert-manager/db_$(date +%Y%m%d).sql

# 备份配置文件
cp /home/sslcert/ssl-cert-manager/backend/config.py /backup/ssl-cert-manager/config_$(date +%Y%m%d).py
```

可以创建定时任务自动执行备份:

```bash
# 编辑crontab
crontab -e

# 添加定时任务 (每天凌晨2点执行备份)
0 2 * * * /path/to/backup_script.sh
```

## 5. 升级指南

### 5.1 后端升级

```bash
# 切换到系统用户
su - sslcert

# 进入项目目录
cd ssl-cert-manager

# 拉取最新代码
git pull

# 进入后端目录
cd backend

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 执行数据库迁移
python migrate.py

# 退出虚拟环境
deactivate

# 切换到root用户
exit

# 重启服务
supervisorctl restart ssl-cert-api
```

### 5.2 前端升级

```bash
# 切换到系统用户
su - sslcert

# 进入项目目录
cd ssl-cert-manager

# 拉取最新代码
git pull

# 进入前端目录
cd frontend

# 安装依赖
npm install

# 构建生产版本
npm run build
```

### 5.3 客户端升级

客户端会自动检查更新，如需手动升级:

```bash
# 在客户端服务器上执行
/usr/local/bin/ssl-cert-manager upgrade
```

## 6. 故障排除

### 6.1 服务启动问题

如果服务无法启动:

```bash
# 检查Supervisor日志
tail -f /var/log/ssl-cert-api.err.log

# 检查Nginx日志
tail -f /var/log/nginx/error.log

# 检查应用日志
tail -f /home/sslcert/ssl-cert-manager/backend/logs/app.log
```

### 6.2 数据库连接问题

如果出现数据库连接错误:

```bash
# 检查MySQL服务状态
systemctl status mysql

# 检查数据库连接
mysql -u sslcert -p -e "SHOW DATABASES;"

# 检查数据库权限
mysql -u root -p -e "SHOW GRANTS FOR 'sslcert'@'localhost';"
```

### 6.3 客户端连接问题

如果客户端无法连接到服务器:

```bash
# 检查客户端日志
cat /var/log/ssl-cert-manager.log

# 测试API连接
curl -v https://api.yourdomain.com/api/v1/client/register

# 检查防火墙设置
iptables -L
```

### 6.4 证书续期失败

如果证书续期失败:

```bash
# 检查acme.sh日志
cat /home/sslcert/.acme.sh/acme.sh.log

# 检查DNS记录
dig _acme-challenge.yourdomain.com TXT

# 手动触发续期
/usr/local/bin/ssl-cert-manager renew
```

## 7. 安全建议

### 7.1 系统安全

- 定期更新操作系统和软件包
- 配置防火墙，只开放必要端口
- 使用强密码和密钥
- 启用SSH密钥认证，禁用密码登录
- 定期审计系统日志

### 7.2 应用安全

- 定期更换API密钥和JWT密钥
- 启用HTTPS，配置适当的SSL/TLS设置
- 实施IP限制和访问控制
- 定期备份数据
- 监控异常活动

### 7.3 证书安全

- 妥善保管证书私钥
- 使用适当的文件权限
- 定期轮换证书
- 监控证书透明度日志

## 8. 性能优化

### 8.1 数据库优化

- 添加适当的索引
- 优化查询语句
- 配置适当的缓存
- 定期清理历史数据

### 8.2 Web服务器优化

- 启用Gzip压缩
- 配置浏览器缓存
- 使用HTTP/2
- 调整工作进程数

### 8.3 应用优化

- 实现API响应缓存
- 优化数据库连接池
- 使用异步任务处理
- 实现请求限流

## 9. 监控与维护

### 9.1 系统监控

建议使用以下工具监控系统:

- Prometheus + Grafana: 监控系统指标
- ELK Stack: 日志收集和分析
- Uptime Robot: 外部可用性监控

### 9.2 日常维护

- 定期检查日志文件
- 监控磁盘使用情况
- 清理临时文件和旧备份
- 验证备份的有效性

### 9.3 证书监控

- 监控证书有效期
- 检查证书续期状态
- 验证证书部署情况
- 监控证书透明度日志

## 10. 附录

### 10.1 目录结构

```
/home/sslcert/ssl-cert-manager/
├── backend/                # 后端代码
│   ├── venv/               # Python虚拟环境
│   ├── src/                # 源代码
│   ├── config.py           # 配置文件
│   └── logs/               # 日志文件
├── frontend/               # 前端代码
│   ├── dist/               # 构建输出
│   └── src/                # 源代码
└── client/                 # 客户端代码
    └── install.sh          # 安装脚本
```

### 10.2 常用命令

```bash
# 启动/停止/重启API服务
supervisorctl start ssl-cert-api
supervisorctl stop ssl-cert-api
supervisorctl restart ssl-cert-api

# 查看API服务状态
supervisorctl status ssl-cert-api

# 重启Nginx
systemctl restart nginx

# 查看Nginx状态
systemctl status nginx

# 查看日志
tail -f /var/log/ssl-cert-api.err.log
tail -f /var/log/nginx/error.log
tail -f /home/sslcert/ssl-cert-manager/backend/logs/app.log
```

### 10.3 配置文件参考

**Nginx配置**:
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;
    
    add_header Strict-Transport-Security "max-age=63072000" always;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name console.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/console.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/console.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;
    
    add_header Strict-Transport-Security "max-age=63072000" always;
    
    root /home/sslcert/ssl-cert-manager/frontend/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```

**Supervisor配置**:
```ini
[program:ssl-cert-api]
command=/home/sslcert/ssl-cert-manager/backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
directory=/home/sslcert/ssl-cert-manager/backend
user=sslcert
autostart=true
autorestart=true
stderr_logfile=/var/log/ssl-cert-api.err.log
stdout_logfile=/var/log/ssl-cert-api.out.log
environment=PATH="/home/sslcert/ssl-cert-manager/backend/venv/bin"
```

**MySQL配置优化**:
```ini
[mysqld]
# 基本设置
max_connections = 200
max_allowed_packet = 16M
thread_cache_size = 8

# InnoDB设置
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# 查询缓存
query_cache_size = 32M
query_cache_limit = 1M

# 日志设置
slow_query_log = 1
slow_query_log_file = /var/log/mysql/mysql-slow.log
long_query_time = 2
```

### 10.4 联系支持

如遇到无法解决的问题，请联系技术支持：
- 邮件：support@example.com
- 电话：400-123-4567
- 工单系统：https://support.example.com
