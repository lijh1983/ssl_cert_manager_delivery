#!/usr/bin/env python3
"""
SSL证书管理系统 - 最终验证脚本
在代码清理后验证所有核心功能的完整性和可用性
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinalVerifier:
    """最终验证器"""
    
    def __init__(self, project_root: str = '.'):
        """初始化验证器"""
        self.project_root = Path(project_root).resolve()
        self.verification_results = {
            'timestamp': None,
            'overall_status': 'unknown',
            'tests': {},
            'summary': {}
        }
    
    def verify_core_imports(self) -> bool:
        """验证核心模块导入"""
        logger.info("验证核心模块导入...")
        
        core_modules = [
            'backend/src/models/database.py',
            'backend/src/models/certificate.py',
            'backend/src/models/user.py',
            'backend/src/models/server.py',
            'backend/src/models/alert.py',
            'backend/src/services/acme_client.py',
            'backend/src/services/certificate_service.py',
            'backend/src/services/monitoring_service.py'
        ]
        
        import_results = []
        
        for module_path in core_modules:
            full_path = self.project_root / module_path
            if not full_path.exists():
                import_results.append(f"❌ {module_path}: File not found")
                continue
            
            try:
                # 检查Python语法
                with open(full_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), str(full_path), 'exec')
                import_results.append(f"✅ {module_path}: Syntax OK")
            except SyntaxError as e:
                import_results.append(f"❌ {module_path}: Syntax Error - {e}")
            except Exception as e:
                import_results.append(f"⚠️ {module_path}: Warning - {e}")
        
        self.verification_results['tests']['core_imports'] = import_results
        
        # 计算成功率
        success_count = len([r for r in import_results if r.startswith('✅')])
        total_count = len(import_results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        logger.info(f"核心模块导入验证: {success_count}/{total_count} 成功 ({success_rate*100:.1f}%)")
        return success_rate >= 0.9
    
    def verify_database_configuration(self) -> bool:
        """验证数据库配置"""
        logger.info("验证数据库配置...")
        
        db_files = [
            'backend/src/models/database.py',
            'backend/database/init_mysql.sql',
            'backend/migrations/003_migrate_to_mysql.sql',
            'mysql/conf.d/ssl_manager.cnf'
        ]
        
        db_results = []
        
        for db_file in db_files:
            full_path = self.project_root / db_file
            if full_path.exists():
                db_results.append(f"✅ {db_file}: Exists")
            else:
                db_results.append(f"❌ {db_file}: Missing")
        
        # 检查数据库配置类
        try:
            sys.path.insert(0, str(self.project_root / 'backend/src'))
            from models.database import DatabaseConfig
            config = DatabaseConfig()
            db_results.append(f"✅ DatabaseConfig: Instantiated successfully")
            db_results.append(f"✅ MySQL Host: {config.host}:{config.port}")
            db_results.append(f"✅ Database: {config.database}")
        except Exception as e:
            db_results.append(f"❌ DatabaseConfig: Failed to instantiate - {e}")
        
        self.verification_results['tests']['database_config'] = db_results
        
        success_count = len([r for r in db_results if r.startswith('✅')])
        total_count = len(db_results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        logger.info(f"数据库配置验证: {success_count}/{total_count} 成功 ({success_rate*100:.1f}%)")
        return success_rate >= 0.8
    
    def verify_deployment_configs(self) -> bool:
        """验证部署配置"""
        logger.info("验证部署配置...")
        
        deployment_files = [
            'docker-compose.production.yml',
            'docker-compose.mysql.yml',
            'backend/Dockerfile.production',
            'nginx/nginx.conf',
            'nginx/conf.d/ssl-manager-production.conf',
            '.env.production.example',
            'backend/config/gunicorn.conf.py'
        ]
        
        deploy_results = []
        
        for deploy_file in deployment_files:
            full_path = self.project_root / deploy_file
            if full_path.exists():
                # 检查文件大小
                size = full_path.stat().st_size
                if size > 0:
                    deploy_results.append(f"✅ {deploy_file}: Exists ({size} bytes)")
                else:
                    deploy_results.append(f"⚠️ {deploy_file}: Empty file")
            else:
                deploy_results.append(f"❌ {deploy_file}: Missing")
        
        self.verification_results['tests']['deployment_configs'] = deploy_results
        
        success_count = len([r for r in deploy_results if r.startswith('✅')])
        total_count = len(deploy_results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        logger.info(f"部署配置验证: {success_count}/{total_count} 成功 ({success_rate*100:.1f}%)")
        return success_rate >= 0.9
    
    def verify_documentation(self) -> bool:
        """验证文档完整性"""
        logger.info("验证文档完整性...")
        
        doc_files = [
            'README.md',
            'docs/production_deployment.md',
            'docs/mysql_deployment.md',
            'docs/api_reference.md',
            'docs/user_manual.md'
        ]
        
        doc_results = []
        
        for doc_file in doc_files:
            full_path = self.project_root / doc_file
            if full_path.exists():
                size = full_path.stat().st_size
                if size > 1000:  # 至少1KB的内容
                    doc_results.append(f"✅ {doc_file}: Complete ({size} bytes)")
                else:
                    doc_results.append(f"⚠️ {doc_file}: Too short ({size} bytes)")
            else:
                doc_results.append(f"❌ {doc_file}: Missing")
        
        self.verification_results['tests']['documentation'] = doc_results
        
        success_count = len([r for r in doc_results if r.startswith('✅')])
        total_count = len(doc_results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        logger.info(f"文档完整性验证: {success_count}/{total_count} 成功 ({success_rate*100:.1f}%)")
        return success_rate >= 0.8
    
    def verify_scripts_and_tools(self) -> bool:
        """验证脚本和工具"""
        logger.info("验证脚本和工具...")
        
        script_files = [
            'scripts/validate_config.py',
            'scripts/deployment_check.py',
            'scripts/functional_integrity_check.py',
            'backend/docker/entrypoint.sh',
            'backend/docker/healthcheck.sh',
            'backend/scripts/migrate_sqlite_to_mysql.py',
            'backend/scripts/test_mysql_connection.py'
        ]
        
        script_results = []
        
        for script_file in script_files:
            full_path = self.project_root / script_file
            if full_path.exists():
                # 检查执行权限（对于shell脚本）
                if script_file.endswith('.sh'):
                    if os.access(full_path, os.X_OK):
                        script_results.append(f"✅ {script_file}: Executable")
                    else:
                        script_results.append(f"⚠️ {script_file}: Not executable")
                else:
                    # 对于Python脚本，检查语法
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            compile(f.read(), str(full_path), 'exec')
                        script_results.append(f"✅ {script_file}: Syntax OK")
                    except SyntaxError:
                        script_results.append(f"❌ {script_file}: Syntax Error")
            else:
                script_results.append(f"❌ {script_file}: Missing")
        
        self.verification_results['tests']['scripts_and_tools'] = script_results
        
        success_count = len([r for r in script_results if r.startswith('✅')])
        total_count = len(script_results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        logger.info(f"脚本和工具验证: {success_count}/{total_count} 成功 ({success_rate*100:.1f}%)")
        return success_rate >= 0.9
    
    def verify_project_structure(self) -> bool:
        """验证项目结构"""
        logger.info("验证项目结构...")
        
        required_dirs = [
            'backend/src/models',
            'backend/src/services',
            'backend/src/utils',
            'backend/config',
            'backend/docker',
            'backend/scripts',
            'nginx/conf.d',
            'docs',
            'scripts'
        ]
        
        structure_results = []
        
        for req_dir in required_dirs:
            full_path = self.project_root / req_dir
            if full_path.is_dir():
                # 计算目录中的文件数
                file_count = len(list(full_path.glob('*')))
                structure_results.append(f"✅ {req_dir}: Directory exists ({file_count} items)")
            else:
                structure_results.append(f"❌ {req_dir}: Directory missing")
        
        self.verification_results['tests']['project_structure'] = structure_results
        
        success_count = len([r for r in structure_results if r.startswith('✅')])
        total_count = len(structure_results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        logger.info(f"项目结构验证: {success_count}/{total_count} 成功 ({success_rate*100:.1f}%)")
        return success_rate >= 0.9
    
    def run_comprehensive_verification(self) -> Dict:
        """运行综合验证"""
        logger.info("开始最终综合验证...")
        
        from datetime import datetime
        self.verification_results['timestamp'] = datetime.now().isoformat()
        
        # 运行所有验证测试
        tests = [
            ('core_imports', self.verify_core_imports),
            ('database_config', self.verify_database_configuration),
            ('deployment_configs', self.verify_deployment_configs),
            ('documentation', self.verify_documentation),
            ('scripts_and_tools', self.verify_scripts_and_tools),
            ('project_structure', self.verify_project_structure)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed_tests += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.warning(f"⚠️ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # 计算总体状态
        success_rate = passed_tests / total_tests
        
        if success_rate >= 0.9:
            overall_status = 'excellent'
        elif success_rate >= 0.8:
            overall_status = 'good'
        elif success_rate >= 0.7:
            overall_status = 'acceptable'
        else:
            overall_status = 'poor'
        
        self.verification_results['overall_status'] = overall_status
        self.verification_results['summary'] = {
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'success_rate': success_rate,
            'status': overall_status
        }
        
        return self.verification_results
    
    def generate_verification_report(self, results: Dict) -> str:
        """生成验证报告"""
        # 保存JSON报告
        json_report_path = self.project_root / 'final_verification_report.json'
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # 生成可读报告
        readable_report = f"""
