#!/usr/bin/env python3
"""
简化版性能优化测试脚本
测试基本的性能优化功能
"""

import time
import asyncio
import json
from typing import Dict, Any, List


class SimpleCacheManager:
    """简化版缓存管理器"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
    
    def get(self, key: str):
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        if len(self.cache) >= self.max_size:
            # 简单的LRU淘汰
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = value
        self.access_times[key] = time.time()
    
    def clear(self):
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self):
        return {
            'total_items': len(self.cache),
            'max_size': self.max_size,
            'memory_usage_kb': len(str(self.cache)) / 1024
        }


class SimplePagination:
    """简化版分页助手"""
    
    @staticmethod
    def paginate(data: List[Any], page: int = 1, per_page: int = 20):
        total = len(data)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'items': data[start:end],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }
        }


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results = {}
        self.cache_manager = SimpleCacheManager()
    
    def test_cache_performance(self):
        """测试缓存性能"""
        print("\n" + "="*50)
        print("🚀 缓存性能测试")
        print("="*50)
        
        # 测试数据
        test_data = [f"test_data_{i}" for i in range(1000)]
        
        # 测试无缓存性能
        start_time = time.time()
        results_no_cache = []
        for i, data in enumerate(test_data):
            # 模拟复杂计算
            result = data.upper() + str(i) + "_processed"
            results_no_cache.append(result)
        no_cache_time = time.time() - start_time
        
        # 测试有缓存性能（首次）
        start_time = time.time()
        results_with_cache = []
        for i, data in enumerate(test_data):
            cache_key = f"processed_{i}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is None:
                result = data.upper() + str(i) + "_processed"
                self.cache_manager.set(cache_key, result)
                results_with_cache.append(result)
            else:
                results_with_cache.append(cached_result)
        with_cache_time = time.time() - start_time
        
        # 测试缓存命中性能（第二次）
        start_time = time.time()
        results_cache_hit = []
        for i in range(len(test_data)):
            cache_key = f"processed_{i}"
            cached_result = self.cache_manager.get(cache_key)
            results_cache_hit.append(cached_result)
        cache_hit_time = time.time() - start_time
        
        print(f"📊 缓存性能测试结果:")
        print(f"  无缓存处理时间: {no_cache_time:.4f}s")
        print(f"  有缓存处理时间: {with_cache_time:.4f}s")
        print(f"  缓存命中时间: {cache_hit_time:.4f}s")
        
        if cache_hit_time > 0:
            improvement = ((no_cache_time - cache_hit_time) / no_cache_time * 100)
            print(f"  性能提升: {improvement:.1f}%")
        else:
            print(f"  性能提升: >99%")
        
        # 缓存统计
        stats = self.cache_manager.get_stats()
        print(f"  缓存统计: {stats}")
        
        self.results['cache'] = {
            'no_cache_time': no_cache_time,
            'with_cache_time': with_cache_time,
            'cache_hit_time': cache_hit_time,
            'improvement': improvement if cache_hit_time > 0 else 99.9,
            'stats': stats
        }
    
    def test_pagination_performance(self):
        """测试分页性能"""
        print("\n" + "="*50)
        print("📄 分页性能测试")
        print("="*50)
        
        # 创建大数据集
        large_dataset = [f"record_{i}" for i in range(10000)]
        
        # 测试不同分页大小的性能
        page_sizes = [10, 20, 50, 100]
        pagination_results = {}
        
        for page_size in page_sizes:
            start_time = time.time()
            
            # 模拟分页查询
            result = SimplePagination.paginate(large_dataset, page=1, per_page=page_size)
            
            end_time = time.time()
            duration = end_time - start_time
            
            pagination_results[page_size] = {
                'duration': duration,
                'items_count': len(result['items']),
                'total_pages': result['pagination']['total_pages']
            }
            
            print(f"  页大小 {page_size}: {duration:.6f}s, {len(result['items'])} 条记录")
        
        # 测试大页码的性能
        start_time = time.time()
        large_page_result = SimplePagination.paginate(large_dataset, page=100, per_page=20)
        large_page_time = time.time() - start_time
        
        print(f"📊 分页性能测试结果:")
        print(f"  大页码查询时间: {large_page_time:.6f}s")
        print(f"  总记录数: {len(large_dataset)}")
        
        self.results['pagination'] = {
            'page_size_results': pagination_results,
            'large_page_time': large_page_time,
            'total_records': len(large_dataset)
        }
    
    async def test_async_performance(self):
        """测试异步性能"""
        print("\n" + "="*50)
        print("⚡ 异步性能测试")
        print("="*50)
        
        async def mock_io_operation(delay: float, data: str):
            """模拟IO操作"""
            await asyncio.sleep(delay)
            return f"processed_{data}"
        
        # 测试数据
        test_items = [f"item_{i}" for i in range(10)]
        delay = 0.05  # 50ms延迟
        
        # 测试串行执行
        start_time = time.time()
        serial_results = []
        for item in test_items:
            result = await mock_io_operation(delay, item)
            serial_results.append(result)
        serial_time = time.time() - start_time
        
        # 测试并行执行
        start_time = time.time()
        tasks = [mock_io_operation(delay, item) for item in test_items]
        parallel_results = await asyncio.gather(*tasks)
        parallel_time = time.time() - start_time
        
        # 测试批量并行执行（限制并发数）
        async def batch_process(items: List[str], batch_size: int = 3):
            results = []
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_tasks = [mock_io_operation(delay, item) for item in batch]
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
            return results
        
        start_time = time.time()
        batch_results = await batch_process(test_items)
        batch_time = time.time() - start_time
        
        print(f"📊 异步性能测试结果:")
        print(f"  串行执行时间: {serial_time:.4f}s")
        print(f"  并行执行时间: {parallel_time:.4f}s")
        print(f"  批量执行时间: {batch_time:.4f}s")
        
        serial_improvement = ((serial_time - parallel_time) / serial_time * 100)
        batch_improvement = ((serial_time - batch_time) / serial_time * 100)
        
        print(f"  并行性能提升: {serial_improvement:.1f}%")
        print(f"  批量性能提升: {batch_improvement:.1f}%")
        
        self.results['async'] = {
            'serial_time': serial_time,
            'parallel_time': parallel_time,
            'batch_time': batch_time,
            'parallel_improvement': serial_improvement,
            'batch_improvement': batch_improvement
        }
    
    def test_data_processing_performance(self):
        """测试数据处理性能"""
        print("\n" + "="*50)
        print("🔄 数据处理性能测试")
        print("="*50)
        
        # 生成测试数据
        raw_data = [
            {'id': i, 'name': f'item_{i}', 'value': i * 2, 'category': f'cat_{i % 5}'}
            for i in range(5000)
        ]
        
        # 测试列表推导式
        start_time = time.time()
        list_comp_result = [
            {'id': item['id'], 'processed_name': item['name'].upper(), 'doubled_value': item['value'] * 2}
            for item in raw_data if item['value'] > 100
        ]
        list_comp_time = time.time() - start_time
        
        # 测试传统循环
        start_time = time.time()
        loop_result = []
        for item in raw_data:
            if item['value'] > 100:
                processed_item = {
                    'id': item['id'],
                    'processed_name': item['name'].upper(),
                    'doubled_value': item['value'] * 2
                }
                loop_result.append(processed_item)
        loop_time = time.time() - start_time
        
        # 测试filter + map
        start_time = time.time()
        filtered_data = filter(lambda x: x['value'] > 100, raw_data)
        map_result = list(map(
            lambda item: {
                'id': item['id'],
                'processed_name': item['name'].upper(),
                'doubled_value': item['value'] * 2
            },
            filtered_data
        ))
        map_time = time.time() - start_time
        
        print(f"📊 数据处理性能测试结果:")
        print(f"  列表推导式: {list_comp_time:.4f}s, {len(list_comp_result)} 条记录")
        print(f"  传统循环: {loop_time:.4f}s, {len(loop_result)} 条记录")
        print(f"  filter+map: {map_time:.4f}s, {len(map_result)} 条记录")
        
        # 计算最快的方法
        times = {'list_comp': list_comp_time, 'loop': loop_time, 'map': map_time}
        fastest = min(times, key=times.get)
        print(f"  最快方法: {fastest}")
        
        self.results['data_processing'] = {
            'list_comp_time': list_comp_time,
            'loop_time': loop_time,
            'map_time': map_time,
            'fastest_method': fastest,
            'processed_count': len(list_comp_result)
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
        
        if 'pagination' in self.results:
            total_records = self.results['pagination']['total_records']
            print(f"  • 分页优化: 处理 {total_records} 条记录")
        
        if 'async' in self.results:
            parallel_improvement = self.results['async']['parallel_improvement']
            batch_improvement = self.results['async']['batch_improvement']
            print(f"  • 异步优化: 并行提升 {parallel_improvement:.1f}%, 批量提升 {batch_improvement:.1f}%")
        
        if 'data_processing' in self.results:
            fastest = self.results['data_processing']['fastest_method']
            print(f"  • 数据处理: 最快方法是 {fastest}")
        
        print("\n💡 优化建议:")
        
        # 根据测试结果生成建议
        if 'cache' in self.results:
            if self.results['cache']['improvement'] > 80:
                print("  • 缓存效果显著，建议在生产环境中启用")
            elif self.results['cache']['improvement'] > 50:
                print("  • 缓存有一定效果，建议优化缓存策略")
            else:
                print("  • 缓存效果不明显，建议检查缓存实现")
        
        if 'async' in self.results:
            if self.results['async']['parallel_improvement'] > 70:
                print("  • 异步并行效果显著，建议在IO密集型操作中使用")
            else:
                print("  • 考虑使用批量处理来平衡并发和资源使用")
        
        print("\n📊 详细数据:")
        print(json.dumps(self.results, indent=2, ensure_ascii=False))
        
        # 保存报告到文件
        with open('simple_performance_report.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 性能测试完成，报告已保存到 simple_performance_report.json")


async def main():
    """主函数"""
    print("🎉 开始SSL证书管理系统性能优化测试")
    print("📝 这是一个简化版本的性能测试，用于验证基本优化效果")
    
    tester = PerformanceTester()
    
    try:
        # 执行各项性能测试
        tester.test_cache_performance()
        tester.test_pagination_performance()
        tester.test_data_processing_performance()
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
