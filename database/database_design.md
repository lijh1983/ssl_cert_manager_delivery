# 数据库设计文档

## 1. 概述

本文档描述了SSL证书自动化管理系统的数据库设计，包括表结构、关系和索引等。系统采用关系型数据库，支持SQLite（单机部署）和PostgreSQL（分布式部署）。

## 2. 实体关系图

```
+---------------+       +----------------+       +---------------+
|     用户      |       |     服务器     |       |     证书      |
+---------------+       +----------------+       +---------------+
| PK: id        |<----->| PK: id         |<----->| PK: id        |
| username      |       | name           |       | domain        |
| password_hash |       | ip             |       | type          |
| email         |       | os_type        |       | status        |
| role          |       | version        |       | created_at    |
| created_at    |       | token          |       | expires_at    |
| updated_at    |       | auto_renew     |       | server_id     |
+---------------+       | user_id        |       | ca_type       |
                        | created_at     |       | private_key   |
                        | updated_at     |       | certificate   |
                        +----------------+       | updated_at    |
                                                 +---------------+
                                                        |
                                                        |
+---------------+       +----------------+              |
|    告警       |       |   操作日志     |              |
+---------------+       +----------------+              |
| PK: id        |       | PK: id         |              |
| type          |       | user_id        |              |
| message       |       | action         |              |
| status        |       | target_type    |              |
| certificate_id|<------|>target_id      |              |
| created_at    |       | ip             |              |
| updated_at    |       | created_at     |              |
+---------------+       +----------------+              |
                                                        |
                                                        |
                        +----------------+              |
                        |  证书部署记录  |              |
                        +----------------+              |
                        | PK: id         |              |
                        | certificate_id |<-------------+
                        | deploy_type    |
                        | deploy_target  |
                        | status         |
                        | created_at     |
                        | updated_at     |
                        +----------------+
```

## 3. 表结构设计

### 3.1 用户表 (users)

存储系统用户信息，包括管理员和普通用户。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY | 用户ID |
| username | VARCHAR(50) | NOT NULL, UNIQUE | 用户名 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希 |
| email | VARCHAR(100) | NOT NULL, UNIQUE | 电子邮箱 |
| role | VARCHAR(20) | NOT NULL | 角色（admin/user） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

索引：
- username_idx: 用户名索引
- email_idx: 邮箱索引

### 3.2 服务器表 (servers)

存储被管理的服务器信息。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY | 服务器ID |
| name | VARCHAR(100) | NOT NULL | 服务器名称 |
| ip | VARCHAR(45) | NOT NULL | IP地址 |
| os_type | VARCHAR(50) | NOT NULL | 操作系统类型 |
| version | VARCHAR(20) | NOT NULL | 客户端版本 |
| token | VARCHAR(255) | NOT NULL, UNIQUE | 认证令牌 |
| auto_renew | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否自动续期 |
| user_id | INTEGER | NOT NULL, FOREIGN KEY | 所属用户ID |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

索引：
- ip_idx: IP地址索引
- token_idx: 令牌索引
- user_id_idx: 用户ID索引

### 3.3 证书表 (certificates)

存储SSL证书信息。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY | 证书ID |
| domain | VARCHAR(255) | NOT NULL | 域名 |
| type | VARCHAR(20) | NOT NULL | 证书类型（single/wildcard/multi） |
| status | VARCHAR(20) | NOT NULL | 状态（valid/expired/revoked/pending） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| expires_at | TIMESTAMP | NOT NULL | 过期时间 |
| server_id | INTEGER | NOT NULL, FOREIGN KEY | 所属服务器ID |
| ca_type | VARCHAR(50) | NOT NULL | CA类型（letsencrypt/zerossl/buypass/google） |
| private_key | TEXT | NOT NULL | 私钥（加密存储） |
| certificate | TEXT | NOT NULL | 证书内容 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

索引：
- domain_idx: 域名索引
- expires_at_idx: 过期时间索引
- server_id_idx: 服务器ID索引
- status_idx: 状态索引

### 3.4 告警表 (alerts)

存储证书相关的告警信息。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY | 告警ID |
| type | VARCHAR(50) | NOT NULL | 告警类型（expiry/error/revoke） |
| message | TEXT | NOT NULL | 告警消息 |
| status | VARCHAR(20) | NOT NULL | 状态（pending/sent/resolved） |
| certificate_id | INTEGER | NOT NULL, FOREIGN KEY | 相关证书ID |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

