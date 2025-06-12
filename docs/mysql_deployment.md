# SSL证书管理系统 MySQL 8.0.41 部署指南

## 概述

本文档描述如何将SSL证书管理系统从SQLite迁移到MySQL 8.0.41，包括数据库配置、数据迁移和部署步骤。

## 系统要求

### 硬件要求
- CPU: 2核心以上
- 内存: 4GB以上（推荐8GB）
- 存储: 50GB以上可用空间
- 网络: 稳定的网络连接

### 软件要求
- MySQL 8.0.41
- Python 3.8+
- Docker 20.10+ (可选)
- Docker Compose 2.0+ (可选)

## 安装MySQL 8.0.41

### 方式一：使用Docker（推荐）

```bash
# 使用提供的Docker Compose配置
docker-compose -f docker-compose.mysql.yml up -d mysql

# 等待MySQL启动完成
docker-compose -f docker-compose.mysql.yml logs -f mysql
```

### 方式二：直接安装

#### Ubuntu/Debian
```bash
# 添加MySQL APT仓库
wget https://dev.mysql.com/get/mysql-apt-config_0.8.24-1_all.deb
sudo dpkg -i mysql-apt-config_0.8.24-1_all.deb

# 更新包列表并安装MySQL
sudo apt update
sudo apt install mysql-server=8.0.41-1ubuntu18.04

# 启动MySQL服务
sudo systemctl start mysql
sudo systemctl enable mysql
```

#### CentOS/RHEL
```bash
# 添加MySQL Yum仓库
sudo yum install https://dev.mysql.com/get/mysql80-community-release-el7-3.noarch.rpm

# 安装MySQL
sudo yum install mysql-community-server-8.0.41

# 启动MySQL服务
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

## 数据库配置

### 1. 创建数据库和用户

```sql
-- 连接到MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE ssl_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'ssl_manager'@'%' IDENTIFIED BY 'ssl_manager_password';

-- 授权
GRANT ALL PRIVILEGES ON ssl_manager.* TO 'ssl_manager'@'%';
FLUSH PRIVILEGES;
```

### 2. 配置MySQL参数

编辑MySQL配置文件 `/etc/mysql/mysql.conf.d/mysqld.cnf`：

```ini
[mysqld]
# 基本设置
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
default-authentication-plugin = mysql_native_password

# 连接设置
max-connections = 200
connect-timeout = 10
wait-timeout = 28800

# 缓冲区设置
innodb-buffer-pool-size = 256M
innodb-log-buffer-size = 16M

# InnoDB设置
innodb-file-per-table = 1
innodb-flush-log-at-trx-commit = 2
innodb-flush-method = O_DIRECT

# 日志设置
slow-query-log = 1
slow-query-log-file = /var/log/mysql/slow.log
long-query-time = 2
```

重启MySQL服务：
```bash
sudo systemctl restart mysql
```

## 环境变量配置

### 1. 复制环境变量模板

```bash
cp .env.mysql.example .env
```

### 2. 编辑环境变量

```bash
# MySQL数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=ssl_manager
MYSQL_PASSWORD=ssl_manager_password
MYSQL_DATABASE=ssl_manager

# 其他配置...
```

## 数据迁移

### 1. 从SQLite迁移到MySQL

如果您已有SQLite数据，可以使用迁移脚本：

```bash
cd backend/scripts

# 运行迁移脚本
python3 migrate_sqlite_to_mysql.py \
    --sqlite-db ../database/ssl_manager.db \
    --mysql-host localhost \
    --mysql-user ssl_manager \
    --mysql-password ssl_manager_password \
    --mysql-database ssl_manager
```

### 2. 全新安装

如果是全新安装，直接初始化数据库：

```bash
cd backend/src
python3 -c "from models.database import init_db; init_db()"
```

## 应用部署

### 方式一：Docker部署（推荐）

```bash
# 构建并启动所有服务
docker-compose -f docker-compose.mysql.yml up -d

# 查看服务状态
docker-compose -f docker-compose.mysql.yml ps

# 查看日志
docker-compose -f docker-compose.mysql.yml logs -f
```

### 方式二：手动部署

```bash
# 安装Python依赖
cd backend
pip3 install -r requirements.txt

# 设置环境变量
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=ssl_manager
export MYSQL_PASSWORD=ssl_manager_password
export MYSQL_DATABASE=ssl_manager

