# 阿里云ECS Docker网络连接问题完整解决方案

## 🚨 问题描述

在阿里云ECS环境中，Docker容器构建时遇到"Unable to connect to deb.debian.org:http"网络连接错误，导致无法正常安装系统包和依赖。

## 🔍 问题诊断步骤

### 1. 网络连通性检查

**执行诊断脚本**:
```bash
# 给脚本执行权限
chmod +x scripts/diagnose-network-issues.sh

# 运行网络诊断
sudo ./scripts/diagnose-network-issues.sh
```

**检查项目**:
- ✅ ECS公网IP和内网IP配置
- ✅ VPC和子网配置
- ✅ 安全组规则（出站HTTP/HTTPS）
- ✅ 默认网关和路由表

### 2. DNS解析测试

**手动测试命令**:
```bash
# 测试DNS解析
nslookup deb.debian.org
nslookup mirrors.aliyun.com
nslookup registry.npmmirror.com

# 测试阿里云DNS
nslookup deb.debian.org 223.5.5.5
```

### 3. 防火墙和网络策略检查

**检查命令**:
```bash
# 检查iptables规则
sudo iptables -L -n

# 检查系统防火墙
sudo ufw status  # Ubuntu
sudo firewall-cmd --state  # CentOS

# 检查Docker网络
docker network ls
docker network inspect bridge
```

### 4. Docker网络模式验证

**测试容器网络**:
```bash
# 测试容器网络连接
docker run --rm alpine:latest sh -c "
    echo 'DNS配置:' && cat /etc/resolv.conf
    echo 'DNS解析测试:' && nslookup deb.debian.org
    echo 'HTTP连接测试:' && wget -T 10 -O /dev/null http://deb.debian.org
"
```

## 🛠️ 解决方案实施

### 方案1: 自动修复脚本（推荐）

```bash
# 给脚本执行权限
chmod +x scripts/fix-network-issues.sh
chmod +x scripts/configure-aliyun-mirrors.sh

# 运行网络修复
sudo ./scripts/fix-network-issues.sh

# 配置阿里云镜像源
sudo ./scripts/configure-aliyun-mirrors.sh
```

### 方案2: 手动配置步骤

#### 步骤1: 配置系统DNS
```bash
# 备份原始DNS配置
sudo cp /etc/resolv.conf /etc/resolv.conf.backup

# 配置阿里云DNS
sudo tee /etc/resolv.conf > /dev/null <<EOF
nameserver 223.5.5.5
nameserver 223.6.6.6
nameserver 8.8.8.8
options timeout:2 attempts:3 rotate
EOF
```

#### 步骤2: 配置Docker daemon
```bash
# 创建Docker配置目录
sudo mkdir -p /etc/docker

# 配置Docker daemon
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://docker.mirrors.ustc.edu.cn"
  ],
  "dns": ["223.5.5.5", "223.6.6.6", "8.8.8.8"],
  "dns-opts": ["timeout:2", "attempts:3"],
  "max-concurrent-downloads": 10,
  "live-restore": true
}
EOF

# 重启Docker服务
sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 步骤3: 配置系统软件源

**Debian/Ubuntu系统**:
```bash
# 备份原始sources.list
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup

# 配置阿里云镜像源（以Ubuntu 20.04为例）
sudo tee /etc/apt/sources.list > /dev/null <<EOF
deb https://mirrors.aliyun.com/ubuntu/ focal main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ focal-security main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ focal-updates main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ focal-backports main restricted universe multiverse
EOF

# 更新软件包列表
sudo apt-get update
```

## 📋 Dockerfile示例

### 后端基础镜像（阿里云优化版）

```dockerfile
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 配置阿里云Debian镜像源
RUN cp /etc/apt/sources.list /etc/apt/sources.list.backup && \
    DEBIAN_CODENAME=$(cat /etc/os-release | grep VERSION_CODENAME | cut -d= -f2 || echo "bookworm") && \
    cat > /etc/apt/sources.list <<SOURCES && \
deb https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME main non-free-firmware
deb https://mirrors.aliyun.com/debian-security/ $DEBIAN_CODENAME-security main non-free-firmware
deb https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME-updates main non-free-firmware
SOURCES
    apt-get update

# 安装系统依赖
RUN apt-get install -y --no-install-recommends \
        build-essential curl git pkg-config \
        libssl-dev libffi-dev libpq-dev ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 配置pip镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com && \
    pip install --upgrade pip setuptools wheel

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 创建用户和目录
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /app/logs /app/data /app/certs && \
    chown -R appuser:appuser /app

