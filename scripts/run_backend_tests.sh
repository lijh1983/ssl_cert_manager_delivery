#!/bin/bash

# 后端测试运行脚本
# 运行所有后端测试并生成覆盖率报告

set -e

echo "🧪 SSL证书管理系统 - 后端测试套件"
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
export ACME_ACCOUNT_EMAIL="test@example.com"

echo -e "${GREEN}✅ 测试环境配置完成${NC}"

# 创建测试报告目录
REPORTS_DIR="$PROJECT_ROOT/test_reports"
mkdir -p "$REPORTS_DIR"

# 运行测试
echo -e "${BLUE}4. 运行后端测试套件...${NC}"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}运行单元测试...${NC}"

# 运行pytest并生成覆盖率报告
python3 -m pytest \
    tests/backend/ \
    tests/conftest.py \
    tests/test_error_handling.py \
    --cov=backend/src \
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
    if (( $(echo "$COVERAGE_PERCENT >= 80.0" | bc -l) )); then
        echo -e "${GREEN}🎯 覆盖率目标达成 (≥80%)${NC}"
        COVERAGE_TARGET_MET=true
    else
        echo -e "${YELLOW}⚠️  覆盖率未达到目标 (目标: ≥80%, 当前: ${COVERAGE_PERCENT}%)${NC}"
        COVERAGE_TARGET_MET=false
    fi
else
    echo -e "${RED}❌ 无法读取覆盖率数据${NC}"
    COVERAGE_TARGET_MET=false
fi

# 生成详细的测试报告
REPORT_FILE="$REPORTS_DIR/test_summary.md"
cat > "$REPORT_FILE" << EOF
# 后端测试报告

## 测试概述
- **执行时间**: $(date)
- **测试环境**: Python $(python3 --version | cut -d' ' -f2)
- **测试框架**: pytest
- **覆盖率工具**: coverage.py

## 测试结果
- **测试状态**: $([ $TEST_EXIT_CODE -eq 0 ] && echo "✅ 通过" || echo "❌ 失败")
- **覆盖率**: ${COVERAGE_PERCENT:-"未知"}%
- **覆盖率目标**: $([ "$COVERAGE_TARGET_MET" = true ] && echo "✅ 达成" || echo "❌ 未达成")

## 测试模块
- **证书服务测试**: tests/backend/test_certificate_service_comprehensive.py
- **ACME管理器测试**: tests/backend/test_acme_manager.py
- **通知服务测试**: tests/backend/test_notification_service.py
- **服务器服务测试**: tests/backend/test_server_service.py
- **工具模块测试**: tests/backend/test_utils_modules.py
- **错误处理测试**: tests/test_error_handling.py

## 覆盖率详情
详细的覆盖率报告请查看: [HTML报告](coverage_html/index.html)

## 测试文件
- **JUnit XML**: junit.xml
- **覆盖率XML**: coverage.xml
- **覆盖率JSON**: coverage.json
- **覆盖率HTML**: coverage_html/

## 改进建议
$([ "$COVERAGE_TARGET_MET" = false ] && echo "
- 增加边界条件测试用例
- 补充异常处理测试
- 添加集成测试用例
- 提高核心业务逻辑覆盖率
" || echo "
- 维持当前测试覆盖率
- 定期更新测试用例
- 添加性能测试
- 考虑添加压力测试
")

---
生成时间: $(date)
EOF

echo -e "${GREEN}✅ 测试报告已生成: $REPORT_FILE${NC}"

# 显示覆盖率最低的模块
echo -e "${BLUE}6. 覆盖率分析...${NC}"
if [ -f "$REPORTS_DIR/coverage.json" ]; then
    echo -e "${YELLOW}覆盖率最低的模块:${NC}"
    python3 -c "
import json
with open('$REPORTS_DIR/coverage.json', 'r') as f:
    data = json.load(f)
    files = data['files']
    sorted_files = sorted(files.items(), key=lambda x: x[1]['summary']['percent_covered'])
    
    print('模块名称'.ljust(50) + '覆盖率')
    print('-' * 60)
    for filename, file_data in sorted_files[:10]:  # 显示覆盖率最低的10个文件
        if 'backend/src' in filename:
            module_name = filename.replace('backend/src/', '').replace('.py', '')
            coverage = file_data['summary']['percent_covered']
            print(f'{module_name}'.ljust(50) + f'{coverage:.1f}%')
"
fi

# 运行代码质量检查
echo -e "${BLUE}7. 代码质量检查...${NC}"

# 检查语法错误
echo -e "${YELLOW}检查语法错误...${NC}"
SYNTAX_ERRORS=0
find "$BACKEND_DIR/src" -name "*.py" | while read -r file; do
    if ! python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${RED}❌ 语法错误: $file${NC}"
        SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
    fi
done

if [ $SYNTAX_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ 无语法错误${NC}"
fi

# 统计测试用例数量
echo -e "${BLUE}8. 测试统计...${NC}"
TEST_FILES=$(find tests/backend -name "test_*.py" | wc -l)
TEST_FUNCTIONS=$(grep -r "def test_" tests/backend/ | wc -l)

echo -e "${GREEN}✅ 测试文件数: $TEST_FILES${NC}"
echo -e "${GREEN}✅ 测试用例数: $TEST_FUNCTIONS${NC}"

# 生成测试执行摘要
echo ""
echo "=================================================="
echo -e "${GREEN}🎉 后端测试执行完成！${NC}"
echo ""
echo -e "${BLUE}测试摘要:${NC}"
echo -e "${GREEN}✅ 测试状态: $([ $TEST_EXIT_CODE -eq 0 ] && echo "通过" || echo "失败")${NC}"
echo -e "${GREEN}✅ 覆盖率: ${COVERAGE_PERCENT:-"未知"}%${NC}"
echo -e "${GREEN}✅ 测试文件: $TEST_FILES 个${NC}"
echo -e "${GREEN}✅ 测试用例: $TEST_FUNCTIONS 个${NC}"
echo ""
echo -e "${YELLOW}📋 报告文件:${NC}"
echo -e "   - 测试摘要: $REPORT_FILE"
echo -e "   - HTML覆盖率: $REPORTS_DIR/coverage_html/index.html"
echo -e "   - JUnit报告: $REPORTS_DIR/junit.xml"
echo ""
echo -e "${BLUE}下一步: $([ "$COVERAGE_TARGET_MET" = true ] && echo "继续前端测试开发" || echo "提高测试覆盖率至80%以上")${NC}"
echo "=================================================="

# 返回测试结果
exit $TEST_EXIT_CODE
