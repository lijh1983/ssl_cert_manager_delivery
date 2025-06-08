#!/bin/bash
# 快速修复nginx镜像拉取问题

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

# 备份原始文件
backup_files() {
    log_info "备份原始文件..."
    
    if [ -f "nginx/Dockerfile.proxy" ]; then
        cp nginx/Dockerfile.proxy nginx/Dockerfile.proxy.backup.$(date +%Y%m%d_%H%M%S)
        log_success "已备份: nginx/Dockerfile.proxy"
    fi
}

# 测试并选择可用的基础镜像
find_working_base_image() {
    log_info "查找可用的nginx基础镜像..."
    
    # 候选镜像列表（按优先级排序）
    local candidate_images=(
        "nginx:1.24-alpine"
        "nginx:alpine" 
        "nginx:1.22-alpine"
        "registry.cn-hangzhou.aliyuncs.com/acs/nginx:1.24-alpine"
        "dockerproxy.com/library/nginx:1.24-alpine"
        "docker.mirrors.ustc.edu.cn/library/nginx:1.24-alpine"
    )
    
    for image in "${candidate_images[@]}"; do
        log_info "测试镜像: $image"
        
        if timeout 30 docker pull "$image" > /dev/null 2>&1; then
            log_success "找到可用镜像: $image"
            echo "$image"
            return 0
        else
            log_warning "镜像不可用: $image"
        fi
    done
    
    log_error "没有找到可用的nginx镜像"
    return 1
}

# 修复Dockerfile
fix_dockerfile() {
    local working_image="$1"
    
    log_info "修复nginx/Dockerfile.proxy..."
    
    # 创建修复后的Dockerfile
    cat > nginx/Dockerfile.proxy <<EOF
# Nginx反向代理Dockerfile - 修复版
FROM $working_image

# 安装必要工具
RUN apk add --no-cache \\
    curl \\
    tzdata \\
    openssl \\
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \\
    && echo "Asia/Shanghai" > /etc/timezone \\
    && apk del tzdata

# 创建nginx用户
RUN addgroup -g 1001 -S nginx-proxy && \\
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx-proxy -g nginx-proxy nginx-proxy

# 创建必要目录
RUN mkdir -p /var/cache/nginx/client_temp \\
    /var/cache/nginx/proxy_temp \\
    /var/cache/nginx/fastcgi_temp \\
    /var/cache/nginx/uwsgi_temp \\
    /var/cache/nginx/scgi_temp \\
    /var/log/nginx \\
    /var/run \\
    /etc/nginx/ssl \\
    && chown -R nginx-proxy:nginx-proxy /var/cache/nginx \\
    && chown -R nginx-proxy:nginx-proxy /var/log/nginx \\
    && chown -R nginx-proxy:nginx-proxy /var/run \\
    && chown -R nginx-proxy:nginx-proxy /etc/nginx/ssl

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# 创建默认SSL证书
RUN mkdir -p /etc/nginx/ssl && \\
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
    -keyout /etc/nginx/ssl/default.key \\
    -out /etc/nginx/ssl/default.crt \\
    -subj "/C=CN/ST=Default/L=Default/O=Default/CN=default"

# 创建健康检查脚本
RUN echo '#!/bin/sh' > /usr/local/bin/health-check.sh && \\
    echo 'curl -f http://localhost:80/health || exit 1' >> /usr/local/bin/health-check.sh && \\
    chmod +x /usr/local/bin/health-check.sh

# 创建启动脚本
RUN echo '#!/bin/sh' > /usr/local/bin/start-nginx.sh && \\
    echo 'set -e' >> /usr/local/bin/start-nginx.sh && \\
    echo 'nginx -t && exec nginx -g "daemon off;"' >> /usr/local/bin/start-nginx.sh && \\
    chmod +x /usr/local/bin/start-nginx.sh

# 切换到非root用户
USER nginx-proxy

# 暴露端口
EXPOSE 80 443

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD /usr/local/bin/health-check.sh

# 启动命令
CMD ["/usr/local/bin/start-nginx.sh"]

# 标签信息
LABEL maintainer="SSL Certificate Manager Team" \\
      version="1.0.0" \\
      description="SSL Certificate Manager Nginx Reverse Proxy (Fixed)" \\
      base_image="$working_image"
EOF
    
    log_success "Dockerfile修复完成，使用基础镜像: $working_image"
}

# 测试构建
test_build() {
    log_info "测试nginx代理镜像构建..."
    
    if docker build -f nginx/Dockerfile.proxy -t ssl-manager-nginx-proxy:test ./nginx; then
        log_success "镜像构建测试成功"
        
        # 清理测试镜像
        docker rmi ssl-manager-nginx-proxy:test > /dev/null 2>&1 || true
        
        return 0
    else
        log_error "镜像构建测试失败"
        return 1
    fi
}

# 配置Docker镜像加速器（如果需要）
setup_docker_mirror() {
    log_info "检查Docker镜像加速器配置..."
    
    if [ -f "/etc/docker/daemon.json" ]; then
        if grep -q "registry-mirrors" /etc/docker/daemon.json; then
            log_success "Docker镜像加速器已配置"
            return 0
        fi
    fi
    
    log_warning "Docker镜像加速器未配置，正在配置..."
    
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://registry.cn-hangzhou.aliyuncs.com",
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com"
    ],
    "max-concurrent-downloads": 10
}
EOF
    
    sudo systemctl restart docker
    sleep 5
    
    log_success "Docker镜像加速器配置完成"
}

# 显示修复结果
show_fix_result() {
    local working_image="$1"
    
    echo
    log_success "🎉 nginx镜像问题修复完成！"
    echo
    echo "=== 修复详情 ==="
    echo "✅ 使用的基础镜像: $working_image"
    echo "✅ Dockerfile已修复: nginx/Dockerfile.proxy"
    echo "✅ 构建测试通过"
    echo
    echo "=== 下一步操作 ==="
    echo "现在可以继续运行nginx反向代理配置："
    echo "  ./scripts/setup_nginx_proxy.sh --domain ssl.gzyggl.com --enable-monitoring"
    echo
    echo "或者直接构建镜像："
    echo "  docker build -f nginx/Dockerfile.proxy -t ssl-manager-nginx-proxy:latest ./nginx"
    echo
}

# 主函数
main() {
    echo "🔧 nginx镜像拉取问题快速修复工具"
    echo "===================================="
    echo
    
    # 检查Docker服务
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行，请先启动Docker"
        exit 1
    fi
    
    # 备份文件
    backup_files
    
    # 配置镜像加速器
    setup_docker_mirror
    
    # 查找可用镜像
    local working_image
    if working_image=$(find_working_base_image); then
        # 修复Dockerfile
        fix_dockerfile "$working_image"
        
        # 测试构建
        if test_build; then
            show_fix_result "$working_image"
        else
            log_error "构建测试失败，请检查配置"
            exit 1
        fi
    else
        log_error "无法找到可用的nginx基础镜像"
        
        echo
        echo "=== 故障排除建议 ==="
        echo "1. 检查网络连接:"
        echo "   ping registry-1.docker.io"
        echo "   ping registry.cn-hangzhou.aliyuncs.com"
        echo
        echo "2. 检查Docker配置:"
        echo "   docker info"
        echo "   systemctl status docker"
        echo
        echo "3. 尝试手动拉取镜像:"
        echo "   docker pull nginx:alpine"
        echo
        echo "4. 配置代理（如果需要）:"
        echo "   export HTTP_PROXY=your-proxy-server"
        echo "   export HTTPS_PROXY=your-proxy-server"
        echo
        
        exit 1
    fi
}

# 执行主函数
main "$@"
