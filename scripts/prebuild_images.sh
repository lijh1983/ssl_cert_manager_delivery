#!/bin/bash
# 预构建镜像脚本 - 减少部署时间

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置阿里云容器镜像服务
setup_acr() {
    log_info "配置阿里云容器镜像服务..."
    
    # 检查是否已登录ACR
    if ! docker info | grep -q "registry.cn-hangzhou.aliyuncs.com"; then
        log_warning "请先登录阿里云容器镜像服务:"
        echo "docker login --username=your-username registry.cn-hangzhou.aliyuncs.com"
        echo "如果没有ACR账号，可以跳过此步骤使用本地构建"
        read -p "是否已登录ACR? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "跳过ACR配置，使用本地构建"
            USE_ACR=false
        else
            USE_ACR=true
        fi
    else
        USE_ACR=true
    fi
}

# 构建基础镜像
build_base_images() {
    log_info "构建基础镜像..."
    
    # 前端基础镜像
    log_info "构建前端基础镜像..."
    cat > frontend/Dockerfile.base <<EOF
FROM registry.cn-hangzhou.aliyuncs.com/library/node:18-alpine

# 配置阿里云npm镜像源
RUN npm config set registry https://registry.npmmirror.com \\
    && npm config set disturl https://npmmirror.com/dist \\
    && npm install -g pnpm

# 设置工作目录
WORKDIR /app

# 预安装常用依赖
RUN pnpm config set registry https://registry.npmmirror.com

LABEL description="SSL Manager Frontend Base Image"
EOF
    
    docker build -f frontend/Dockerfile.base -t ssl-manager-frontend-base:latest ./frontend
    
    # 后端基础镜像
    log_info "构建后端基础镜像..."
    cat > backend/Dockerfile.base <<EOF
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.10-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1 \\
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \\
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 配置阿里云软件源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \\
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    curl gcc g++ make libffi-dev libssl-dev libpq-dev netcat-traditional \\
    && rm -rf /var/lib/apt/lists/* \\
    && apt-get clean

# 升级pip
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 预安装常用Python包
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \\
    flask gunicorn sqlalchemy psycopg2-binary redis celery

LABEL description="SSL Manager Backend Base Image"
EOF
    
    docker build -f backend/Dockerfile.base -t ssl-manager-backend-base:latest ./backend
    
    log_success "基础镜像构建完成"
}

# 构建应用镜像
build_app_images() {
    log_info "构建应用镜像..."
    
    # 使用基础镜像构建前端
    log_info "构建前端应用镜像..."
    cat > frontend/Dockerfile.fast <<EOF
# 使用预构建的基础镜像
FROM ssl-manager-frontend-base:latest AS builder

# 复制package文件
COPY package*.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install --frozen-lockfile --prefer-offline

# 复制源代码
COPY . .

# 构建应用
ARG NODE_ENV=production
ARG VITE_API_BASE_URL=/api
ENV NODE_ENV=\$NODE_ENV
ENV VITE_API_BASE_URL=\$VITE_API_BASE_URL

RUN pnpm run build

# 生产阶段
FROM registry.cn-hangzhou.aliyuncs.com/library/nginx:1.24-alpine AS production

# 复制构建产物和配置
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-default.conf /etc/nginx/conf.d/default.conf

# 创建用户和目录
RUN addgroup -g 1001 -S nginx-app && \\
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx-app -g nginx-app nginx-app && \\
    mkdir -p /var/cache/nginx /var/log/nginx /var/run && \\
    chown -R nginx-app:nginx-app /var/cache/nginx /var/log/nginx /var/run /usr/share/nginx/html

# 健康检查脚本
RUN echo '#!/bin/sh' > /usr/local/bin/health-check.sh && \\
    echo 'curl -f http://localhost:80/health || exit 1' >> /usr/local/bin/health-check.sh && \\
    chmod +x /usr/local/bin/health-check.sh

USER nginx-app
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD /usr/local/bin/health-check.sh
CMD ["nginx", "-g", "daemon off;"]
EOF
    
    docker build -f frontend/Dockerfile.fast -t ssl-manager-frontend:fast ./frontend
    
    # 使用基础镜像构建后端
    log_info "构建后端应用镜像..."
    cat > backend/Dockerfile.fast <<EOF
# 使用预构建的基础镜像
FROM ssl-manager-backend-base:latest

# 创建应用用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 复制requirements并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 创建目录和脚本
RUN mkdir -p /app/logs /app/data /app/certs /app/backups && \\
    chown -R appuser:appuser /app

# 健康检查和启动脚本
RUN echo '#!/bin/bash' > /usr/local/bin/health-check.sh && \\
    echo 'curl -f http://localhost:8000/health || exit 1' >> /usr/local/bin/health-check.sh && \\
    chmod +x /usr/local/bin/health-check.sh

RUN echo '#!/bin/bash' > /usr/local/bin/start.sh && \\
    echo 'set -e' >> /usr/local/bin/start.sh && \\
    echo 'timeout=60' >> /usr/local/bin/start.sh && \\
    echo 'while ! nc -z \${DB_HOST:-localhost} \${DB_PORT:-5432}; do' >> /usr/local/bin/start.sh && \\
    echo '  sleep 1; timeout=\$((timeout-1))' >> /usr/local/bin/start.sh && \\
    echo '  [ \$timeout -eq 0 ] && exit 1' >> /usr/local/bin/start.sh && \\
    echo 'done' >> /usr/local/bin/start.sh && \\
    echo 'python src/models/database.py' >> /usr/local/bin/start.sh && \\
    echo 'exec gunicorn --bind 0.0.0.0:8000 --workers \${WORKERS:-2} --worker-class gevent src.app:app' >> /usr/local/bin/start.sh && \\
    chmod +x /usr/local/bin/start.sh

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 CMD /usr/local/bin/health-check.sh
CMD ["/usr/local/bin/start.sh"]
EOF
    
    docker build -f backend/Dockerfile.fast -t ssl-manager-backend:fast ./backend
    
    log_success "应用镜像构建完成"
}

# 推送镜像到ACR
push_to_acr() {
    if [ "$USE_ACR" = "true" ]; then
        log_info "推送镜像到阿里云容器镜像服务..."
        
        # 设置ACR命名空间（需要替换为实际的命名空间）
        ACR_NAMESPACE=${ACR_NAMESPACE:-"ssl-manager"}
        ACR_REGISTRY=${ACR_REGISTRY:-"registry.cn-hangzhou.aliyuncs.com"}
        
        # 标记和推送镜像
        local images=(
            "ssl-manager-frontend-base:latest"
            "ssl-manager-backend-base:latest"
            "ssl-manager-frontend:fast"
            "ssl-manager-backend:fast"
        )
        
        for image in "${images[@]}"; do
            local acr_image="$ACR_REGISTRY/$ACR_NAMESPACE/$image"
            log_info "推送镜像: $acr_image"
            docker tag "$image" "$acr_image"
            docker push "$acr_image" &
        done
        
        wait
        log_success "镜像推送完成"
    else
        log_info "跳过ACR推送"
    fi
}

# 创建快速部署配置
create_fast_compose() {
    log_info "创建快速部署配置..."
    
    cat > docker-compose.fast.yml <<EOF
version: '3.8'

networks:
  ssl-manager-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  ssl_certs:
  app_logs:

services:
  postgres:
    image: registry.cn-hangzhou.aliyuncs.com/library/postgres:15-alpine
    container_name: ssl-manager-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: \${DB_NAME:-ssl_manager}
      POSTGRES_USER: \${DB_USER:-ssl_user}
      POSTGRES_PASSWORD: \${DB_PASSWORD:-ssl_password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - ssl-manager-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${DB_USER:-ssl_user}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: registry.cn-hangzhou.aliyuncs.com/library/redis:7-alpine
    container_name: ssl-manager-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - ssl-manager-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  backend:
    image: ssl-manager-backend:fast
    container_name: ssl-manager-backend
    restart: unless-stopped
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: \${DB_NAME:-ssl_manager}
      DB_USER: \${DB_USER:-ssl_user}
      DB_PASSWORD: \${DB_PASSWORD:-ssl_password}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      SECRET_KEY: \${SECRET_KEY:-your-secret-key}
      JWT_SECRET_KEY: \${JWT_SECRET_KEY:-your-jwt-secret}
    volumes:
      - ssl_certs:/app/certs
      - app_logs:/app/logs
    ports:
      - "8000:8000"
    networks:
      - ssl-manager-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  frontend:
    image: ssl-manager-frontend:fast
    container_name: ssl-manager-frontend
    restart: unless-stopped
    ports:
      - "80:80"
    networks:
      - ssl-manager-network
    depends_on:
      - backend
EOF
    
    log_success "快速部署配置创建完成"
}

# 清理临时文件
cleanup() {
    log_info "清理临时文件..."
    
    # 删除临时Dockerfile
    rm -f frontend/Dockerfile.base frontend/Dockerfile.fast
    rm -f backend/Dockerfile.base backend/Dockerfile.fast
    
    log_success "清理完成"
}

# 主函数
main() {
    log_info "开始预构建镜像..."
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --acr-namespace)
                ACR_NAMESPACE="$2"
                shift 2
                ;;
            --acr-registry)
                ACR_REGISTRY="$2"
                shift 2
                ;;
            --skip-acr)
                USE_ACR=false
                shift
                ;;
            --help)
                echo "预构建镜像脚本"
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --acr-namespace NS    ACR命名空间"
                echo "  --acr-registry REG    ACR注册表地址"
                echo "  --skip-acr           跳过ACR推送"
                echo "  --help               显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行构建步骤
    setup_acr
    build_base_images
    build_app_images
    push_to_acr
    create_fast_compose
    cleanup
    
    log_success "预构建完成！"
    echo
    echo "=== 使用说明 ==="
    echo "1. 快速部署: docker-compose -f docker-compose.fast.yml up -d"
    echo "2. 查看镜像: docker images | grep ssl-manager"
    echo "3. 如果推送到了ACR，其他机器可以直接拉取使用"
    echo
}

# 执行主函数
main "$@"
