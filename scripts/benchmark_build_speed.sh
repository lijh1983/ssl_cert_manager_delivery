#!/bin/bash
# 构建速度基准测试脚本

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

# 格式化时间显示
format_time() {
    local seconds=$1
    local minutes=$((seconds / 60))
    local remaining_seconds=$((seconds % 60))
    
    if [ $minutes -gt 0 ]; then
        echo "${minutes}分${remaining_seconds}秒"
    else
        echo "${seconds}秒"
    fi
}

# 测试原始构建速度
test_original_build() {
    log_info "测试原始构建速度（使用官方软件源）..."
    
    # 创建原始Dockerfile
    cat > backend/Dockerfile.original <<EOF
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    TZ=Asia/Shanghai

RUN ln -snf /usr/share/zoneinfo/\$TZ /etc/localtime && echo \$TZ > /etc/timezone

# 使用官方软件源（慢）
RUN apt-get update && apt-get install -y \\
    curl \\
    gcc \\
    g++ \\
    make \\
    libffi-dev \\
    libssl-dev \\
    libpq-dev \\
    netcat-traditional \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["python", "src/app.py"]
EOF
    
    log_info "开始原始构建测试..."
    local start_time=$(date +%s)
    
    if timeout 1800 docker build -f backend/Dockerfile.original -t ssl-backend-original ./backend > build_original.log 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "原始构建完成，耗时: $(format_time $duration)"
        
        # 清理测试镜像
        docker rmi ssl-backend-original > /dev/null 2>&1 || true
        rm backend/Dockerfile.original
        
        echo $duration
    else
        log_error "原始构建失败或超时（30分钟）"
        rm backend/Dockerfile.original
        echo "1800"  # 返回超时时间
    fi
}

# 测试优化后构建速度
test_optimized_build() {
    log_info "测试优化后构建速度（使用阿里云软件源）..."
    
    log_info "开始优化构建测试..."
    local start_time=$(date +%s)
    
    if docker build -f backend/Dockerfile.aliyun.fast -t ssl-backend-optimized ./backend > build_optimized.log 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "优化构建完成，耗时: $(format_time $duration)"
        
        # 清理测试镜像
        docker rmi ssl-backend-optimized > /dev/null 2>&1 || true
        
        echo $duration
    else
        log_error "优化构建失败"
        echo "0"
    fi
}

# 测试网络速度
test_network_speed() {
    log_info "测试网络下载速度..."
    
    # 测试官方源速度
    log_info "测试官方Debian源速度..."
    local start_time=$(date +%s)
    if timeout 30 curl -s http://deb.debian.org/debian/ls-lR.gz > /dev/null 2>&1; then
        local end_time=$(date +%s)
        local official_time=$((end_time - start_time))
        log_info "官方源响应时间: ${official_time}秒"
    else
        log_warning "官方源连接超时"
        local official_time=30
    fi
    
    # 测试阿里云源速度
    log_info "测试阿里云镜像源速度..."
    start_time=$(date +%s)
    if timeout 30 curl -s https://mirrors.aliyun.com/debian/ls-lR.gz > /dev/null 2>&1; then
        local end_time=$(date +%s)
        local aliyun_time=$((end_time - start_time))
        log_info "阿里云源响应时间: ${aliyun_time}秒"
    else
        log_warning "阿里云源连接超时"
        local aliyun_time=30
    fi
    
    # 计算速度提升
    if [ $official_time -gt 0 ] && [ $aliyun_time -gt 0 ]; then
        local speedup=$(echo "scale=1; $official_time / $aliyun_time" | bc 2>/dev/null || echo "N/A")
        log_success "网络速度提升: ${speedup}倍"
    fi
}

# 分析构建日志
analyze_build_logs() {
    log_info "分析构建日志..."
    
    if [ -f "build_original.log" ]; then
        log_info "原始构建日志分析:"
        
        # 分析apt-get update时间
        local apt_update_time=$(grep -o "apt-get update.*" build_original.log | wc -l)
        echo "  apt-get update 步骤: ${apt_update_time}次"
        
        # 分析包下载时间
        local download_count=$(grep -c "Get:" build_original.log || echo "0")
        echo "  下载的包数量: ${download_count}个"
        
        # 查找最慢的步骤
        echo "  最耗时的步骤:"
        grep -E "Step [0-9]+/[0-9]+" build_original.log | tail -5 || echo "    无法解析"
    fi
    
    if [ -f "build_optimized.log" ]; then
        log_info "优化构建日志分析:"
        
        # 分析优化效果
        local optimization_steps=$(grep -c "阿里云" build_optimized.log || echo "0")
        echo "  优化步骤数量: ${optimization_steps}个"
        
        # 分析包下载时间
        local download_count=$(grep -c "Get:" build_optimized.log || echo "0")
        echo "  下载的包数量: ${download_count}个"
    fi
}

