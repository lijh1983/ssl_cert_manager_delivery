# SSL证书管理器

一个基于Docker的SSL证书自动化管理系统，专为阿里云ECS环境优化，支持Let's Encrypt证书的自动申请、续期和部署。

## 🚀 快速部署

### 一键部署（推荐）

```bash
# 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 一键部署
./deploy.sh --quick
```

### 手动部署

```bash
# 1. 创建环境配置
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

# 2. 构建基础镜像
docker build -t ssl-manager-backend-base:latest -f backend/Dockerfile.base ./backend
docker build -t ssl-manager-frontend-base:latest -f frontend/Dockerfile.base ./frontend

# 3. 启动完整服务（包含监控）
docker-compose -f docker-compose.aliyun.yml --profile monitoring up -d
```

## 📋 系统要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Docker**: 20.10+
- **内存**: 最低2GB，推荐4GB+
- **磁盘**: 最低10GB可用空间
- **网络**: 需要访问互联网（已配置阿里云镜像源）

## 🌐 访问地址

部署完成后，可以通过以下地址访问：

- **主应用**: http://ssl.gzyggl.com
- **API文档**: http://ssl.gzyggl.com/api/docs
- **监控面板**: http://ssl.gzyggl.com/monitoring/
- **Prometheus**: http://ssl.gzyggl.com:9090

## 🔑 默认账户

- **管理员**: admin / admin123
- **Grafana**: admin / grafana_admin_123
- **数据库**: ssl_user / ssl_password_123

⚠️ **生产环境请及时修改默认密码**

## 🛠️ 管理命令

```bash
# 查看服务状态
docker-compose -f docker-compose.aliyun.yml ps

# 查看服务日志
docker-compose -f docker-compose.aliyun.yml logs -f

# 重启服务
docker-compose -f docker-compose.aliyun.yml restart

# 停止服务
docker-compose -f docker-compose.aliyun.yml down

# 备份数据库
docker exec ssl-manager-postgres pg_dump -U ssl_user ssl_manager > backup.sql
```

## 📊 功能特性

- 🔒 **自动SSL证书管理**: Let's Encrypt证书自动申请和续期
- 🌐 **多域名支持**: 支持单域名、通配符和多域名证书
- 📊 **实时监控**: Prometheus + Grafana监控面板
- 🔄 **自动部署**: 证书自动部署到多个服务器
- 📱 **Web管理界面**: 直观的证书管理界面
- 🗄️ **PostgreSQL数据库**: 高性能数据存储
- 🚨 **告警系统**: 证书过期提醒和故障告警

## 🏗️ 系统架构

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

## 📁 项目结构

```
ssl_cert_manager_delivery/
├── backend/                    # 后端服务
│   ├── Dockerfile             # 后端应用镜像
│   ├── Dockerfile.base        # 后端基础镜像
│   ├── requirements.txt       # Python依赖
│   └── src/                   # 源代码
├── frontend/                  # 前端应用
│   ├── Dockerfile             # 前端应用镜像
│   ├── Dockerfile.base        # 前端基础镜像
│   ├── package.json           # Node.js依赖
│   └── src/                   # 源代码
├── database/                  # 数据库配置
│   └── init/                  # 初始化脚本
├── nginx/                     # Nginx配置
├── monitoring/                # 监控配置
├── scripts/                   # 管理脚本
│   └── ssl-manager.sh         # 核心管理脚本
├── tests/                     # 测试用例
├── deploy.sh                  # 一键部署脚本
├── docker-compose.aliyun.yml  # Docker Compose配置
├── DEPLOYMENT.md              # 部署指南
└── README.md                  # 项目说明
```

## 🔧 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查日志
   docker-compose -f docker-compose.aliyun.yml logs backend
   
   # 检查端口占用
   netstat -tlnp | grep :80
   netstat -tlnp | grep :443
   ```

2. **数据库连接失败**
   ```bash
   # 检查PostgreSQL状态
   docker exec ssl-manager-postgres pg_isready -U ssl_user -d ssl_manager
   
   # 重启数据库
   docker-compose -f docker-compose.aliyun.yml restart postgres
   ```

3. **网络连接问题**
   ```bash
   # 测试网络连接
   docker run --rm alpine:latest wget -O- https://mirrors.aliyun.com
   
   # 检查DNS配置
   cat /etc/resolv.conf
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

## 📖 部署说明

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DOMAIN_NAME | 主域名 | ssl.gzyggl.com |
| EMAIL | 联系邮箱 | 19822088@qq.com |
| ENVIRONMENT | 运行环境 | production |
| DB_NAME | 数据库名 | ssl_manager |
| DB_USER | 数据库用户 | ssl_user |
| DB_PASSWORD | 数据库密码 | 随机生成 |

### 数据持久化

- **PostgreSQL数据**: 保存在Docker卷 `postgres_data`
- **SSL证书**: 保存在Docker卷 `ssl_certs`
- **应用日志**: 保存在Docker卷 `app_logs`
- **监控数据**: 保存在Docker卷 `prometheus_data` 和 `grafana_data`

### 安全配置

- 使用bcrypt哈希存储密码
- PostgreSQL外键约束确保数据一致性
- UUID主键避免ID猜测攻击
- 完整的操作审计日志

## 🎯 生产环境建议

1. **域名配置**: 确保域名 `ssl.gzyggl.com` 正确解析到服务器
2. **防火墙**: 开放80和443端口
3. **SSL证书**: 系统会自动申请和续期Let's Encrypt证书
4. **备份策略**: 定期备份PostgreSQL数据库和SSL证书
5. **监控**: 启用Prometheus和Grafana监控
6. **日志**: 定期清理和归档应用日志

## 📞 技术支持

- **GitHub Issues**: https://github.com/lijh1983/ssl_cert_manager_delivery/issues
- **邮箱**: 19822088@qq.com

## 📄 许可证

MIT License
