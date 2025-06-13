# SSL证书管理器

一个企业级的SSL证书管理系统，提供证书申请、监控、续期和管理的完整解决方案。具备四大核心功能模块：检测开关控制、域名监控、端口监控和证书操作，为企业提供专业的SSL证书生命周期管理。

## 🚀 快速开始

### 📖 文档导航

- **[快速开始指南](QUICKSTART.md)** - 5分钟快速部署
- **[技术概览](TECHNICAL_OVERVIEW.md)** - 系统架构和技术栈
- **[功能特性](SSL_CERTIFICATE_FEATURES.md)** - 核心功能详解
- **[脚本使用示例](SCRIPT_USAGE_EXAMPLES.md)** - 部署脚本使用指南
- **[开发规则](DEVELOPMENT_RULES.md)** - 开发和维护规范
- **[环境配置指南](ENV_CONFIG_GUIDE.md)** - 环境变量配置说明
- **[环境安全指南](ENVIRONMENT_SECURITY_GUIDE.md)** - 环境变量安全管理
- **[更新日志](update.log)** - 版本更新记录

### ⚡ 一键部署（推荐）

```bash
# 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 生产环境一键部署
./scripts/deploy-production.sh
```

**系统要求**: Ubuntu 22.04.5 LTS, 16GB内存, 4核CPU, Docker 26.1.3+

### 手动部署

#### 1. 选择配置模板
```bash
# 独立部署环境 (推荐)
cp .env.example .env

# 或 Docker环境
cp .env.docker.example .env
```

#### 2. 修改配置文件
```bash
# 编辑配置文件
nano .env

# 必须修改的配置项 (包含CHANGE_THIS的项目)
# - MYSQL_PASSWORD
# - SECRET_KEY
# - JWT_SECRET_KEY
# - REDIS_PASSWORD
# 等等...

# 生成安全密钥
openssl rand -base64 32  # 用于SECRET_KEY等
```

#### 3. 启动服务
```bash
# 独立部署
./scripts/deploy-local.sh

# 或 Docker环境
docker-compose up -d
```

## 📋 系统要求

### 推荐配置
- **操作系统**: Ubuntu 22.04.5 LTS
- **架构**: x86_64
- **Docker**: 26.1.3+
- **Docker Compose**: v2.24.0+
- **内存**: 16GB (最低8GB)
- **CPU**: 4核心 (最低2核心)
- **磁盘**: 系统盘40GB + 数据盘20GB
- **网络**: 需要访问互联网

## 🌐 服务访问地址

部署完成后，可以通过以下地址访问各项服务：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | http://localhost/ | SSL证书管理界面 |
| API接口 | http://localhost/api/ | REST API接口 |
| API文档 | http://localhost/api/docs | Swagger API文档 |

## 🔑 SSL证书管理功能

### 🎯 四大核心功能模块 (100%完成)

#### 1. 检测开关控制系统
- ✅ **证书级别监控开关** - 灵活控制每个证书的监控状态
- ✅ **监控频率配置** - 支持每小时到每周的检查频率
- ✅ **批量监控配置** - 批量设置多个证书的监控参数
- ✅ **告警阈值管理** - 自定义证书到期告警天数

#### 2. 域名监控功能
- ✅ **DNS解析检查** - 实时监控域名DNS解析状态
- ✅ **域名可达性监控** - 检测域名HTTP/HTTPS访问状态
- ✅ **智能告警机制** - 多渠道告警（邮件、短信、Webhook）
- ✅ **监控历史记录** - 完整的域名监控历史和趋势分析

#### 3. 端口监控系统
- ✅ **SSL端口检查** - 监控443、8443等SSL端口状态
- ✅ **TLS协议检测** - 检测支持的TLS版本和加密套件
- ✅ **安全评估分析** - 专业的SSL安全等级评估(A+到F)
- ✅ **漏洞扫描检测** - 检测已知SSL/TLS安全漏洞

#### 4. 证书操作功能
- ✅ **手动检测触发** - 支持手动触发完整证书检测
- ✅ **批量导入导出** - CSV格式批量导入导出证书信息
- ✅ **网络发现扫描** - 自动发现网络中的SSL证书
- ✅ **证书续期管理** - 自动和手动证书续期功能

