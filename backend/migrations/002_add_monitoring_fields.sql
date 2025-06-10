-- SSL证书管理器数据库迁移脚本
-- 版本: 002
-- 描述: 添加监控相关字段和表
-- 创建时间: 2025-01-10

-- 为证书表添加监控字段
ALTER TABLE certificates ADD COLUMN monitoring_enabled BOOLEAN DEFAULT 1;
ALTER TABLE certificates ADD COLUMN check_frequency VARCHAR(20) DEFAULT 'daily';
ALTER TABLE certificates ADD COLUMN alert_threshold_days INTEGER DEFAULT 30;
ALTER TABLE certificates ADD COLUMN last_check TIMESTAMP;
ALTER TABLE certificates ADD COLUMN dns_status VARCHAR(20);
ALTER TABLE certificates ADD COLUMN domain_reachable BOOLEAN;
ALTER TABLE certificates ADD COLUMN last_dns_check TIMESTAMP;
ALTER TABLE certificates ADD COLUMN last_reachability_check TIMESTAMP;

-- 创建域名监控历史记录表
CREATE TABLE IF NOT EXISTS domain_monitoring_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER NOT NULL,
    check_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time INTEGER,
    error_message TEXT,
    dns_records TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
);

-- 创建域名监控配置表
CREATE TABLE IF NOT EXISTS domain_monitoring_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER NOT NULL UNIQUE,
    dns_check_enabled BOOLEAN DEFAULT 1,
    reachability_check_enabled BOOLEAN DEFAULT 1,
    check_timeout INTEGER DEFAULT 30,
    max_retry_count INTEGER DEFAULT 3,
    alert_email VARCHAR(255),
    email_alerts_enabled BOOLEAN DEFAULT 0,
    alert_level VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_certificates_monitoring_enabled ON certificates(monitoring_enabled);
CREATE INDEX IF NOT EXISTS idx_certificates_dns_status ON certificates(dns_status);
CREATE INDEX IF NOT EXISTS idx_certificates_domain_reachable ON certificates(domain_reachable);
CREATE INDEX IF NOT EXISTS idx_certificates_last_check ON certificates(last_check);
CREATE INDEX IF NOT EXISTS idx_domain_monitoring_history_certificate_id ON domain_monitoring_history(certificate_id);
CREATE INDEX IF NOT EXISTS idx_domain_monitoring_history_check_type ON domain_monitoring_history(check_type);
CREATE INDEX IF NOT EXISTS idx_domain_monitoring_history_status ON domain_monitoring_history(status);
CREATE INDEX IF NOT EXISTS idx_domain_monitoring_history_created_at ON domain_monitoring_history(created_at);
CREATE INDEX IF NOT EXISTS idx_domain_monitoring_config_certificate_id ON domain_monitoring_config(certificate_id);

-- 更新现有记录的默认值
UPDATE certificates SET 
    monitoring_enabled = 1,
    check_frequency = 'daily',
    alert_threshold_days = 30
WHERE monitoring_enabled IS NULL;

-- 添加注释
COMMENT ON COLUMN certificates.monitoring_enabled IS '是否启用监控';
COMMENT ON COLUMN certificates.check_frequency IS '检查频率';
COMMENT ON COLUMN certificates.alert_threshold_days IS '告警阈值天数';
COMMENT ON COLUMN certificates.dns_status IS 'DNS解析状态';
COMMENT ON COLUMN certificates.domain_reachable IS '域名可达性';

COMMENT ON TABLE domain_monitoring_history IS '域名监控历史记录表';
COMMENT ON COLUMN domain_monitoring_history.check_type IS '检查类型: dns/reachability';
COMMENT ON COLUMN domain_monitoring_history.status IS '检查状态: success/failed/timeout';
COMMENT ON COLUMN domain_monitoring_history.dns_records IS 'DNS记录(JSON格式)';

COMMENT ON TABLE domain_monitoring_config IS '域名监控配置表';
COMMENT ON COLUMN domain_monitoring_config.dns_check_enabled IS '是否启用DNS检查';
COMMENT ON COLUMN domain_monitoring_config.reachability_check_enabled IS '是否启用可达性检查';
