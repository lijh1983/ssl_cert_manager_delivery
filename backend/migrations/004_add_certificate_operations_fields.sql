-- SSL证书管理器数据库迁移脚本
-- 版本: 004
-- 描述: 添加证书操作相关字段
-- 创建时间: 2025-01-10

-- 添加证书操作相关字段
ALTER TABLE certificates ADD COLUMN last_manual_check TIMESTAMP;
ALTER TABLE certificates ADD COLUMN check_in_progress BOOLEAN DEFAULT 0;
ALTER TABLE certificates ADD COLUMN renewal_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE certificates ADD COLUMN auto_renewal_enabled BOOLEAN DEFAULT 0;
ALTER TABLE certificates ADD COLUMN renewal_days_before INTEGER DEFAULT 30;
ALTER TABLE certificates ADD COLUMN import_source VARCHAR(50) DEFAULT 'manual';
ALTER TABLE certificates ADD COLUMN last_renewal_attempt TIMESTAMP;

-- 创建证书操作历史记录表
CREATE TABLE IF NOT EXISTS certificate_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER,
    operation_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    details TEXT,
    user_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
);

-- 创建证书发现记录表
CREATE TABLE IF NOT EXISTS certificate_discovery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address VARCHAR(45) NOT NULL,
    port INTEGER NOT NULL,
    domain VARCHAR(255),
    san_domains TEXT,
    certificate_fingerprint VARCHAR(64),
    issuer_info TEXT,
    expires_at TIMESTAMP,
    discovery_method VARCHAR(20) DEFAULT 'network_scan',
    imported BOOLEAN DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建任务队列表
CREATE TABLE IF NOT EXISTS operation_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(36) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    task_data TEXT,
    result_data TEXT,
    error_message TEXT,
    user_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_certificates_last_manual_check ON certificates(last_manual_check);
CREATE INDEX IF NOT EXISTS idx_certificates_check_in_progress ON certificates(check_in_progress);
CREATE INDEX IF NOT EXISTS idx_certificates_renewal_status ON certificates(renewal_status);
CREATE INDEX IF NOT EXISTS idx_certificates_auto_renewal_enabled ON certificates(auto_renewal_enabled);
CREATE INDEX IF NOT EXISTS idx_certificates_import_source ON certificates(import_source);
CREATE INDEX IF NOT EXISTS idx_certificates_last_renewal_attempt ON certificates(last_renewal_attempt);
CREATE INDEX IF NOT EXISTS idx_certificate_operations_certificate_id ON certificate_operations(certificate_id);
CREATE INDEX IF NOT EXISTS idx_certificate_operations_operation_type ON certificate_operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_certificate_operations_status ON certificate_operations(status);
CREATE INDEX IF NOT EXISTS idx_certificate_operations_user_id ON certificate_operations(user_id);
CREATE INDEX IF NOT EXISTS idx_certificate_operations_created_at ON certificate_operations(created_at);
CREATE INDEX IF NOT EXISTS idx_certificate_discovery_ip_port ON certificate_discovery(ip_address, port);
CREATE INDEX IF NOT EXISTS idx_certificate_discovery_domain ON certificate_discovery(domain);
CREATE INDEX IF NOT EXISTS idx_certificate_discovery_fingerprint ON certificate_discovery(certificate_fingerprint);
CREATE INDEX IF NOT EXISTS idx_certificate_discovery_imported ON certificate_discovery(imported);
CREATE INDEX IF NOT EXISTS idx_operation_tasks_task_id ON operation_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_operation_tasks_task_type ON operation_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_operation_tasks_status ON operation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_operation_tasks_user_id ON operation_tasks(user_id);

-- 更新现有记录的默认值
UPDATE certificates SET 
    check_in_progress = 0,
    renewal_status = 'pending',
    auto_renewal_enabled = 0,
    renewal_days_before = 30,
    import_source = 'manual'
WHERE check_in_progress IS NULL;

-- 添加注释
COMMENT ON COLUMN certificates.last_manual_check IS '最后手动检查时间';
COMMENT ON COLUMN certificates.check_in_progress IS '检测进行中状态';
COMMENT ON COLUMN certificates.renewal_status IS '续期状态: pending/in_progress/completed/failed';
COMMENT ON COLUMN certificates.auto_renewal_enabled IS '自动续期开关';
COMMENT ON COLUMN certificates.renewal_days_before IS '提前续期天数';
COMMENT ON COLUMN certificates.import_source IS '导入来源: manual/csv/discovery';
COMMENT ON COLUMN certificates.last_renewal_attempt IS '最后续期尝试时间';

COMMENT ON TABLE certificate_operations IS '证书操作历史记录表';
COMMENT ON COLUMN certificate_operations.operation_type IS '操作类型: manual_check/deep_scan/renewal/import/export/delete';
COMMENT ON COLUMN certificate_operations.status IS '状态: pending/running/completed/failed/cancelled';
COMMENT ON COLUMN certificate_operations.details IS '操作详细信息(JSON格式)';

COMMENT ON TABLE certificate_discovery IS '证书发现记录表';
COMMENT ON COLUMN certificate_discovery.discovery_method IS '发现方式: network_scan/manual_add';
COMMENT ON COLUMN certificate_discovery.san_domains IS 'SAN域名列表(JSON格式)';
COMMENT ON COLUMN certificate_discovery.issuer_info IS '颁发者信息(JSON格式)';

COMMENT ON TABLE operation_tasks IS '操作任务队列表';
COMMENT ON COLUMN operation_tasks.task_type IS '任务类型: manual_check/batch_check/discovery_scan/import/export';
COMMENT ON COLUMN operation_tasks.task_data IS '任务数据(JSON格式)';
COMMENT ON COLUMN operation_tasks.result_data IS '结果数据(JSON格式)';
