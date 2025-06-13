# MySQL安全合规指南

## 🚨 重要安全修正

### 问题说明
之前的配置中包含了`MYSQL_ROOT_PASSWORD`环境变量，这是一个严重的安全违规！

### 为什么MYSQL_ROOT_PASSWORD不合规？

#### 1. **最小权限原则违反**
- 应用程序不应该拥有数据库管理员权限
- Root用户拥有所有数据库的完全控制权
- 应用程序只需要访问自己的数据库

#### 2. **安全风险**
- 如果应用程序被攻击，攻击者可能获得整个数据库系统的控制权
- Root密码泄露会影响所有数据库
- 违反了数据库安全最佳实践

#### 3. **合规要求**
- 大多数安全标准（如ISO 27001、SOC 2）要求最小权限访问
- 金融、医疗等行业的合规要求禁止应用程序使用管理员账户
- 安全审计会将此标记为高风险问题

## ✅ 正确的安全配置

### 1. **应用程序数据库用户**
```sql
-- 创建专用的应用程序用户
CREATE USER 'ssl_manager'@'%' IDENTIFIED BY 'secure_password';

-- 只授予必要的权限
GRANT SELECT, INSERT, UPDATE, DELETE ON ssl_manager.* TO 'ssl_manager'@'%';

-- 不要授予以下权限：
-- GRANT ALL PRIVILEGES  ❌ 权限过大
-- GRANT SUPER           ❌ 管理员权限
-- GRANT CREATE USER     ❌ 用户管理权限
-- GRANT RELOAD          ❌ 服务器管理权限
```

### 2. **环境变量配置**
```bash
# ✅ 正确：应用程序使用专用用户
MYSQL_USER=ssl_manager
MYSQL_PASSWORD=secure_application_password

# ❌ 错误：应用程序不应该知道root密码
# MYSQL_ROOT_PASSWORD=root_password
```

### 3. **Docker容器配置**
```yaml
# docker-compose.yml
services:
  mysql:
    environment:
      # 容器初始化需要root密码（仅用于创建数据库和用户）
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-secure_root_password}
      # 应用程序使用的数据库和用户
      MYSQL_DATABASE: ${MYSQL_DATABASE:-ssl_manager}
      MYSQL_USER: ${MYSQL_USER:-ssl_manager}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-secure_app_password}
    
    # ✅ 健康检查使用应用程序用户
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-u", "${MYSQL_USER}", "-p${MYSQL_PASSWORD}"]
```

## 🔧 已修正的配置

### 1. **环境变量文件**
- ✅ 从`.env.example`中移除了`MYSQL_ROOT_PASSWORD`
- ✅ 从`.env.docker.example`中移除了`MYSQL_ROOT_PASSWORD`
- ✅ 添加了安全说明注释

### 2. **Docker Compose文件**
- ✅ 健康检查改为使用应用程序用户
- ✅ 应用程序连接使用专用用户
- ✅ Root密码仅用于容器初始化

### 3. **验证脚本**
- ✅ 添加了安全违规检查
- ✅ 会警告不合规的配置

## 🛡️ 安全最佳实践

### 1. **权限分离**
```sql
-- 应用程序用户：只能访问应用数据库
GRANT SELECT, INSERT, UPDATE, DELETE ON ssl_manager.* TO 'ssl_manager'@'%';

-- 备份用户：只读权限
CREATE USER 'backup_user'@'localhost' IDENTIFIED BY 'backup_password';
GRANT SELECT, LOCK TABLES ON ssl_manager.* TO 'backup_user'@'localhost';

-- 监控用户：只能查看状态
CREATE USER 'monitor_user'@'%' IDENTIFIED BY 'monitor_password';
GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'monitor_user'@'%';
```

### 2. **网络安全**
```sql
-- 限制用户的网络访问
CREATE USER 'ssl_manager'@'192.168.1.%' IDENTIFIED BY 'password';  -- 只允许特定网段
CREATE USER 'ssl_manager'@'app-server' IDENTIFIED BY 'password';   -- 只允许特定主机
```

### 3. **密码策略**
```sql
-- 设置密码策略
SET GLOBAL validate_password.policy = STRONG;
SET GLOBAL validate_password.length = 12;
SET GLOBAL validate_password.mixed_case_count = 1;
SET GLOBAL validate_password.number_count = 1;
SET GLOBAL validate_password.special_char_count = 1;
```

### 4. **审计日志**
```sql
-- 启用审计日志
SET GLOBAL general_log = 'ON';
SET GLOBAL log_output = 'FILE';
SET GLOBAL general_log_file = '/var/log/mysql/general.log';
```

## 🔍 安全检查清单

### ✅ 应用程序配置检查
- [ ] 应用程序不使用root用户连接数据库
- [ ] 应用程序用户只有必要的权限
- [ ] 密码符合强度要求
- [ ] 连接使用SSL（生产环境）
- [ ] 网络访问受限

### ✅ 环境变量检查
- [ ] 不包含MYSQL_ROOT_PASSWORD
- [ ] 使用专用的MYSQL_USER和MYSQL_PASSWORD
- [ ] 密码不是默认值
- [ ] 配置文件不提交到版本控制

### ✅ Docker配置检查
- [ ] 健康检查使用应用程序用户
- [ ] 容器间网络隔离
- [ ] 数据卷权限正确
- [ ] 日志配置安全

## 🚨 安全事件响应

### 如果发现root密码泄露
1. **立即更改root密码**
   ```sql
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_secure_password';
   ```

2. **检查访问日志**
   ```bash
   # 检查MySQL访问日志
   grep "root" /var/log/mysql/general.log
   
   # 检查应用程序日志
   grep -i "root\|admin" /app/logs/ssl_manager.log
   ```

3. **审查用户权限**
   ```sql
   -- 查看所有用户
   SELECT user, host FROM mysql.user;
   
   -- 查看用户权限
   SHOW GRANTS FOR 'ssl_manager'@'%';
   ```

4. **加强监控**
   ```sql
   -- 启用失败登录日志
   SET GLOBAL log_error_verbosity = 3;
   ```

## 📋 合规文档

### 1. **权限矩阵**
| 用户类型 | 数据库权限 | 网络访问 | 用途 |
|----------|------------|----------|------|
| ssl_manager | SELECT, INSERT, UPDATE, DELETE on ssl_manager.* | 应用服务器 | 应用程序 |
| backup_user | SELECT, LOCK TABLES on ssl_manager.* | 备份服务器 | 数据备份 |
| monitor_user | PROCESS, REPLICATION CLIENT | 监控服务器 | 性能监控 |
| root | ALL PRIVILEGES | localhost only | 系统管理 |

### 2. **访问控制记录**
- 所有数据库用户都有明确的业务用途
- 权限遵循最小权限原则
- 定期审查和清理不必要的权限
- 所有权限变更都有审批记录

## 🎯 总结

通过移除`MYSQL_ROOT_PASSWORD`环境变量，我们：

1. **提高了安全性**：应用程序不再拥有数据库管理员权限
2. **符合合规要求**：遵循最小权限原则
3. **降低了风险**：即使应用程序被攻击，数据库系统仍然安全
4. **改善了可维护性**：权限清晰，职责分离

这是一个重要的安全修正，感谢您的提醒！

---

**重要提醒**: 
- 🔴 **绝不要**让应用程序使用数据库root用户
- 🔴 **绝不要**在应用程序配置中存储root密码
- 🟢 **务必**为每个应用程序创建专用数据库用户
- 🟢 **务必**遵循最小权限原则
