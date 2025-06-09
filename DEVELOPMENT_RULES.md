# SSL证书管理器开发和维护规则

本文档定义了SSL证书管理器项目的开发和维护标准，确保项目始终保持干净、有序和专业的状态。

## 📁 1. 文件管理规则

### 1.1 保留文件标准

#### ✅ 必须保留的文件类型
- **核心脚本**: `deploy.sh`, `scripts/ssl-manager.sh`, `client/client.sh`
- **主要文档**: `README.md`, `DEPLOYMENT.md`, `update.log`
- **配置文件**: `docker-compose.aliyun.yml`, `Dockerfile*`, `.env.example`
- **源代码**: `backend/src/`, `frontend/src/`
- **测试文件**: `tests/` 目录下的所有文件
- **依赖配置**: `requirements.txt`, `package.json`

#### ❌ 禁止保留的文件类型
- **临时脚本**: `fix-*.sh`, `test-*.sh`, `diagnose-*.sh`, `temp_*.sh`
- **报告文档**: `*_REPORT.md`, `*_FIX*.md`, `*_VALIDATION*.md`
- **备份文件**: `*.backup`, `*.bak`, `*.old`, `*.tmp`
- **构建产物**: `dist/`, `build/`, `node_modules/` (应在.gitignore中)
- **多版本文件**: `README_v2.md`, `docker-compose.yml.new`

### 1.2 命名约定

#### 临时文件命名规则
```bash
# 开发期间的临时文件（仅本地使用）
temp_YYYYMMDD_功能描述.sh
temp_YYYYMMDD_文档类型.md

# 示例
temp_20250109_database_fix.sh
temp_20250109_deployment_notes.md
```

#### 永久文件命名规则
- **脚本文件**: kebab-case，如 `ssl-manager.sh`
- **文档文件**: UPPERCASE，如 `README.md`, `DEPLOYMENT.md`
- **配置文件**: 保持原始格式，如 `docker-compose.aliyun.yml`

### 1.3 文件生命周期管理

#### 开发阶段
```bash
# 允许临时文件存在于本地开发环境
temp_* 文件可以存在，但不能提交到Git

# 提交前必须检查
find . -name "temp_*" -o -name "fix-*" -o -name "*_REPORT.md"
```

#### 提交前清理
```bash
# 自动清理命令
./scripts/ssl-manager.sh cleanup --dry-run  # 预览
./scripts/ssl-manager.sh cleanup            # 执行清理
```

#### 定期维护
```bash
# 每周执行
./scripts/ssl-manager.sh cleanup
```

## 📝 2. 更新和维护工作流

### 2.1 统一更新日志 (update.log)

#### 标准格式
```
### [YYYY-MM-DD HH:MM] [类型] 更新描述
影响范围: 具体影响的组件或功能
变更详情: 详细的变更内容
测试状态: 测试结果和验证情况
---
```

#### 更新类型分类
- `[FEATURE]` - 新功能添加
- `[BUGFIX]` - 错误修复
- `[CLEANUP]` - 代码清理
- `[DOCKER]` - Docker相关更改
- `[DATABASE]` - 数据库相关更改
- `[SECURITY]` - 安全相关更改
- `[DOCS]` - 文档更新

#### 更新日志维护
```bash
# 使用ssl-manager.sh添加记录
./scripts/ssl-manager.sh update-log

# 或手动添加
./scripts/ssl-manager.sh update-log \
  --type FEATURE \
  --desc "添加SSL证书自动续期功能" \
  --impact "证书管理模块" \
  --details "实现了基于cron的自动续期机制" \
  --test "✅ 功能测试通过"
```

### 2.2 更新日志维护规则

#### 必须记录的更改
- 新功能添加或重要功能修改
- 配置文件的重要更改
- 数据库结构变更
- 安全相关更新
- 部署流程变更

