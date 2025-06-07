# API设计文档

## 1. 概述

本文档描述了SSL证书自动化管理系统的API设计，包括接口规范、认证机制和错误处理等。系统采用RESTful API设计风格，提供JSON格式的数据交换。

## 2. API基础信息

### 2.1 基础URL

```
https://{server_host}/api/v1
```

### 2.2 认证方式

系统采用JWT（JSON Web Token）进行API认证：

1. 客户端通过登录接口获取JWT令牌
2. 后续请求在HTTP头部添加`Authorization: Bearer {token}`进行认证
3. 服务器端验证令牌的有效性和权限

服务器客户端通过专用Token进行认证：

1. 服务器客户端在安装时生成唯一Token
2. API请求在HTTP头部添加`X-Server-Token: {token}`进行认证
3. 服务器端验证Token的有效性和关联服务器

### 2.3 通用响应格式

所有API响应采用统一的JSON格式：

```json
{
  "code": 200,           // 状态码，200表示成功，非200表示错误
  "message": "success",  // 状态描述
  "data": { ... }        // 响应数据，错误时可能为null
}
```

### 2.4 错误码

| 错误码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |

## 3. API接口设计

### 3.1 用户认证相关接口

#### 3.1.1 用户登录

- **URL**: `/auth/login`
- **方法**: POST
- **描述**: 用户登录并获取JWT令牌
- **请求参数**:

```json
{
  "username": "admin",
  "password": "password"
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

#### 3.1.2 刷新令牌

- **URL**: `/auth/refresh`
- **方法**: POST
- **描述**: 刷新JWT令牌
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600
  }
}
```

#### 3.1.3 用户登出

- **URL**: `/auth/logout`
- **方法**: POST
- **描述**: 用户登出，使当前令牌失效
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

### 3.2 用户管理相关接口

#### 3.2.1 获取用户列表

- **URL**: `/users`
- **方法**: GET
- **描述**: 获取用户列表（仅管理员可用）
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `keyword`: 搜索关键词
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "items": [
      {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "created_at": "2025-01-01T00:00:00Z"
      },
      // ...
    ]
  }
}
```

#### 3.2.2 创建用户

- **URL**: `/users`
- **方法**: POST
- **描述**: 创建新用户（仅管理员可用）
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:

```json
{
  "username": "user1",
  "password": "password",
  "email": "user1@example.com",
  "role": "user"
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "username": "user1",
    "email": "user1@example.com",
    "role": "user",
    "created_at": "2025-06-05T08:42:00Z"
  }
}
```

#### 3.2.3 获取用户详情

- **URL**: `/users/{id}`
- **方法**: GET
- **描述**: 获取用户详情
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "username": "user1",
    "email": "user1@example.com",
    "role": "user",
    "created_at": "2025-06-05T08:42:00Z",
    "updated_at": "2025-06-05T08:42:00Z"
  }
}
```

#### 3.2.4 更新用户

- **URL**: `/users/{id}`
- **方法**: PUT
- **描述**: 更新用户信息
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:

```json
{
  "email": "new_email@example.com",
  "password": "new_password"  // 可选
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "username": "user1",
    "email": "new_email@example.com",
    "role": "user",
    "updated_at": "2025-06-05T08:45:00Z"
  }
}
```

#### 3.2.5 删除用户

- **URL**: `/users/{id}`
- **方法**: DELETE
- **描述**: 删除用户（仅管理员可用）
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

### 3.3 服务器管理相关接口

#### 3.3.1 获取服务器列表

