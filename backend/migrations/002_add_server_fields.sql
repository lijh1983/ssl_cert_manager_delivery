-- 添加服务器新字段的迁移脚本
-- 执行时间：2025-01-10

-- 为servers表添加新字段
ALTER TABLE servers ADD COLUMN server_type VARCHAR(50) DEFAULT 'nginx';
ALTER TABLE servers ADD COLUMN description TEXT DEFAULT '';
ALTER TABLE servers ADD COLUMN last_seen DATETIME;
ALTER TABLE servers ADD COLUMN user_id INTEGER;
ALTER TABLE servers ADD COLUMN ip VARCHAR(45);
ALTER TABLE servers ADD COLUMN os_type VARCHAR(50);
ALTER TABLE servers ADD COLUMN version VARCHAR(20);
ALTER TABLE servers ADD COLUMN token VARCHAR(255);
ALTER TABLE servers ADD COLUMN auto_renew BOOLEAN DEFAULT 1;

-- 更新现有数据的默认值
UPDATE servers SET
    server_type = 'nginx',
    description = '',
    status = CASE
        WHEN updated_at > datetime('now', '-5 minutes') THEN 'online'
        ELSE 'offline'
    END,
    last_seen = updated_at,
    user_id = 1,
    ip = ip_address,
    os_type = 'Unknown',
    version = '1.0.0',
    token = hex(randomblob(16)),
    auto_renew = 1
WHERE server_type IS NULL;

-- 创建监控配置表
CREATE TABLE IF NOT EXISTS monitoring_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 443,
    ip_type VARCHAR(10) DEFAULT 'ipv4',
    ip_address VARCHAR(45),
    monitoring_enabled BOOLEAN DEFAULT 1,
    description TEXT DEFAULT '',
    user_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'unknown',
    days_left INTEGER DEFAULT 0,
    cert_level VARCHAR(10) DEFAULT 'DV',
    encryption_type VARCHAR(10) DEFAULT 'RSA',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(domain, user_id)
);

-- 创建监控历史表
CREATE TABLE IF NOT EXISTS monitoring_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitoring_id INTEGER NOT NULL,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    days_left INTEGER DEFAULT 0,
    response_time INTEGER DEFAULT 0,
    ssl_version VARCHAR(20),
    message TEXT,
    FOREIGN KEY (monitoring_id) REFERENCES monitoring_configs(id) ON DELETE CASCADE
);

-- 为certificates表添加新字段（如果不存在）
ALTER TABLE certificates ADD COLUMN encryption_algorithm VARCHAR(10) DEFAULT 'rsa';
ALTER TABLE certificates ADD COLUMN validation_method VARCHAR(20) DEFAULT 'dns';
ALTER TABLE certificates ADD COLUMN user_id INTEGER;
ALTER TABLE certificates ADD COLUMN private_key TEXT;
ALTER TABLE certificates ADD COLUMN certificate TEXT;
ALTER TABLE certificates ADD COLUMN monitoring_enabled BOOLEAN DEFAULT 1;
ALTER TABLE certificates ADD COLUMN monitoring_frequency INTEGER DEFAULT 3600;
ALTER TABLE certificates ADD COLUMN alert_enabled BOOLEAN DEFAULT 1;
ALTER TABLE certificates ADD COLUMN tags TEXT;
ALTER TABLE certificates ADD COLUMN dns_status VARCHAR(20);
ALTER TABLE certificates ADD COLUMN dns_response_time INTEGER;
ALTER TABLE certificates ADD COLUMN domain_reachable BOOLEAN;
ALTER TABLE certificates ADD COLUMN http_status_code INTEGER;
ALTER TABLE certificates ADD COLUMN last_dns_check TIMESTAMP;
ALTER TABLE certificates ADD COLUMN last_reachability_check TIMESTAMP;
ALTER TABLE certificates ADD COLUMN monitored_ports TEXT;
ALTER TABLE certificates ADD COLUMN ssl_handshake_time INTEGER;
ALTER TABLE certificates ADD COLUMN tls_version VARCHAR(10);
ALTER TABLE certificates ADD COLUMN cipher_suite VARCHAR(100);
ALTER TABLE certificates ADD COLUMN certificate_chain_valid BOOLEAN;
ALTER TABLE certificates ADD COLUMN http_redirect_status VARCHAR(20);
ALTER TABLE certificates ADD COLUMN last_port_check TIMESTAMP;
ALTER TABLE certificates ADD COLUMN last_manual_check TIMESTAMP;
ALTER TABLE certificates ADD COLUMN check_in_progress BOOLEAN DEFAULT 0;
ALTER TABLE certificates ADD COLUMN renewal_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE certificates ADD COLUMN auto_renewal_enabled BOOLEAN DEFAULT 0;
ALTER TABLE certificates ADD COLUMN renewal_days_before INTEGER DEFAULT 30;
ALTER TABLE certificates ADD COLUMN import_source VARCHAR(50) DEFAULT 'manual';
ALTER TABLE certificates ADD COLUMN last_renewal_attempt TIMESTAMP;

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_servers_user_id ON servers(user_id);
CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_configs_user_id ON monitoring_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_configs_domain ON monitoring_configs(domain);
CREATE INDEX IF NOT EXISTS idx_monitoring_history_monitoring_id ON monitoring_history(monitoring_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_history_check_time ON monitoring_history(check_time);
CREATE INDEX IF NOT EXISTS idx_certificates_ca_type ON certificates(ca_type);
