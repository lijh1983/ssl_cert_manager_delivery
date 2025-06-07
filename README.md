# SSL证书自动化管理系统

一个基于Vue.js + Flask的SSL证书自动化管理系统，提供证书申请、续期、部署和监控的完整解决方案。

## 🚀 功能特性

### 核心功能
- **证书管理**: 支持单域名、通配符、多域名证书的申请和管理
- **自动续期**: 智能监控证书过期时间，自动续期即将过期的证书
- **多CA支持**: 支持Let's Encrypt、ZeroSSL、Buypass等多个CA
- **服务器管理**: 统一管理多台服务器的证书部署
- **告警通知**: 邮件通知证书过期、续期失败等事件

### 技术特性
- **现代化界面**: 基于Vue 3 + Element Plus的响应式前端
- **RESTful API**: 标准化的API接口设计
- **安全认证**: JWT Token认证和权限控制
- **实时监控**: 服务器状态和证书状态实时监控
- **操作日志**: 完整的操作审计日志

## 📋 系统要求

### 服务端要求
- Python 3.8+
- Node.js 16+
- SQLite 3 (或其他支持的数据库)

### 客户端要求
- Linux系统 (Ubuntu 18.04+, CentOS 7+)
- Nginx 或 Apache Web服务器
- 具有sudo权限的用户账户

## 🛠️ 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd ssl_cert_manager_delivery
```

### 2. 运行构建脚本
```bash
chmod +x scripts/build.sh
./scripts/build.sh
```

### 3. 配置环境变量
```bash
cd backend
cp .env.example .env
# 编辑 .env 文件配置相关参数
```

### 4. 启动服务
```bash
# 开发模式
./start.sh dev

# 生产模式
./start-prod.sh
```

### 5. 访问系统
- 前端地址: http://localhost:3000
- 后端API: http://localhost:5000
- 默认账户: admin / admin123

## 📁 项目结构

```
ssl_cert_manager_delivery/
├── backend/                 # 后端服务
│   ├── app.py              # Flask应用入口
│   ├── models.py           # 数据模型
│   ├── config.py           # 配置管理
│   ├── requirements.txt    # Python依赖
│   └── .env.example        # 环境变量模板
├── frontend/               # 前端应用
│   ├── src/                # 源代码
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 通用组件
│   │   ├── api/            # API接口
│   │   ├── stores/         # 状态管理
│   │   └── types/          # TypeScript类型
│   ├── package.json        # 前端依赖
│   └── vite.config.ts      # 构建配置
├── client/                 # 客户端脚本
│   └── client.sh           # 客户端安装脚本
├── scripts/                # 构建脚本
│   └── build.sh            # 系统构建脚本
├── docs/                   # 文档
│   ├── api_reference.md    # API文档
│   ├── deployment_guide.md # 部署指南
│   └── user_manual.md      # 用户手册
└── tests/                  # 测试用例
    └── run_tests.sh        # 测试脚本
```

## 🔧 配置说明

### 后端配置 (backend/.env)
```bash
# Flask配置
FLASK_ENV=production
SECRET_KEY=your-secret-key

# 数据库配置
DATABASE_URL=sqlite:///ssl_cert_manager.db

# JWT配置
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600

# 邮件配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 前端配置 (frontend/vite.config.ts)
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
```

## 📚 API文档

### 认证接口
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/logout` - 用户登出
- `POST /api/v1/auth/refresh` - 刷新Token

### 服务器管理
- `GET /api/v1/servers` - 获取服务器列表
- `POST /api/v1/servers` - 创建服务器
- `PUT /api/v1/servers/{id}` - 更新服务器
- `DELETE /api/v1/servers/{id}` - 删除服务器

### 证书管理
- `GET /api/v1/certificates` - 获取证书列表
- `POST /api/v1/certificates` - 申请证书
- `PUT /api/v1/certificates/{id}` - 更新证书
- `POST /api/v1/certificates/{id}/renew` - 续期证书

详细API文档请参考: [docs/api_reference.md](docs/api_reference.md)

## 🚀 部署指南

### 开发环境部署
1. 按照快速开始步骤安装依赖
2. 使用 `./start.sh dev` 启动开发服务

### 生产环境部署
1. 配置生产环境变量
2. 构建前端应用: `npm run build`
3. 使用 `./start-prod.sh` 启动生产服务
4. 配置Nginx反向代理

详细部署指南请参考: [docs/deployment_guide.md](docs/deployment_guide.md)

## 🧪 测试

### 运行测试
```bash
# 后端测试
cd backend
python -m pytest

# 前端测试
cd frontend
npm run test

# 集成测试
./tests/run_tests.sh
```

## 📖 使用说明

### 1. 添加服务器
1. 登录管理界面
2. 进入"服务器管理"页面
3. 点击"添加服务器"
4. 复制安装命令到目标服务器执行

### 2. 申请证书
1. 进入"证书管理"页面
2. 点击"申请证书"
3. 填写域名和选择服务器
4. 选择验证方式并提交

### 3. 监控告警
1. 进入"告警管理"页面
2. 查看证书过期预警
3. 处理相关告警事件

详细使用说明请参考: [docs/user_manual.md](docs/user_manual.md)

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 支持

如果您遇到问题或有任何疑问，请：

1. 查看 [文档](docs/)
2. 搜索 [Issues](../../issues)
3. 创建新的 [Issue](../../issues/new)

## 🔄 更新日志

### v1.0.0 (2025-06-05)
- ✨ 初始版本发布
- 🎉 完整的证书管理功能
- 🔐 用户认证和权限控制
- 📱 响应式前端界面
- 🤖 自动化证书续期
- 📧 邮件告警通知

---

**注意**: 请在生产环境中及时修改默认密码并配置相关安全参数。
