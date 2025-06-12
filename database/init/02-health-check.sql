-- MySQL数据库健康检查脚本
-- 验证数据库结构和基础数据

-- 检查表是否存在（验证与后端代码匹配的表）
SET @expected_tables = 'users,servers,certificates,alerts,operation_logs,certificate_deployments,settings';
SET @missing_tables = '';
SET @table_count = 0;

-- 检查每个必需的表
SELECT COUNT(*) INTO @table_count
FROM information_schema.tables
WHERE table_schema = DATABASE()
AND table_type = 'BASE TABLE'
AND table_name IN ('users', 'servers', 'certificates', 'alerts', 'operation_logs', 'certificate_deployments', 'settings');

-- 验证表数量
SELECT
    CASE
        WHEN @table_count >= 7 THEN CONCAT('✓ 数据库表结构检查通过 (', @table_count, ' 个表)')
        ELSE CONCAT('✗ 缺少必需的表，当前只有 ', @table_count, ' 个表')
    END AS health_check_result;

-- 检查MySQL版本
SELECT
    CONCAT('✓ MySQL版本: ', VERSION()) AS mysql_version;

-- 检查字符集
SELECT
    CONCAT('✓ 默认字符集: ', DEFAULT_CHARACTER_SET_NAME) AS default_charset
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = DATABASE();

-- 检查存储引擎
SELECT
    CONCAT('✓ 支持的存储引擎: ', GROUP_CONCAT(ENGINE SEPARATOR ', ')) AS supported_engines
FROM information_schema.ENGINES
WHERE SUPPORT IN ('YES', 'DEFAULT');

-- 检查默认配置是否存在
SET @config_count = 0;
SELECT COUNT(*) INTO @config_count FROM settings;

SELECT
    CASE
        WHEN @config_count >= 5 THEN CONCAT('✓ 系统配置检查通过 (', @config_count, ' 项配置)')
        ELSE CONCAT('✗ 系统配置不完整，只有 ', @config_count, ' 项配置')
    END AS config_check_result;

-- 检查默认管理员用户是否存在
SET @admin_count = 0;
SELECT COUNT(*) INTO @admin_count FROM users WHERE role = 'admin';

SELECT
    CASE
        WHEN @admin_count >= 1 THEN CONCAT('✓ 管理员用户检查通过 (', @admin_count, ' 个管理员)')
        ELSE '✗ 没有管理员用户'
    END AS admin_check_result;

-- 输出数据库信息
SELECT
    CONCAT('MySQL ', VERSION()) AS database_version,
    DATABASE() AS database_name,
    USER() AS current_user,
    NOW() AS current_time;

-- 完成提示
SELECT '🎉 MySQL数据库健康检查完成！' AS completion_message;
