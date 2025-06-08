# Nginx反向代理配置指南

本文档详细说明如何配置nginx反向代理，实现统一域名下访问所有服务。

## 🎯 配置目标

**配置前（不便利）：**
- 前端: http://ssl.gzyggl.com:80
- 后端API: http://ssl.gzyggl.com:8000  
- 监控面板: http://ssl.gzyggl.com:3000

**配置后（便利）：**
- 前端: http://ssl.gzyggl.com/ （主页面）
- 后端API: http://ssl.gzyggl.com/api/ （API接口）
- 监控面板: http://ssl.gzyggl.com/monitoring/ （监控界面）

## 🚀 快速配置

### 一键配置nginx反向代理

```bash
# 1. 停止现有服务
docker-compose -f docker-compose.aliyun.yml down

# 2. 配置nginx反向代理
chmod +x scripts/setup_nginx_proxy.sh
./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring

# 3. 验证配置
chmod +x scripts/verify_nginx_proxy.sh
./scripts/verify_nginx_proxy.sh
```

## 📋 详细配置步骤

### 步骤1：准备工作

```bash
# 确保在项目根目录
cd ssl_cert_manager_delivery

# 检查当前服务状态
docker-compose -f docker-compose.aliyun.yml ps

# 停止现有服务
docker-compose -f docker-compose.aliyun.yml down
```

### 步骤2：配置环境变量

```bash
# 编辑环境变量文件
nano .env

# 确保包含以下配置
DOMAIN_NAME=ssl.gzyggl.com
ENABLE_MONITORING=true
GRAFANA_USER=admin
GRAFANA_PASSWORD=your-secure-password
```

### 步骤3：构建nginx代理镜像

```bash
# 构建nginx反向代理镜像
docker build -f nginx/Dockerfile.proxy -t ssl-manager-nginx-proxy:latest ./nginx
```

### 步骤4：启动服务

```bash
# 启动所有服务（包含nginx反向代理）
docker-compose -f docker-compose.aliyun.yml up -d

# 检查服务状态
docker-compose -f docker-compose.aliyun.yml ps
```

### 步骤5：验证配置

```bash
# 运行验证脚本
./scripts/verify_nginx_proxy.sh

# 手动测试访问
curl http://localhost/                    # 前端
curl http://localhost/api/health          # API健康检查
curl http://localhost/monitoring/         # 监控面板
```

## 🔧 配置文件说明

### nginx反向代理配置

主要配置文件：`nginx/conf.d/ssl-manager.conf`

```nginx
# 前端主页
location / {
    proxy_pass http://frontend_servers;
    # ... 其他配置
}

# API接口
location /api/ {
    proxy_pass http://api_servers/;
    # ... 其他配置
}

# 监控面板
location /monitoring/ {
    proxy_pass http://monitoring_servers/;
    # ... 其他配置
}
```

### docker-compose配置变更

主要变更：
1. 移除了各服务的端口映射
2. 添加了nginx-proxy服务
3. 配置了Grafana子路径支持

```yaml
# 新增nginx反向代理服务
nginx-proxy:
  build:
    context: ./nginx
    dockerfile: Dockerfile.proxy
  ports:
    - "80:80"
    - "443:443"
  depends_on:
    - frontend
    - backend
    - grafana
```

## 🛠️ 管理命令

### 服务管理

```bash
# 查看服务状态
./scripts/restart_services.sh status

# 重启nginx代理
./scripts/restart_services.sh restart nginx

# 重启所有服务
./scripts/restart_services.sh restart all

# 优雅重启nginx（零停机）
./scripts/restart_services.sh graceful nginx

# 检查服务健康状态
./scripts/restart_services.sh health
```

### 日志查看

```bash
# 查看nginx日志
./scripts/restart_services.sh logs nginx

# 查看后端日志
./scripts/restart_services.sh logs backend

# 查看所有服务日志
./scripts/restart_services.sh logs all
```

### 配置验证

```bash
# 基础验证
./scripts/verify_nginx_proxy.sh

# 包含性能测试
./scripts/verify_nginx_proxy.sh --performance

# 生成详细报告
./scripts/verify_nginx_proxy.sh --report
```

## 🔍 故障排除

### 常见问题

#### 1. Docker镜像拉取失败 ⭐ **最常见问题**
```bash
# 错误信息: pull access denied, repository does not exist
# 原因: 阿里云镜像仓库路径不正确或网络问题

# 解决方案1: 使用快速修复脚本（推荐）
chmod +x scripts/fix_nginx_image_issue.sh
./scripts/fix_nginx_image_issue.sh

# 解决方案2: 测试并自动修复
chmod +x scripts/test_docker_images.sh
./scripts/test_docker_images.sh --auto-fix

# 解决方案3: 手动修复Dockerfile
# 将nginx/Dockerfile.proxy中的FROM行改为:
# FROM nginx:1.24-alpine  # 使用官方镜像
# 或
# FROM nginx:alpine       # 使用最新alpine版本
```

#### 2. 网络连接问题
```bash
# 检查Docker镜像源连通性
ping registry-1.docker.io
ping registry.cn-hangzhou.aliyuncs.com

# 配置Docker镜像加速器
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn"
    ]
}
EOF
sudo systemctl restart docker
```

#### 3. 端口冲突
```bash
# 检查端口占用
sudo ss -tlnp | grep -E ':(80|443)'

# 停止占用端口的服务
sudo systemctl stop httpd nginx apache2

# 重启nginx代理
./scripts/restart_services.sh restart nginx
```

