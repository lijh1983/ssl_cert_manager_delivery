-- 数据库索引优化脚本
-- 为SSL证书管理系统添加必要的索引以提升查询性能

-- ==========================================
-- 用户表索引优化
-- ==========================================

-- 用户邮箱唯一索引（如果不存在）
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 用户角色索引（用于权限查询）
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- 用户状态索引（用于活跃用户查询）
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- 用户创建时间索引（用于统计和排序）
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- 复合索引：角色+状态（用于管理员查询活跃用户）
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active);

-- ==========================================
-- 服务器表索引优化
-- ==========================================

-- 服务器用户ID索引（用于查询用户的服务器）
CREATE INDEX IF NOT EXISTS idx_servers_user_id ON servers(user_id);

-- 服务器状态索引（用于查询在线/离线服务器）
CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);

-- 服务器最后心跳时间索引（用于监控离线服务器）
CREATE INDEX IF NOT EXISTS idx_servers_last_heartbeat ON servers(last_heartbeat);

-- 服务器创建时间索引
CREATE INDEX IF NOT EXISTS idx_servers_created_at ON servers(created_at);

-- 复合索引：用户ID+状态（用于查询用户的在线服务器）
CREATE INDEX IF NOT EXISTS idx_servers_user_status ON servers(user_id, status);

-- 复合索引：状态+最后心跳（用于监控查询）
CREATE INDEX IF NOT EXISTS idx_servers_status_heartbeat ON servers(status, last_heartbeat);

-- ==========================================
-- 证书表索引优化
-- ==========================================

-- 证书域名索引（用于域名查询和去重）
CREATE INDEX IF NOT EXISTS idx_certificates_domain ON certificates(domain);

-- 证书服务器ID索引（用于查询服务器的证书）
CREATE INDEX IF NOT EXISTS idx_certificates_server_id ON certificates(server_id);

-- 证书用户ID索引（用于查询用户的证书）
CREATE INDEX IF NOT EXISTS idx_certificates_user_id ON certificates(user_id);

-- 证书状态索引（用于查询有效/过期证书）
CREATE INDEX IF NOT EXISTS idx_certificates_status ON certificates(status);

-- 证书过期时间索引（用于过期监控）
CREATE INDEX IF NOT EXISTS idx_certificates_expires_at ON certificates(expires_at);

-- 证书CA类型索引（用于按CA分类查询）
CREATE INDEX IF NOT EXISTS idx_certificates_ca_type ON certificates(ca_type);

-- 证书验证方式索引
CREATE INDEX IF NOT EXISTS idx_certificates_validation_method ON certificates(validation_method);

-- 证书自动续期标志索引
CREATE INDEX IF NOT EXISTS idx_certificates_auto_renew ON certificates(auto_renew);

-- 证书创建时间索引
CREATE INDEX IF NOT EXISTS idx_certificates_created_at ON certificates(created_at);

-- 复合索引：用户ID+状态（用于查询用户的有效证书）
CREATE INDEX IF NOT EXISTS idx_certificates_user_status ON certificates(user_id, status);

-- 复合索引：服务器ID+状态（用于查询服务器的有效证书）
CREATE INDEX IF NOT EXISTS idx_certificates_server_status ON certificates(server_id, status);

-- 复合索引：状态+过期时间（用于过期监控查询）
CREATE INDEX IF NOT EXISTS idx_certificates_status_expires ON certificates(status, expires_at);

-- 复合索引：自动续期+过期时间（用于自动续期任务）
CREATE INDEX IF NOT EXISTS idx_certificates_auto_renew_expires ON certificates(auto_renew, expires_at);

-- 复合索引：CA类型+状态（用于按CA统计）
CREATE INDEX IF NOT EXISTS idx_certificates_ca_status ON certificates(ca_type, status);

-- ==========================================
-- 日志表索引优化（如果存在）
-- ==========================================

-- 日志级别索引
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);

-- 日志时间索引（用于时间范围查询）
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);

-- 日志用户ID索引（如果有用户关联）
CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id);

-- 日志操作类型索引
CREATE INDEX IF NOT EXISTS idx_logs_action ON logs(action);

-- 复合索引：级别+时间（用于错误日志查询）
CREATE INDEX IF NOT EXISTS idx_logs_level_timestamp ON logs(level, timestamp);

-- 复合索引：用户ID+时间（用于用户操作历史）
CREATE INDEX IF NOT EXISTS idx_logs_user_timestamp ON logs(user_id, timestamp);

-- ==========================================
-- 会话表索引优化（如果使用数据库存储会话）
-- ==========================================

-- 会话token索引
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);

-- 会话用户ID索引
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- 会话过期时间索引（用于清理过期会话）
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- 会话创建时间索引
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);

-- ==========================================
-- 告警表索引优化（如果使用数据库存储告警）
-- ==========================================

-- 告警状态索引
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

-- 告警级别索引
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);

-- 告警类型索引
CREATE INDEX IF NOT EXISTS idx_alerts_alert_type ON alerts(alert_type);

-- 告警创建时间索引
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);

-- 告警解决时间索引
CREATE INDEX IF NOT EXISTS idx_alerts_resolved_at ON alerts(resolved_at);

-- 复合索引：状态+级别（用于活跃告警查询）
CREATE INDEX IF NOT EXISTS idx_alerts_status_severity ON alerts(status, severity);

-- 复合索引：类型+状态（用于按类型统计告警）
CREATE INDEX IF NOT EXISTS idx_alerts_type_status ON alerts(alert_type, status);

-- ==========================================
-- 性能监控查询
-- ==========================================

-- 查看索引使用情况（PostgreSQL）
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch 
-- FROM pg_stat_user_indexes 
-- ORDER BY idx_scan DESC;

-- 查看表扫描情况（PostgreSQL）
-- SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch,
--        n_tup_ins, n_tup_upd, n_tup_del
-- FROM pg_stat_user_tables
-- ORDER BY seq_scan DESC;

-- 查看慢查询（需要开启慢查询日志）
-- SELECT query, calls, total_time, mean_time, rows
-- FROM pg_stat_statements
-- ORDER BY total_time DESC
-- LIMIT 10;

-- ==========================================
-- 索引维护建议
-- ==========================================

-- 1. 定期分析表统计信息
-- ANALYZE users;
-- ANALYZE servers;
-- ANALYZE certificates;

-- 2. 定期重建索引（如果需要）
-- REINDEX INDEX idx_certificates_expires_at;

-- 3. 监控索引大小
-- SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size
-- FROM pg_indexes
-- WHERE tablename IN ('users', 'servers', 'certificates')
-- ORDER BY pg_relation_size(indexname::regclass) DESC;

-- 4. 检查未使用的索引
-- SELECT schemaname, tablename, indexname, idx_scan
-- FROM pg_stat_user_indexes
-- WHERE idx_scan = 0
-- ORDER BY schemaname, tablename, indexname;

-- ==========================================
-- 查询优化建议
-- ==========================================

-- 1. 使用EXPLAIN ANALYZE分析查询计划
-- EXPLAIN ANALYZE SELECT * FROM certificates WHERE expires_at < NOW() + INTERVAL '30 days';

-- 2. 避免SELECT *，只查询需要的字段
-- 3. 使用LIMIT限制返回结果数量
-- 4. 合理使用WHERE条件，优先使用有索引的字段
-- 5. 对于复杂查询，考虑分解为多个简单查询
-- 6. 使用连接查询代替子查询（在适当的情况下）
-- 7. 定期更新表统计信息以保证查询计划的准确性
