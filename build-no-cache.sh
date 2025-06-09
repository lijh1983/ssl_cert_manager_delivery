#!/bin/bash
echo "=== 无缓存构建SSL证书管理器 ==="

# 构建所有服务（无缓存）
docker-compose -f docker-compose.aliyun.yml build --no-cache

echo "构建完成！"
docker images | grep ssl-manager