索引：
- certificate_id_idx: 证书ID索引
- status_idx: 状态索引
- type_idx: 类型索引

### 3.5 操作日志表 (operation_logs)

记录系统操作日志。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY | 日志ID |
| user_id | INTEGER | FOREIGN KEY | 操作用户ID |
| action | VARCHAR(50) | NOT NULL | 操作类型 |
| target_type | VARCHAR(50) | NOT NULL | 目标类型（server/certificate/user） |
| target_id | INTEGER | NOT NULL | 目标ID |
| ip | VARCHAR(45) | NOT NULL | 操作IP |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

索引：
- user_id_idx: 用户ID索引
- target_type_target_id_idx: 目标类型和ID联合索引
- created_at_idx: 创建时间索引

### 3.6 证书部署记录表 (certificate_deployments)

记录证书部署到不同环境的情况。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY | 部署记录ID |
| certificate_id | INTEGER | NOT NULL, FOREIGN KEY | 证书ID |
| deploy_type | VARCHAR(50) | NOT NULL | 部署类型（nginx/apache/cdn/lb/oss） |
| deploy_target | VARCHAR(255) | NOT NULL | 部署目标 |
| status | VARCHAR(20) | NOT NULL | 状态（success/failed/pending） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

索引：
- certificate_id_idx: 证书ID索引
- deploy_type_idx: 部署类型索引
- status_idx: 状态索引

## 4. 数据库初始化脚本

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX username_idx ON users(username);
CREATE INDEX email_idx ON users(email);

-- 服务器表
CREATE TABLE servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    ip VARCHAR(45) NOT NULL,
    os_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX ip_idx ON servers(ip);
CREATE INDEX token_idx ON servers(token);
CREATE INDEX user_id_idx ON servers(user_id);

-- 证书表
CREATE TABLE certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    server_id INTEGER NOT NULL,
    ca_type VARCHAR(50) NOT NULL,
    private_key TEXT NOT NULL,
    certificate TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers(id)
);

CREATE INDEX domain_idx ON certificates(domain);
CREATE INDEX expires_at_idx ON certificates(expires_at);
CREATE INDEX server_id_idx ON certificates(server_id);
CREATE INDEX status_idx ON certificates(status);

-- 告警表
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    certificate_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id)
);

CREATE INDEX certificate_id_idx ON alerts(certificate_id);
CREATE INDEX status_idx ON alerts(status);
CREATE INDEX type_idx ON alerts(type);

-- 操作日志表
CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id INTEGER NOT NULL,
    ip VARCHAR(45) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX user_id_idx ON operation_logs(user_id);
CREATE INDEX target_type_target_id_idx ON operation_logs(target_type, target_id);
CREATE INDEX created_at_idx ON operation_logs(created_at);

-- 证书部署记录表
CREATE TABLE certificate_deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER NOT NULL,
    deploy_type VARCHAR(50) NOT NULL,
    deploy_target VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id)
);

CREATE INDEX certificate_id_idx ON certificate_deployments(certificate_id);
CREATE INDEX deploy_type_idx ON certificate_deployments(deploy_type);
CREATE INDEX status_idx ON certificate_deployments(status);

-- 初始管理员用户
INSERT INTO users (username, password_hash, email, role, created_at, updated_at)
VALUES ('admin', '$2b$12$1234567890123456789012uGZLCTXlLKw0GETpR5.Pu.ZV0vpbUW6', 'admin@example.com', 'admin', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
```

## 5. 数据库迁移策略

系统将采用版本化的数据库迁移策略，确保数据库结构能够随着系统的迭代而平滑升级。

1. 每个版本的数据库变更都将创建对应的迁移脚本
2. 迁移脚本包含升级（up）和回滚（down）两部分
3. 系统将记录当前数据库版本，并在升级时自动应用未执行的迁移脚本
4. 支持数据库结构的向前兼容，确保旧版客户端仍能正常工作

## 6. 数据安全策略

1. 敏感数据加密：私钥等敏感信息使用AES-256加密存储
2. 密码安全：用户密码使用bcrypt算法加盐哈希存储
3. 访问控制：实施基于角色的访问控制，限制用户只能访问其有权限的数据
4. 审计日志：所有关键操作都记录在操作日志表中，便于追溯
5. 备份策略：定期备份数据库，支持时间点恢复
6. 数据隔离：确保多租户环境下的数据隔离
