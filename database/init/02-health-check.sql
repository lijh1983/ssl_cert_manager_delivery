-- 数据库健康检查脚本
-- 验证数据库结构和基础数据

-- 检查表是否存在（验证与后端代码匹配的表）
DO $$
DECLARE
    table_count INTEGER;
    expected_tables TEXT[] := ARRAY['users', 'servers', 'certificates', 'alerts', 'operation_logs', 'certificate_deployments', 'settings'];
    missing_tables TEXT := '';
    current_table TEXT;
BEGIN
    -- 检查每个必需的表
    FOREACH current_table IN ARRAY expected_tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = current_table
        ) THEN
            missing_tables := missing_tables || current_table || ', ';
        END IF;
    END LOOP;

    IF missing_tables = '' THEN
        SELECT COUNT(*) INTO table_count
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE';
        RAISE NOTICE '✓ 数据库表结构检查通过 (% 个表)', table_count;
    ELSE
        RAISE EXCEPTION '✗ 缺少必需的表: %', TRIM(TRAILING ', ' FROM missing_tables);
    END IF;
END $$;

-- 检查扩展是否安装
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') THEN
        RAISE NOTICE '✓ uuid-ossp 扩展已安装';
    ELSE
        RAISE EXCEPTION '✗ uuid-ossp 扩展未安装';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        RAISE NOTICE '✓ pgcrypto 扩展已安装';
    ELSE
        RAISE EXCEPTION '✗ pgcrypto 扩展未安装';
    END IF;
END $$;

-- 检查默认配置是否存在
DO $$
DECLARE
    config_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO config_count FROM settings;

    IF config_count >= 5 THEN
        RAISE NOTICE '✓ 系统配置检查通过 (% 项配置)', config_count;
    ELSE
        RAISE EXCEPTION '✗ 系统配置不完整，只有 % 项配置', config_count;
    END IF;
END $$;

-- 检查默认管理员用户是否存在
DO $$
DECLARE
    admin_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO admin_count FROM users WHERE role = 'admin';

    IF admin_count >= 1 THEN
        RAISE NOTICE '✓ 管理员用户检查通过 (% 个管理员)', admin_count;
    ELSE
        RAISE EXCEPTION '✗ 没有管理员用户';
    END IF;
END $$;

-- 输出数据库信息
SELECT 
    'PostgreSQL ' || version() AS database_version,
    current_database() AS database_name,
    current_user AS current_user,
    now() AS current_time;

DO $$
BEGIN
    RAISE NOTICE '🎉 数据库健康检查完成！';
END $$;