- **URL**: `/servers`
- **方法**: GET
- **描述**: 获取服务器列表
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `keyword`: 搜索关键词
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 50,
    "page": 1,
    "limit": 20,
    "items": [
      {
        "id": 1,
        "name": "web-server-1",
        "ip": "192.168.1.100",
        "os_type": "CentOS 7",
        "version": "1.0.0",
        "auto_renew": true,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
      },
      // ...
    ]
  }
}
```

#### 3.3.2 创建服务器

- **URL**: `/servers`
- **方法**: POST
- **描述**: 创建新服务器记录并生成安装令牌
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:

```json
{
  "name": "web-server-2",
  "auto_renew": true
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "name": "web-server-2",
    "token": "abcdef1234567890",
    "auto_renew": true,
    "created_at": "2025-06-05T08:50:00Z",
    "install_command": "curl -s https://example.com/install.sh | bash -s abcdef1234567890"
  }
}
```

#### 3.3.3 获取服务器详情

- **URL**: `/servers/{id}`
- **方法**: GET
- **描述**: 获取服务器详情
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "name": "web-server-2",
    "ip": "192.168.1.101",
    "os_type": "Ubuntu 22.04",
    "version": "1.0.0",
    "auto_renew": true,
    "created_at": "2025-06-05T08:50:00Z",
    "updated_at": "2025-06-05T08:55:00Z",
    "certificates_count": 5,
    "certificates": [
      {
        "id": 1,
        "domain": "example.com",
        "status": "valid",
        "expires_at": "2025-09-05T08:55:00Z"
      },
      // ...
    ]
  }
}
```

#### 3.3.4 更新服务器

- **URL**: `/servers/{id}`
- **方法**: PUT
- **描述**: 更新服务器信息
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:

```json
{
  "name": "web-server-2-new",
  "auto_renew": false
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "name": "web-server-2-new",
    "auto_renew": false,
    "updated_at": "2025-06-05T09:00:00Z"
  }
}
```

#### 3.3.5 删除服务器

- **URL**: `/servers/{id}`
- **方法**: DELETE
- **描述**: 删除服务器记录
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

#### 3.3.6 服务器注册

- **URL**: `/servers/register`
- **方法**: POST
- **描述**: 客户端注册服务器信息
- **请求头**: `X-Server-Token: {token}`
- **请求参数**:

```json
{
  "ip": "192.168.1.101",
  "os_type": "Ubuntu 22.04",
  "version": "1.0.0",
  "hostname": "web-server-2"
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "name": "web-server-2",
    "auto_renew": true
  }
}
```

#### 3.3.7 服务器心跳

- **URL**: `/servers/heartbeat`
- **方法**: POST
- **描述**: 客户端定期发送心跳
- **请求头**: `X-Server-Token: {token}`
- **请求参数**:

```json
{
  "version": "1.0.0",
  "timestamp": 1717661400
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "server_time": 1717661405,
    "commands": []  // 可能包含需要执行的命令
  }
}
```

### 3.4 证书管理相关接口

#### 3.4.1 获取证书列表

- **URL**: `/certificates`
- **方法**: GET
- **描述**: 获取证书列表
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `keyword`: 搜索关键词
  - `status`: 证书状态筛选
  - `server_id`: 服务器ID筛选
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "items": [
      {
        "id": 1,
        "domain": "example.com",
        "type": "wildcard",
        "status": "valid",
        "created_at": "2025-01-01T00:00:00Z",
        "expires_at": "2025-04-01T00:00:00Z",
        "server": {
          "id": 1,
          "name": "web-server-1"
        },
        "ca_type": "letsencrypt"
      },
      // ...
    ]
  }
}
```

#### 3.4.2 手动申请证书

- **URL**: `/certificates`
- **方法**: POST
- **描述**: 手动申请新证书
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:

```json
{
  "domain": "example.org",
  "type": "wildcard",
  "server_id": 1,
  "ca_type": "letsencrypt",
  "validation_method": "dns"
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 10,
    "domain": "example.org",
    "type": "wildcard",
    "status": "pending",
    "server_id": 1,
    "ca_type": "letsencrypt",
    "validation": {
      "type": "dns",
      "record": "_acme-challenge",
      "value": "randomvalue123",
      "instructions": "请添加以下DNS记录：_acme-challenge.example.org TXT randomvalue123"
    }
  }
}
```

#### 3.4.3 获取证书详情

- **URL**: `/certificates/{id}`
- **方法**: GET
- **描述**: 获取证书详情
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "domain": "example.com",
    "type": "wildcard",
    "status": "valid",
    "created_at": "2025-01-01T00:00:00Z",
    "expires_at": "2025-04-01T00:00:00Z",
    "server": {
      "id": 1,
      "name": "web-server-1"
    },
    "ca_type": "letsencrypt",
    "deployments": [
      {
        "id": 1,
        "deploy_type": "nginx",
        "deploy_target": "/etc/nginx/certs/",
        "status": "success",
        "created_at": "2025-01-01T00:10:00Z"
      }
    ]
  }
}
```