### 📊 专业特性
- 🔒 **证书生命周期管理** - 从申请到续期的完整流程
- 📈 **实时监控面板** - 动态图表和状态展示
- 🛡️ **安全合规检查** - 基于最佳实践的安全建议
- 🚀 **批量操作支持** - 高效的批量处理能力
- 📱 **响应式界面** - 支持桌面和移动端访问

## 🛠️ 管理命令

```bash
# 使用统一管理脚本
./scripts/ssl-manager.sh status          # 查看服务状态
./scripts/ssl-manager.sh logs            # 查看服务日志
./scripts/ssl-manager.sh restart         # 重启服务
./scripts/ssl-manager.sh stop            # 停止服务
./scripts/ssl-manager.sh verify --all    # 验证系统配置

# 或使用Docker Compose命令
docker-compose ps                         # 查看服务状态
docker-compose logs -f                    # 查看服务日志
docker-compose restart backend           # 重启特定服务
docker-compose down                       # 停止所有服务

# 备份数据库
docker exec ssl-manager-mysql mysqldump -u ssl_manager -p ssl_manager > backup_$(date +%Y%m%d_%H%M%S).sql
```

## 📊 功能特性

- 🔒 **自动SSL证书管理**: Let's Encrypt证书自动申请和续期
- 🌐 **多域名支持**: 支持单域名、通配符和多域名证书
- 📊 **证书监控**: 内置SSL证书状态监控和到期提醒
- 🔄 **自动部署**: 证书自动部署到多个服务器
- 📱 **Web管理界面**: 直观的证书管理界面
- 🗄️ **MySQL 8.0.41数据库**: 企业级高性能数据存储
- 🚨 **告警系统**: 证书过期提醒和状态告警

## 🏗️ 系统架构

### 技术栈

**后端**:
- Python 3.11+ / Flask
- SQLAlchemy ORM
- MySQL 8.0.41 数据库 (专用)
- Redis 7.2 缓存
- Celery 异步任务队列
- Let's Encrypt ACME协议
- JWT认证 + CSRF保护
- PyMySQL 数据库驱动

**前端**:
- Vue.js 3 + TypeScript
- Element Plus UI组件库
- Vite 4.4+ 构建工具
- Pinia 状态管理
- Axios HTTP客户端
- ECharts 数据可视化
- 响应式设计 + PWA支持

**部署**:
- Docker + Docker Compose
- Nginx 反向代理 + 负载均衡
- MySQL 8.0.41 高可用配置
- 支持阿里云ECS部署
- 支持本地化部署
- 企业级监控和日志

### 架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │────│    Frontend     │────│     Backend     │
│   (Port 80/443) │    │   (Vue.js SPA)  │    │  (FastAPI/Flask)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │   MySQL 8.0.41 │    │    Redis 7.2    │
         │              │   (Database)    │    │     (Cache)     │
         │              └─────────────────┘    └─────────────────┘
         │

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
   # 检查MySQL状态
   docker exec ssl-manager-mysql mysqladmin ping -h localhost -u ssl_manager -p

   # 重启数据库
   docker-compose -f docker-compose.mysql.yml restart mysql
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
| MYSQL_DATABASE | 数据库名 | ssl_manager |
| MYSQL_USER | 数据库用户 | ssl_manager |
| MYSQL_PASSWORD | 数据库密码 | 随机生成 |

### 数据持久化

- **MySQL数据**: 保存在Docker卷 `mysql_data`
- **SSL证书**: 保存在Docker卷 `ssl_certs`
- **应用日志**: 保存在Docker卷 `app_logs`
- **Redis缓存**: 保存在Docker卷 `redis_data`

### 安全配置

- 使用bcrypt哈希存储密码
- MySQL外键约束确保数据一致性
- 自增主键和唯一索引避免数据冲突
- 完整的操作审计日志

## 🎯 生产环境建议

1. **域名配置**: 确保域名 `ssl.gzyggl.com` 正确解析到服务器
2. **防火墙**: 开放80和443端口
3. **SSL证书**: 系统会自动申请和续期Let's Encrypt证书
4. **备份策略**: 定期备份MySQL数据库和SSL证书
5. **监控**: 启用Prometheus和Grafana监控
6. **日志**: 定期清理和归档应用日志

## 📞 技术支持

- **GitHub Issues**: https://github.com/lijh1983/ssl_cert_manager_delivery/issues
- **邮箱**: 19822088@qq.com

## 📄 许可证

MIT License
