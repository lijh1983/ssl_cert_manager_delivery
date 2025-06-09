#!/bin/bash

# 阿里云镜像源配置脚本
# 为SSL证书管理器项目配置所有必要的阿里云镜像源

set -e

echo "=== 阿里云镜像源配置工具 ==="
echo "配置时间: $(date)"
echo "==============================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请使用root权限运行此脚本${NC}"
    echo "使用方法: sudo $0"
    exit 1
fi

echo -e "${BLUE}1. 配置系统软件源${NC}"

# 检测系统类型
if [ -f /etc/debian_version ]; then
    # Debian/Ubuntu系统
    DEBIAN_VERSION=$(cat /etc/debian_version | cut -d. -f1)
    if [ -f /etc/lsb-release ]; then
        # Ubuntu
        UBUNTU_CODENAME=$(lsb_release -cs)
        echo "检测到Ubuntu系统，代号: $UBUNTU_CODENAME"
        
        # 备份原始sources.list
        cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)
        
        # 配置Ubuntu阿里云镜像源
        cat > /etc/apt/sources.list <<EOF
# 阿里云Ubuntu镜像源
deb https://mirrors.aliyun.com/ubuntu/ $UBUNTU_CODENAME main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ $UBUNTU_CODENAME main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ $UBUNTU_CODENAME-security main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ $UBUNTU_CODENAME-security main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ $UBUNTU_CODENAME-updates main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ $UBUNTU_CODENAME-updates main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ $UBUNTU_CODENAME-backports main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ $UBUNTU_CODENAME-backports main restricted universe multiverse
EOF
        echo -e "${GREEN}✓${NC} 已配置Ubuntu阿里云镜像源"
        
    else
        # Debian
        DEBIAN_CODENAME=$(cat /etc/os-release | grep VERSION_CODENAME | cut -d= -f2)
        echo "检测到Debian系统，代号: $DEBIAN_CODENAME"
        
        # 备份原始sources.list
        cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)
        
        # 配置Debian阿里云镜像源
        cat > /etc/apt/sources.list <<EOF
# 阿里云Debian镜像源
deb https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME main non-free-firmware
deb-src https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME main non-free-firmware

deb https://mirrors.aliyun.com/debian-security/ $DEBIAN_CODENAME-security main non-free-firmware
deb-src https://mirrors.aliyun.com/debian-security/ $DEBIAN_CODENAME-security main non-free-firmware

deb https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME-updates main non-free-firmware
deb-src https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME-updates main non-free-firmware
EOF
        echo -e "${GREEN}✓${NC} 已配置Debian阿里云镜像源"
    fi
    
    # 更新软件包列表
    echo "更新软件包列表..."
    apt-get update
    echo -e "${GREEN}✓${NC} 软件包列表更新完成"
    