#### 3.4.4 更新证书

- **URL**: `/certificates/{id}`
- **方法**: PUT
- **描述**: 更新证书信息
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:

```json
{
  "auto_renew": false
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "domain": "example.com",
    "auto_renew": false,
    "updated_at": "2025-06-05T09:10:00Z"
  }
}
```

#### 3.4.5 删除证书

- **URL**: `/certificates/{id}`
- **方法**: DELETE
- **描述**: 删除证书记录
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

#### 3.4.6 续期证书

- **URL**: `/certificates/{id}/renew`
- **方法**: POST
- **描述**: 手动续期证书
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "domain": "example.com",
    "status": "renewing",
    "message": "证书续期任务已提交"
  }
}
```

#### 3.4.7 下载证书

- **URL**: `/certificates/{id}/download`
- **方法**: GET
- **描述**: 下载证书文件
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:
  - `format`: 证书格式（nginx/apache/pem/pkcs12）
- **响应**: 二进制文件流

#### 3.4.8 同步证书

- **URL**: `/certificates/sync`
- **方法**: POST
- **描述**: 客户端同步证书信息
- **请求头**: `X-Server-Token: {token}`
- **请求参数**:

```json
{
  "certificates": [
    {
      "domain": "example.com",
      "type": "wildcard",
      "path": "/etc/nginx/certs/example.com.pem",
      "key_path": "/etc/nginx/certs/example.com.key",
      "expires_at": "2025-04-01T00:00:00Z"
    },
    // ...
  ]
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "synced": 5,
    "new": 2,
    "updated": 3
  }
}
```

### 3.5 告警管理相关接口

#### 3.5.1 获取告警列表

- **URL**: `/alerts`
- **方法**: GET
- **描述**: 获取告警列表
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `status`: 告警状态筛选
  - `type`: 告警类型筛选
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 50,
    "page": 1,
    "limit": 20,
    "items": [
      {
        "id": 1,
        "type": "expiry",
        "message": "证书即将过期",
        "status": "pending",
        "created_at": "2025-06-01T00:00:00Z",
        "certificate": {
          "id": 1,
          "domain": "example.com",
          "expires_at": "2025-06-15T00:00:00Z"
        }
      },
      // ...
    ]
  }
}
```

#### 3.5.2 更新告警状态

- **URL**: `/alerts/{id}`
- **方法**: PUT
- **描述**: 更新告警状态
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:

```json
{
  "status": "resolved"
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "status": "resolved",
    "updated_at": "2025-06-05T09:20:00Z"
  }
}
```

### 3.6 操作日志相关接口

#### 3.6.1 获取操作日志