#### 4. 服务无法访问
```bash
# 检查容器状态
docker-compose -f docker-compose.aliyun.yml ps

# 检查网络连接
docker network ls
docker network inspect ssl_cert_manager_delivery_ssl-manager-network

# 重启相关服务
./scripts/restart_services.sh restart all
```

#### 5. API跨域问题
```bash
# 检查nginx配置
docker-compose -f docker-compose.aliyun.yml exec nginx-proxy nginx -t

# 查看nginx错误日志
./scripts/restart_services.sh logs nginx | grep error

# 重新加载nginx配置
docker-compose -f docker-compose.aliyun.yml exec nginx-proxy nginx -s reload
```

#### 6. 监控面板无法访问
```bash
# 检查Grafana配置
docker-compose -f docker-compose.aliyun.yml logs grafana

# 检查Grafana环境变量
docker-compose -f docker-compose.aliyun.yml exec grafana env | grep GF_

# 重启Grafana服务
./scripts/restart_services.sh restart grafana
```

### Docker镜像问题专项解决方案

#### 问题诊断工具
```bash
# 1. 运行镜像拉取测试
./scripts/test_docker_images.sh

# 2. 查看详细的网络和镜像状态
./scripts/test_docker_images.sh --cleanup

# 3. 自动修复Dockerfile
./scripts/test_docker_images.sh --auto-fix
```

#### 手动修复步骤
```bash
# 步骤1: 备份原始文件
cp nginx/Dockerfile.proxy nginx/Dockerfile.proxy.backup

# 步骤2: 测试可用镜像
docker pull nginx:alpine
docker pull nginx:1.24-alpine

# 步骤3: 修改Dockerfile
sed -i 's|FROM.*nginx.*|FROM nginx:alpine|' nginx/Dockerfile.proxy

# 步骤4: 测试构建
docker build -f nginx/Dockerfile.proxy -t test-nginx ./nginx

# 步骤5: 清理测试镜像
docker rmi test-nginx
```

#### 镜像源优先级
```bash
# 推荐使用顺序（按可用性和速度排序）:
1. nginx:alpine                    # 官方最新alpine版本
2. nginx:1.24-alpine               # 官方指定版本
3. registry.cn-hangzhou.aliyuncs.com/acs/nginx:1.24-alpine  # 阿里云ACS
4. dockerproxy.com/library/nginx:alpine                     # Docker代理
5. docker.mirrors.ustc.edu.cn/library/nginx:alpine         # 中科大镜像
```

### 调试命令

```bash
# 进入nginx容器调试
docker-compose -f docker-compose.aliyun.yml exec nginx-proxy sh

# 测试nginx配置
docker-compose -f docker-compose.aliyun.yml exec nginx-proxy nginx -t

# 查看nginx进程
docker-compose -f docker-compose.aliyun.yml exec nginx-proxy ps aux

# 测试upstream连接
docker-compose -f docker-compose.aliyun.yml exec nginx-proxy wget -qO- http://ssl-manager-frontend:80/health
docker-compose -f docker-compose.aliyun.yml exec nginx-proxy wget -qO- http://ssl-manager-backend:8000/health
```

## 🔒 SSL/HTTPS配置

### 自动生成自签名证书

脚本会自动生成自签名证书用于测试：

```bash
# 证书位置
nginx/ssl/ssl.gzyggl.com.crt
nginx/ssl/ssl.gzyggl.com.key
```

### 使用Let's Encrypt证书

```bash
# 安装certbot
sudo dnf install -y certbot

# 申请证书
sudo certbot certonly --standalone -d ssl.gzyggl.com

# 复制证书到nginx目录
sudo cp /etc/letsencrypt/live/ssl.gzyggl.com/fullchain.pem nginx/ssl/ssl.gzyggl.com.crt
sudo cp /etc/letsencrypt/live/ssl.gzyggl.com/privkey.pem nginx/ssl/ssl.gzyggl.com.key

# 重启nginx
./scripts/restart_services.sh restart nginx
```

## 📊 性能优化

### nginx优化配置

已包含的优化：
- 启用gzip压缩
- 静态资源缓存
- 连接池优化
- 负载均衡配置

### 监控指标

```bash
# nginx状态监控
curl http://localhost/nginx_status

# 服务响应时间
./scripts/verify_nginx_proxy.sh --performance

# 系统资源监控
htop
iotop
```

## 🎯 验证清单

配置完成后，请验证以下功能：

- [ ] 前端主页正常访问：http://ssl.gzyggl.com/
- [ ] API接口正常工作：http://ssl.gzyggl.com/api/health
- [ ] 监控面板正常访问：http://ssl.gzyggl.com/monitoring/
- [ ] 前端能正常调用后端API（无跨域问题）
- [ ] 静态资源正常加载
- [ ] WebSocket连接正常（如果使用）
- [ ] SSL证书配置正确（如果启用HTTPS）
- [ ] 服务重启后配置保持有效

## 📞 获取支持

如果遇到问题，请：

1. 运行验证脚本：`./scripts/verify_nginx_proxy.sh --report`
2. 查看详细日志：`./scripts/restart_services.sh logs all`
3. 检查服务状态：`./scripts/restart_services.sh status`
4. 提供错误信息和系统环境信息

通过nginx反向代理配置，您现在可以通过统一的域名访问所有服务，提供更好的用户体验！
