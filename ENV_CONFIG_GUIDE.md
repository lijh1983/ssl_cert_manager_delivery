# 环境变量配置指南

## 📋 配置文件说明

SSL证书管理项目提供了两个环境变量配置模板，适用于不同的部署环境：

### 1. `.env.example` - 独立部署环境
- **适用场景**: 独立服务器部署、本地开发、非Docker环境
- **特点**: 使用IP地址进行服务间通信
- **主机配置**: `MYSQL_HOST=127.0.0.1`, `REDIS_HOST=127.0.0.1`

### 2. `.env.docker.example` - Docker环境
- **适用场景**: Docker Compose部署、容器化环境
- **特点**: 使用Docker服务名进行服务间通信
- **主机配置**: `MYSQL_HOST=mysql`, `REDIS_HOST=redis`

## 🚀 快速开始

### 独立部署环境
```bash
# 复制配置文件
cp .env.example .env

# 修改必要的配置
nano .env

# 启动服务
./scripts/deploy-local.sh
```

### Docker环境
```bash
# 复制Docker配置文件
cp .env.docker.example .env

# 修改必要的配置
nano .env

# 启动Docker服务
docker-compose up -d
```

## 🔧 主要配置差异

| 配置项 | 独立部署 | Docker环境 | 说明 |
|--------|----------|------------|------|
| MYSQL_HOST | 127.0.0.1 | mysql | MySQL服务器地址 |
| REDIS_HOST | 127.0.0.1 | redis | Redis服务器地址 |
| VITE_PROXY_TARGET | http://127.0.0.1:8000 | http://backend:8000 | 前端代理目标 |
| RATE_LIMIT_STORAGE_URL | redis://127.0.0.1:6379/1 | redis://redis:6379/1 | 速率限制存储 |
| ELASTICSEARCH_HOSTS | 127.0.0.1:9200 | elasticsearch:9200 | Elasticsearch地址 |
| KIBANA_HOST | 127.0.0.1:5601 | kibana:5601 | Kibana地址 |

## 🔐 安全配置

### 必须修改的配置项
以下配置项包含"CHANGE_THIS"标识，**必须**在生产环境中修改：

```bash
# 数据库密码
MYSQL_PASSWORD=CHANGE_THIS_TO_A_SECURE_MYSQL_PASSWORD
MYSQL_ROOT_PASSWORD=CHANGE_THIS_TO_A_SECURE_MYSQL_ROOT_PASSWORD

# 应用密钥
SECRET_KEY=CHANGE_THIS_TO_A_SECURE_32_CHAR_SECRET_KEY_IN_PRODUCTION
JWT_SECRET_KEY=CHANGE_THIS_TO_A_SECURE_32_CHAR_JWT_SECRET_KEY_TOO
CSRF_SECRET_KEY=CHANGE_THIS_TO_A_SECURE_32_CHAR_CSRF_SECRET_KEY

# Redis密码
REDIS_PASSWORD=CHANGE_THIS_TO_A_SECURE_REDIS_PASSWORD

# 监控密码
GRAFANA_PASSWORD=CHANGE_THIS_TO_A_SECURE_GRAFANA_PASSWORD
GRAFANA_ADMIN_PASSWORD=CHANGE_THIS_TO_A_SECURE_GRAFANA_ADMIN_PASSWORD

# 邮件配置
SMTP_USERNAME=CHANGE_THIS_TO_YOUR_EMAIL@example.com
SMTP_PASSWORD=CHANGE_THIS_TO_YOUR_EMAIL_PASSWORD
```

### 密钥生成命令
```bash
# 生成32位安全密钥
openssl rand -base64 32

# 生成16位安全密码
openssl rand -base64 16

# 生成64位超强密钥
openssl rand -base64 64
```

## 🏗️ 数据库连接配置

项目支持两种数据库连接方式：

### 方式1: 使用独立环境变量（推荐）
```bash
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=ssl_manager
MYSQL_USER=ssl_manager
MYSQL_PASSWORD=your_password
```
程序会自动使用这些变量构建连接URL。

### 方式2: 使用完整连接URL
```bash
DATABASE_URL=mysql+pymysql://ssl_manager:password@127.0.0.1:3306/ssl_manager?charset=utf8mb4
```
如果设置了`DATABASE_URL`，将优先使用此URL。

## 🐳 Docker环境特殊说明

### 服务名解析
在Docker Compose环境中，容器间通信使用服务名：
- `mysql` - MySQL数据库服务
- `redis` - Redis缓存服务
- `backend` - 后端API服务
- `frontend` - 前端Web服务
- `nginx` - 反向代理服务

### 网络配置
Docker Compose会自动创建内部网络，服务名会被解析为对应容器的IP地址。

### 端口映射
容器内部端口和主机端口可能不同：
- 容器内: `mysql:3306`
- 主机访问: `localhost:3306`

## 🔍 配置验证

### 使用验证工具
```bash
# 验证配置完整性
python3 scripts/validate_env_example.py

# 检查必需的环境变量
./scripts/ssl-manager.sh verify --all
```

### 手动验证
```bash
# 检查配置文件语法
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
print('配置文件加载成功')
print(f'MYSQL_HOST: {os.getenv(\"MYSQL_HOST\")}')
print(f'REDIS_HOST: {os.getenv(\"REDIS_HOST\")}')
"
```

## 🚨 常见问题

### 1. 连接失败
**问题**: 无法连接到MySQL或Redis
**解决**: 检查主机地址配置是否正确
- 独立部署: 使用`127.0.0.1`或实际IP
- Docker环境: 使用服务名`mysql`、`redis`

### 2. 权限错误
**问题**: 数据库连接权限被拒绝
**解决**: 检查用户名和密码配置
```bash
MYSQL_USER=ssl_manager
MYSQL_PASSWORD=正确的密码
```

### 3. 端口冲突
**问题**: 端口已被占用
**解决**: 修改端口配置
```bash
MYSQL_PORT=3307  # 改为其他端口
REDIS_PORT=6380  # 改为其他端口
```

### 4. 前端代理失败
**问题**: 前端无法访问后端API
**解决**: 检查代理目标配置
- 独立部署: `VITE_PROXY_TARGET=http://127.0.0.1:8000`
- Docker环境: `VITE_PROXY_TARGET=http://backend:8000`

## 📝 配置模板选择指南

| 部署方式 | 推荐配置模板 | 说明 |
|----------|--------------|------|
| 本地开发 | `.env.example` | 使用本地IP地址 |
| 独立服务器 | `.env.example` | 修改IP为实际服务器地址 |
| Docker Compose | `.env.docker.example` | 使用Docker服务名 |
| Kubernetes | 自定义 | 使用K8s服务发现 |
| 云服务 | 根据情况 | 使用云服务内网地址 |

## 🎯 最佳实践

1. **环境隔离**: 不同环境使用不同的配置文件
2. **密码安全**: 生产环境必须使用强密码
3. **版本控制**: 配置文件不要提交到Git
4. **备份配置**: 重要配置要有备份
5. **定期更新**: 定期轮换密码和密钥
6. **监控告警**: 配置异常要及时告警

---

**重要提醒**: 
- 🔴 **绝不要**将包含真实密码的.env文件提交到Git
- 🔴 **绝不要**在生产环境使用默认密码
- 🟢 **务必**根据部署环境选择正确的配置模板
- 🟢 **务必**修改所有包含"CHANGE_THIS"的配置项