- **URL**: `/logs`
- **方法**: GET
- **描述**: 获取操作日志
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `user_id`: 用户ID筛选
  - `action`: 操作类型筛选
  - `target_type`: 目标类型筛选
  - `start_time`: 开始时间
  - `end_time`: 结束时间
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1000,
    "page": 1,
    "limit": 20,
    "items": [
      {
        "id": 1,
        "user": {
          "id": 1,
          "username": "admin"
        },
        "action": "create",
        "target_type": "certificate",
        "target_id": 1,
        "ip": "192.168.1.1",
        "created_at": "2025-06-05T09:00:00Z"
      },
      // ...
    ]
  }
}
```

### 3.7 系统设置相关接口

#### 3.7.1 获取系统设置

- **URL**: `/settings`
- **方法**: GET
- **描述**: 获取系统设置
- **请求头**: `Authorization: Bearer {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "default_ca": "letsencrypt",
    "renew_before_days": 15,
    "alert_before_days": 30,
    "webhook_url": "https://example.com/webhook",
    "email_notification": true,
    "notification_email": "admin@example.com"
  }
}
```

#### 3.7.2 更新系统设置

- **URL**: `/settings`
- **方法**: PUT
- **描述**: 更新系统设置
- **请求头**: `Authorization: Bearer {token}`
- **请求参数**:

```json
{
  "default_ca": "zerossl",
  "renew_before_days": 20,
  "alert_before_days": 25,
  "webhook_url": "https://example.com/new-webhook",
  "email_notification": true,
  "notification_email": "new-admin@example.com"
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "default_ca": "zerossl",
    "renew_before_days": 20,
    "alert_before_days": 25,
    "webhook_url": "https://example.com/new-webhook",
    "email_notification": true,
    "notification_email": "new-admin@example.com",
    "updated_at": "2025-06-05T09:30:00Z"
  }
}
```

## 4. Webhook接口

系统支持通过Webhook向外部系统推送事件通知。

### 4.1 Webhook数据格式

```json
{
  "event": "certificate.expiry",  // 事件类型
  "timestamp": 1717661400,        // 事件时间戳
  "data": {                       // 事件数据
    "certificate_id": 1,
    "domain": "example.com",
    "expires_at": "2025-06-15T00:00:00Z",
    "days_left": 10
  }
}
```

### 4.2 事件类型

| 事件类型 | 描述 |
|---------|------|
| certificate.created | 证书创建 |
| certificate.renewed | 证书续期 |
| certificate.expired | 证书过期 |
| certificate.expiry | 证书即将过期 |
| certificate.deployed | 证书部署 |
| server.registered | 服务器注册 |
| server.offline | 服务器离线 |
| alert.created | 告警创建 |

## 5. 客户端API

客户端脚本通过以下API与服务端通信：

### 5.1 客户端注册

- **URL**: `/client/register`
- **方法**: POST
- **描述**: 客户端首次注册
- **请求头**: `X-Server-Token: {token}`
- **请求参数**:

```json
{
  "hostname": "web-server-1",
  "ip": "192.168.1.100",
  "os_type": "CentOS 7",
  "version": "1.0.0"
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "server_id": 1,
    "name": "web-server-1",
    "auto_renew": true,
    "settings": {
      "default_ca": "letsencrypt",
      "renew_before_days": 15
    }
  }
}
```

### 5.2 证书同步

- **URL**: `/client/certificates/sync`
- **方法**: POST
- **描述**: 同步证书信息
- **请求头**: `X-Server-Token: {token}`
- **请求参数**:

```json
{
  "certificates": [
    {
      "domain": "example.com",
      "type": "wildcard",
      "path": "/etc/nginx/certs/example.com.pem",
      "key_path": "/etc/nginx/certs/example.com.key",
      "expires_at": "2025-04-01T00:00:00Z"
    }
  ]
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "synced": 1,
    "certificates": [
      {
        "id": 1,
        "domain": "example.com",
        "status": "valid",
        "auto_renew": true
      }
    ]
  }
}
```

### 5.3 获取任务

- **URL**: `/client/tasks`
- **方法**: GET
- **描述**: 获取需要执行的任务
- **请求头**: `X-Server-Token: {token}`
- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "tasks": [
      {
        "id": 1,
        "type": "renew",
        "certificate_id": 1,
        "domain": "example.com",
        "params": {
          "ca_type": "letsencrypt",
          "validation_method": "dns"
        }
      }
    ]
  }
}
```

### 5.4 更新任务状态

- **URL**: `/client/tasks/{id}`
- **方法**: PUT
- **描述**: 更新任务执行状态
- **请求头**: `X-Server-Token: {token}`
- **请求参数**:

```json
{
  "status": "completed",
  "result": {
    "success": true,
    "message": "证书续期成功",
    "certificate": {
      "domain": "example.com",
      "expires_at": "2025-10-01T00:00:00Z",
      "path": "/etc/nginx/certs/example.com.pem",
      "key_path": "/etc/nginx/certs/example.com.key"
    }
  }
}
```

- **响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

## 6. API版本控制

系统采用URL路径中的版本号进行API版本控制：

1. `/api/v1/...` - 当前版本
2. 未来版本将使用 `/api/v2/...` 等路径

当API发生不兼容变更时，将发布新版本API，并保持旧版本API一段时间以便客户端迁移。

## 7. API限流策略

为保护系统稳定性，API实施以下限流策略：

1. 基于IP的限流：每IP每分钟最多100次请求
2. 基于用户的限流：每用户每分钟最多200次请求
3. 基于接口的限流：敏感接口（如登录）每IP每分钟最多10次请求

超出限制的请求将返回429状态码。

## 8. API文档生成

系统使用OpenAPI 3.0规范描述API，并自动生成交互式API文档。

API文档访问地址：`/api/docs`
