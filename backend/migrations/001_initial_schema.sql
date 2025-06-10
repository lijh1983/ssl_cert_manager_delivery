-- SSL证书管理器初始数据库结构
-- 版本: 001
-- 描述: 创建基础表结构
-- 创建时间: 2025-01-10

-- 服务器表
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    port INTEGER DEFAULT 22,
    username VARCHAR(100),
    ssh_key_path VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 证书表
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(20) NOT NULL DEFAULT 'single',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    server_id INTEGER,
    ca_type VARCHAR(50) DEFAULT 'letsencrypt',
    certificate_path VARCHAR(500),
    private_key_path VARCHAR(500),
    chain_path VARCHAR(500),
    issued_at TIMESTAMP,
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT 1,
    notes TEXT,
    owner VARCHAR(100),
    business_unit VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers(id)
);

-- 告警表
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_certificates_domain ON certificates(domain);
CREATE INDEX IF NOT EXISTS idx_certificates_status ON certificates(status);
CREATE INDEX IF NOT EXISTS idx_certificates_expires_at ON certificates(expires_at);
CREATE INDEX IF NOT EXISTS idx_certificates_server_id ON certificates(server_id);
CREATE INDEX IF NOT EXISTS idx_alerts_certificate_id ON alerts(certificate_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);

-- 插入示例数据
INSERT OR IGNORE INTO servers (id, name, ip_address, username) VALUES 
(1, '默认服务器', '127.0.0.1', 'root');

-- 添加注释
COMMENT ON TABLE servers IS '服务器信息表';
COMMENT ON TABLE certificates IS 'SSL证书信息表';
COMMENT ON TABLE alerts IS '告警信息表';
