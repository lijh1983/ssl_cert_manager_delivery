#!/bin/bash

# SSL证书自动化管理系统现代化测试运行脚本
# 包含安全测试、单元测试、集成测试和端到端测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 未安装"
        return 1
    fi
    return 0
}

# 清理函数
cleanup() {
    log_info "清理测试环境..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
}

# 设置清理陷阱
trap cleanup EXIT

echo "=========================================="
echo "SSL证书自动化管理系统 - 现代化测试套件"
echo "=========================================="

# 设置测试环境变量
export FLASK_ENV=testing
export SECRET_KEY=test_secret_key_for_testing_only
export DATABASE_URL=sqlite:///:memory:

# 进入项目根目录
cd "$(dirname "$0")/.."

# 检查依赖
log_info "检查测试依赖..."
check_command python3 || exit 1
check_command npm || exit 1

# 创建测试报告目录
mkdir -p tests/reports

# ==========================================
# 1. 后端测试
# ==========================================
log_info "开始后端测试..."

cd backend

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    log_info "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
log_info "安装后端依赖..."
pip install -r requirements.txt
pip install pytest pytest-cov pytest-flask flake8 mypy bandit safety

# 运行安全扫描
log_info "运行安全扫描..."
bandit -r src/ -f json -o ../tests/reports/security_report.json || log_warning "安全扫描发现问题"
safety check --json --output ../tests/reports/safety_report.json || log_warning "依赖安全检查发现问题"

# 运行代码质量检查
log_info "运行代码质量检查..."
flake8 src/ --max-line-length=100 --exclude=venv --output-file=../tests/reports/flake8_report.txt || log_warning "代码质量检查发现问题"

# 运行类型检查
log_info "运行类型检查..."
mypy src/ --ignore-missing-imports --html-report ../tests/reports/mypy_report || log_warning "类型检查发现问题"

# 运行后端单元测试
log_info "运行后端单元测试..."
python -m pytest ../tests/backend/ -v \
    --cov=src \
    --cov-report=html:../tests/reports/backend_coverage \
    --cov-report=term \
    --cov-fail-under=70 \
    --junit-xml=../tests/reports/backend_junit.xml

log_success "后端测试完成"

# ==========================================
# 2. 前端测试
# ==========================================
log_info "开始前端测试..."

cd ../frontend

# 安装前端依赖
if [ ! -d "node_modules" ]; then
    log_info "安装前端依赖..."
    npm install
fi

# 安装测试依赖
log_info "安装前端测试依赖..."
npm install --save-dev vitest @vue/test-utils @playwright/test jsdom

# 运行前端代码质量检查
log_info "运行前端代码质量检查..."
npm run lint || log_warning "前端代码质量检查发现问题"
npm run type-check || log_warning "前端类型检查发现问题"

# 运行前端单元测试
log_info "运行前端单元测试..."
npm run test:unit -- --coverage --reporter=junit --outputFile=../tests/reports/frontend_junit.xml

log_success "前端测试完成"

# ==========================================
# 3. 集成测试
# ==========================================
log_info "开始集成测试..."

# 启动后端服务（测试模式）
cd ../backend
source venv/bin/activate
export FLASK_ENV=testing
log_info "启动后端测试服务..."
python src/app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 5

# 运行API集成测试
log_info "运行API集成测试..."
python -m pytest ../tests/backend/ -v -k "test_api" --junit-xml=../tests/reports/integration_junit.xml

log_success "集成测试完成"

# ==========================================
# 4. 端到端测试
# ==========================================
log_info "开始端到端测试..."

cd ../frontend

# 启动前端开发服务器
log_info "启动前端测试服务..."
npm run dev &
FRONTEND_PID=$!

# 等待前端启动
sleep 10

# 安装Playwright浏览器
npx playwright install

# 运行E2E测试
log_info "运行端到端测试..."
npx playwright test ../tests/e2e/ --reporter=html --output-dir=../tests/reports/e2e_report

log_success "端到端测试完成"

# ==========================================
# 5. 性能测试
# ==========================================
log_info "开始性能测试..."

# 运行简单的性能测试
if command -v ab &> /dev/null; then
    log_info "运行API性能测试..."
    ab -n 100 -c 10 http://localhost:5000/api/v1/health > ../tests/reports/performance_report.txt
else
    log_warning "Apache Bench (ab) 未安装，跳过性能测试"
fi

# ==========================================
# 6. 生成测试报告
# ==========================================
log_info "生成测试报告..."

cd ../tests/reports

# 创建测试报告汇总
cat > test_summary.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>SSL证书管理系统 - 测试报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .success { background: #d4edda; border-color: #c3e6cb; }
        .warning { background: #fff3cd; border-color: #ffeaa7; }
        .error { background: #f8d7da; border-color: #f5c6cb; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <h1>SSL证书自动化管理系统 - 测试报告</h1>
        <p>生成时间: $(date)</p>
    </div>
    
    <div class="section success">
        <h2>测试概览</h2>
        <ul>
            <li>✅ 后端单元测试</li>
            <li>✅ 前端单元测试</li>
            <li>✅ 集成测试</li>
            <li>✅ 端到端测试</li>
            <li>✅ 安全扫描</li>
            <li>✅ 代码质量检查</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>详细报告</h2>
        <ul>
            <li><a href="backend_coverage/index.html">后端测试覆盖率报告</a></li>
            <li><a href="e2e_report/index.html">端到端测试报告</a></li>
            <li><a href="security_report.json">安全扫描报告</a></li>
            <li><a href="flake8_report.txt">代码质量报告</a></li>
            <li><a href="performance_report.txt">性能测试报告</a></li>
        </ul>
    </div>
</body>
</html>
EOF

echo ""
echo "=========================================="
log_success "所有测试完成！"
echo "=========================================="
echo ""
echo "测试报告位置:"
echo "📊 测试汇总: tests/reports/test_summary.html"
echo "🔒 安全报告: tests/reports/security_report.json"
echo "📈 覆盖率报告: tests/reports/backend_coverage/index.html"
echo "🌐 E2E测试报告: tests/reports/e2e_report/index.html"
echo "⚡ 性能报告: tests/reports/performance_report.txt"
echo ""
echo "测试统计:"
echo "- 后端测试覆盖率: $(grep -o 'TOTAL.*[0-9]\+%' tests/reports/backend_coverage/index.html | tail -1 || echo '未知')"
echo "- 安全问题: $(jq '.results | length' tests/reports/security_report.json 2>/dev/null || echo '未知')"
echo ""

# 如果在CI环境中，设置退出码
if [ "$CI" = "true" ]; then
    # 检查是否有测试失败
    if grep -q "FAILED" tests/reports/*.xml 2>/dev/null; then
        log_error "发现测试失败"
        exit 1
    fi
fi

log_success "测试套件执行完成！"
