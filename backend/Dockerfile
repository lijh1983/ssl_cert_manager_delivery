# 阿里云优化版后端Dockerfile
# 多阶段构建 - 后端应用

# 阶段1: 应用构建
# 使用预构建的后端基础镜像（包含所有依赖）
FROM ssl-manager-backend-base:latest AS production

# 切换回root用户进行系统配置
USER root

# 设置工作目录（基础镜像中已设置，但为了明确性再次设置）
WORKDIR /app

# 复制应用代码
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/data /app/certs /app/backups \
    && chown -R appuser:appuser /app/logs /app/data /app/certs /app/backups \
    && chmod -R 755 /app/logs /app/data /app/certs /app/backups

# 创建健康检查脚本
RUN echo '#!/bin/bash' > /usr/local/bin/health-check.sh && \
    echo 'curl -f http://localhost:8000/health || exit 1' >> /usr/local/bin/health-check.sh && \
    chmod +x /usr/local/bin/health-check.sh

# 创建优化的启动脚本
RUN echo '#!/bin/bash' > /usr/local/bin/start.sh && \
    echo 'set -e' >> /usr/local/bin/start.sh && \
    echo '' >> /usr/local/bin/start.sh && \
    echo '# 等待数据库就绪' >> /usr/local/bin/start.sh && \
    echo 'echo "Waiting for database..."' >> /usr/local/bin/start.sh && \
    echo 'timeout=60' >> /usr/local/bin/start.sh && \
    echo 'while ! nc -z ${DB_HOST:-localhost} ${DB_PORT:-5432}; do' >> /usr/local/bin/start.sh && \
    echo '  sleep 1' >> /usr/local/bin/start.sh && \
    echo '  timeout=$((timeout-1))' >> /usr/local/bin/start.sh && \
    echo '  if [ $timeout -eq 0 ]; then' >> /usr/local/bin/start.sh && \
    echo '    echo "Database connection timeout"' >> /usr/local/bin/start.sh && \
    echo '    exit 1' >> /usr/local/bin/start.sh && \
    echo '  fi' >> /usr/local/bin/start.sh && \
    echo 'done' >> /usr/local/bin/start.sh && \
    echo 'echo "Database is ready!"' >> /usr/local/bin/start.sh && \
    echo '' >> /usr/local/bin/start.sh && \
    echo '# 运行数据库迁移' >> /usr/local/bin/start.sh && \
    echo 'echo "Running database migrations..."' >> /usr/local/bin/start.sh && \
    echo 'python src/models/database.py' >> /usr/local/bin/start.sh && \
    echo '' >> /usr/local/bin/start.sh && \
    echo '# 启动应用' >> /usr/local/bin/start.sh && \
    echo 'echo "Starting application..."' >> /usr/local/bin/start.sh && \
    echo 'exec gunicorn --bind 0.0.0.0:8000 --workers ${WORKERS:-2} --worker-class gevent --worker-connections 1000 --timeout 120 --keepalive 5 --max-requests 1000 --max-requests-jitter 100 --preload src.app:app' >> /usr/local/bin/start.sh && \
    chmod +x /usr/local/bin/start.sh

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
    WORKERS=2 \
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
      description="SSL Certificate Manager Backend API (Aliyun Optimized)" \
      org.opencontainers.image.source="https://github.com/lijh1983/ssl_cert_manager_delivery"