#### 不需要记录的更改
- 小的文档修正
- 代码注释更新
- 格式化调整
- 临时文件清理

## 🔧 3. 脚本管理规则

### 3.1 核心脚本维护

#### 主要管理脚本
- `scripts/ssl-manager.sh` - 唯一的核心管理脚本
- 包含所有系统管理功能
- 禁止创建新的独立管理脚本

#### 功能模块结构
```bash
./scripts/ssl-manager.sh <command> [options]

# 核心命令
deploy      # 部署功能
verify      # 验证功能
fix         # 修复功能
status      # 状态查看
logs        # 日志查看
restart     # 重启服务
stop        # 停止服务
cleanup     # 清理系统
update-log  # 更新日志
```

### 3.2 脚本添加规则

#### ✅ 正确做法：集成到ssl-manager.sh
```bash
# 在ssl-manager.sh中添加新功能
case "$command" in
    new-feature)
        new_feature_function "$@"
        ;;
esac
```

#### ❌ 错误做法：创建独立脚本
```bash
# 禁止创建
scripts/new-feature.sh
scripts/fix-something.sh
scripts/diagnose-issue.sh
```

#### 脚本文档要求
- 每个新功能必须在 `show_help()` 函数中添加说明
- 必须包含使用示例
- 必须包含参数说明

### 3.3 允许的辅助脚本
- `deploy.sh` - 一键部署脚本（用户入口）
- `client/client.sh` - 客户端安装脚本
- `scripts/cleanup-repo.sh` - 独立清理脚本（可选）

## 📖 4. 文档维护规则

### 4.1 核心文档管理

#### 主要文档文件
- `README.md` - 项目概述和快速开始
- `DEPLOYMENT.md` - 详细部署指南
- `update.log` - 更新日志
- `DEVELOPMENT_RULES.md` - 开发规则（本文档）

#### 文档更新原则
```bash
# ✅ 正确做法：直接更新现有文档
vim README.md
git add README.md
git commit -m "docs: 更新README部署说明"

# ❌ 错误做法：创建新版本文档
# 禁止：README_v2.md, README_NEW.md, DEPLOYMENT_UPDATED.md
```

### 4.2 文档版本控制

#### 变更追踪
- 重要文档更改必须在 `update.log` 中记录
- 使用Git提交信息追踪小的文档更改
- 保持文档简洁，避免冗余信息

#### 文档质量标准
- 清晰的目录结构
- 标准的Markdown格式
- 实际可执行的命令示例
- 避免过时信息和无效链接

### 4.3 文档内容规范

#### README.md结构
```markdown
# 项目标题
## 🚀 快速部署
## 📋 系统要求
## 🌐 访问地址
## 🔑 默认账户
## 🛠️ 管理命令
## 📊 功能特性
## 🔧 故障排除
```

#### DEPLOYMENT.md结构
```markdown
# 部署指南
## 📋 部署前准备
## 🚀 部署方法
## ✅ 部署验证
## 🔧 服务管理
## 🔍 故障排除
```

## ⚙️ 5. 配置文件管理规则

### 5.1 主要配置文件
- `docker-compose.aliyun.yml` - 主要部署配置
- `backend/Dockerfile`, `backend/Dockerfile.base`
- `frontend/Dockerfile`, `frontend/Dockerfile.base`
- `.env.example` - 环境变量模板

### 5.2 配置更新流程
```bash
# 1. 备份当前配置（本地，不提交）
cp docker-compose.aliyun.yml docker-compose.aliyun.yml.backup

# 2. 进行配置更改
vim docker-compose.aliyun.yml

# 3. 本地测试验证
docker-compose -f docker-compose.aliyun.yml config

# 4. 功能测试
docker-compose -f docker-compose.aliyun.yml up -d
# 验证服务正常运行

# 5. 提交更改
git add docker-compose.aliyun.yml
git commit -m "config: 更新Docker Compose配置"

# 6. 记录到update.log（重要更改）
./scripts/ssl-manager.sh update-log --type DOCKER --desc "更新Docker Compose配置"
```

