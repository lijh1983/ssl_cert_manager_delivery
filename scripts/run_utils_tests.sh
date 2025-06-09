#!/bin/bash

# 工具模块测试运行脚本
# 运行后端工具模块测试并生成覆盖率报告

set -e

echo "🧪 SSL证书管理系统 - 工具模块测试套件"
echo "=================================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
TESTS_DIR="$PROJECT_ROOT/tests"

echo -e "${BLUE}项目根目录: $PROJECT_ROOT${NC}"
echo ""

# 检查Python环境
echo -e "${BLUE}1. 检查Python环境...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Python环境: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ 未找到Python3${NC}"
    exit 1
fi

# 检查测试依赖
echo -e "${BLUE}2. 检查测试依赖...${NC}"
REQUIRED_PACKAGES=("pytest" "pytest-cov" "pytest-mock" "coverage")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✅ $package${NC}"
    else
        echo -e "${RED}❌ $package (缺失)${NC}"
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现缺失依赖，尝试安装...${NC}"
    pip3 install "${MISSING_PACKAGES[@]}" || {
        echo -e "${RED}❌ 依赖安装失败${NC}"
        exit 1
    }
fi

# 设置环境变量
echo -e "${BLUE}3. 设置测试环境...${NC}"
export PYTHONPATH="$BACKEND_DIR/src:$PYTHONPATH"
export ENVIRONMENT="test"
export DATABASE_URL="sqlite:///:memory:"
export SECRET_KEY="test_secret_key"
export LOG_LEVEL="DEBUG"

echo -e "${GREEN}✅ 测试环境配置完成${NC}"

# 创建测试报告目录
REPORTS_DIR="$PROJECT_ROOT/test_reports"
mkdir -p "$REPORTS_DIR"

# 运行测试
echo -e "${BLUE}4. 运行工具模块测试套件...${NC}"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}运行工具模块测试...${NC}"

# 运行pytest并生成覆盖率报告
python3 -m pytest \
    tests/backend/test_utils_modules.py \
    tests/test_error_handling.py \
    --cov=backend/src/utils \
    --cov-report=term-missing \
    --cov-report=html:$REPORTS_DIR/coverage_html \
    --cov-report=xml:$REPORTS_DIR/coverage.xml \
    --cov-report=json:$REPORTS_DIR/coverage.json \
    --junit-xml=$REPORTS_DIR/junit.xml \
    --verbose \
    --tb=short \
    --durations=10

TEST_EXIT_CODE=$?

# 检查测试结果
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
else
    echo -e "${RED}❌ 部分测试失败${NC}"
fi

# 生成覆盖率摘要
echo -e "${BLUE}5. 生成测试报告...${NC}"

# 解析覆盖率数据
if [ -f "$REPORTS_DIR/coverage.json" ]; then
    COVERAGE_PERCENT=$(python3 -c "
import json
with open('$REPORTS_DIR/coverage.json', 'r') as f:
    data = json.load(f)
    print(f\"{data['totals']['percent_covered']:.1f}\")
")
    
    echo -e "${BLUE}测试覆盖率: ${COVERAGE_PERCENT}%${NC}"
    
    # 检查覆盖率目标
    if (( $(echo "$COVERAGE_PERCENT >= 50.0" | bc -l) )); then
        echo -e "${GREEN}🎯 覆盖率目标达成 (≥50%)${NC}"
        COVERAGE_TARGET_MET=true
    else
        echo -e "${YELLOW}⚠️  覆盖率未达到目标 (目标: ≥50%, 当前: ${COVERAGE_PERCENT}%)${NC}"
        COVERAGE_TARGET_MET=false
    fi
else
    echo -e "${RED}❌ 无法读取覆盖率数据${NC}"
    COVERAGE_TARGET_MET=false
fi

# 统计测试用例数量
echo -e "${BLUE}6. 测试统计...${NC}"
TEST_FILES=$(find tests/backend -name "test_utils_modules.py" | wc -l)
TEST_FUNCTIONS=$(grep -r "def test_" tests/backend/test_utils_modules.py tests/test_error_handling.py | wc -l)

echo -e "${GREEN}✅ 测试文件数: $((TEST_FILES + 1))${NC}"
echo -e "${GREEN}✅ 测试用例数: $TEST_FUNCTIONS${NC}"

# 显示覆盖率最低的模块
echo -e "${BLUE}7. 覆盖率分析...${NC}"
if [ -f "$REPORTS_DIR/coverage.json" ]; then
    echo -e "${YELLOW}模块覆盖率详情:${NC}"
    python3 -c "
import json
with open('$REPORTS_DIR/coverage.json', 'r') as f:
    data = json.load(f)
    files = data['files']
    
    print('模块名称'.ljust(40) + '覆盖率'.ljust(10) + '缺失行数')
    print('-' * 60)
    for filename, file_data in files.items():
        if 'backend/src/utils' in filename:
            module_name = filename.replace('backend/src/utils/', '').replace('.py', '')
            coverage = file_data['summary']['percent_covered']
            missing = file_data['summary']['num_statements'] - file_data['summary']['covered_lines']
            print(f'{module_name}'.ljust(40) + f'{coverage:.1f}%'.ljust(10) + f'{missing}')
"
fi

# 生成测试执行摘要
echo ""
echo "=================================================="
echo -e "${GREEN}🎉 工具模块测试执行完成！${NC}"
echo ""
echo -e "${BLUE}测试摘要:${NC}"
echo -e "${GREEN}✅ 测试状态: $([ $TEST_EXIT_CODE -eq 0 ] && echo "通过" || echo "失败")${NC}"
echo -e "${GREEN}✅ 覆盖率: ${COVERAGE_PERCENT:-"未知"}%${NC}"
echo -e "${GREEN}✅ 测试文件: $((TEST_FILES + 1)) 个${NC}"
echo -e "${GREEN}✅ 测试用例: $TEST_FUNCTIONS 个${NC}"
echo ""
echo -e "${YELLOW}📋 报告文件:${NC}"
echo -e "   - 测试摘要: $REPORTS_DIR/backend_test_summary.md"
echo -e "   - HTML覆盖率: $REPORTS_DIR/coverage_html/index.html"
echo -e "   - JUnit报告: $REPORTS_DIR/junit.xml"
echo ""

# 显示改进建议
echo -e "${BLUE}📈 改进建议:${NC}"
if [ -f "$REPORTS_DIR/coverage.json" ]; then
    python3 -c "
import json
with open('$REPORTS_DIR/coverage.json', 'r') as f:
    data = json.load(f)
    files = data['files']
    
    low_coverage_files = []
    for filename, file_data in files.items():
        if 'backend/src/utils' in filename:
            coverage = file_data['summary']['percent_covered']
            if coverage < 70:
                module_name = filename.replace('backend/src/utils/', '').replace('.py', '')
                low_coverage_files.append((module_name, coverage))
    
    if low_coverage_files:
        print('需要提高覆盖率的模块:')
        for module, coverage in sorted(low_coverage_files, key=lambda x: x[1]):
            print(f'  - {module}: {coverage:.1f}%')
    else:
        print('所有模块覆盖率良好！')
"
fi

echo ""
echo -e "${BLUE}下一步: $([ "$COVERAGE_TARGET_MET" = true ] && echo "继续服务层测试开发" || echo "提高工具模块测试覆盖率")${NC}"
echo "=================================================="

# 返回测试结果
exit $TEST_EXIT_CODE
