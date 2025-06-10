# 生产环境部署脚本使用示例

本文档提供SSL证书管理器生产环境部署脚本的详细使用示例和最佳实践。

## 📋 脚本功能概览

优化后的部署脚本 `./scripts/deploy-production.sh` 提供以下功能：

- **配置文件保护**: 避免覆盖用户自定义配置
- **模块化部署**: 支持分步骤执行部署流程
- **环境差异处理**: 智能检测和适配不同系统环境
- **交互式部署**: 用户友好的确认和选择机制
- **智能验证**: 完整的部署后验证和报告

## 🚀 基本使用示例

### 1. 查看帮助信息

```bash
./scripts/deploy-production.sh --help
```

### 2. 标准部署（推荐）

```bash
# 一键完整部署
./scripts/deploy-production.sh
```

### 3. 交互式部署

```bash
# 用户确认每个关键步骤
./scripts/deploy-production.sh --interactive
```

## 🔧 高级使用场景

### 场景1: 首次部署

```bash
# 完整的首次部署，包含所有检查和配置
./scripts/deploy-production.sh --interactive

# 预期流程:
# 1. 系统要求检查
# 2. 环境差异检测
# 3. Docker安装和配置
# 4. 数据目录创建
# 5. 环境变量配置
# 6. 镜像构建和拉取
# 7. 服务启动
# 8. 部署验证
```

### 场景2: 更新部署（保留现有配置）

```bash
# 跳过环境配置，保留现有设置
./scripts/deploy-production.sh --skip-env-setup

# 或者使用交互式模式选择保留配置
./scripts/deploy-production.sh --interactive
# 选择: 1) 保留现有配置
```

### 场景3: 仅构建镜像

```bash
# 只构建和拉取镜像，不启动服务
./scripts/deploy-production.sh --only-build

# 适用场景:
# - 预先准备镜像
# - 验证镜像构建
# - 网络较慢时分步执行
```

### 场景4: 快速重新部署

```bash
# 跳过镜像构建，使用现有镜像
./scripts/deploy-production.sh --skip-build --skip-env-setup

# 适用场景:
# - 配置文件修改后重新部署
# - 服务重启
# - 快速恢复
```

### 场景5: 强制覆盖配置

```bash
# 强制覆盖所有现有配置
./scripts/deploy-production.sh --force-overwrite

# 注意: 会备份现有配置到 .env.backup.TIMESTAMP
```

### 场景6: 最小化部署

```bash
# 跳过所有可选步骤，最小化部署
./scripts/deploy-production.sh --skip-system-check --skip-docker-config --skip-env-setup

# 适用场景:
# - 已知环境正确
# - 快速部署
# - 自动化脚本
```

## 🛠️ 故障排除场景

### 场景1: Docker配置问题

```bash
# 跳过Docker配置修改，使用现有配置
./scripts/deploy-production.sh --skip-docker-config

# 如果Docker配置有问题，手动恢复:
sudo cp /etc/docker/daemon.json.backup.TIMESTAMP /etc/docker/daemon.json
sudo systemctl restart docker
```

### 场景2: 环境变量配置错误

```bash
# 重新生成环境配置
./scripts/deploy-production.sh --force-overwrite --skip-build

# 或者手动编辑后重新部署
nano .env
./scripts/deploy-production.sh --skip-env-setup
```

### 场景3: 镜像拉取失败

```bash
# 跳过镜像拉取，使用本地镜像
./scripts/deploy-production.sh --skip-build

# 或者仅重新拉取镜像
./scripts/deploy-production.sh --only-build
```

### 场景4: 服务启动失败

```bash
# 查看详细日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs

# 重新部署特定服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d [service_name]

# 完全重新部署
./scripts/deploy-production.sh --skip-env-setup --skip-docker-config
```

## 📊 配置管理最佳实践

### 1. 配置文件保护

```bash
# 首次部署
./scripts/deploy-production.sh --interactive

# 更新时保留配置
./scripts/deploy-production.sh --skip-env-setup

# 需要更新配置时
./scripts/deploy-production.sh --interactive
# 选择: 3) 合并配置
```

### 2. 环境变量管理

```bash
# 查看当前配置
cat .env

# 备份重要配置
cp .env .env.manual.backup

# 合并新功能配置
./scripts/deploy-production.sh --interactive
# 选择: 3) 合并配置
```

### 3. Docker配置管理

```bash
# 查看当前Docker配置
sudo cat /etc/docker/daemon.json

# 保留现有Docker配置
./scripts/deploy-production.sh --skip-docker-config

# 应用推荐配置（会备份现有配置）
./scripts/deploy-production.sh --interactive
# 选择: 2) 备份并应用推荐配置
```

## 🔍 验证和监控

### 部署后验证

```bash
# 脚本会自动执行验证，也可以手动验证:

# 检查服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production ps

# 验证核心功能
curl http://localhost/health
curl http://localhost/api/health
curl -I http://localhost/

# 检查SSL证书管理功能
curl http://localhost/api/certificates/status  # SSL证书状态
curl http://localhost/api/certificates/expiry  # 证书到期情况
docker stats --no-stream                       # 容器资源监控
```

### 查看验证报告

```bash
# 脚本会生成验证报告
cat /tmp/ssl_manager_verification_report.txt

# 查看环境报告
cat /tmp/ssl_manager_env_report.txt
```

## 📝 参数组合建议

### 开发环境测试

```bash
./scripts/deploy-production.sh --interactive --skip-system-check
```

### 生产环境首次部署

```bash
./scripts/deploy-production.sh --interactive
```

### 生产环境更新

```bash
./scripts/deploy-production.sh --skip-env-setup
```

### CI/CD自动化部署

```bash
./scripts/deploy-production.sh --skip-system-check --force-overwrite
```

### 故障恢复

```bash
./scripts/deploy-production.sh --skip-build --skip-env-setup --skip-docker-config
```

## ⚠️ 注意事项

1. **备份重要性**: 脚本会自动备份配置文件，但建议手动备份重要数据
2. **权限要求**: 脚本需要sudo权限来配置Docker和创建系统目录
3. **网络要求**: 镜像拉取需要稳定的网络连接
4. **资源要求**: 确保系统满足最低资源要求（8GB内存，4核CPU）
5. **cgroup v2**: 建议支持cgroup v2以获得更好的系统监控兼容性

## 🆘 获取帮助

如果遇到问题：

1. 查看脚本帮助: `./scripts/deploy-production.sh --help`
2. 查看验证报告: `/tmp/ssl_manager_verification_report.txt`
3. 查看环境报告: `/tmp/ssl_manager_env_report.txt`
4. 查看服务日志: `docker-compose logs [service_name]`
5. 参考文档: `DEPLOYMENT.md`, `QUICKSTART.md`
