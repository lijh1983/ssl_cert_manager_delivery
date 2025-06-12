-- SSL证书管理系统 SQLite到MySQL迁移脚本
-- 创建时间: 2025-01-10
-- 版本: 1.0.0
-- 目标: MySQL 8.0.41

-- 注意：此脚本用于记录迁移过程，实际迁移需要使用Python脚本

-- 1. 数据类型映射说明
-- SQLite -> MySQL 8.0.41
-- INTEGER -> INT
-- INTEGER PRIMARY KEY AUTOINCREMENT -> INT AUTO_INCREMENT PRIMARY KEY
-- TEXT -> TEXT/LONGTEXT (根据内容长度)
-- VARCHAR(n) -> VARCHAR(n)
-- BOOLEAN -> BOOLEAN
-- TIMESTAMP -> TIMESTAMP
-- DATETIME -> TIMESTAMP

-- 2. 语法差异处理
-- SQLite的 ? 占位符 -> MySQL的 %s 占位符
-- SQLite的 AUTOINCREMENT -> MySQL的 AUTO_INCREMENT
-- SQLite的 DEFAULT TRUE/FALSE -> MySQL的 DEFAULT TRUE/FALSE
-- SQLite的 CURRENT_TIMESTAMP -> MySQL的 CURRENT_TIMESTAMP

-- 3. 索引和约束迁移
-- SQLite的索引语法基本兼容MySQL
-- 外键约束需要调整为MySQL语法
-- 唯一约束保持不变

-- 4. 字符集和排序规则
-- 所有表使用 utf8mb4 字符集
-- 使用 utf8mb4_unicode_ci 排序规则

-- 5. 存储引擎
-- 所有表使用 InnoDB 存储引擎
-- 支持事务、外键约束和行级锁定

-- 6. 迁移检查点
-- 验证所有表结构正确创建
-- 验证所有索引正确创建
-- 验证所有外键约束正确设置
-- 验证默认数据正确插入

-- 7. 性能优化建议
-- 为经常查询的字段添加索引
-- 使用适当的数据类型减少存储空间
-- 定期分析表统计信息
-- 监控慢查询日志

-- 8. 备份和恢复策略
-- 定期备份数据库
-- 测试备份恢复流程
-- 保留多个备份版本
-- 监控备份任务状态

-- 9. 安全配置建议
-- 使用强密码策略
-- 限制数据库访问权限
-- 启用SSL连接
-- 定期更新MySQL版本

-- 10. 监控和维护
-- 监控数据库性能指标
-- 定期优化表结构
-- 清理过期数据
-- 监控磁盘空间使用

-- 迁移完成后的验证SQL
-- SELECT COUNT(*) FROM users;
-- SELECT COUNT(*) FROM servers;
-- SELECT COUNT(*) FROM certificates;
-- SELECT COUNT(*) FROM monitoring_configs;
-- SELECT COUNT(*) FROM monitoring_history;
-- SELECT COUNT(*) FROM settings;

-- 检查表结构
-- DESCRIBE users;
-- DESCRIBE servers;
-- DESCRIBE certificates;
-- DESCRIBE monitoring_configs;
-- DESCRIBE monitoring_history;

-- 检查索引
-- SHOW INDEX FROM users;
-- SHOW INDEX FROM servers;
-- SHOW INDEX FROM certificates;
-- SHOW INDEX FROM monitoring_configs;
-- SHOW INDEX FROM monitoring_history;

-- 检查外键约束
-- SELECT 
--     TABLE_NAME,
--     COLUMN_NAME,
--     CONSTRAINT_NAME,
--     REFERENCED_TABLE_NAME,
--     REFERENCED_COLUMN_NAME
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE REFERENCED_TABLE_SCHEMA = 'ssl_manager'
-- AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 检查字符集和排序规则
-- SELECT 
--     TABLE_NAME,
--     TABLE_COLLATION
-- FROM INFORMATION_SCHEMA.TABLES
-- WHERE TABLE_SCHEMA = 'ssl_manager';

-- 性能测试查询
-- EXPLAIN SELECT * FROM certificates WHERE domain = 'example.com';
-- EXPLAIN SELECT * FROM monitoring_configs WHERE user_id = 1;
-- EXPLAIN SELECT * FROM monitoring_history WHERE monitoring_id = 1 ORDER BY check_time DESC LIMIT 10;
