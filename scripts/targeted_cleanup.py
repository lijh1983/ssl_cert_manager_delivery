#!/usr/bin/env python3
"""
SSL证书管理系统 - 目标清理脚本
基于功能完整性分析结果，执行精确的代码清理
"""

import os
import sys
import json
import shutil
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Set

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TargetedCleaner:
    """目标清理器"""
    
    def __init__(self, project_root: str = '.'):
        """初始化清理器"""
        self.project_root = Path(project_root).resolve()
        
        # 明确要删除的冗余文件
        self.files_to_delete = [
            # 重复的数据库模型文件
            'backend/src/models/database_postgres.py',  # 已迁移到MySQL，PostgreSQL文件冗余
            
            # 重复的部署文档
            'DEPLOYMENT_LOCAL.md',  # 与docs/中的部署文档重复
            'DEPLOYMENT.md',  # 与docs/production_deployment.md重复
            
            # 重复的设计文档
            'DESIGN_DOCUMENT.md',  # 与docs/中的设计文档重复
            'DESIGN_DOCUMENT_DETAILED.md',  # 详细设计文档重复
            'DESIGN_DOCUMENT_ENHANCED.md',  # 增强设计文档重复
            'DESIGN_DOCUMENT_FINAL.md',  # 最终设计文档重复
            'DESIGN_DOCUMENT_UPDATED.md',  # 更新设计文档重复
            
            # 重复的nginx配置
            'frontend/nginx.conf',  # 与nginx/conf.d/中的配置重复
            
            # 临时和备份文件
            'cleanup.log',  # 清理过程产生的临时日志
            'migration.log',  # 迁移过程产生的临时日志
            
            # 未使用的测试文件
            'test_*.py',  # 如果存在未使用的测试文件
            
            # 空的或占位符文件
            'backend/src/utils/__init__.py',  # 如果只是空的__init__.py
        ]
        
        # 要删除的目录模式
        self.dirs_to_clean = [
            '__pycache__',
            '.pytest_cache',
            'node_modules',
            '.coverage',
            'dist',
            'build'
        ]
        
        # 绝对不能删除的核心文件
        self.protected_files = {
            'backend/src/app.py',
            'backend/src/simple_app.py',
            'backend/src/models/database.py',
            'backend/src/models/certificate.py',
            'backend/src/models/user.py',
            'backend/src/models/server.py',
            'backend/src/models/alert.py',
            'backend/src/services/acme_client.py',
            'backend/src/services/certificate_service.py',
            'backend/src/services/monitoring_service.py',
            'backend/requirements.txt',
            'backend/requirements-prod.txt',
            'docker-compose.production.yml',
            'docker-compose.mysql.yml',
            'nginx/nginx.conf',
            'nginx/conf.d/ssl-manager-production.conf',
            'README.md',
            'docs/production_deployment.md',
            'docs/mysql_deployment.md'
        }
    
    def find_redundant_files(self) -> List[Dict]:
        """查找冗余文件"""
        redundant_files = []
        
        # 1. 查找重复的设计文档
        design_docs = []
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if 'DESIGN_DOCUMENT' in file.upper() and file.endswith('.md'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    design_docs.append(str(relative_path))
        
        # 保留最重要的设计文档，删除其他
        if len(design_docs) > 2:
            # 保留README.md和一个主要的设计文档
            essential_docs = ['README.md', 'DESIGN_DOCUMENT.md']
            for doc in design_docs:
                if Path(doc).name not in essential_docs:
                    redundant_files.append({
                        'path': doc,
                        'reason': 'Redundant design document',
                        'type': 'documentation'
                    })
        
        # 2. 查找重复的部署文档
        deployment_docs = []
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if 'DEPLOYMENT' in file.upper() and file.endswith('.md'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    deployment_docs.append(str(relative_path))
        
        # 保留docs/目录下的部署文档，删除根目录的
        for doc in deployment_docs:
            if not doc.startswith('docs/') and doc != 'README.md':
                redundant_files.append({
                    'path': doc,
                    'reason': 'Redundant deployment document (superseded by docs/)',
                    'type': 'documentation'
                })
        
        # 3. 查找过时的数据库文件
        if (self.project_root / 'backend/src/models/database_postgres.py').exists():
            redundant_files.append({
                'path': 'backend/src/models/database_postgres.py',
                'reason': 'PostgreSQL support removed, migrated to MySQL',
                'type': 'code'
            })
        
        # 4. 查找重复的nginx配置
        nginx_configs = []
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.conf') and 'nginx' in root.lower():
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    nginx_configs.append(str(relative_path))
        
        # 如果有多个nginx配置，保留主要的
        if len(nginx_configs) > 2:
            essential_nginx = ['nginx/nginx.conf', 'nginx/conf.d/ssl-manager-production.conf']
            for config in nginx_configs:
                if config not in essential_nginx:
                    redundant_files.append({
                        'path': config,
                        'reason': 'Redundant nginx configuration',
                        'type': 'configuration'
                    })
        
        return redundant_files
    
    def find_cache_and_temp_files(self) -> List[Dict]:
        """查找缓存和临时文件"""
        temp_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # 删除缓存目录
            dirs_to_remove = []
            for dir_name in dirs:
                if dir_name in self.dirs_to_clean:
                    dir_path = Path(root) / dir_name
                    relative_path = dir_path.relative_to(self.project_root)
                    temp_files.append({
                        'path': str(relative_path),
                        'reason': f'Cache/temporary directory: {dir_name}',
                        'type': 'cache'
                    })
                    dirs_to_remove.append(dir_name)
            
            # 从dirs列表中移除，避免遍历
            for dir_name in dirs_to_remove:
                dirs.remove(dir_name)
            
            # 查找临时文件
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)
                
                # 跳过隐藏文件
                if file.startswith('.'):
                    continue
                
                # 查找特定的临时文件
                if (file.endswith('.log') and file in ['cleanup.log', 'migration.log'] or
                    file.endswith('.tmp') or
                    file.endswith('.bak') or
                    file.endswith('.old') or
                    file.endswith('~')):
                    temp_files.append({
                        'path': str(relative_path),
                        'reason': f'Temporary/log file: {file}',
                        'type': 'temporary'
                    })
        
        return temp_files
    
    def find_empty_files(self) -> List[Dict]:
        """查找空文件"""
        empty_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)
                
                # 跳过受保护的文件
                if str(relative_path) in self.protected_files:
                    continue
                
                try:
                    # 检查文件大小
                    if file_path.stat().st_size == 0:
                        # 特殊处理__init__.py文件
                        if file == '__init__.py':
                            # 检查是否真的需要这个__init__.py
                            parent_dir = file_path.parent
                            py_files = list(parent_dir.glob('*.py'))
                            if len(py_files) <= 1:  # 只有__init__.py本身
                                empty_files.append({
                                    'path': str(relative_path),
                                    'reason': 'Empty __init__.py in directory with no other Python files',
                                    'type': 'empty'
                                })
                        else:
                            empty_files.append({
                                'path': str(relative_path),
                                'reason': 'Empty file',
                                'type': 'empty'
                            })
                except OSError:
                    continue
        
        return empty_files
    
    def create_cleanup_plan(self) -> Dict:
        """创建清理计划"""
        logger.info("创建清理计划...")
        
        plan = {
            'redundant_files': self.find_redundant_files(),
            'cache_and_temp': self.find_cache_and_temp_files(),
            'empty_files': self.find_empty_files(),
            'protected_files': list(self.protected_files),
            'summary': {}
        }
        
        # 合并所有要删除的文件
        all_files_to_delete = []
        all_files_to_delete.extend(plan['redundant_files'])
        all_files_to_delete.extend(plan['cache_and_temp'])
        all_files_to_delete.extend(plan['empty_files'])
        
        # 安全检查 - 确保受保护的文件不被删除
        safe_files_to_delete = []
        for file_info in all_files_to_delete:
            if file_info['path'] not in self.protected_files:
                safe_files_to_delete.append(file_info)
            else:
                logger.warning(f"Protected file skipped: {file_info['path']}")
        
        plan['files_to_delete'] = safe_files_to_delete
        plan['summary'] = {
            'total_files': len(safe_files_to_delete),
            'redundant_count': len(plan['redundant_files']),
            'cache_temp_count': len(plan['cache_and_temp']),
            'empty_count': len(plan['empty_files']),
            'protected_count': len(self.protected_files)
        }
        
        return plan
    
    def execute_cleanup(self, plan: Dict, dry_run: bool = True) -> bool:
        """执行清理"""
        logger.info(f"执行清理 (dry_run={dry_run})...")
        
        success_count = 0
        error_count = 0
        
        for file_info in plan['files_to_delete']:
            file_path = self.project_root / file_info['path']
            
            try:
                if file_path.exists():
                    if not dry_run:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                    
                    logger.info(f"{'[DRY RUN] ' if dry_run else ''}删除: {file_info['path']} - {file_info['reason']}")
                    success_count += 1
                else:
                    logger.debug(f"文件不存在: {file_info['path']}")
            
            except Exception as e:
                logger.error(f"删除失败 {file_info['path']}: {e}")
                error_count += 1
        
        logger.info(f"清理完成: 成功 {success_count}, 失败 {error_count}")
        return error_count == 0
    
    def generate_report(self, plan: Dict, executed: bool = False) -> str:
        """生成清理报告"""
        timestamp = datetime.datetime.now().isoformat()
        
        report = {
            'timestamp': timestamp,
            'executed': executed,
            'plan': plan
        }
        
        # 保存JSON报告
        json_report_path = self.project_root / 'targeted_cleanup_report.json'
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 生成可读报告
        readable_report = f"""
SSL证书管理系统 - 目标清理报告
===============================

清理时间: {timestamp}
执行状态: {'已执行' if executed else '计划中'}

清理统计:
- 总文件数: {plan['summary']['total_files']}
- 冗余文件: {plan['summary']['redundant_count']}
- 缓存/临时文件: {plan['summary']['cache_temp_count']}
- 空文件: {plan['summary']['empty_count']}
- 受保护文件: {plan['summary']['protected_count']}

清理详情:
"""
        
        # 按类型分组显示
        for category, files in [
            ('冗余文件', plan['redundant_files']),
            ('缓存和临时文件', plan['cache_and_temp']),
            ('空文件', plan['empty_files'])
        ]:
            if files:
                readable_report += f"\n{category}:\n"
                for file_info in files:
                    readable_report += f"  - {file_info['path']} ({file_info['reason']})\n"
        
        readable_report += f"\n受保护的核心文件 (共{len(plan['protected_files'])}个):\n"
        for protected_file in sorted(plan['protected_files'])[:10]:  # 只显示前10个
            readable_report += f"  - {protected_file}\n"
        
        if len(plan['protected_files']) > 10:
            readable_report += f"  ... 还有 {len(plan['protected_files']) - 10} 个文件\n"
        
        # 保存可读报告
        txt_report_path = self.project_root / 'targeted_cleanup_report.txt'
        with open(txt_report_path, 'w', encoding='utf-8') as f:
            f.write(readable_report)
        
        return str(txt_report_path)
    
    def run_targeted_cleanup(self, dry_run: bool = True) -> bool:
        """运行目标清理"""
        logger.info("开始目标清理...")
        
        try:
            # 创建清理计划
            plan = self.create_cleanup_plan()
            
            # 生成计划报告
            report_path = self.generate_report(plan, executed=False)
            logger.info(f"清理计划已生成: {report_path}")
            
            # 执行清理
            success = self.execute_cleanup(plan, dry_run)
            
            # 生成执行报告
            if not dry_run:
                final_report_path = self.generate_report(plan, executed=True)
                logger.info(f"清理执行报告: {final_report_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"目标清理失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SSL证书管理系统目标清理工具')
    parser.add_argument('--project-root', default='.', help='项目根目录')
    parser.add_argument('--dry-run', action='store_true', help='试运行，不实际删除文件')
    parser.add_argument('--execute', action='store_true', help='实际执行清理（危险操作）')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 安全检查
    if args.execute and args.dry_run:
        print("错误: --execute 和 --dry-run 不能同时使用")
        sys.exit(1)
    
    if args.execute:
        response = input("⚠️  您确定要执行实际的文件删除操作吗？这个操作不可逆！(yes/no): ")
        if response.lower() != 'yes':
            print("操作已取消")
            sys.exit(0)
    
    # 运行清理
    cleaner = TargetedCleaner(args.project_root)
    
    dry_run = not args.execute
    if cleaner.run_targeted_cleanup(dry_run=dry_run):
        if dry_run:
            print("\n✅ 清理计划生成成功！请查看报告文件。")
            print("如需实际执行清理，请使用 --execute 参数")
        else:
            print("\n🎉 目标清理执行成功！")
        sys.exit(0)
    else:
        print("\n💥 目标清理失败！")
        sys.exit(1)


if __name__ == '__main__':
    main()
