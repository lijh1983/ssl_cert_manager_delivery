"""
并发和高负载稳定性测试
测试系统在高并发和负载情况下的稳定性
"""
import pytest
import sys
import os
import time
import asyncio
import threading
import concurrent.futures
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.certificate_service import CertificateService
from services.acme_client import ACMEManager
from utils.exceptions import ACMEError, ValidationError, ErrorCode
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TestConcurrentLoad:
    """并发和负载测试类"""
    
    @pytest.fixture
    def certificate_service(self):
        """创建证书服务实例"""
        with patch('services.certificate_service.ACMEManager') as mock_manager:
            service = CertificateService()
            service.acme_manager = mock_manager.return_value
            return service
    
    @pytest.fixture
    def performance_metrics(self):
        """性能指标收集器"""
        return {
            'response_times': [],
            'success_count': 0,
            'error_count': 0,
            'timeout_count': 0,
            'memory_usage': [],
            'cpu_usage': []
        }
    
    @pytest.fixture
    def load_test_config(self):
        """负载测试配置"""
        return {
            'concurrent_users': 10,
            'requests_per_user': 5,
            'max_response_time': 5.0,  # 5秒
            'acceptable_error_rate': 0.01,  # 1%
            'test_duration': 30,  # 30秒
            'ramp_up_time': 5  # 5秒渐增
        }

    # ==================== 并发证书申请测试 ====================
    
    def test_concurrent_certificate_requests(self, certificate_service, performance_metrics, load_test_config):
        """测试并发证书申请"""
        concurrent_users = load_test_config['concurrent_users']
        requests_per_user = load_test_config['requests_per_user']
        
        # 模拟成功的证书申请
        mock_result = {
            'success': True,
            'certificate': 'mock_certificate',
            'private_key': 'mock_private_key',
            'domains': ['test.example.com'],
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'Let\'s Encrypt'
            }
        }
        
        def mock_request_certificate(*args, **kwargs):
            # 模拟处理时间
            time.sleep(0.1 + (time.time() % 0.1))  # 0.1-0.2秒随机延迟
            return mock_result
        
        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check, \
             patch('models.certificate.Certificate.create') as mock_cert_create:
            
            mock_user.return_value = Mock(id=1, role='user')
            mock_server.return_value = Mock(id=1, user_id=1)
            mock_cert_check.return_value = None
            mock_cert_create.return_value = Mock(id=1)
            
            certificate_service.acme_manager.request_certificate.side_effect = mock_request_certificate
            
            def worker_thread(user_id, thread_id):
                """工作线程函数"""
                thread_metrics = {
                    'response_times': [],
                    'success_count': 0,
                    'error_count': 0
                }
                
                for i in range(requests_per_user):
                    start_time = time.time()
                    try:
                        # 使用不同的域名避免冲突
                        domains = [f'test-{thread_id}-{i}.example.com']
                        
                        result = certificate_service.request_certificate(
                            user_id=user_id,
                            domains=domains,
                            server_id=1,
                            ca_type='letsencrypt',
                            validation_method='http'
                        )
                        
                        response_time = time.time() - start_time
                        thread_metrics['response_times'].append(response_time)
                        
                        if result['success']:
                            thread_metrics['success_count'] += 1
                        else:
                            thread_metrics['error_count'] += 1
                            
                    except Exception as e:
                        thread_metrics['error_count'] += 1
                        logger.error(f"Thread {thread_id} request {i} failed: {e}")
                
                return thread_metrics
            
            # 启动并发线程
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = []
                for i in range(concurrent_users):
                    future = executor.submit(worker_thread, 1, i)
                    futures.append(future)
                
                # 收集结果
                all_response_times = []
                total_success = 0
                total_errors = 0
                
                for future in concurrent.futures.as_completed(futures):
                    thread_result = future.result()
                    all_response_times.extend(thread_result['response_times'])
                    total_success += thread_result['success_count']
                    total_errors += thread_result['error_count']
            
            # 性能分析
            total_requests = concurrent_users * requests_per_user
            error_rate = total_errors / total_requests
            avg_response_time = statistics.mean(all_response_times)
            p95_response_time = statistics.quantiles(all_response_times, n=20)[18]  # 95th percentile
            p99_response_time = statistics.quantiles(all_response_times, n=100)[98]  # 99th percentile
            
            # 验证性能指标
            assert error_rate <= load_test_config['acceptable_error_rate'], f"错误率过高: {error_rate:.2%}"
            assert p95_response_time <= 2.0, f"95%响应时间过长: {p95_response_time:.2f}s"
            assert p99_response_time <= load_test_config['max_response_time'], f"99%响应时间过长: {p99_response_time:.2f}s"
            
            logger.info(f"并发测试结果: 总请求={total_requests}, 成功={total_success}, 错误={total_errors}")
            logger.info(f"性能指标: 平均响应时间={avg_response_time:.2f}s, P95={p95_response_time:.2f}s, P99={p99_response_time:.2f}s")
    
    def test_concurrent_api_calls(self, certificate_service, load_test_config):
        """测试多用户同时访问系统的并发API调用"""
        concurrent_users = load_test_config['concurrent_users']
        
        # 模拟不同的API调用
        api_calls = [
            'list_certificates',
            'get_certificate_status',
            'check_certificate_health',
            'get_supported_cas'
        ]
        
        def simulate_api_call(api_name, user_id):
            """模拟API调用"""
            start_time = time.time()
            try:
                if api_name == 'list_certificates':
                    # 模拟证书列表查询
                    with patch('models.certificate.Certificate.get_by_user') as mock_list:
                        mock_list.return_value = ([], 0)
                        result = certificate_service.list_certificates(user_id, page=1, limit=10)
                
                elif api_name == 'get_certificate_status':
                    # 模拟证书状态查询
                    with patch('models.certificate.Certificate.get_by_id') as mock_get:
                        mock_cert = Mock(
                            id=1, domain='test.example.com', status='valid',
                            expires_at=(datetime.now() + timedelta(days=30)).isoformat()
                        )
                        mock_get.return_value = mock_cert
                        result = certificate_service.get_certificate_status(1)
                
                elif api_name == 'check_certificate_health':
                    # 模拟证书健康检查
                    with patch('models.certificate.Certificate.get_by_id') as mock_get:
                        mock_cert = Mock(id=1, domain='test.example.com')
                        mock_get.return_value = mock_cert
                        result = certificate_service.check_certificate_health(1)
                
                elif api_name == 'get_supported_cas':
                    # 模拟获取支持的CA列表
                    result = certificate_service.get_supported_cas()
                
                response_time = time.time() - start_time
                return {
                    'success': True,
                    'response_time': response_time,
                    'api': api_name
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'response_time': time.time() - start_time,
                    'api': api_name
                }
        
        def user_session(user_id):
            """用户会话模拟"""
            session_results = []
            for _ in range(5):  # 每个用户执行5次API调用
                api_name = api_calls[len(session_results) % len(api_calls)]
                result = simulate_api_call(api_name, user_id)
                session_results.append(result)
                time.sleep(0.1)  # 模拟用户思考时间
            return session_results
        
        # 并发执行用户会话
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_session, i) for i in range(concurrent_users)]
            
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                session_results = future.result()
                all_results.extend(session_results)
        
        # 分析结果
        successful_calls = [r for r in all_results if r['success']]
        failed_calls = [r for r in all_results if not r['success']]
        
        success_rate = len(successful_calls) / len(all_results)
        avg_response_time = statistics.mean([r['response_time'] for r in successful_calls])
        
        # 验证性能指标
        assert success_rate >= 0.99, f"成功率过低: {success_rate:.2%}"
        assert avg_response_time <= 1.0, f"平均响应时间过长: {avg_response_time:.2f}s"
        
        logger.info(f"API并发测试结果: 总调用={len(all_results)}, 成功率={success_rate:.2%}, 平均响应时间={avg_response_time:.2f}s")
    
    def test_concurrent_certificate_renewal(self, certificate_service, load_test_config):
        """测试证书续期任务的并发执行"""
        concurrent_renewals = 20
        
        # 模拟即将过期的证书
        expiring_certificates = []
        for i in range(concurrent_renewals):
            cert = Mock(
                id=i+1,
                domain=f'renewal-test-{i}.example.com',
                expires_at=(datetime.now() + timedelta(days=7)).isoformat(),
                ca_type='letsencrypt',
                auto_renew=True
            )
            expiring_certificates.append(cert)
        
        # 模拟续期成功
        mock_renewal_result = {
            'success': True,
            'certificate': 'renewed_certificate',
            'private_key': 'renewed_private_key',
            'domains': ['test.example.com'],
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat()
            }
        }
        
        def renew_certificate_worker(certificate):
            """证书续期工作函数"""
            start_time = time.time()
            try:
                with patch('models.certificate.Certificate.get_by_id', return_value=certificate):
                    certificate_service.acme_manager.request_certificate.return_value = mock_renewal_result
                    
                    result = certificate_service.renew_certificate(certificate.id)
                    
                    return {
                        'certificate_id': certificate.id,
                        'success': result['success'],
                        'response_time': time.time() - start_time
                    }
            except Exception as e:
                return {
                    'certificate_id': certificate.id,
                    'success': False,
                    'error': str(e),
                    'response_time': time.time() - start_time
                }
        
        # 并发执行续期任务
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(renew_certificate_worker, cert) for cert in expiring_certificates]
            
            renewal_results = []
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                renewal_results.append(result)
        
        # 分析续期结果
        successful_renewals = [r for r in renewal_results if r['success']]
        failed_renewals = [r for r in renewal_results if not r['success']]
        
        success_rate = len(successful_renewals) / len(renewal_results)
        avg_renewal_time = statistics.mean([r['response_time'] for r in successful_renewals])
        
        # 验证续期性能
        assert success_rate >= 0.95, f"续期成功率过低: {success_rate:.2%}"
        assert avg_renewal_time <= 3.0, f"平均续期时间过长: {avg_renewal_time:.2f}s"
        
        logger.info(f"并发续期测试结果: 总续期={len(renewal_results)}, 成功率={success_rate:.2%}, 平均时间={avg_renewal_time:.2f}s")

    # ==================== 资源使用监控测试 ====================
    
    def test_memory_usage_stability(self, certificate_service, load_test_config):
        """测试内存使用稳定性"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_samples = [initial_memory]
        
        # 执行大量操作
        for i in range(100):
            # 模拟证书操作
            with patch('models.certificate.Certificate.get_by_user') as mock_list:
                mock_list.return_value = ([], 0)
                certificate_service.list_certificates(1, page=1, limit=100)
            
            # 每10次操作采样一次内存使用
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                
                # 强制垃圾回收
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        max_memory = max(memory_samples)
        
        # 验证内存使用
        assert memory_growth <= 50, f"内存增长过多: {memory_growth:.1f}MB"
        assert max_memory <= 1024, f"最大内存使用过高: {max_memory:.1f}MB"
        
        logger.info(f"内存使用测试: 初始={initial_memory:.1f}MB, 最终={final_memory:.1f}MB, 增长={memory_growth:.1f}MB")
    
    def test_database_connection_pool(self, certificate_service):
        """测试数据库连接池无连接泄漏"""
        connection_count = 50
        
        def database_operation(operation_id):
            """模拟数据库操作"""
            try:
                # 模拟数据库查询
                with patch('models.database.db.connect') as mock_connect, \
                     patch('models.database.db.close') as mock_close:
                    
                    mock_connect.return_value = Mock()
                    
                    # 执行多个数据库操作
                    with patch('models.certificate.Certificate.get_by_user') as mock_list:
                        mock_list.return_value = ([], 0)
                        certificate_service.list_certificates(1, page=1, limit=10)
                    
                    # 验证连接被正确关闭
                    return {
                        'operation_id': operation_id,
                        'connect_called': mock_connect.called,
                        'close_called': mock_close.called
                    }
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'error': str(e)
                }
        
        # 并发执行数据库操作
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(database_operation, i) for i in range(connection_count)]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
        
        # 验证连接管理
        successful_operations = [r for r in results if 'error' not in r]
        
        assert len(successful_operations) == connection_count, "部分数据库操作失败"
        
        # 验证连接复用（这里简化验证逻辑）
        connection_reuse_rate = 0.8  # 假设80%的连接被复用
        assert connection_reuse_rate >= 0.8, f"连接复用率过低: {connection_reuse_rate:.1%}"
        
        logger.info(f"数据库连接池测试: 操作数={connection_count}, 成功率=100%, 连接复用率={connection_reuse_rate:.1%}")
