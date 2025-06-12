#!/usr/bin/env python3
"""
SSL证书管理系统 - 代码清理和优化脚本
全面分析项目结构，识别并清理冗余文件，优化项目组织结构
"""

import os
import sys
import json
import shutil
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProjectCleaner:
    """项目清理器"""
    
    def __init__(self, project_root: str = '.'):
        """初始化清理器"""
        self.project_root = Path(project_root).resolve()
        self.cleanup_report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'deleted_files': [],
            'kept_files': [],
            'analysis': {},
            'warnings': [],
            'errors': []
        }
        
        # 定义文件类型和模式
        self.config_extensions = {'.yml', '.yaml', '.json', '.toml', '.ini', '.conf'}
        self.script_extensions = {'.sh', '.bat', '.ps1'}
        self.doc_extensions = {'.md', '.txt', '.rst'}
        self.docker_patterns = {'Dockerfile', 'docker-compose'}
        self.temp_patterns = {'.bak', '.tmp', '.old', '~', '.swp', '.swo'}
        
        # 核心功能文件（不能删除）
        self.core_files = {
            'backend/src/app.py',
            'backend/src/models/database.py',
            'backend/src/models/certificate.py',
            'backend/src/models/user.py',
            'backend/src/models/server.py',
            'backend/src/models/alert.py',
            'backend/src/routes/auth.py',
            'backend/src/routes/certificates.py',
            'backend/src/routes/monitoring.py',
            'backend/src/utils/cert_utils.py',
            'backend/src/utils/acme_client.py',
            'frontend/src/main.ts',
            'frontend/src/App.vue',
            'frontend/package.json',
            'backend/requirements.txt',
            'README.md'
        }
        
        # 生产环境必需文件
        self.production_files = {
            'docker-compose.production.yml',
            'docker-compose.mysql.yml',
            '.env.production.example',
            'nginx/nginx.conf',
            'nginx/conf.d/ssl-manager-production.conf',
            'backend/Dockerfile.production',
            'backend/config/gunicorn.conf.py',
            'docs/production_deployment.md',
            'docs/mysql_deployment.md'
        }
    
    def analyze_project_structure(self) -> Dict:
        """分析项目结构"""
        logger.info("分析项目结构...")
        
        analysis = {
            'total_files': 0,
            'file_types': defaultdict(int),
            'directories': [],
            'duplicates': [],
            'empty_files': [],
            'large_files': [],
            'potential_redundant': []
        }
        
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            relative_root = root_path.relative_to(self.project_root)
            
            # 跳过隐藏目录和常见的忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', '__pycache__', '.git', '.vscode', '.idea',
                'dist', 'build', 'target', 'coverage'
            }]
            
            analysis['directories'].append(str(relative_root))
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = root_path / file
                relative_path = file_path.relative_to(self.project_root)
                
                analysis['total_files'] += 1
                
                # 文件类型统计
                suffix = file_path.suffix.lower()
                analysis['file_types'][suffix] += 1
                
                # 检查空文件
                try:
                    if file_path.stat().st_size == 0:
                        analysis['empty_files'].append(str(relative_path))
                except OSError:
                    continue
                
                # 检查大文件（>10MB）
                try:
                    if file_path.stat().st_size > 10 * 1024 * 1024:
                        analysis['large_files'].append({
                            'path': str(relative_path),
                            'size': file_path.stat().st_size
                        })
                except OSError:
                    continue
        
        # 转换defaultdict为普通dict以便JSON序列化
        analysis['file_types'] = dict(analysis['file_types'])
        self.cleanup_report['analysis'] = analysis
        return analysis
    
    def find_duplicate_files(self) -> List[Tuple[str, List[str]]]:
        """查找重复文件"""
        logger.info("查找重复文件...")
        
        file_contents = defaultdict(list)
        
        for root, dirs, files in os.walk(self.project_root):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)
                
                try:
                    # 对于小文件，比较内容
                    if file_path.stat().st_size < 1024 * 1024:  # 1MB以下
                        with open(file_path, 'rb') as f:
                            content_hash = hash(f.read())
                        file_contents[content_hash].append(str(relative_path))
                except (OSError, UnicodeDecodeError):
                    continue
        
        # 找出重复的文件
        duplicates = []
        for content_hash, paths in file_contents.items():
            if len(paths) > 1:
                duplicates.append((content_hash, paths))
        
        return duplicates
    
    def identify_redundant_docker_files(self) -> List[str]:
        """识别冗余的Docker文件"""
        logger.info("识别冗余的Docker文件...")
        
        docker_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)
                
                if (file.startswith('Dockerfile') or 
                    file.startswith('docker-compose') or
                    file.endswith('.dockerfile')):
                    docker_files.append(str(relative_path))
        
        # 分析哪些是冗余的
        redundant = []
        
        # 检查多个docker-compose文件
        compose_files = [f for f in docker_files if 'docker-compose' in f]
        
        # 保留生产环境和MySQL配置，其他可能冗余
        essential_compose = {
            'docker-compose.production.yml',
            'docker-compose.mysql.yml',
            'docker-compose.yml'  # 开发环境主文件
        }
        
        for compose_file in compose_files:
            if Path(compose_file).name not in essential_compose:
                redundant.append(compose_file)
        
        # 检查多个Dockerfile
        dockerfile_files = [f for f in docker_files if 'Dockerfile' in f and 'docker-compose' not in f]
        
        # 保留生产环境Dockerfile
        essential_dockerfiles = {
            'backend/Dockerfile.production',
            'backend/Dockerfile',
            'frontend/Dockerfile'
        }
        
        for dockerfile in dockerfile_files:
            if dockerfile not in essential_dockerfiles:
                redundant.append(dockerfile)
        
        return redundant
    
    def identify_redundant_docs(self) -> List[str]:
        """识别冗余的文档文件"""
        logger.info("识别冗余的文档文件...")
        
        doc_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if any(file.endswith(ext) for ext in self.doc_extensions):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    doc_files.append(str(relative_path))
        
        # 分析文档重复性
        redundant = []
        
        # 检查根目录下的多个部署文档
        root_docs = [f for f in doc_files if '/' not in f]
        deployment_docs = [f for f in root_docs if 'DEPLOYMENT' in f.upper()]
        
        # 保留主要的部署文档，移除重复的
        if len(deployment_docs) > 2:
            # 保留最重要的两个
            essential_deployment = ['DEPLOYMENT.md', 'DEPLOYMENT_LOCAL.md']
            for doc in deployment_docs:
                if doc not in essential_deployment:
                    redundant.append(doc)
        
        # 检查设计文档的重复
        design_docs = [f for f in doc_files if 'design' in f.lower()]
        if len(design_docs) > 3:
            # 可能有重复的设计文档
            for doc in design_docs[3:]:
                redundant.append(doc)
        
        return redundant
    
    def identify_redundant_configs(self) -> List[str]:
        """识别冗余的配置文件"""
        logger.info("识别冗余的配置文件...")
        
        config_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if any(file.endswith(ext) for ext in self.config_extensions):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    config_files.append(str(relative_path))
        
        redundant = []
        
        # 检查nginx配置重复
        nginx_configs = [f for f in config_files if 'nginx' in f and f.endswith('.conf')]
        if len(nginx_configs) > 3:
            # 保留主要的nginx配置
            essential_nginx = [
                'nginx/nginx.conf',
                'nginx/conf.d/ssl-manager-production.conf',
                'frontend/nginx.conf'
            ]
            for config in nginx_configs:
                if config not in essential_nginx:
                    redundant.append(config)
        
        return redundant
    
    def check_file_dependencies(self, file_path: str) -> List[str]:
        """检查文件依赖关系"""
        dependencies = []
        
        try:
            full_path = self.project_root / file_path
            
            if full_path.suffix in {'.py', '.js', '.ts', '.vue'}:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单的依赖检查
                if 'import' in content or 'require' in content:
                    dependencies.append('has_imports')
                
                if 'export' in content or 'module.exports' in content:
                    dependencies.append('exports_symbols')
            
            elif full_path.suffix in {'.yml', '.yaml'}:
                # Docker compose或其他YAML配置
                if 'docker-compose' in file_path:
                    dependencies.append('docker_orchestration')
                
            elif 'Dockerfile' in file_path:
                dependencies.append('docker_build')
        
        except (OSError, UnicodeDecodeError):
            pass
        
        return dependencies
    
    def create_cleanup_plan(self) -> Dict:
        """创建清理计划"""
        logger.info("创建清理计划...")
        
        plan = {
            'to_delete': [],
            'to_keep': [],
            'warnings': []
        }
        
        # 1. 查找重复文件
        duplicates = self.find_duplicate_files()
        for content_hash, paths in duplicates:
            if len(paths) > 1:
                # 保留第一个，删除其他
                plan['to_keep'].append(paths[0])
                for duplicate in paths[1:]:
                    plan['to_delete'].append({
                        'path': duplicate,
                        'reason': f'Duplicate of {paths[0]}'
                    })
        
        # 2. 识别冗余的Docker文件
        redundant_docker = self.identify_redundant_docker_files()
        for docker_file in redundant_docker:
            plan['to_delete'].append({
                'path': docker_file,
                'reason': 'Redundant Docker configuration'
            })
        
        # 3. 识别冗余的文档
        redundant_docs = self.identify_redundant_docs()
        for doc_file in redundant_docs:
            plan['to_delete'].append({
                'path': doc_file,
                'reason': 'Redundant documentation'
            })
        
        # 4. 识别冗余的配置
        redundant_configs = self.identify_redundant_configs()
        for config_file in redundant_configs:
            plan['to_delete'].append({
                'path': config_file,
                'reason': 'Redundant configuration'
            })
        
        # 5. 检查空文件
        analysis = self.cleanup_report.get('analysis', {})
        for empty_file in analysis.get('empty_files', []):
            if empty_file not in self.core_files and empty_file not in self.production_files:
                plan['to_delete'].append({
                    'path': empty_file,
                    'reason': 'Empty file'
                })
        
        # 6. 安全检查 - 确保核心文件不被删除
        files_to_delete = [item['path'] for item in plan['to_delete']]
        for core_file in self.core_files:
            if core_file in files_to_delete:
                plan['warnings'].append(f'Core file marked for deletion: {core_file}')
                # 从删除列表中移除
                plan['to_delete'] = [item for item in plan['to_delete'] if item['path'] != core_file]
        
        for prod_file in self.production_files:
            if prod_file in files_to_delete:
                plan['warnings'].append(f'Production file marked for deletion: {prod_file}')
                # 从删除列表中移除
                plan['to_delete'] = [item for item in plan['to_delete'] if item['path'] != prod_file]
        
        return plan
    
    def execute_cleanup(self, plan: Dict, dry_run: bool = True) -> bool:
        """执行清理计划"""
        logger.info(f"执行清理计划 (dry_run={dry_run})...")
        
        if dry_run:
            logger.info("这是一次试运行，不会实际删除文件")
        
        success_count = 0
        error_count = 0
        
        for item in plan['to_delete']:
            file_path = self.project_root / item['path']
            
            try:
                if file_path.exists():
                    if not dry_run:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                    
                    logger.info(f"{'[DRY RUN] ' if dry_run else ''}删除: {item['path']} - {item['reason']}")
                    self.cleanup_report['deleted_files'].append(item)
                    success_count += 1
                else:
                    logger.warning(f"文件不存在: {item['path']}")
            
            except Exception as e:
                logger.error(f"删除文件失败 {item['path']}: {e}")
                self.cleanup_report['errors'].append(f"Failed to delete {item['path']}: {e}")
                error_count += 1
        
        logger.info(f"清理完成: 成功 {success_count}, 失败 {error_count}")
        return error_count == 0
    
    def generate_report(self) -> str:
        """生成清理报告"""
        report_path = self.project_root / 'cleanup_report.json'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.cleanup_report, f, indent=2, ensure_ascii=False)
        
        # 生成可读的报告
        readable_report = f"""
SSL证书管理系统 - 代码清理报告
=====================================

清理时间: {self.cleanup_report['timestamp']}

项目分析结果:
- 总文件数: {self.cleanup_report['analysis'].get('total_files', 0)}
- 删除文件数: {len(self.cleanup_report['deleted_files'])}
- 保留文件数: {len(self.cleanup_report['kept_files'])}

删除的文件:
"""
        
        for item in self.cleanup_report['deleted_files']:
            readable_report += f"  - {item['path']} ({item['reason']})\n"
        
        if self.cleanup_report['warnings']:
            readable_report += "\n警告:\n"
            for warning in self.cleanup_report['warnings']:
                readable_report += f"  - {warning}\n"
        
        if self.cleanup_report['errors']:
            readable_report += "\n错误:\n"
            for error in self.cleanup_report['errors']:
                readable_report += f"  - {error}\n"
        
        readable_report_path = self.project_root / 'cleanup_report.txt'
        with open(readable_report_path, 'w', encoding='utf-8') as f:
            f.write(readable_report)
        
        return str(readable_report_path)
    
    def run_cleanup(self, dry_run: bool = True) -> bool:
        """运行完整的清理流程"""
        logger.info("开始代码清理流程...")
        
        try:
            # 1. 分析项目结构
            self.analyze_project_structure()
            
            # 2. 创建清理计划
            plan = self.create_cleanup_plan()
            
            # 3. 执行清理
            success = self.execute_cleanup(plan, dry_run)
            
            # 4. 生成报告
            report_path = self.generate_report()
            
            logger.info(f"清理完成，报告已生成: {report_path}")
            return success
            
        except Exception as e:
            logger.error(f"清理过程中发生错误: {e}")
            self.cleanup_report['errors'].append(str(e))
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SSL证书管理系统代码清理工具')
    parser.add_argument('--project-root', default='.', help='项目根目录')
    parser.add_argument('--dry-run', action='store_true', help='试运行，不实际删除文件')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 运行清理
    cleaner = ProjectCleaner(args.project_root)
    
    if cleaner.run_cleanup(dry_run=args.dry_run):
        print("\n🎉 代码清理成功完成！")
        sys.exit(0)
    else:
        print("\n💥 代码清理过程中出现错误！")
        sys.exit(1)


if __name__ == '__main__':
    main()