elif [ -f /etc/redhat-release ]; then
    # CentOS/RHEL系统
    echo "检测到CentOS/RHEL系统"
    
    # 备份原始repo文件
    mkdir -p /etc/yum.repos.d/backup
    cp /etc/yum.repos.d/*.repo /etc/yum.repos.d/backup/ 2>/dev/null || true
    
    # 配置CentOS阿里云镜像源
    curl -o /etc/yum.repos.d/CentOS-Base.repo https://mirrors.aliyun.com/repo/Centos-8.repo
    yum makecache
    echo -e "${GREEN}✓${NC} 已配置CentOS阿里云镜像源"
fi

echo -e "\n${BLUE}2. 更新Docker基础镜像配置${NC}"

# 更新后端基础镜像的Dockerfile
cat > backend/Dockerfile.base.aliyun <<'EOF'
# 后端基础镜像 - 阿里云优化版本
# 基于Python 3.10 Slim，使用阿里云镜像源

FROM python:3.10-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

# 配置阿里云Debian镜像源
RUN echo "=== 配置阿里云Debian镜像源 ===" && \
    # 备份原始sources.list
    cp /etc/apt/sources.list /etc/apt/sources.list.backup && \
    # 检测Debian版本
    DEBIAN_CODENAME=$(cat /etc/os-release | grep VERSION_CODENAME | cut -d= -f2 || echo "bookworm") && \
    echo "检测到Debian版本: $DEBIAN_CODENAME" && \
    # 配置阿里云镜像源
    cat > /etc/apt/sources.list <<SOURCES && \
# 阿里云Debian镜像源
deb https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME main non-free-firmware
deb-src https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME main non-free-firmware

deb https://mirrors.aliyun.com/debian-security/ $DEBIAN_CODENAME-security main non-free-firmware
deb-src https://mirrors.aliyun.com/debian-security/ $DEBIAN_CODENAME-security main non-free-firmware

deb https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME-updates main non-free-firmware
deb-src https://mirrors.aliyun.com/debian/ $DEBIAN_CODENAME-updates main non-free-firmware
SOURCES
    echo "阿里云Debian镜像源配置完成"

# 更新系统并安装必要的系统依赖
RUN echo "=== 更新系统包 ===" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        pkg-config \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        ca-certificates \
        && \
    echo "=== 系统包安装完成 ==="

# 配置阿里云pip镜像源
RUN echo "=== 配置pip镜像源 ===" && \
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com && \
    pip config set global.timeout 60 && \
    pip config list && \
    echo "=== pip镜像源配置完成 ==="

# 升级pip和安装基础工具
RUN echo "=== 升级pip ===" && \
    pip install --upgrade pip setuptools wheel && \
    pip --version && \
    echo "=== pip升级完成 ==="

# 复制依赖配置文件
COPY requirements.txt ./

# 安装Python依赖
RUN echo "=== 开始安装Python依赖 ===" && \
    pip install --no-cache-dir -r requirements.txt && \
    echo "=== Python依赖安装完成 ===" && \
    pip list

# 创建非root用户
RUN echo "=== 创建应用用户 ===" && \
    groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin -c "App User" appuser && \
    echo "=== 用户创建完成 ==="

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/data /app/certs && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# 清理系统缓存
RUN echo "=== 清理系统缓存 ===" && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    echo "=== 缓存清理完成 ==="

# 切换到非root用户
USER appuser

# 验证安装
RUN echo "=== 验证Python环境 ===" && \
    python --version && \
    pip --version && \
    python -c "import sys; print('Python path:', sys.path)" && \
    echo "=== 基础镜像构建完成 ==="

# 标签信息
LABEL maintainer="SSL Certificate Manager Team" \
      version="1.0.0" \
      description="Backend Base Image with Aliyun Mirrors" \
      stage="base" \
      component="backend" \
      mirrors="aliyun"

# 默认命令
CMD ["python", "--version"]
EOF

echo -e "${GREEN}✓${NC} 已创建阿里云优化的后端基础镜像"

# 更新前端基础镜像的Dockerfile
cat > frontend/Dockerfile.base.aliyun <<'EOF'
# 前端基础镜像 - 阿里云优化版本
# 基于Node.js 18 Alpine，使用阿里云镜像源

FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 配置阿里云Alpine镜像源
RUN echo "=== 配置阿里云Alpine镜像源 ===" && \
    # 备份原始配置
    cp /etc/apk/repositories /etc/apk/repositories.backup && \
    # 检测Alpine版本
    ALPINE_VERSION=$(cat /etc/alpine-release | cut -d. -f1,2) && \
    echo "检测到Alpine版本: $ALPINE_VERSION" && \
    # 配置阿里云镜像源
    cat > /etc/apk/repositories <<REPOS && \
https://mirrors.aliyun.com/alpine/v$ALPINE_VERSION/main
https://mirrors.aliyun.com/alpine/v$ALPINE_VERSION/community
REPOS
    echo "阿里云Alpine镜像源配置完成" && \
    # 更新包索引
    apk update && \
    echo "包索引更新完成"

# 配置阿里云npm镜像源和二进制文件镜像（使用环境变量方式）
ENV ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ \
    SASS_BINARY_SITE=https://npmmirror.com/mirrors/node-sass/ \
    PHANTOMJS_CDNURL=https://npmmirror.com/mirrors/phantomjs/ \
    CHROMEDRIVER_CDNURL=https://npmmirror.com/mirrors/chromedriver/ \
    OPERADRIVER_CDNURL=https://npmmirror.com/mirrors/operadriver/ \
    GECKODRIVER_CDNURL=https://npmmirror.com/mirrors/geckodriver/ \
    SELENIUM_CDNURL=https://npmmirror.com/mirrors/selenium/ \
    NODE_ENV=production

# 配置npm镜像源
RUN npm config set registry https://registry.npmmirror.com && \
    npm config set disturl https://npmmirror.com/mirrors/node && \
    npm config set electron_mirror https://npmmirror.com/mirrors/electron/ && \
    npm config set sass_binary_site https://npmmirror.com/mirrors/node-sass/ && \
    npm config set phantomjs_cdnurl https://npmmirror.com/mirrors/phantomjs/ && \
    npm config list

# 安装pnpm包管理器
RUN npm install -g pnpm && \
    pnpm --version

# 配置pnpm镜像源
RUN pnpm config set registry https://registry.npmmirror.com && \
    pnpm config list

# 复制依赖配置文件
COPY package.json package-lock.json* pnpm-lock.yaml* ./

# 安装依赖
RUN echo "=== 开始安装前端依赖 ===" && \
    pnpm install --no-frozen-lockfile && \
    echo "=== 前端依赖安装完成 ===" && \
    pnpm list --depth=0

# 清理缓存以减小镜像大小
RUN npm cache clean --force && \
    pnpm store prune && \
    rm -rf /tmp/* /var/tmp/* /root/.npm /root/.pnpm-store

# 创建非root用户
RUN addgroup -g 1001 -S nodeapp && \
    adduser -S -D -H -u 1001 -h /app -s /sbin/nologin -G nodeapp -g nodeapp nodeapp

# 设置目录权限
RUN chown -R nodeapp:nodeapp /app

# 切换到非root用户
USER nodeapp

# 验证安装
RUN echo "=== 验证依赖安装 ===" && \
    node --version && \
    npm --version && \
    pnpm --version && \
    echo "=== 基础镜像构建完成 ==="

# 标签信息
LABEL maintainer="SSL Certificate Manager Team" \
      version="1.0.0" \
      description="Frontend Base Image with Aliyun Mirrors" \
      stage="base" \
      component="frontend" \
      mirrors="aliyun"

# 默认命令
CMD ["node", "--version"]
EOF

echo -e "${GREEN}✓${NC} 已创建阿里云优化的前端基础镜像"

echo -e "\n${BLUE}3. 创建镜像源测试脚本${NC}"

# 创建镜像源测试脚本
cat > /usr/local/bin/test-aliyun-mirrors.sh <<'EOF'
#!/bin/bash
echo "=== 阿里云镜像源连接测试 ==="
echo "测试时间: $(date)"

# 测试项目
mirrors=(
    "Debian镜像源:curl -I --connect-timeout 5 https://mirrors.aliyun.com/debian/"
    "Python镜像源:curl -I --connect-timeout 5 https://mirrors.aliyun.com/pypi/simple/"
    "npm镜像源:curl -I --connect-timeout 5 https://registry.npmmirror.com/"
    "Alpine镜像源:curl -I --connect-timeout 5 https://mirrors.aliyun.com/alpine/"
    "Docker镜像源:curl -I --connect-timeout 5 https://registry.cn-hangzhou.aliyuncs.com/"
)

passed=0
total=${#mirrors[@]}

for mirror in "${mirrors[@]}"; do
    name=$(echo "$mirror" | cut -d: -f1)
    command=$(echo "$mirror" | cut -d: -f2-)
    
    echo -n "测试 $name ... "
    if eval "$command" >/dev/null 2>&1; then
        echo "通过"
        passed=$((passed + 1))
    else
        echo "失败"
    fi
done

echo "测试结果: $passed/$total 通过"
if [ $passed -eq $total ]; then
    echo "✓ 所有阿里云镜像源连接正常"
    exit 0
else
    echo "✗ 部分阿里云镜像源连接异常"
    exit 1
fi
EOF

chmod +x /usr/local/bin/test-aliyun-mirrors.sh
echo -e "${GREEN}✓${NC} 已创建镜像源测试脚本: /usr/local/bin/test-aliyun-mirrors.sh"

echo -e "\n==============================="
echo -e "${GREEN}🎉 阿里云镜像源配置完成！${NC}"

echo -e "\n${BLUE}配置内容汇总:${NC}"
echo "1. ✓ 配置系统软件源 (Debian/Ubuntu/CentOS)"
echo "2. ✓ 创建阿里云优化的后端基础镜像"
echo "3. ✓ 创建阿里云优化的前端基础镜像"
echo "4. ✓ 创建镜像源测试工具"

echo -e "\n${BLUE}下一步操作:${NC}"
echo "1. 测试镜像源: /usr/local/bin/test-aliyun-mirrors.sh"
echo "2. 构建阿里云优化镜像:"
echo "   docker build -t ssl-manager-backend-base:aliyun -f backend/Dockerfile.base.aliyun ./backend"
echo "   docker build -t ssl-manager-frontend-base:aliyun -f frontend/Dockerfile.base.aliyun ./frontend"
echo "3. 重新构建SSL证书管理器"

echo -e "\n${YELLOW}注意事项:${NC}"
echo "- 阿里云优化镜像使用.aliyun后缀"
echo "- 原始镜像配置已备份"
echo "- 建议在阿里云ECS环境中使用优化版本"
