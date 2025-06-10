# SSL证书管理器

一个基于Docker的SSL证书自动化管理系统，专为生产环境优化，支持Let's Encrypt证书的自动申请、续期和部署。

## 🚀 快速开始

### 📖 文档导航

- **[快速开始指南](QUICKSTART.md)** - 5分钟快速部署
- **[详细部署指南](DEPLOYMENT.md)** - 完整部署文档
- **[更新日志](update.log)** - 版本更新记录

### ⚡ 一键部署（推荐）

```bash
# 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 生产环境一键部署
./scripts/deploy-production.sh
```

**系统要求**: Ubuntu 22.04.5 LTS, 16GB内存, 4核CPU, 支持cgroup v2

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

## 📋 系统要求（基于生产环境验证）

### 推荐配置
- **操作系统**: Ubuntu 22.04.5 LTS (已验证)
- **架构**: x86_64
- **内核**: >= 6.0 (支持cgroup v2)
- **Docker**: 26.1.3+ (必须支持cgroup v2)
- **Docker Compose**: v2.24.0+
- **内存**: 16GB (最低8GB)
- **CPU**: 4核心 (最低2核心)
- **磁盘**: 系统盘40GB + 数据盘20GB
- **网络**: 需要访问互联网

### 关键要求
- ⚠️ **cgroup v2支持**: 必须启用，用于cAdvisor容器监控
- ⚠️ **端口号格式**: 环境变量中端口号必须使用字符串格式

## 🌐 服务访问地址

部署完成后，可以通过以下地址访问各项服务：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | http://localhost/ | SSL证书管理界面 |
| API接口 | http://localhost/api/ | REST API接口 |
| API文档 | http://localhost/api/docs | Swagger API文档 |
| Prometheus | http://localhost/prometheus/ | 监控数据收集 |
| Grafana | http://localhost/grafana/ | 可视化监控面板 |
| cAdvisor | http://localhost:8080/ | 容器监控 |

## 🔑 默认登录信息

**Grafana监控面板:**
- 用户名: admin
- 密码: 查看 `.env` 文件中的 `GRAFANA_PASSWORD`

⚠️ **生产环境请及时修改默认密码**

## 🛠️ 管理命令

```bash
# 查看服务状态 (生产环境)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring ps

# 查看服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring logs -f

# 重启特定服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart backend

# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring down

# 备份数据库
docker exec ssl-manager-postgres pg_dump -U ssl_user ssl_manager > backup_$(date +%Y%m%d_%H%M%S).sql

# 检查系统资源
docker stats --no-stream && free -h
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