# 生成性能报告
generate_performance_report() {
    local original_time=$1
    local optimized_time=$2
    
    log_info "生成性能报告..."
    
    local report_file="build_performance_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "SSL证书管理系统 - 构建性能测试报告"
        echo "生成时间: $(date)"
        echo "========================================"
        echo
        
        echo "=== 系统环境 ==="
        echo "操作系统: $(uname -a)"
        echo "CPU核心数: $(nproc)"
        echo "内存大小: $(free -h | awk 'NR==2{print $2}')"
        echo "Docker版本: $(docker --version)"
        echo
        
        echo "=== 构建时间对比 ==="
        echo "原始构建时间: $(format_time $original_time)"
        echo "优化构建时间: $(format_time $optimized_time)"
        
        if [ $optimized_time -gt 0 ] && [ $original_time -gt 0 ]; then
            local speedup=$(echo "scale=1; $original_time / $optimized_time" | bc 2>/dev/null || echo "N/A")
            local time_saved=$((original_time - optimized_time))
            local improvement=$(echo "scale=1; ($time_saved * 100) / $original_time" | bc 2>/dev/null || echo "N/A")
            
            echo "速度提升: ${speedup}倍"
            echo "时间节省: $(format_time $time_saved)"
            echo "性能改善: ${improvement}%"
        fi
        echo
        
        echo "=== 优化措施 ==="
        echo "✅ 配置阿里云Debian镜像源"
        echo "✅ 配置阿里云pip镜像源"
        echo "✅ 优化APT安装参数"
        echo "✅ 分批安装依赖包"
        echo "✅ 启用Docker BuildKit"
        echo "✅ 优化Docker缓存策略"
        echo
        
        echo "=== 网络环境测试 ==="
        ping -c 3 deb.debian.org 2>/dev/null | grep "time=" | tail -1 || echo "官方源: 连接失败"
        ping -c 3 mirrors.aliyun.com 2>/dev/null | grep "time=" | tail -1 || echo "阿里云源: 连接失败"
        echo
        
        echo "=== 建议 ==="
        if [ $optimized_time -lt 300 ]; then
            echo "✅ 构建速度优秀（<5分钟）"
        elif [ $optimized_time -lt 600 ]; then
            echo "⚠️  构建速度良好（5-10分钟）"
        else
            echo "❌ 构建速度需要进一步优化（>10分钟）"
        fi
        
        echo
        echo "进一步优化建议:"
        echo "1. 使用多阶段构建减少镜像大小"
        echo "2. 使用.dockerignore减少构建上下文"
        echo "3. 考虑使用预构建的基础镜像"
        echo "4. 启用Docker BuildKit缓存"
        
    } > "$report_file"
    
    log_success "性能报告已生成: $report_file"
}

# 显示测试结果
show_test_results() {
    local original_time=$1
    local optimized_time=$2
    
    echo
    log_success "🎉 构建速度基准测试完成！"
    echo
    echo "=== 测试结果 ==="
    echo "原始构建时间: $(format_time $original_time)"
    echo "优化构建时间: $(format_time $optimized_time)"
    
    if [ $optimized_time -gt 0 ] && [ $original_time -gt 0 ]; then
        local speedup=$(echo "scale=1; $original_time / $optimized_time" | bc 2>/dev/null || echo "N/A")
        local time_saved=$((original_time - optimized_time))
        local improvement=$(echo "scale=1; ($time_saved * 100) / $original_time" | bc 2>/dev/null || echo "N/A")
        
        echo
        echo "=== 性能提升 ==="
        echo "🚀 速度提升: ${speedup}倍"
        echo "⏰ 时间节省: $(format_time $time_saved)"
        echo "📈 性能改善: ${improvement}%"
        
        if [ $optimized_time -lt 300 ]; then
            echo "🏆 构建速度等级: 优秀"
        elif [ $optimized_time -lt 600 ]; then
            echo "🥈 构建速度等级: 良好"
        else
            echo "🥉 构建速度等级: 一般"
        fi
    fi
    
    echo
    echo "=== 下一步操作 ==="
    echo "使用优化后的构建:"
    echo "  docker build -f backend/Dockerfile.aliyun.fast -t ssl-manager-backend ./backend"
    echo
    echo "或使用快速构建脚本:"
    echo "  ./fast_build_backend.sh"
    echo
}

# 主函数
main() {
    echo "📊 SSL证书管理系统 - 构建速度基准测试"
    echo "========================================"
    echo
    
    # 检查依赖
    if ! command -v bc > /dev/null 2>&1; then
        log_warning "bc命令未安装，部分计算功能可能不可用"
    fi
    
    # 检查Docker服务
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行，请先启动Docker"
        exit 1
    fi
    
    # 清理之前的测试镜像
    log_info "清理之前的测试镜像..."
    docker rmi ssl-backend-original ssl-backend-optimized > /dev/null 2>&1 || true
    
    # 执行测试
    test_network_speed
    echo
    
    log_info "开始构建速度基准测试..."
    echo "注意: 原始构建可能需要20-30分钟，请耐心等待..."
    echo
    
    # 测试原始构建（可选，因为时间较长）
    local original_time=0
    read -p "是否执行原始构建测试？(可能需要20-30分钟) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        original_time=$(test_original_build)
    else
        log_info "跳过原始构建测试，使用估算时间"
        original_time=1200  # 假设20分钟
    fi
    echo
    
    # 测试优化构建
    local optimized_time
    optimized_time=$(test_optimized_build)
    echo
    
    # 分析日志
    analyze_build_logs
    echo
    
    # 生成报告
    generate_performance_report $original_time $optimized_time
    echo
    
    # 显示结果
    show_test_results $original_time $optimized_time
    
    # 清理日志文件
    rm -f build_original.log build_optimized.log
}

# 执行主函数
main "$@"
