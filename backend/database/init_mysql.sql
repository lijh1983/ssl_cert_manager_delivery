-- SSL证书管理系统 MySQL 8.0.41 初始化脚本
-- 创建时间: 2025-01-10
-- 版本: 1.0.0

-- 设置字符集和排序规则
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `ssl_manager` 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `ssl_manager`;

-- 用户表
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `role` VARCHAR(20) NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_username` (`username`),
    INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 服务器表
DROP TABLE IF EXISTS `servers`;
CREATE TABLE `servers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `ip` VARCHAR(45),
    `os_type` VARCHAR(50),
    `version` VARCHAR(20),
    `token` VARCHAR(255) NOT NULL UNIQUE,
    `auto_renew` BOOLEAN NOT NULL DEFAULT TRUE,
    `user_id` INT NOT NULL,
    `server_type` VARCHAR(50) DEFAULT 'nginx',
    `description` TEXT,
    `status` VARCHAR(20) DEFAULT 'unknown',
    `last_seen` TIMESTAMP NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_servers_ip` (`ip`),
    INDEX `idx_servers_token` (`token`),
    INDEX `idx_servers_user_id` (`user_id`),
    INDEX `idx_servers_status` (`status`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 证书表
DROP TABLE IF EXISTS `certificates`;
CREATE TABLE `certificates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `domain` VARCHAR(255) NOT NULL,
    `type` VARCHAR(20) NOT NULL,
    `status` VARCHAR(20) NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `expires_at` TIMESTAMP NOT NULL,
    `server_id` INT NOT NULL,
    `ca_type` VARCHAR(50) NOT NULL,
    `private_key` LONGTEXT NOT NULL,
    `certificate` LONGTEXT NOT NULL,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `monitoring_enabled` BOOLEAN DEFAULT TRUE,
    `monitoring_frequency` INT DEFAULT 3600,
    `alert_enabled` BOOLEAN DEFAULT TRUE,
    `notes` TEXT,
    `tags` TEXT,
    `owner` VARCHAR(100),
    `business_unit` VARCHAR(100),
    `dns_status` VARCHAR(20),
    `dns_response_time` INT,
    `domain_reachable` BOOLEAN,
    `http_status_code` INT,
    `last_dns_check` TIMESTAMP NULL,
    `last_reachability_check` TIMESTAMP NULL,
    `monitored_ports` TEXT,
    `ssl_handshake_time` INT,
    `tls_version` VARCHAR(10),
    `cipher_suite` VARCHAR(100),
    `certificate_chain_valid` BOOLEAN,
    `http_redirect_status` VARCHAR(20),
    `last_port_check` TIMESTAMP NULL,
    `last_manual_check` TIMESTAMP NULL,
    `check_in_progress` BOOLEAN DEFAULT FALSE,
    `renewal_status` VARCHAR(20) DEFAULT 'pending',
    `auto_renewal_enabled` BOOLEAN DEFAULT FALSE,
    `renewal_days_before` INT DEFAULT 30,
    `import_source` VARCHAR(50) DEFAULT 'manual',
    `last_renewal_attempt` TIMESTAMP NULL,
    INDEX `idx_certificates_domain` (`domain`),
    INDEX `idx_certificates_expires_at` (`expires_at`),
    INDEX `idx_certificates_server_id` (`server_id`),
    INDEX `idx_certificates_status` (`status`),
    INDEX `idx_certificates_monitoring_enabled` (`monitoring_enabled`),
    INDEX `idx_certificates_owner` (`owner`),
    INDEX `idx_certificates_business_unit` (`business_unit`),
    INDEX `idx_certificates_dns_status` (`dns_status`),
    INDEX `idx_certificates_domain_reachable` (`domain_reachable`),
    INDEX `idx_certificates_renewal_status` (`renewal_status`),
    INDEX `idx_certificates_auto_renewal_enabled` (`auto_renewal_enabled`),
    FOREIGN KEY (`server_id`) REFERENCES `servers`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 告警表
