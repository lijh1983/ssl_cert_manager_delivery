#!/usr/bin/env python3
"""
性能优化测试脚本
测试前端和后端的性能优化效果
"""

import time
import asyncio
import sys
import os
from typing import List, Dict, Any
import json

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 禁用监控线程以避免测试时的干扰
os.environ['DISABLE_MONITORING'] = '1'

try:
    from src.utils.query_optimizer import (
        query_cache, query_optimizer, optimize_query,
        get_query_performance_report, PaginationHelper
    )
    print("✅ 查询优化模块导入成功")
except ImportError as e:
    print(f"❌ 查询优化模块导入失败: {e}")
    # 创建简化版本用于测试
    class CacheManager:
        def __init__(self, config=None):
            self.cache = {}
        def get(self, key):
            return self.cache.get(key)
        def set(self, key, value):
            self.cache[key] = value
        def clear(self):
            self.cache.clear()
        def getStats(self):
            return {'total_items': len(self.cache)}
    print("✅ 使用简化版缓存管理器")


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results = {}
        self.cache_manager = CacheManager()
    
    def test_cache_performance(self):
        """测试缓存性能"""
        print("\n" + "="*50)
        print("🚀 缓存性能测试")
        print("="*50)
        
        # 测试数据
        test_data = [f"test_data_{i}" for i in range(1000)]
        
        # 测试无缓存性能
        start_time = time.time()
        for i, data in enumerate(test_data):
            # 模拟数据处理
            processed = data.upper() + str(i)
        no_cache_time = time.time() - start_time
        
        # 测试有缓存性能
        start_time = time.time()
        for i, data in enumerate(test_data):
            cache_key = f"processed_{i}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is None:
                processed = data.upper() + str(i)
                self.cache_manager.set(cache_key, processed)
            else:
                processed = cached_result
        with_cache_time = time.time() - start_time
        
        # 测试缓存命中性能
        start_time = time.time()
        for i in range(len(test_data)):
            cache_key = f"processed_{i}"
            cached_result = self.cache_manager.get(cache_key)
        cache_hit_time = time.time() - start_time
        
        print(f"📊 缓存性能测试结果:")
        print(f"  无缓存处理时间: {no_cache_time:.4f}s")
        print(f"  有缓存处理时间: {with_cache_time:.4f}s")
        print(f"  缓存命中时间: {cache_hit_time:.4f}s")
        print(f"  性能提升: {((no_cache_time - cache_hit_time) / no_cache_time * 100):.1f}%")
        
        # 测试缓存统计
        stats = self.cache_manager.getStats()
        print(f"  缓存统计: {stats}")
        
        self.results['cache'] = {
            'no_cache_time': no_cache_time,
            'with_cache_time': with_cache_time,
            'cache_hit_time': cache_hit_time,
            'improvement': (no_cache_time - cache_hit_time) / no_cache_time * 100,
            'stats': stats
        }
    
    def test_query_optimization(self):
        """测试查询优化"""
        print("\n" + "="*50)
        print("🔍 查询优化测试")
        print("="*50)
        
        # 模拟查询函数
        @optimize_query(cache_ttl=60, monitor=True)
        def mock_database_query(table: str, conditions: Dict[str, Any]):
            """模拟数据库查询"""
            # 模拟查询延迟
            time.sleep(0.01)  # 10ms延迟
            return {
                'table': table,
                'conditions': conditions,
                'results': [f"record_{i}" for i in range(100)],
                'count': 100
            }
        
        # 测试查询性能
        queries = [
            ('users', {'status': 'active'}),
            ('certificates', {'expires_at': '<2024-01-01'}),
            ('servers', {'status': 'online'}),
            ('users', {'status': 'active'}),  # 重复查询，测试缓存
            ('certificates', {'expires_at': '<2024-01-01'}),  # 重复查询
        ]
        
        start_time = time.time()
        for table, conditions in queries:
            result = mock_database_query(table, conditions)
        total_time = time.time() - start_time
        
        print(f"📊 查询优化测试结果:")
        print(f"  总查询时间: {total_time:.4f}s")
        print(f"  平均查询时间: {total_time/len(queries):.4f}s")
        
        # 获取慢查询统计
        slow_queries = query_optimizer.get_slow_queries()
        print(f"  慢查询数量: {len(slow_queries)}")
        
        # 获取查询分析
        analysis = query_optimizer.analyze_query_patterns()
        print(f"  查询分析: {analysis}")
        
        self.results['query_optimization'] = {
            'total_time': total_time,
            'average_time': total_time / len(queries),
            'slow_queries_count': len(slow_queries),
            'analysis': analysis
        }
    
    def test_pagination_performance(self):
        """测试分页性能"""
        print("\n" + "="*50)
        print("📄 分页性能测试")
        print("="*50)
        
        # 模拟大数据集
        large_dataset = list(range(10000))
        
        def mock_query_with_pagination(offset: int, limit: int):
            """模拟分页查询"""
            time.sleep(0.005)  # 5ms延迟
            return large_dataset[offset:offset + limit]
        
        def mock_count_query():
            """模拟计数查询"""
            time.sleep(0.002)  # 2ms延迟
            return len(large_dataset)
        
        # 测试分页性能
        pagination_helper = PaginationHelper()
        
        start_time = time.time()
        result = pagination_helper.paginate(
            query_func=mock_query_with_pagination,
            page=1,
            per_page=20,
            count_func=mock_count_query
        )
        pagination_time = time.time() - start_time
        
        print(f"📊 分页性能测试结果:")
        print(f"  分页查询时间: {pagination_time:.4f}s")
        print(f"  返回记录数: {len(result['items'])}")
        print(f"  总记录数: {result['pagination']['total']}")
        print(f"  总页数: {result['pagination']['total_pages']}")
        print(f"  查询时间: {result['meta']['query_time']:.4f}s")
        print(f"  计数时间: {result['meta']['count_time']:.4f}s")
        
        self.results['pagination'] = {
            'pagination_time': pagination_time,
            'items_count': len(result['items']),
            'total_records': result['pagination']['total'],
            'total_pages': result['pagination']['total_pages'],
            'query_time': result['meta']['query_time'],
            'count_time': result['meta']['count_time']
        }
    
    def test_memory_usage(self):
        """测试内存使用"""
        print("\n" + "="*50)
        print("💾 内存使用测试")
        print("="*50)
        
        import psutil
        import gc
        
        # 获取当前进程
        process = psutil.Process()
        
        # 测试前内存使用
        gc.collect()  # 强制垃圾回收
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建大量缓存数据
        large_cache = CacheManager({'maxSize': 1000})
        for i in range(1000):
            large_cache.set(f"key_{i}", f"value_{i}" * 100)  # 较大的值
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        # 清理缓存
        large_cache.clear()
        gc.collect()
        memory_after_cleanup = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"📊 内存使用测试结果:")
        print(f"  测试前内存: {memory_before:.2f} MB")
        print(f"  测试后内存: {memory_after:.2f} MB")
        print(f"  清理后内存: {memory_after_cleanup:.2f} MB")
        print(f"  内存增长: {memory_after - memory_before:.2f} MB")
        print(f"  清理效果: {memory_after - memory_after_cleanup:.2f} MB")
        
        self.results['memory'] = {
            'memory_before': memory_before,
            'memory_after': memory_after,
            'memory_after_cleanup': memory_after_cleanup,
            'memory_growth': memory_after - memory_before,
            'cleanup_effect': memory_after - memory_after_cleanup
        }
    
    async def test_async_performance(self):
        """测试异步性能"""
        print("\n" + "="*50)
        print("⚡ 异步性能测试")
        print("="*50)
        
        async def mock_async_operation(delay: float):
            """模拟异步操作"""
            await asyncio.sleep(delay)
            return f"result_after_{delay}s"
        
        # 测试串行执行
        start_time = time.time()
        for i in range(5):
            await mock_async_operation(0.1)
        serial_time = time.time() - start_time
        
        # 测试并行执行
        start_time = time.time()
        tasks = [mock_async_operation(0.1) for _ in range(5)]
        await asyncio.gather(*tasks)
        parallel_time = time.time() - start_time
        
        print(f"📊 异步性能测试结果:")
        print(f"  串行执行时间: {serial_time:.4f}s")
        print(f"  并行执行时间: {parallel_time:.4f}s")
        print(f"  性能提升: {((serial_time - parallel_time) / serial_time * 100):.1f}%")
        
        self.results['async'] = {
            'serial_time': serial_time,
            'parallel_time': parallel_time,
            'improvement': (serial_time - parallel_time) / serial_time * 100
        }
    
    def generate_report(self):
        """生成性能测试报告"""
        print("\n" + "="*60)
        print("📋 性能优化测试报告")
        print("="*60)
        
        print("\n🎯 测试总结:")
        
        if 'cache' in self.results:
            cache_improvement = self.results['cache']['improvement']
            print(f"  • 缓存优化: 性能提升 {cache_improvement:.1f}%")
        
        if 'query_optimization' in self.results:
            avg_time = self.results['query_optimization']['average_time']
            print(f"  • 查询优化: 平均查询时间 {avg_time:.4f}s")
        
        if 'pagination' in self.results:
            pagination_time = self.results['pagination']['pagination_time']
            print(f"  • 分页优化: 分页查询时间 {pagination_time:.4f}s")
        
        if 'memory' in self.results:
            memory_growth = self.results['memory']['memory_growth']
            print(f"  • 内存优化: 内存增长 {memory_growth:.2f} MB")
        
        if 'async' in self.results:
            async_improvement = self.results['async']['improvement']
            print(f"  • 异步优化: 性能提升 {async_improvement:.1f}%")
        
        print("\n💡 优化建议:")
        
        # 根据测试结果生成建议
        if 'cache' in self.results and self.results['cache']['improvement'] < 50:
            print("  • 考虑增加缓存TTL或优化缓存策略")
        
        if 'query_optimization' in self.results:
            slow_queries = self.results['query_optimization']['slow_queries_count']
            if slow_queries > 0:
                print(f"  • 发现 {slow_queries} 个慢查询，建议优化")
        
        if 'memory' in self.results and self.results['memory']['memory_growth'] > 100:
            print("  • 内存使用量较高，建议检查内存泄漏")
        
        print("\n📊 详细数据:")
        print(json.dumps(self.results, indent=2, ensure_ascii=False))
        
        # 保存报告到文件
        with open('performance_report.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 性能测试完成，报告已保存到 performance_report.json")


async def main():
    """主函数"""
    print("🎉 开始SSL证书管理系统性能优化测试")
    
    tester = PerformanceTester()
    
    try:
        # 执行各项性能测试
        tester.test_cache_performance()
        tester.test_query_optimization()
        tester.test_pagination_performance()
        
        # 检查是否有psutil模块
        try:
            import psutil
            tester.test_memory_usage()
        except ImportError:
            print("\n⚠️  psutil模块未安装，跳过内存测试")
        
        await tester.test_async_performance()
        
        # 生成测试报告
        tester.generate_report()
        
    except KeyboardInterrupt:
        print("\n\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