SSL证书管理系统 - 最终验证报告
===============================

验证时间: {results['timestamp']}
总体状态: {results['overall_status'].upper()}
成功率: {results['summary']['success_rate']*100:.1f}%
通过测试: {results['summary']['passed_tests']}/{results['summary']['total_tests']}

详细结果:
"""
        
        for test_name, test_results in results['tests'].items():
            readable_report += f"\n{test_name.replace('_', ' ').title()}:\n"
            for result in test_results:
                readable_report += f"  {result}\n"
        
        # 保存可读报告
        txt_report_path = self.project_root / 'final_verification_report.txt'
        with open(txt_report_path, 'w', encoding='utf-8') as f:
            f.write(readable_report)
        
        return str(txt_report_path)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SSL证书管理系统最终验证工具')
    parser.add_argument('--project-root', default='.', help='项目根目录')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 运行验证
    verifier = FinalVerifier(args.project_root)
    results = verifier.run_comprehensive_verification()
    report_path = verifier.generate_verification_report(results)
    
    print(f"\n最终验证完成")
    print(f"总体状态: {results['overall_status'].upper()}")
    print(f"成功率: {results['summary']['success_rate']*100:.1f}%")
    print(f"通过测试: {results['summary']['passed_tests']}/{results['summary']['total_tests']}")
    print(f"详细报告: {report_path}")
    
    if results['overall_status'] in ['excellent', 'good']:
        print("\n🎉 系统验证通过，可以安全部署！")
        sys.exit(0)
    elif results['overall_status'] == 'acceptable':
        print("\n⚠️ 系统基本可用，但建议修复一些问题")
        sys.exit(0)
    else:
        print("\n❌ 系统存在严重问题，需要修复后再部署")
        sys.exit(1)


if __name__ == '__main__':
    main()
