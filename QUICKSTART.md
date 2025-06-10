# SSL证书管理器快速开始指南

本指南提供SSL证书管理器的快速部署方法，适用于生产环境。

## 🚀 一键部署（推荐）

### 前提条件
- Ubuntu 22.04.5 LTS
- 16GB+ 内存，4+ CPU核心
- 40GB+ 磁盘空间
- 支持cgroup v2

### 快速部署命令

```bash
# 1. 克隆项目
git clone https://github.com/lijh1983/ssl_cert_manager_delivery.git
cd ssl_cert_manager_delivery

# 2. 执行一键部署
./scripts/deploy-production.sh

# 3. 等待部署完成（约5-10分钟）
```

### 验证部署

```bash
# 检查服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production ps

# 验证核心功能
curl http://localhost/health          # Nginx健康检查
curl http://localhost/api/health      # API健康检查
curl -I http://localhost/             # 前端页面
```

## 📋 服务访问

部署成功后，可以通过以下地址访问各项服务：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | http://localhost/ | SSL证书管理界面 |
| API接口 | http://localhost/api/ | REST API接口 |
| API文档 | http://localhost/api/docs | Swagger API文档 |

**注**: 系统监控功能已移除，专注SSL证书管理核心业务功能

### SSL证书管理功能

**核心功能特性:**
- ✓ 主机域名监控：监控证书绑定的域名状态
- ✓ 证书等级检查：DV、OV、EV证书类型识别
- ✓ 加密方式验证：RSA、ECC等加密算法检查
- ✓ 端口监控：443、80等端口的证书状态
- ✓ 证书状态跟踪：有效、过期、即将过期状态
- ✓ 有效期管理：剩余天数计算和到期提醒

## 🔧 常用管理命令

### 服务管理

```bash
# 查看服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production ps

# 查看服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production logs -f

# 重启特定服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart backend

# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production down

# 重新启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d
```

### 数据管理

```bash
# 备份数据库
docker exec ssl-manager-postgres pg_dump -U ssl_user ssl_manager > backup_$(date +%Y%m%d_%H%M%S).sql

# 查看数据库表
docker exec ssl-manager-postgres psql -U ssl_user -d ssl_manager -c "\dt"

# 检查Redis状态
docker exec ssl-manager-redis redis-cli ping
```

### SSL证书监控检查

```bash
# 检查SSL证书管理API
curl -f http://localhost/api/certificates/status

# 检查证书到期情况
curl -f http://localhost/api/certificates/expiry

# 检查容器资源使用
docker stats --no-stream

# 检查系统资源
free -h && df -h
```

## ⚠️ 故障排除

### 常见问题快速解决

**1. 服务启动失败**
```bash
# 检查Docker状态
sudo systemctl status docker

# 查看详细错误日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs [service_name]

# 重新创建服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d --force-recreate
```

**2. SSL证书监控问题**
```bash
# 系统监控已移除，使用SSL证书管理内置功能:

# 查看SSL证书状态
curl http://localhost/api/certificates/status

# 查看证书到期情况
curl http://localhost/api/certificates/expiry

# 查看容器状态和日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs

# 查看容器资源使用情况
docker stats --no-stream
```

**3. 数据库连接失败**
```bash
# 检查数据库容器状态
docker ps | grep postgres

# 重新初始化数据库
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
docker volume rm workspace_postgres_data
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres
```

**4. 端口占用冲突**
```bash
# 检查端口占用
netstat -tlnp | grep :80

# 停止占用端口的服务
sudo systemctl stop apache2  # 如果是Apache
sudo systemctl stop nginx    # 如果是系统nginx
```

**5. 镜像拉取失败**
```bash
# 检查网络连接
ping docker.io

# 配置镜像加速器
sudo mkdir -p /etc/docker
cat > /tmp/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
sudo mv /tmp/daemon.json /etc/docker/daemon.json
sudo systemctl restart docker
```

## 📞 获取帮助

如果遇到问题，请按以下顺序检查：

1. **查看日志**: `docker-compose logs [service_name]`
2. **检查系统要求**: 确保满足最低配置要求
3. **验证网络**: 确保可以访问Docker Hub和相关镜像仓库
4. **查看文档**: 参考 `DEPLOYMENT.md` 获取详细部署指南
5. **检查更新日志**: 查看 `update.log` 了解已知问题和解决方案

## 🔄 更新和维护

### 更新系统

```bash
# 拉取最新代码
git pull origin main

# 重新构建和部署
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production down
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d --build
```

### 定期维护

```bash
# 清理未使用的Docker资源
docker system prune -f

# 备份重要数据
./scripts/backup.sh  # 如果存在备份脚本

# 检查系统资源使用
df -h && free -h
```

---

**🎉 恭喜！您已成功部署SSL证书管理器！**

如需更详细的配置和故障排除信息，请参考 [DEPLOYMENT.md](DEPLOYMENT.md) 文档。