DROP TABLE IF EXISTS `alerts`;
CREATE TABLE `alerts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `type` VARCHAR(50) NOT NULL,
    `message` TEXT NOT NULL,
    `status` VARCHAR(20) NOT NULL,
    `certificate_id` INT NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_alerts_certificate_id` (`certificate_id`),
    INDEX `idx_alerts_status` (`status`),
    INDEX `idx_alerts_type` (`type`),
    FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 监控配置表
DROP TABLE IF EXISTS `monitoring_configs`;
CREATE TABLE `monitoring_configs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `domain` VARCHAR(255) NOT NULL,
    `port` INT DEFAULT 443,
    `ip_type` VARCHAR(10) DEFAULT 'ipv4',
    `ip_address` VARCHAR(45),
    `monitoring_enabled` BOOLEAN DEFAULT TRUE,
    `description` TEXT,
    `user_id` INT NOT NULL,
    `status` VARCHAR(20) DEFAULT 'unknown',
    `days_left` INT DEFAULT 0,
    `cert_level` VARCHAR(10) DEFAULT 'DV',
    `encryption_type` VARCHAR(10) DEFAULT 'RSA',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_monitoring_configs_user_id` (`user_id`),
    INDEX `idx_monitoring_configs_domain` (`domain`),
    INDEX `idx_monitoring_configs_status` (`status`),
    UNIQUE KEY `unique_domain_user` (`domain`, `user_id`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 监控历史表
DROP TABLE IF EXISTS `monitoring_history`;
CREATE TABLE `monitoring_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `monitoring_id` INT NOT NULL,
    `check_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `status` VARCHAR(20) NOT NULL,
    `days_left` INT DEFAULT 0,
    `response_time` INT DEFAULT 0,
    `ssl_version` VARCHAR(20),
    `message` TEXT,
    INDEX `idx_monitoring_history_monitoring_id` (`monitoring_id`),
    INDEX `idx_monitoring_history_check_time` (`check_time`),
    INDEX `idx_monitoring_history_status` (`status`),
    FOREIGN KEY (`monitoring_id`) REFERENCES `monitoring_configs`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 系统设置表
DROP TABLE IF EXISTS `settings`;
CREATE TABLE `settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(50) NOT NULL UNIQUE,
    `value` TEXT NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_settings_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 证书部署记录表
DROP TABLE IF EXISTS `certificate_deployments`;
CREATE TABLE `certificate_deployments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `certificate_id` INT NOT NULL,
    `deploy_type` VARCHAR(50) NOT NULL,
    `deploy_target` VARCHAR(255) NOT NULL,
    `status` VARCHAR(20) NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_certificate_deployments_certificate_id` (`certificate_id`),
    INDEX `idx_certificate_deployments_deploy_type` (`deploy_type`),
    INDEX `idx_certificate_deployments_status` (`status`),
    FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 操作日志表
DROP TABLE IF EXISTS `operation_logs`;
CREATE TABLE `operation_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT,
    `action` VARCHAR(50) NOT NULL,
    `target_type` VARCHAR(50) NOT NULL,
    `target_id` INT NOT NULL,
    `ip` VARCHAR(45) NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_operation_logs_user_id` (`user_id`),
    INDEX `idx_operation_logs_target` (`target_type`, `target_id`),
    INDEX `idx_operation_logs_created_at` (`created_at`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认数据
INSERT INTO `users` (`username`, `password_hash`, `email`, `role`) VALUES
('admin', '$2b$12$1234567890123456789012uGZLCTXlLKw0GETpR5.Pu.ZV0vpbUW6', 'admin@example.com', 'admin');

INSERT INTO `settings` (`key`, `value`) VALUES
('default_ca', 'letsencrypt'),
('renew_before_days', '15'),
('alert_before_days', '30'),
('email_notification', 'true'),
('notification_email', 'admin@example.com'),
('mysql_version', '8.0.41'),
('system_initialized', 'true');

SET FOREIGN_KEY_CHECKS = 1;
