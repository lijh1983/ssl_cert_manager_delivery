# SSL证书管理系统 - 项目结构说明

本文档详细说明项目的目录结构和文件组织方式。

## 📁 项目根目录结构

```
ssl_cert_manager_delivery/
├── README.md                           # 项目主要说明文档
├── .gitignore                          # Git忽略文件配置
├── .env.example                        # 环境变量配置模板
├── docker-compose.yml                  # 标准Docker Compose配置
├── docker-compose.aliyun.yml          # 阿里云优化Docker Compose配置
├── docker-compose.dev.yml             # 开发环境配置
├── docker-compose.prod.yml            # 生产环境配置
├── backend/                            # 后端API服务
├── frontend/                           # 前端Web应用
├── nginx/                              # Nginx反向代理配置
├── monitoring/                         # 监控和指标配置
├── database/                           # 数据库初始化脚本
├── scripts/                            # 部署和管理脚本
└── docs/                               # 项目文档
```

## 🔧 Scripts目录详细说明

### 部署相关脚本
- `deploy.sh` - 通用部署脚本
- `deploy_aliyun.sh` - 阿里云环境专用部署脚本
- `setup_nginx_proxy.sh` - nginx反向代理配置脚本

### 环境配置脚本
- `setup_aliyun_docker.sh` - 阿里云Docker环境配置
- `setup_rhel9_docker.sh` - RHEL/CentOS 9专用Docker配置

### 问题修复脚本
- `fix_nginx_image_issue.sh` - nginx镜像拉取问题修复
- `test_docker_images.sh` - Docker镜像拉取测试工具

### 构建和测试脚本
- `build.sh` - 项目构建脚本
- `prebuild_images.sh` - 预构建镜像脚本
- `test_deployment.sh` - 部署测试脚本

### 服务管理脚本
- `restart_services.sh` - 服务重启管理脚本

### 验证脚本
- `verify.sh` - 通用验证脚本
- `verify_aliyun_deployment.sh` - 阿里云部署验证
- `verify_nginx_proxy.sh` - nginx代理验证

### 系统服务配置
- `systemd/` - systemd服务配置文件
  - `ssl-manager.service` - 主服务配置
  - `ssl-manager-backend.service` - 后端服务配置

## 🌐 Nginx目录结构

```
nginx/
├── nginx.conf                          # 主nginx配置文件
├── conf.d/                             # 虚拟主机配置目录
│   ├── ssl-manager.conf                # SSL管理系统配置
│   └── ssl-manager.conf.template       # 配置模板
├── ssl/                                # SSL证书存储目录
├── Dockerfile.proxy                    # nginx代理镜像Dockerfile
└── Dockerfile.proxy.aliyun            # 阿里云优化版Dockerfile
```

## 📚 Docs目录结构

```
docs/
├── DEPLOYMENT.md                       # 通用部署指南
├── ALIYUN_DEPLOYMENT.md               # 阿里云部署指南
├── NGINX_PROXY_SETUP.md               # nginx反向代理配置指南
├── RHEL9_DEPLOYMENT_FIX.md            # RHEL 9部署问题解决方案
├── PROJECT_STRUCTURE.md               # 项目结构说明（本文档）
├── API.md                              # API接口文档
├── USER_GUIDE.md                      # 用户使用指南
├── DEVELOPMENT.md                      # 开发环境配置
└── SECURITY.md                        # 安全配置说明
```

## 🔨 Backend目录结构

```
backend/
├── src/                                # 源代码目录
│   ├── app.py                         # 主应用入口
│   ├── models/                        # 数据模型
│   ├── api/                           # API路由
│   ├── services/                      # 业务逻辑服务
│   └── utils/                         # 工具函数
├── requirements.txt                    # Python依赖包
├── Dockerfile                         # 标准Dockerfile
├── Dockerfile.aliyun                 # 阿里云优化Dockerfile
└── tests/                             # 测试文件
```

## 🎨 Frontend目录结构

```
frontend/
├── src/                               # 源代码目录
│   ├── components/                    # Vue组件
│   ├── views/                         # 页面视图
│   ├── router/                        # 路由配置
│   ├── store/                         # 状态管理
│   └── utils/                         # 工具函数
├── public/                            # 静态资源
├── package.json                       # Node.js依赖配置
├── vite.config.ts                     # Vite构建配置
├── Dockerfile                         # 标准Dockerfile
├── Dockerfile.aliyun                 # 阿里云优化Dockerfile
└── nginx-default.conf                # nginx配置
```

## 📊 Monitoring目录结构

```
monitoring/
├── prometheus/                        # Prometheus配置
│   └── prometheus.yml                 # Prometheus主配置
├── grafana/                           # Grafana配置
│   ├── dashboards/                    # 仪表板配置
│   └── datasources/                   # 数据源配置
└── alertmanager/                      # 告警管理配置
```

## 🗄️ Database目录结构

```
database/
├── init/                              # 数据库初始化脚本
│   ├── 01-init-database.sql          # 数据库创建脚本
│   ├── 02-create-tables.sql          # 表结构创建
│   └── 03-insert-data.sql            # 初始数据插入
├── migrations/                        # 数据库迁移脚本
└── backups/                           # 数据库备份文件
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
