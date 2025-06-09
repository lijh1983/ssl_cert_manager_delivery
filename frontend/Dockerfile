# 阿里云优化版前端Dockerfile
# 多阶段构建 - 前端应用

# 阶段1: 构建阶段
# 使用预构建的前端基础镜像（包含所有依赖）
FROM ssl-manager-frontend-base:latest AS builder

# 设置工作目录（基础镜像中已设置，但为了明确性再次设置）
WORKDIR /app

# 复制源代码
COPY . .

# 构建应用
ARG NODE_ENV=production
ARG VITE_API_BASE_URL=/api
ENV NODE_ENV=$NODE_ENV
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# 构建时优化
RUN pnpm run build

# 阶段2: 生产阶段
FROM nginx:1.24-alpine AS production

# 安装必要工具
RUN apk add --no-cache \
    curl \
    tzdata \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apk del tzdata

# 创建nginx用户
RUN addgroup -g 1001 -S nginx-app && \
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx-app -g nginx-app nginx-app

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-default.conf /etc/nginx/conf.d/default.conf

# 创建必要目录并设置权限
RUN mkdir -p /var/cache/nginx/client_temp \
    /var/cache/nginx/proxy_temp \
    /var/cache/nginx/fastcgi_temp \
    /var/cache/nginx/uwsgi_temp \
    /var/cache/nginx/scgi_temp \
    /var/log/nginx \
    /tmp \
    && chown -R nginx-app:nginx-app /var/cache/nginx \
    && chown -R nginx-app:nginx-app /var/log/nginx \
    && chown -R nginx-app:nginx-app /tmp \
    && chown -R nginx-app:nginx-app /usr/share/nginx/html \
    && chmod -R 755 /usr/share/nginx/html \
    && chmod 755 /tmp

# 创建健康检查脚本
RUN echo '#!/bin/sh' > /usr/local/bin/health-check.sh && \
    echo 'curl -f http://localhost:80/health || exit 1' >> /usr/local/bin/health-check.sh && \
    chmod +x /usr/local/bin/health-check.sh

# 创建启动脚本
RUN echo '#!/bin/sh' > /usr/local/bin/start-nginx.sh && \
    echo 'set -e' >> /usr/local/bin/start-nginx.sh && \
    echo '' >> /usr/local/bin/start-nginx.sh && \
    echo '# 确保必要目录存在并有正确权限' >> /usr/local/bin/start-nginx.sh && \
    echo 'mkdir -p /tmp /var/log/nginx /var/cache/nginx' >> /usr/local/bin/start-nginx.sh && \
    echo 'touch /tmp/nginx.pid' >> /usr/local/bin/start-nginx.sh && \
    echo '' >> /usr/local/bin/start-nginx.sh && \
    echo '# 测试nginx配置' >> /usr/local/bin/start-nginx.sh && \
    echo 'nginx -t' >> /usr/local/bin/start-nginx.sh && \
    echo '' >> /usr/local/bin/start-nginx.sh && \
    echo '# 启动nginx' >> /usr/local/bin/start-nginx.sh && \
    echo 'exec nginx -g "daemon off;"' >> /usr/local/bin/start-nginx.sh && \
    chmod +x /usr/local/bin/start-nginx.sh

# 切换到非root用户
USER nginx-app

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# 启动nginx
CMD ["/usr/local/bin/start-nginx.sh"]

# 标签信息
LABEL maintainer="SSL Certificate Manager Team" \
      version="1.0.0" \
      description="SSL Certificate Manager Frontend (Aliyun Optimized)" \
      org.opencontainers.image.source="https://github.com/lijh1983/ssl_cert_manager_delivery"
