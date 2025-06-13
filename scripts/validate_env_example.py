#!/usr/bin/env python3
"""
环境变量配置验证脚本
验证.env.example文件是否包含所有必需的环境变量
"""

import os
import re
import sys
from pathlib import Path

def load_env_example():
    """加载.env.example文件中的环境变量"""
    env_file = Path('.env.example')
    if not env_file.exists():
        print("❌ .env.example文件不存在")
        return None
    
    env_vars = {}
    with open(env_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            
            # 解析环境变量
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = {
                    'value': value.strip(),
                    'line': line_num
                }
    
    return env_vars

def get_required_vars_from_docker_compose():
    """从docker-compose文件中提取必需的环境变量"""
    required_vars = set()
    
    compose_files = [
        'docker-compose.yml',
        'docker-compose.production.yml',
        'docker-compose.mysql.yml'
    ]
    
    for compose_file in compose_files:
        if not os.path.exists(compose_file):
            continue
            
        with open(compose_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 查找${VAR}或${VAR:-default}格式的环境变量
            matches = re.findall(r'\$\{([^}:]+)(?::-[^}]*)?\}', content)
            required_vars.update(matches)
    
    return required_vars

def get_required_vars_from_backend():
    """从后端代码中提取必需的环境变量"""
    required_vars = set()
    
    # 从config.py中提取
    config_file = Path('backend/config.py')
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 查找os.environ.get('VAR')格式
            matches = re.findall(r"os\.environ\.get\(['\"]([^'\"]+)['\"]", content)
            required_vars.update(matches)
    
    # 从entrypoint.sh中提取
    entrypoint_file = Path('backend/docker/entrypoint.sh')
    if entrypoint_file.exists():
        with open(entrypoint_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 查找required_vars数组中的变量
            in_required_vars = False
            for line in content.split('\n'):
                line = line.strip()
                if 'required_vars=(' in line:
                    in_required_vars = True
                    continue
                if in_required_vars:
                    if ')' in line:
                        break
                    # 提取变量名
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        required_vars.add(match.group(1))
    
    return required_vars

def get_required_vars_from_frontend():
    """从前端代码中提取必需的环境变量"""
    required_vars = set()
    
    # 从vite.config.ts中提取
    vite_config = Path('frontend/vite.config.ts')
    if vite_config.exists():
        with open(vite_config, 'r', encoding='utf-8') as f:
            content = f.read()
            # 查找env.VITE_*格式的变量
            matches = re.findall(r'env\.([A-Z_]+)', content)
            required_vars.update(matches)
    
    return required_vars

def validate_env_example():
    """验证.env.example文件的完整性"""
    print("🔍 验证.env.example文件...")
    
    # 加载.env.example
    env_vars = load_env_example()
    if env_vars is None:
        return False
    
    print(f"✅ 已加载 {len(env_vars)} 个环境变量")
    
    # 获取所有必需的环境变量
    docker_vars = get_required_vars_from_docker_compose()
    backend_vars = get_required_vars_from_backend()
    frontend_vars = get_required_vars_from_frontend()

    # 合并所有必需变量
    all_required_vars = docker_vars | backend_vars | frontend_vars

    # 移除不应该在应用程序配置中的变量
    docker_only_vars = {
        'MYSQL_ROOT_PASSWORD',  # 仅用于Docker容器初始化，应用程序不应使用
    }
    all_required_vars = all_required_vars - docker_only_vars
    
    print(f"📋 发现 {len(all_required_vars)} 个必需的环境变量")
    
    # 检查缺失的变量
    missing_vars = []
    for var in all_required_vars:
        if var not in env_vars:
            missing_vars.append(var)
    
    # 检查多余的变量（可能已废弃）
    extra_vars = []
    for var in env_vars:
        if var not in all_required_vars:
            extra_vars.append(var)
    
    # 输出结果
    success = True
    
    if missing_vars:
        print(f"\n❌ 缺失的环境变量 ({len(missing_vars)}个):")
        for var in sorted(missing_vars):
            print(f"  - {var}")
        success = False
    
    if extra_vars:
        print(f"\n⚠️  可能多余的环境变量 ({len(extra_vars)}个):")
        for var in sorted(extra_vars):
            print(f"  - {var} (第{env_vars[var]['line']}行)")
    
    # 检查重要变量的值
    important_vars = {
        'SECRET_KEY': 32,  # 最小长度
        'JWT_SECRET_KEY': 32,
        'MYSQL_PASSWORD': 8,
        'REDIS_PASSWORD': 8
    }

    # 检查不合规的配置
    security_violations = []
    if 'MYSQL_ROOT_PASSWORD' in env_vars:
        security_violations.append('MYSQL_ROOT_PASSWORD - 应用程序不应使用MySQL root用户')
    
    weak_vars = []
    for var, min_length in important_vars.items():
        if var in env_vars:
            value = env_vars[var]['value']
            # 移除引号
            value = value.strip('\'"')
            if len(value) < min_length or 'change' in value.lower() or 'your' in value.lower():
                weak_vars.append(var)
    
    if weak_vars:
        print(f"\n⚠️  需要更改的默认值 ({len(weak_vars)}个):")
        for var in weak_vars:
            print(f"  - {var}: 请设置强密码")

    if security_violations:
        print(f"\n🚨 安全违规配置 ({len(security_violations)}个):")
        for violation in security_violations:
            print(f"  - {violation}")
        success = False

    if success and not missing_vars and not security_violations:
        print("\n🎉 .env.example文件验证通过！")
        return True
    else:
        print(f"\n❌ .env.example文件需要完善")
        return False

def main():
    """主函数"""
    if not validate_env_example():
        sys.exit(1)

if __name__ == '__main__':
    main()
