-- SSL证书管理器数据库迁移脚本
-- 版本: 003
-- 描述: 添加端口监控相关字段
-- 创建时间: 2025-01-10

-- 添加端口监控字段到证书表
ALTER TABLE certificates ADD COLUMN monitored_ports TEXT;
ALTER TABLE certificates ADD COLUMN ssl_handshake_time INTEGER;
ALTER TABLE certificates ADD COLUMN tls_version VARCHAR(10);
ALTER TABLE certificates ADD COLUMN cipher_suite VARCHAR(100);
ALTER TABLE certificates ADD COLUMN certificate_chain_valid BOOLEAN;
ALTER TABLE certificates ADD COLUMN http_redirect_status VARCHAR(20);
ALTER TABLE certificates ADD COLUMN last_port_check TIMESTAMP;

-- 创建端口监控历史记录表
CREATE TABLE IF NOT EXISTS port_monitoring_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER NOT NULL,
    port INTEGER NOT NULL,
    check_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    ssl_enabled BOOLEAN DEFAULT 0,
    tls_version VARCHAR(10),
    cipher_suite VARCHAR(100),
    handshake_time INTEGER,
    certificate_chain_valid BOOLEAN,
    security_grade VARCHAR(5),
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
);

-- 创建SSL安全配置表
CREATE TABLE IF NOT EXISTS ssl_security_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER NOT NULL UNIQUE,
    min_tls_version VARCHAR(10) DEFAULT 'TLS 1.2',
    allowed_cipher_suites TEXT,
    require_perfect_forward_secrecy BOOLEAN DEFAULT 1,
    hsts_enabled BOOLEAN DEFAULT 0,
    hsts_max_age INTEGER DEFAULT 31536000,
    hsts_include_subdomains BOOLEAN DEFAULT 0,
    ocsp_stapling_enabled BOOLEAN DEFAULT 0,
    security_grade_threshold VARCHAR(5) DEFAULT 'B',
    alert_on_grade_drop BOOLEAN DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_certificates_monitored_ports ON certificates(monitored_ports);
CREATE INDEX IF NOT EXISTS idx_certificates_tls_version ON certificates(tls_version);
CREATE INDEX IF NOT EXISTS idx_certificates_certificate_chain_valid ON certificates(certificate_chain_valid);
CREATE INDEX IF NOT EXISTS idx_certificates_last_port_check ON certificates(last_port_check);
CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_certificate_id ON port_monitoring_history(certificate_id);
CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_port ON port_monitoring_history(port);
CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_check_type ON port_monitoring_history(check_type);
CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_status ON port_monitoring_history(status);
CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_security_grade ON port_monitoring_history(security_grade);
CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_created_at ON port_monitoring_history(created_at);
CREATE INDEX IF NOT EXISTS idx_ssl_security_config_certificate_id ON ssl_security_config(certificate_id);

-- 更新现有记录的默认值
UPDATE certificates SET 
    monitored_ports = '["80", "443"]'
WHERE monitored_ports IS NULL;

-- 添加注释
COMMENT ON COLUMN certificates.monitored_ports IS '监控的端口列表(JSON格式)';
COMMENT ON COLUMN certificates.ssl_handshake_time IS 'SSL握手时间(毫秒)';
COMMENT ON COLUMN certificates.tls_version IS 'TLS协议版本';
COMMENT ON COLUMN certificates.cipher_suite IS '使用的加密套件';
COMMENT ON COLUMN certificates.certificate_chain_valid IS '证书链有效性';
COMMENT ON COLUMN certificates.http_redirect_status IS 'HTTP重定向状态';

COMMENT ON TABLE port_monitoring_history IS '端口监控历史记录表';
COMMENT ON COLUMN port_monitoring_history.check_type IS '检查类型: ssl/http_redirect';
COMMENT ON COLUMN port_monitoring_history.status IS '检查状态: success/failed/timeout';
COMMENT ON COLUMN port_monitoring_history.security_grade IS '安全等级: A+/A/B/C/D/F';

COMMENT ON TABLE ssl_security_config IS 'SSL安全配置表';
COMMENT ON COLUMN ssl_security_config.min_tls_version IS '最低TLS版本要求';
COMMENT ON COLUMN ssl_security_config.allowed_cipher_suites IS '允许的加密套件列表(JSON格式)';
COMMENT ON COLUMN ssl_security_config.security_grade_threshold IS '安全等级阈值';
