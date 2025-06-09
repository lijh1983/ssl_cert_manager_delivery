-- 数据库健康检查脚本
-- 验证数据库结构和基础数据

-- 检查表是否存在
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
    
    IF table_count >= 6 THEN
        RAISE NOTICE '✓ 数据库表结构检查通过 (% 个表)', table_count;
    ELSE
        RAISE EXCEPTION '✗ 数据库表结构不完整，只有 % 个表', table_count;
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
    SELECT COUNT(*) INTO config_count FROM system_config;
    
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
    SELECT COUNT(*) INTO admin_count FROM users WHERE is_admin = true;
    
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
