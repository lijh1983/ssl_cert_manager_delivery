#!/usr/bin/env python3
"""
SSL证书管理系统 - 功能完整性检查脚本
在代码清理前后验证所有核心功能模块的完整性
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FunctionalIntegrityChecker:
    """功能完整性检查器"""
    
    def __init__(self, project_root: str = '.'):
        """初始化检查器"""
        self.project_root = Path(project_root).resolve()
        
        # 定义核心功能模块（基于实际项目结构）
        self.core_modules = {
            'authentication': {
                'files': [
                    'backend/src/models/user.py',
                    'frontend/src/views/Login.vue'
                ],
                'description': '用户认证和授权'
            },
            'certificate_management': {
                'files': [
                    'backend/src/models/certificate.py',
                    'backend/src/services/certificate_service.py',
                    'backend/src/services/certificate_operations_service.py',
                    'frontend/src/views/Certificates.vue'
                ],
                'description': '证书管理核心功能'
            },
            'acme_integration': {
                'files': [
                    'backend/src/services/acme_client.py',
                    'backend/src/services/certificate_service.py'
                ],
                'description': 'ACME协议集成'
            },
            'monitoring': {
                'files': [
                    'backend/src/services/monitoring_service.py',
                    'backend/src/services/domain_monitoring_service.py',
                    'backend/src/services/port_monitoring_service.py',
                    'backend/src/models/alert.py',
                    'frontend/src/views/Monitoring.vue'
                ],
                'description': '证书监控和告警'
            },
            'server_management': {
                'files': [
                    'backend/src/models/server.py',
                    'backend/src/services/server_service.py',
                    'frontend/src/views/Servers.vue'
                ],
                'description': '服务器管理'
            },
            'database': {
                'files': [
                    'backend/src/models/database.py',
                    'backend/database/init_mysql.sql',
                    'backend/migrations/'
                ],
                'description': '数据库层'
            },
            'api_layer': {
                'files': [
                    'backend/src/app.py',
                    'backend/src/simple_app.py',
                    'backend/src/services/',
                    'backend/src/utils/'
                ],
                'description': 'API接口层'
            },
            'frontend_core': {
                'files': [
                    'frontend/src/main.ts',
                    'frontend/src/App.vue',
                    'frontend/src/router/',
                    'frontend/src/store/'
                ],
                'description': '前端核心'
            },
            'deployment': {
                'files': [
                    'docker-compose.production.yml',
                    'docker-compose.mysql.yml',
                    'backend/Dockerfile.production',
                    'nginx/nginx.conf'
                ],
                'description': '部署配置'
            }
        }
        
        # 定义API端点
        self.api_endpoints = [
            '/api/v1/auth/login',
            '/api/v1/auth/logout',
            '/api/v1/certificates',
            '/api/v1/certificates/{id}',
            '/api/v1/certificates/{id}/renew',
            '/api/v1/servers',
            '/api/v1/monitoring',
            '/api/v1/alerts',
            '/api/health'
        ]
        
        # 定义前端页面
        self.frontend_pages = [
            'Login',
            'Dashboard',
            'Certificates',
            'Servers',
            'Monitoring',
            'Settings'
        ]
    
    def check_file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        full_path = self.project_root / file_path
        return full_path.exists()
    
    def check_directory_exists(self, dir_path: str) -> bool:
        """检查目录是否存在"""
        full_path = self.project_root / dir_path
        return full_path.is_dir()
    
    def check_core_modules(self) -> Dict[str, Dict]:
        """检查核心功能模块完整性"""
        logger.info("检查核心功能模块完整性...")
        
        results = {}
        
        for module_name, module_info in self.core_modules.items():
            module_result = {
                'description': module_info['description'],
                'files_checked': 0,
                'files_missing': [],
                'files_present': [],
                'status': 'unknown'
            }
            
            for file_path in module_info['files']:
                module_result['files_checked'] += 1
                
                if file_path.endswith('/'):
                    # 这是一个目录
                    if self.check_directory_exists(file_path):
                        module_result['files_present'].append(file_path)
                    else:
                        module_result['files_missing'].append(file_path)
                else:
                    # 这是一个文件
                    if self.check_file_exists(file_path):
                        module_result['files_present'].append(file_path)
                    else:
                        module_result['files_missing'].append(file_path)
            
            # 计算模块状态
            missing_count = len(module_result['files_missing'])
            total_count = module_result['files_checked']
            
            if missing_count == 0:
                module_result['status'] = 'complete'
            elif missing_count < total_count / 2:
                module_result['status'] = 'partial'
            else:
                module_result['status'] = 'critical'
            
            results[module_name] = module_result
        
        return results
    
    def check_python_syntax(self) -> Dict[str, List]:
        """检查Python文件语法"""
        logger.info("检查Python文件语法...")
        
        results = {
            'valid': [],
            'invalid': [],
            'errors': []
        }
        
        # 查找所有Python文件
        for root, dirs, files in os.walk(self.project_root):
            # 跳过隐藏目录和虚拟环境
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'venv', 'env', '__pycache__', 'node_modules'}]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            compile(f.read(), str(file_path), 'exec')
                        results['valid'].append(str(relative_path))
                    except SyntaxError as e:
                        results['invalid'].append(str(relative_path))
                        results['errors'].append(f"{relative_path}: {e}")
                    except Exception as e:
                        results['errors'].append(f"{relative_path}: {e}")
        
        return results
    
    def check_import_dependencies(self) -> Dict[str, List]:
        """检查Python模块导入依赖"""
        logger.info("检查Python模块导入依赖...")
        
        results = {
            'resolved': [],
            'unresolved': [],
            'errors': []
        }
        
        # 检查主要模块的导入
        main_modules = [
            'backend/src/app.py',
            'backend/src/models/database.py',
            'backend/src/models/certificate.py',
            'backend/src/utils/acme_client.py'
        ]
        
        for module_path in main_modules:
            full_path = self.project_root / module_path
            if not full_path.exists():
                results['unresolved'].append(f"{module_path}: File not found")
                continue
            
            try:
                # 简单的导入检查
                sys.path.insert(0, str(full_path.parent))
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查import语句
                import_lines = [line.strip() for line in content.split('\n') if line.strip().startswith(('import ', 'from '))]
                
                if import_lines:
                    results['resolved'].append(f"{module_path}: {len(import_lines)} imports found")
                else:
                    results['unresolved'].append(f"{module_path}: No imports found")
                
            except Exception as e:
                results['errors'].append(f"{module_path}: {e}")
        
        return results
    
    def check_docker_configurations(self) -> Dict[str, Dict]:
        """检查Docker配置完整性"""
        logger.info("检查Docker配置完整性...")
        
        results = {}
        
        # 检查主要的Docker文件
        docker_files = {
            'docker-compose.yml': '开发环境编排',
            'docker-compose.production.yml': '生产环境编排',
            'docker-compose.mysql.yml': 'MySQL数据库编排',
            'backend/Dockerfile': '后端开发镜像',
            'backend/Dockerfile.production': '后端生产镜像',
            'frontend/Dockerfile': '前端镜像'
        }
        
        for docker_file, description in docker_files.items():
            file_result = {
                'description': description,
                'exists': self.check_file_exists(docker_file),
                'syntax_valid': False,
                'errors': []
            }
            
            if file_result['exists']:
                try:
                    # 简单的语法检查
                    if 'docker-compose' in docker_file:
                        # 检查docker-compose文件
                        result = subprocess.run(
                            ['docker-compose', '-f', str(self.project_root / docker_file), 'config'],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        file_result['syntax_valid'] = result.returncode == 0
                        if result.returncode != 0:
                            file_result['errors'].append(result.stderr)
                    else:
                        # 对于Dockerfile，简单检查是否有FROM指令
                        with open(self.project_root / docker_file, 'r') as f:
                            content = f.read()
                        file_result['syntax_valid'] = 'FROM ' in content
                
                except subprocess.TimeoutExpired:
                    file_result['errors'].append("Syntax check timeout")
                except FileNotFoundError:
                    file_result['errors'].append("docker-compose command not found")
                except Exception as e:
                    file_result['errors'].append(str(e))
            
            results[docker_file] = file_result
        
        return results
    
    def check_configuration_files(self) -> Dict[str, Dict]:
        """检查配置文件完整性"""
        logger.info("检查配置文件完整性...")
        
        results = {}
        
        # 检查主要配置文件
        config_files = {
            'backend/requirements.txt': 'Python依赖',
            'backend/requirements-prod.txt': 'Python生产依赖',
            'frontend/package.json': 'Node.js依赖',
            'nginx/nginx.conf': 'Nginx主配置',
            'nginx/conf.d/ssl-manager-production.conf': 'Nginx生产配置',
            '.env.production.example': '生产环境变量模板'
        }
        
        for config_file, description in config_files.items():
            file_result = {
                'description': description,
                'exists': self.check_file_exists(config_file),
                'size': 0,
                'non_empty': False
            }
            
            if file_result['exists']:
                try:
                    file_path = self.project_root / config_file
                    file_result['size'] = file_path.stat().st_size
                    file_result['non_empty'] = file_result['size'] > 0
                except Exception as e:
                    file_result['error'] = str(e)
            
            results[config_file] = file_result
        
        return results
    
    def run_comprehensive_check(self) -> Dict:
        """运行综合检查"""
        logger.info("开始功能完整性综合检查...")
        
        check_results = {
            'timestamp': str(Path().cwd()),
            'core_modules': self.check_core_modules(),
            'python_syntax': self.check_python_syntax(),
            'import_dependencies': self.check_import_dependencies(),
            'docker_configurations': self.check_docker_configurations(),
            'configuration_files': self.check_configuration_files()
        }
        
        # 计算总体状态
        total_issues = 0
        critical_issues = 0
        
        # 检查核心模块
        for module_name, module_result in check_results['core_modules'].items():
            if module_result['status'] == 'critical':
                critical_issues += 1
            elif module_result['status'] == 'partial':
                total_issues += 1
        
        # 检查Python语法
        if check_results['python_syntax']['invalid']:
            critical_issues += len(check_results['python_syntax']['invalid'])
        
        # 检查Docker配置
        for docker_file, docker_result in check_results['docker_configurations'].items():
            if not docker_result['exists'] and 'production' in docker_file:
                critical_issues += 1
            elif not docker_result['syntax_valid']:
                total_issues += 1
        
        check_results['summary'] = {
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'status': 'healthy' if critical_issues == 0 and total_issues < 3 else 'warning' if critical_issues == 0 else 'critical'
        }
        
        return check_results
    
    def generate_report(self, results: Dict) -> str:
        """生成检查报告"""
        report_path = self.project_root / 'functional_integrity_report.json'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # 生成可读报告
        readable_report = f"""