### 5.3 配置测试清单
```bash
# 1. 语法验证
docker-compose -f docker-compose.aliyun.yml config

# 2. 构建测试
docker-compose -f docker-compose.aliyun.yml build

# 3. 启动测试
docker-compose -f docker-compose.aliyun.yml up -d

# 4. 健康检查
docker-compose -f docker-compose.aliyun.yml ps
curl http://localhost/health

# 5. 清理测试环境
docker-compose -f docker-compose.aliyun.yml down
```

## 🧹 6. 仓库卫生规则

### 6.1 自动清理程序

#### 使用ssl-manager.sh清理
```bash
# 预览清理内容
./scripts/ssl-manager.sh cleanup --dry-run

# 执行清理
./scripts/ssl-manager.sh cleanup
```

#### 清理内容
- 临时脚本：`temp_*.sh`, `fix-*.sh`, `test-*.sh`, `diagnose-*.sh`
- 临时文档：`*_REPORT.md`, `*_FIX*.md`, `*_VALIDATION*.md`
- 备份文件：`*.backup`, `*.bak`, `*.old`, `*.tmp`
- 空目录
- Docker系统清理

### 6.2 提交前检查清单
```bash
# 1. 运行仓库清理
./scripts/ssl-manager.sh cleanup

# 2. 检查文件状态
git status

# 3. 验证没有临时文件
git ls-files --others --exclude-standard | grep -E "(temp_|fix-|test-|_REPORT)"

# 4. 更新update.log（如果是重要更改）
./scripts/ssl-manager.sh update-log

# 5. 提交更改
git add .
git commit -m "类型: 简洁的提交描述"
```

### 6.3 提交信息规范
```bash
# 提交类型前缀
feat:     新功能
fix:      错误修复
docs:     文档更新
style:    代码格式调整
refactor: 代码重构
test:     测试相关
chore:    构建或辅助工具更改
cleanup:  代码清理

# 示例
git commit -m "feat: 添加SSL证书自动续期功能"
git commit -m "fix: 修复PostgreSQL连接超时问题"
git commit -m "docs: 更新部署指南中的环境要求"
git commit -m "cleanup: 删除临时测试脚本"
```

### 6.4 定期维护计划

#### 每日维护（开发期间）
```bash
# 检查临时文件
find . -name "temp_*" -o -name "fix-*" -o -name "*_REPORT.md"

# 及时清理
./scripts/ssl-manager.sh cleanup
```

#### 每周维护
```bash
# 1. 完整仓库清理
./scripts/ssl-manager.sh cleanup

# 2. 检查update.log
# 如果超过100行，考虑归档旧记录

# 3. 验证核心功能
./scripts/ssl-manager.sh verify --all

# 4. 更新文档（如有需要）
```

#### 每月维护
```bash
# 1. 依赖更新检查
# 检查requirements.txt和package.json

# 2. 安全更新
# 检查Docker基础镜像更新

# 3. 性能优化
# 检查Docker镜像大小

# 4. 文档审查
# 全面审查文档准确性
```

## 🎯 7. 执行和监督

### 7.1 规则执行
- 所有开发人员必须遵守这些规则
- 代码审查时检查规则遵守情况
- 定期审查和更新规则

### 7.2 违规处理
- 发现违规文件时立即清理
- 在代码审查中指出违规行为
- 持续教育和提醒

### 7.3 规则更新
- 根据项目发展需要更新规则
- 重要规则变更需要在update.log中记录
- 确保所有团队成员了解规则变更

## 📞 支持和反馈

如果对这些规则有疑问或建议，请：
1. 在项目中创建Issue讨论
2. 联系项目维护者
3. 在团队会议中提出

遵守这些规则将确保SSL证书管理器项目始终保持专业、干净和易于维护的状态。
