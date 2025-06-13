# SSL证书管理系统 - 项目结构说明

本文档详细说明项目的目录结构和文件组织方式。

## 📁 项目根目录结构

```
ssl_cert_manager_delivery/
├── README.md                           # 项目主要说明文档
├── QUICKSTART.md                       # 快速开始指南
├── DEVELOPMENT_RULES.md                # 开发和维护规则
├── SSL_CERTIFICATE_FEATURES.md        # SSL证书功能特性说明
├── TECHNICAL_OVERVIEW.md              # 技术概览和架构说明
├── SCRIPT_USAGE_EXAMPLES.md           # 脚本使用示例
├── update.log                          # 项目更新日志
├── .gitignore                          # Git忽略文件配置
├── .env.example                        # 环境变量配置模板
├── docker-compose.yml                  # 主要Docker Compose配置
├── docker-compose.production.yml       # 生产环境配置
├── docker-compose.mysql.yml           # MySQL专用配置
├── deploy.sh                           # 一键部署脚本
├── backend/                            # 后端API服务
├── frontend/                           # 前端Web应用
├── nginx/                              # Nginx反向代理配置
├── mysql/                              # MySQL数据库配置
├── database/                           # 数据库初始化脚本
├── scripts/                            # 部署和管理脚本
├── tests/                              # 测试文件
├── test/                               # 测试模拟数据
├── examples/                           # 示例代码
├── client/                             # 客户端工具
└── docs/                               # 项目文档
```

## 🔧 Scripts目录详细说明

### 核心管理脚本
- `ssl-manager.sh` - 统一管理脚本（核心）
  - 包含部署、验证、修复、状态查看等所有功能
  - 替代了之前的多个独立脚本

### 部署相关脚本
- `deploy-production.sh` - 生产环境部署脚本
- `deploy-local.sh` - 本地环境部署脚本
- `verify-deployment.sh` - 部署验证脚本

### 配置验证脚本
- `validate_config.py` - 配置文件验证工具

### 系统服务配置
- `systemd/` - systemd服务配置文件
  - `ssl-manager.service` - 主服务配置
  - `ssl-manager-backend.service` - 后端服务配置

## 🌐 Nginx目录结构

```
nginx/
├── nginx.conf                          # 主nginx配置文件
├── conf.d/                             # 虚拟主机配置目录
│   └── ssl-manager-production.conf     # 生产环境配置
├── Dockerfile.proxy.alpine            # Alpine版nginx代理镜像
└── Dockerfile.standalone              # 独立nginx镜像
```

## 📚 Docs目录结构

```
docs/
├── PROJECT_STRUCTURE.md               # 项目结构说明（本文档）
├── ALIYUN_DEPLOYMENT.md               # 阿里云部署指南
├── api_reference.md                   # API接口文档
├── user_manual.md                     # 用户使用指南
├── mysql_deployment.md                # MySQL部署指南
└── production_deployment.md           # 生产环境部署指南
```

## 🔨 Backend目录结构

```
backend/
├── src/                                # 源代码目录
│   ├── app.py                         # 主应用入口
│   ├── models/                        # 数据模型
│   ├── routes/                        # API路由
│   ├── services/                      # 业务逻辑服务
│   └── utils/                         # 工具函数
├── config/                            # 配置文件
│   └── gunicorn.conf.py              # Gunicorn配置
├── database/                          # 数据库相关
│   └── init_mysql.sql                # MySQL初始化脚本
├── migrations/                        # 数据库迁移脚本
├── scripts/                           # 后端脚本
├── docker/                            # Docker相关文件
├── requirements.txt                   # Python依赖包
├── requirements-prod.txt              # 生产环境依赖
├── Dockerfile                         # 标准Dockerfile
├── Dockerfile.base                    # 基础镜像Dockerfile
├── Dockerfile.production              # 生产环境Dockerfile
└── tests/                             # 测试文件
```

## 🎨 Frontend目录结构

```
frontend/
├── src/                               # 源代码目录
│   ├── components/                    # Vue组件
│   ├── views/                         # 页面视图
│   ├── router/                        # 路由配置
│   ├── stores/                        # Pinia状态管理
│   └── utils/                         # 工具函数
├── public/                            # 静态资源
├── package.json                       # Node.js依赖配置
├── vite.config.ts                     # Vite构建配置
├── vitest.config.ts                   # Vitest测试配置
├── playwright.config.ts               # Playwright E2E测试配置
├── tsconfig.json                      # TypeScript配置
├── tsconfig.node.json                 # Node.js TypeScript配置
├── index.html                         # 入口HTML文件
├── Dockerfile                         # 标准Dockerfile
├── Dockerfile.base                    # 基础镜像Dockerfile
├── nginx.conf                         # nginx配置
└── nginx-default.conf                # 默认nginx配置
```

## 🗄️ MySQL目录结构

```
mysql/
├── conf.d/                            # MySQL配置文件目录
│   └── mysql.cnf                     # MySQL优化配置
└── logs/                              # MySQL日志目录
```

## 🗄️ Database目录结构

```
database/
├── init/                              # 数据库初始化脚本
│   └── init_mysql.sql                # MySQL初始化脚本
└── database_design.md                # 数据库设计文档
```

## 🧪 Tests目录结构

```
tests/
├── backend/                           # 后端测试
├── frontend/                          # 前端测试
├── e2e/                              # 端到端测试
├── integration/                       # 集成测试
├── conftest.py                       # pytest配置
└── test_error_handling.py           # 错误处理测试
```

## 🔧 Client目录结构

```
client/
└── client.sh                         # 客户端安装脚本
```

## 📋 文件命名规范

### 脚本文件命名
- 使用小写字母和下划线分隔
- 功能描述清晰，如：`setup_nginx_proxy.sh`
- 特定环境的脚本添加环境后缀，如：`deploy_aliyun.sh`

### 配置文件命名
- Docker相关：`Dockerfile.环境名`
- 配置文件：`服务名.conf`
- 模板文件：`文件名.template`

### 文档文件命名
- 使用大写字母和下划线分隔
- 功能描述清晰，如：`NGINX_PROXY_SETUP.md`
- 特定环境的文档添加环境前缀，如：`ALIYUN_DEPLOYMENT.md`

## 🔧 维护建议

### 定期清理
```bash
# 清理Docker缓存
docker system prune -a

# 清理临时文件
find . -name "*.tmp" -delete
find . -name "*.backup" -delete

# 清理日志文件
find . -name "*.log" -mtime +7 -delete
```

### 权限检查
```bash
# 确保脚本有执行权限
find scripts/ -name "*.sh" | xargs chmod +x

# 检查配置文件权限
find . -name "*.conf" -exec chmod 644 {} \;
```

### 代码质量
- 所有脚本使用中文注释
- 配置文件包含详细说明
- 文档保持更新和同步
- 遵循统一的编码规范

## 📞 获取支持

如果对项目结构有疑问，请：
1. 查看相关文档目录下的详细说明
2. 运行对应的验证脚本检查配置
3. 查看脚本内的注释说明
4. 提交Issue到项目仓库

项目结构设计遵循最佳实践，确保易于维护和扩展。
