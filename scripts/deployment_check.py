#!/usr/bin/env python3
"""
SSL证书管理系统部署检查脚本
验证生产环境部署的完整性和正确性
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentChecker:
    """部署检查器"""
    
    def __init__(self, project_root: str = '.'):
        """初始化检查器"""
        self.project_root = Path(project_root).resolve()
        self.errors = []
        self.warnings = []
        self.passed_checks = 0
        self.total_checks = 0
    
    def check_file_exists(self, file_path: str, required: bool = True) -> bool:
        """检查文件是否存在"""
        self.total_checks += 1
        full_path = self.project_root / file_path
        
        if full_path.exists():
            logger.info(f"✓ 文件存在: {file_path}")
            self.passed_checks += 1
            return True
        else:
            message = f"文件不存在: {file_path}"
            if required:
                self.errors.append(message)
                logger.error(f"✗ {message}")
            else:
                self.warnings.append(message)
                logger.warning(f"⚠ {message}")
            return False
    
    def check_directory_exists(self, dir_path: str, required: bool = True) -> bool:
        """检查目录是否存在"""
        self.total_checks += 1
        full_path = self.project_root / dir_path
        
        if full_path.is_dir():
            logger.info(f"✓ 目录存在: {dir_path}")
            self.passed_checks += 1
            return True
        else:
            message = f"目录不存在: {dir_path}"
            if required:
                self.errors.append(message)
                logger.error(f"✗ {message}")
            else:
                self.warnings.append(message)
                logger.warning(f"⚠ {message}")
            return False
    
    def check_docker_files(self) -> bool:
        """检查Docker相关文件"""
        logger.info("检查Docker配置文件...")
        
        docker_files = [
            ('docker-compose.production.yml', True),
            ('docker-compose.mysql.yml', True),
            ('backend/Dockerfile.production', True),
            ('backend/docker/entrypoint.sh', True),
            ('backend/docker/healthcheck.sh', True),
            ('frontend/Dockerfile.production', False),
        ]
        
        all_passed = True
        for file_path, required in docker_files:
            if not self.check_file_exists(file_path, required):
                if required:
                    all_passed = False
        
        return all_passed
    
    def check_config_files(self) -> bool:
        """检查配置文件"""
        logger.info("检查配置文件...")
        
        config_files = [
            ('.env.production.example', True),
            ('backend/config/gunicorn.conf.py', True),
            ('backend/requirements.txt', True),
            ('backend/requirements-prod.txt', True),
            ('nginx/nginx.conf', True),
            ('nginx/conf.d/ssl-manager-production.conf', True),
            ('mysql/conf.d/ssl_manager.cnf', True),
        ]
        
        all_passed = True
        for file_path, required in config_files:
            if not self.check_file_exists(file_path, required):
                if required:
                    all_passed = False
        
        return all_passed
    
    def check_database_files(self) -> bool:
        """检查数据库相关文件"""
        logger.info("检查数据库文件...")
        
        db_files = [
            ('backend/database/init_mysql.sql', True),
            ('backend/scripts/test_mysql_connection.py', True),
        ]
        
        all_passed = True
        for file_path, required in db_files:
            if not self.check_file_exists(file_path, required):
                if required:
                    all_passed = False
        
        return all_passed
    
    def check_script_files(self) -> bool:
        """检查脚本文件"""
        logger.info("检查脚本文件...")
        
        script_files = [
            ('scripts/validate_config.py', True),
            ('scripts/deployment_check.py', True),
        ]
        
        all_passed = True
        for file_path, required in script_files:
            if not self.check_file_exists(file_path, required):
                if required:
                    all_passed = False
        
        return all_passed
    
    def check_documentation(self) -> bool:
        """检查文档文件"""
        logger.info("检查文档文件...")
        
        doc_files = [
            ('docs/production_deployment.md', True),
            ('docs/mysql_deployment.md', True),
            ('README.md', False),
        ]
        
        all_passed = True
        for file_path, required in doc_files:
            if not self.check_file_exists(file_path, required):
                if required:
                    all_passed = False
        
        return all_passed
    
    def check_directory_structure(self) -> bool:
        """检查目录结构"""
        logger.info("检查目录结构...")
        
        directories = [
            ('backend/src', True),
            ('backend/config', True),
            ('backend/docker', True),
            ('backend/database', True),
            ('backend/migrations', True),
            ('backend/scripts', True),
            ('nginx/conf.d', True),
            ('mysql/conf.d', True),
            ('scripts', True),
            ('docs', True),
            ('frontend', False),
        ]
        
        all_passed = True
        for dir_path, required in directories:
            if not self.check_directory_exists(dir_path, required):
                if required:
                    all_passed = False
        
        return all_passed
    
    def check_python_syntax(self) -> bool:
        """检查Python文件语法"""
        logger.info("检查Python文件语法...")
        
        python_files = [
            'backend/src/models/database.py',
            'backend/config/gunicorn.conf.py',
            'scripts/validate_config.py',
            'scripts/deployment_check.py',
            'backend/scripts/migrate_sqlite_to_mysql.py',
            'backend/scripts/test_mysql_connection.py',
        ]
        
        all_passed = True
        for file_path in python_files:
            self.total_checks += 1
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
            
            try:
                # 检查语法
                with open(full_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), str(full_path), 'exec')
                
                logger.info(f"✓ Python语法正确: {file_path}")
                self.passed_checks += 1
                
            except SyntaxError as e:
                error_msg = f"Python语法错误 {file_path}: {e}"
                self.errors.append(error_msg)
                logger.error(f"✗ {error_msg}")
                all_passed = False
            except Exception as e:
                error_msg = f"检查Python文件失败 {file_path}: {e}"
                self.warnings.append(error_msg)
                logger.warning(f"⚠ {error_msg}")
        
        return all_passed
    
    def check_shell_scripts(self) -> bool:
        """检查Shell脚本"""
        logger.info("检查Shell脚本...")
        
        shell_scripts = [
            'backend/docker/entrypoint.sh',
            'backend/docker/healthcheck.sh',
        ]
        
        all_passed = True
        for script_path in shell_scripts:
            self.total_checks += 1
            full_path = self.project_root / script_path
            
            if not full_path.exists():
                continue
            
            # 检查是否有执行权限
            if not os.access(full_path, os.X_OK):
                warning_msg = f"Shell脚本缺少执行权限: {script_path}"
                self.warnings.append(warning_msg)
                logger.warning(f"⚠ {warning_msg}")
            else:
                logger.info(f"✓ Shell脚本权限正确: {script_path}")
                self.passed_checks += 1
        
        return all_passed
    
    def check_docker_compose_syntax(self) -> bool:
        """检查Docker Compose文件语法"""
        logger.info("检查Docker Compose文件语法...")
        
        compose_files = [
            'docker-compose.production.yml',
            'docker-compose.mysql.yml',
        ]
        
        all_passed = True
        for compose_file in compose_files:
            self.total_checks += 1
            full_path = self.project_root / compose_file
            
            if not full_path.exists():
                continue
            
            try:
                # 使用docker-compose验证语法
                result = subprocess.run(
                    ['docker-compose', '-f', str(full_path), 'config'],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                if result.returncode == 0:
                    logger.info(f"✓ Docker Compose语法正确: {compose_file}")
                    self.passed_checks += 1
                else:
                    error_msg = f"Docker Compose语法错误 {compose_file}: {result.stderr}"
                    self.errors.append(error_msg)
                    logger.error(f"✗ {error_msg}")
                    all_passed = False
                    
            except FileNotFoundError:
                warning_msg = f"docker-compose命令未找到，跳过语法检查: {compose_file}"
                self.warnings.append(warning_msg)
                logger.warning(f"⚠ {warning_msg}")
            except Exception as e:
                warning_msg = f"检查Docker Compose文件失败 {compose_file}: {e}"
                self.warnings.append(warning_msg)
                logger.warning(f"⚠ {warning_msg}")
        
        return all_passed
    
    def run_all_checks(self) -> bool:
        """运行所有检查"""
        logger.info("开始部署检查...")
        logger.info(f"项目根目录: {self.project_root}")
        
        checks = [
            ("目录结构", self.check_directory_structure),
            ("Docker文件", self.check_docker_files),
            ("配置文件", self.check_config_files),
            ("数据库文件", self.check_database_files),
            ("脚本文件", self.check_script_files),
            ("文档文件", self.check_documentation),
            ("Python语法", self.check_python_syntax),
            ("Shell脚本", self.check_shell_scripts),
            ("Docker Compose语法", self.check_docker_compose_syntax),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            logger.info(f"\n--- {check_name}检查 ---")
            try:
                if not check_func():
                    all_passed = False
            except Exception as e:
                error_msg = f"{check_name}检查失败: {e}"
                self.errors.append(error_msg)
                logger.error(f"✗ {error_msg}")
                all_passed = False
        
        # 输出结果
        self._print_summary()
        
        return all_passed and len(self.errors) == 0
    
    def _print_summary(self):
        """输出检查结果摘要"""
        print("\n" + "="*60)
        print("部署检查结果摘要")
        print("="*60)
        
        print(f"\n📊 检查统计:")
        print(f"  - 总检查项: {self.total_checks}")
        print(f"  - 通过检查: {self.passed_checks}")
        print(f"  - 失败检查: {self.total_checks - self.passed_checks}")
        print(f"  - 成功率: {self.passed_checks/self.total_checks*100:.1f}%" if self.total_checks > 0 else "  - 成功率: 0%")
        
        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  发现 {len(self.warnings)} 个警告:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors and not self.warnings:
            print("\n🎉 所有检查通过！系统已准备好部署。")
        elif not self.errors:
            print("\n✅ 部署检查通过（有警告）")
        else:
            print("\n💥 部署检查失败！请修复错误后重试。")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SSL证书管理系统部署检查工具')
    parser.add_argument('--project-root', default='.', help='项目根目录路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 运行检查
    checker = DeploymentChecker(args.project_root)
    
    if checker.run_all_checks():
        print("\n🚀 部署检查成功！系统可以部署到生产环境。")
        sys.exit(0)
    else:
        print("\n🛑 部署检查失败！请修复问题后重试。")
        sys.exit(1)


if __name__ == '__main__':
    main()