USER appuser
CMD ["python", "--version"]
```

### 前端基础镜像（阿里云优化版）

```dockerfile
FROM node:18-alpine

WORKDIR /app

# 配置阿里云Alpine镜像源
RUN cp /etc/apk/repositories /etc/apk/repositories.backup && \
    ALPINE_VERSION=$(cat /etc/alpine-release | cut -d. -f1,2) && \
    cat > /etc/apk/repositories <<REPOS && \
https://mirrors.aliyun.com/alpine/v$ALPINE_VERSION/main
https://mirrors.aliyun.com/alpine/v$ALPINE_VERSION/community
REPOS
    apk update

# 配置npm镜像源
ENV ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ \
    NODE_ENV=production

RUN npm config set registry https://registry.npmmirror.com && \
    npm config set disturl https://npmmirror.com/mirrors/node && \
    npm install -g pnpm && \
    pnpm config set registry https://registry.npmmirror.com

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --no-frozen-lockfile && \
    npm cache clean --force && pnpm store prune

RUN addgroup -g 1001 -S nodeapp && \
    adduser -S -D -H -u 1001 -h /app -G nodeapp nodeapp && \
    chown -R nodeapp:nodeapp /app

USER nodeapp
CMD ["node", "--version"]
```

## ✅ 验证和测试

### 测试命令

```bash
# 测试网络连接
/usr/local/bin/test-docker-network.sh

# 测试阿里云镜像源
/usr/local/bin/test-aliyun-mirrors.sh

# 测试基础镜像构建
docker build -t test-backend-base -f backend/Dockerfile.base ./backend
docker build -t test-frontend-base -f frontend/Dockerfile.base ./frontend

# 测试容器网络
docker run --rm test-backend-base python -c "import requests; print('网络正常')"
docker run --rm test-frontend-base node -e "console.log('网络正常')"
```

### 预期输出

```
=== Docker网络连接测试 ===
测试 DNS解析 ... 通过
测试 HTTP连接 ... 通过
测试 HTTPS连接 ... 通过
测试 Docker网络 ... 通过
测试结果: 4/4 通过
✓ 网络连接正常
```

## 🎯 阿里云ECS最佳实践

### 1. 安全组配置
- **出站规则**: 允许HTTP(80)、HTTPS(443)、DNS(53)
- **入站规则**: 根据应用需求开放端口
- **协议**: TCP和UDP都要配置

### 2. VPC网络配置
- 确保子网有公网访问能力
- 配置NAT网关（如果使用私有子网）
- 检查路由表配置

### 3. DNS配置优化
- 优先使用阿里云DNS: 223.5.5.5, 223.6.6.6
- 备用公共DNS: 8.8.8.8, 8.8.4.4
- 配置DNS超时和重试参数

### 4. 镜像源选择策略
- **系统包**: 优先阿里云镜像源
- **Python包**: 阿里云PyPI镜像
- **npm包**: npmmirror.com镜像
- **Docker镜像**: 阿里云容器镜像服务

## 🚨 常见错误排查

### 错误1: "Unable to connect to deb.debian.org:http"
**原因**: Debian官方源网络不通
**解决**: 使用阿里云Debian镜像源

### 错误2: "Temporary failure resolving 'xxx'"
**原因**: DNS解析失败
**解决**: 配置阿里云DNS服务器

### 错误3: "Connection timed out"
**原因**: 网络连接超时
**解决**: 检查安全组和防火墙配置

### 错误4: "Package 'xxx' has no installation candidate"
**原因**: 软件源配置错误
**解决**: 更新sources.list并执行apt-get update

## 📞 技术支持

如果问题持续存在，请：

1. **收集诊断信息**:
   ```bash
   ./scripts/diagnose-network-issues.sh > network-diagnosis.log 2>&1
   ```

2. **联系阿里云技术支持**:
   - 提供ECS实例ID
   - 提供网络诊断日志
   - 描述具体错误信息

3. **社区支持**:
   - 阿里云开发者社区
   - Docker官方文档
   - GitHub Issues

## 🎉 成功标志

当看到以下输出时，表示问题已解决：

```
🎉 网络问题修复完成！
✓ 所有阿里云镜像源连接正常
✓ Docker容器网络正常
✓ SSL证书管理器可以正常构建和部署
```
