# 多阶段构建 - 后端应用
# 阶段1: 基础镜像
FROM python:3.10-slim AS base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 阶段2: 依赖安装
FROM base AS dependencies

# 设置工作目录
WORKDIR /app

# 升级pip
RUN pip install --upgrade pip

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 阶段3: 生产镜像
FROM base AS production

# 创建应用用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 从依赖阶段复制已安装的包
COPY --from=dependencies /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/logs /app/data /app/certs /app/backups \
    && chown -R appuser:appuser /app \
    && chmod +x /app/scripts/*.sh

# 创建健康检查脚本
RUN echo '#!/bin/bash' > /usr/local/bin/health-check.sh && \
    echo 'curl -f http://localhost:8000/health || exit 1' >> /usr/local/bin/health-check.sh && \
    chmod +x /usr/local/bin/health-check.sh

# 创建启动脚本
RUN echo '#!/bin/bash' > /usr/local/bin/start.sh && \
    echo 'set -e' >> /usr/local/bin/start.sh && \
    echo '' >> /usr/local/bin/start.sh && \
    echo '# 等待数据库就绪' >> /usr/local/bin/start.sh && \
    echo 'echo "Waiting for database..."' >> /usr/local/bin/start.sh && \
    echo 'while ! nc -z ${DB_HOST:-localhost} ${DB_PORT:-5432}; do' >> /usr/local/bin/start.sh && \
    echo '  sleep 1' >> /usr/local/bin/start.sh && \
    echo 'done' >> /usr/local/bin/start.sh && \
    echo 'echo "Database is ready!"' >> /usr/local/bin/start.sh && \
    echo '' >> /usr/local/bin/start.sh && \
    echo '# 运行数据库迁移' >> /usr/local/bin/start.sh && \
    echo 'echo "Running database migrations..."' >> /usr/local/bin/start.sh && \
    echo 'python src/models/database.py' >> /usr/local/bin/start.sh && \
    echo '' >> /usr/local/bin/start.sh && \
    echo '# 启动应用' >> /usr/local/bin/start.sh && \
    echo 'echo "Starting application..."' >> /usr/local/bin/start.sh && \
    echo 'exec uvicorn src.app:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-1}' >> /usr/local/bin/start.sh && \
    chmod +x /usr/local/bin/start.sh

# 安装netcat用于健康检查
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# 设置默认环境变量
ENV ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    WORKERS=1 \
    DB_HOST=postgres \
    DB_PORT=5432 \
    DB_NAME=ssl_manager \
    DB_USER=ssl_user \
    REDIS_HOST=redis \
    REDIS_PORT=6379

# 启动命令
CMD ["/usr/local/bin/start.sh"]

# 标签信息
LABEL maintainer="SSL Certificate Manager Team" \
      version="1.0.0" \
      description="SSL Certificate Manager Backend API" \
      org.opencontainers.image.source="https://github.com/lijh1983/ssl_cert_manager_delivery"