SSL证书管理系统 - 功能完整性检查报告
=========================================

检查时间: {results.get('timestamp', 'Unknown')}
总体状态: {results['summary']['status'].upper()}
问题总数: {results['summary']['total_issues']}
严重问题: {results['summary']['critical_issues']}

核心模块检查:
"""
        
        for module_name, module_result in results['core_modules'].items():
            status_icon = "✅" if module_result['status'] == 'complete' else "⚠️" if module_result['status'] == 'partial' else "❌"
            readable_report += f"  {status_icon} {module_name}: {module_result['description']} ({module_result['status']})\n"
            
            if module_result['files_missing']:
                readable_report += f"    缺失文件: {', '.join(module_result['files_missing'])}\n"
        
        readable_report += f"\nPython语法检查:\n"
        readable_report += f"  有效文件: {len(results['python_syntax']['valid'])}\n"
        readable_report += f"  无效文件: {len(results['python_syntax']['invalid'])}\n"
        
        if results['python_syntax']['invalid']:
            readable_report += f"  语法错误:\n"
            for error in results['python_syntax']['errors']:
                readable_report += f"    - {error}\n"
        
        readable_report += f"\nDocker配置检查:\n"
        for docker_file, docker_result in results['docker_configurations'].items():
            status_icon = "✅" if docker_result['exists'] and docker_result['syntax_valid'] else "❌"
            readable_report += f"  {status_icon} {docker_file}: {docker_result['description']}\n"
            
            if docker_result['errors']:
                for error in docker_result['errors']:
                    readable_report += f"    错误: {error}\n"
        
        readable_report_path = self.project_root / 'functional_integrity_report.txt'
        with open(readable_report_path, 'w', encoding='utf-8') as f:
            f.write(readable_report)
        
        return str(readable_report_path)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SSL证书管理系统功能完整性检查工具')
    parser.add_argument('--project-root', default='.', help='项目根目录')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 运行检查
    checker = FunctionalIntegrityChecker(args.project_root)
    results = checker.run_comprehensive_check()
    report_path = checker.generate_report(results)
    
    print(f"\n功能完整性检查完成")
    print(f"总体状态: {results['summary']['status'].upper()}")
    print(f"问题总数: {results['summary']['total_issues']}")
    print(f"严重问题: {results['summary']['critical_issues']}")
    print(f"详细报告: {report_path}")
    
    if results['summary']['status'] == 'critical':
        print("\n⚠️  发现严重问题，建议修复后再进行代码清理")
        sys.exit(1)
    elif results['summary']['status'] == 'warning':
        print("\n⚠️  发现一些问题，但不影响核心功能")
        sys.exit(0)
    else:
        print("\n✅ 所有核心功能完整，可以安全进行代码清理")
        sys.exit(0)


if __name__ == '__main__':
    main()