# 启动应用
cd src
python3 app.py
```

## 测试验证

### 1. 数据库连接测试

```bash
cd backend/scripts
python3 test_mysql_connection.py \
    --host localhost \
    --user ssl_manager \
    --password ssl_manager_password \
    --database ssl_manager
```

### 2. API接口测试

```bash
# 健康检查
curl http://localhost:5000/api/health

# 登录测试
curl -X POST http://localhost:5000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}'
```

## 性能优化

### 1. MySQL优化

```sql
-- 查看当前配置
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';

-- 优化查询缓存
SET GLOBAL query_cache_size = 33554432;
SET GLOBAL query_cache_type = 1;

-- 分析表统计信息
ANALYZE TABLE certificates;
ANALYZE TABLE monitoring_configs;
```

### 2. 索引优化

```sql
-- 查看索引使用情况
EXPLAIN SELECT * FROM certificates WHERE domain = 'example.com';

-- 添加复合索引（如需要）
CREATE INDEX idx_cert_domain_status ON certificates(domain, status);
```

## 监控和维护

### 1. 数据库监控

```bash
# 查看MySQL状态
mysqladmin -u ssl_manager -p status

# 查看进程列表
mysqladmin -u ssl_manager -p processlist

# 查看慢查询
tail -f /var/log/mysql/slow.log
```

### 2. 备份策略

```bash
# 创建备份脚本
cat > /opt/ssl_manager/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/ssl_manager/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="ssl_manager_backup_${DATE}.sql"

mkdir -p $BACKUP_DIR

mysqldump -u ssl_manager -p ssl_manager > $BACKUP_DIR/$BACKUP_FILE

# 压缩备份文件
gzip $BACKUP_DIR/$BACKUP_FILE

# 删除7天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x /opt/ssl_manager/backup.sh

# 添加到crontab
echo "0 2 * * * /opt/ssl_manager/backup.sh" | crontab -
```

### 3. 日志轮转

```bash
# 配置MySQL日志轮转
cat > /etc/logrotate.d/mysql << 'EOF'
/var/log/mysql/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 640 mysql mysql
    postrotate
        mysqladmin flush-logs
    endscript
}
EOF
```

## 故障排除

### 常见问题

1. **连接被拒绝**
   ```bash
   # 检查MySQL服务状态
   sudo systemctl status mysql
   
   # 检查端口监听
   netstat -tlnp | grep 3306
   ```

2. **字符集问题**
   ```sql
   -- 检查字符集设置
   SHOW VARIABLES LIKE 'character_set%';
   SHOW VARIABLES LIKE 'collation%';
   ```

3. **权限问题**
   ```sql
   -- 检查用户权限
   SHOW GRANTS FOR 'ssl_manager'@'%';
   ```

4. **性能问题**
   ```sql
   -- 查看慢查询
   SHOW VARIABLES LIKE 'slow_query_log%';
   
   -- 查看连接数
   SHOW STATUS LIKE 'Threads_connected';
   ```

### 日志分析

```bash
# 查看MySQL错误日志
tail -f /var/log/mysql/error.log

# 查看应用日志
tail -f /app/logs/ssl_manager.log

# 查看Docker容器日志
docker logs ssl_manager_mysql
docker logs ssl_manager_backend
```

## 安全配置

### 1. MySQL安全加固

```bash
# 运行安全脚本
mysql_secure_installation
```

### 2. 防火墙配置

```bash
# 只允许特定IP访问MySQL
sudo ufw allow from 192.168.1.0/24 to any port 3306
```

### 3. SSL连接（可选）

```sql
-- 启用SSL
ALTER USER 'ssl_manager'@'%' REQUIRE SSL;
```

## 升级和维护

### 版本升级

```bash
# 备份数据
mysqldump -u ssl_manager -p ssl_manager > backup_before_upgrade.sql

# 升级MySQL
sudo apt update
sudo apt upgrade mysql-server

# 升级数据库结构
mysql_upgrade -u root -p
```

### 定期维护

```sql
-- 优化表
OPTIMIZE TABLE certificates;
OPTIMIZE TABLE monitoring_configs;

-- 检查表
CHECK TABLE certificates;
CHECK TABLE monitoring_configs;

-- 修复表（如需要）
REPAIR TABLE table_name;
```

## 联系支持

如果在部署过程中遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 检查配置文件是否正确
3. 确认网络连接和防火墙设置
4. 联系技术支持团队

---

**注意**: 在生产环境中部署前，请务必在测试环境中验证所有配置和功能。
