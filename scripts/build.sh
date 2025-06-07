#!/bin/bash

# SSL证书自动化管理系统构建脚本
# 用于构建前端和后端应用

set -e

# 设置脚本权限
chmod +x "$0"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
        log_error "$1 命令未找到，请先安装 $1"
        exit 1
    fi
}

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log_info "开始构建SSL证书自动化管理系统..."
log_info "项目根目录: $PROJECT_ROOT"

# 检查必要的命令
log_info "检查依赖命令..."
check_command "node"
check_command "npm"
check_command "python3"

# 构建前端
log_info "构建前端应用..."
cd "$PROJECT_ROOT/frontend"

# 检查package.json是否存在
if [ ! -f "package.json" ]; then
    log_error "frontend/package.json 文件不存在"
    exit 1
fi

# 安装依赖
log_info "安装前端依赖..."
npm install

# 构建前端
log_info "编译前端代码..."
npm run build

if [ $? -eq 0 ]; then
    log_success "前端构建完成"
else
    log_error "前端构建失败"
    exit 1
fi

# 构建后端
log_info "准备后端应用..."
cd "$PROJECT_ROOT/backend"

# 检查requirements.txt是否存在
if [ ! -f "requirements.txt" ]; then
    log_error "backend/requirements.txt 文件不存在"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    log_info "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
log_info "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
log_info "安装后端依赖..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    log_success "后端依赖安装完成"
else
    log_error "后端依赖安装失败"
    exit 1
fi

# 创建必要的目录
log_info "创建必要的目录..."
mkdir -p logs
mkdir -p data
mkdir -p certs

# 复制配置文件模板
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    log_info "复制环境配置文件..."
    cp .env.example .env
    log_warning "请编辑 backend/.env 文件配置相关参数"
fi

# 初始化数据库
log_info "初始化数据库..."
python3 -c "
from app import create_app, db
from models import User
import bcrypt

app = create_app()
with app.app_context():
    db.create_all()
    
    # 检查是否已存在管理员用户
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # 创建默认管理员用户
        password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=password_hash.decode('utf-8'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print('默认管理员用户已创建: admin/admin123')
    else:
        print('管理员用户已存在')
"

if [ $? -eq 0 ]; then
    log_success "数据库初始化完成"
else
    log_error "数据库初始化失败"
    exit 1
fi

# 返回项目根目录
cd "$PROJECT_ROOT"

# 创建启动脚本
log_info "创建启动脚本..."
cat > start.sh << 'EOF'
#!/bin/bash

# SSL证书自动化管理系统启动脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 启动后端服务
echo "启动后端服务..."
cd backend
source venv/bin/activate
python3 app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端服务（如果是开发模式）
if [ "$1" = "dev" ]; then
    echo "启动前端开发服务..."
    cd ../frontend
    npm run dev &
    FRONTEND_PID=$!
    
    echo "前端开发服务PID: $FRONTEND_PID"
fi

echo "后端服务PID: $BACKEND_PID"
echo "服务已启动"
echo "后端地址: http://localhost:5000"
echo "前端地址: http://localhost:3000"

# 等待用户输入以停止服务
read -p "按回车键停止服务..."

# 停止服务
kill $BACKEND_PID 2>/dev/null
if [ ! -z "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID 2>/dev/null
fi

echo "服务已停止"
EOF

chmod +x start.sh

# 创建生产环境启动脚本
log_info "创建生产环境启动脚本..."
cat > start-prod.sh << 'EOF'
#!/bin/bash

# SSL证书自动化管理系统生产环境启动脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT/backend"

# 设置生产环境变量
export FLASK_ENV=production

# 激活虚拟环境
source venv/bin/activate

# 使用gunicorn启动
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile logs/access.log --error-logfile logs/error.log app:app
EOF

chmod +x start-prod.sh

log_success "构建完成！"
log_info "使用以下命令启动服务:"
log_info "  开发模式: ./start.sh dev"
log_info "  生产模式: ./start-prod.sh"
log_info ""
log_info "默认管理员账户:"
log_info "  用户名: admin"
log_info "  密码: admin123"
log_info ""
log_warning "请及时修改默认密码并配置 backend/.env 文件"
