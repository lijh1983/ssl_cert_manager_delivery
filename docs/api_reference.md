# SSL证书自动化管理系统 - API文档

## 概述

本文档详细描述了SSL证书自动化管理系统的RESTful API接口，供开发人员集成和使用。

API基础URL: `https://api.yourdomain.com/api/v1`

## 认证

除了登录接口外，所有API请求都需要认证。认证方式如下：

### 用户认证

使用Bearer Token认证：
```
Authorization: Bearer <token>
```

Token通过登录接口获取，有效期为1小时。

### 服务器认证

客户端API使用服务器令牌认证：
```
X-Server-Token: <server_token>
```

服务器令牌在创建服务器时生成。

## 响应格式

所有API响应均使用JSON格式，结构如下：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

- `code`: 状态码，200表示成功，其他值表示错误
- `message`: 状态描述
- `data`: 响应数据

## 错误码

- 200: 成功
- 400: 请求参数错误
- 401: 未认证或认证失败
- 403: 权限不足
- 404: 资源不存在
- 409: 资源冲突
- 500: 服务器内部错误

## API接口

### 认证API

#### 用户登录

- **URL**: `/auth/login`
- **方法**: `POST`
- **认证**: 不需要
- **请求体**:
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

#### 刷新令牌

- **URL**: `/auth/refresh`
- **方法**: `POST`
- **认证**: 需要
- **请求体**: 无
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

#### 用户登出

- **URL**: `/auth/logout`
- **方法**: `POST`
- **认证**: 需要
- **请求体**: 无
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": null
  }
  ```

### 用户API

#### 获取用户列表

- **URL**: `/users`
- **方法**: `GET`
- **认证**: 需要（管理员）
- **参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `keyword`: 搜索关键词
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "total": 10,
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
        ...
      ]
    }
  }
  ```

#### 创建用户

- **URL**: `/users`
- **方法**: `POST`
- **认证**: 需要（管理员）
- **请求体**:
  ```json
  {
    "username": "user1",
    "email": "user1@example.com",
    "password": "password",
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
      "created_at": "2025-06-05T09:00:00Z"
    }
  }
  ```

#### 获取用户详情

- **URL**: `/users/{id}`
- **方法**: `GET`
- **认证**: 需要（管理员或本人）
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
      "created_at": "2025-06-05T09:00:00Z",
      "updated_at": "2025-06-05T09:00:00Z"
    }
  }
  ```

#### 更新用户信息

- **URL**: `/users/{id}`
- **方法**: `PUT`
- **认证**: 需要（管理员或本人）
- **请求体**:
  ```json
  {
    "email": "newemail@example.com",
    "password": "newpassword",
    "role": "admin"
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
      "email": "newemail@example.com",
      "role": "admin",
      "updated_at": "2025-06-05T10:00:00Z"
    }
  }
  ```

#### 删除用户

- **URL**: `/users/{id}`
- **方法**: `DELETE`
- **认证**: 需要（管理员）
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": null
  }
  ```

### 服务器API

#### 获取服务器列表

- **URL**: `/servers`
- **方法**: `GET`
- **认证**: 需要
- **参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `keyword`: 搜索关键词
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "total": 5,
      "page": 1,
      "limit": 20,
      "items": [
        {
          "id": 1,
          "name": "Web Server 1",
          "ip": "192.168.1.100",
          "os_type": "Ubuntu 22.04",
          "status": "online",
          "last_seen": "2025-06-05T08:00:00Z",
          "auto_renew": true,
          "created_at": "2025-01-01T00:00:00Z"
        },
        ...
      ]
    }
  }
  ```

#### 创建服务器

- **URL**: `/servers`
- **方法**: `POST`
- **认证**: 需要
- **请求体**:
  ```json
  {
    "name": "Web Server 2",
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
      "name": "Web Server 2",
      "token": "server_token_123456",
      "auto_renew": true,
      "created_at": "2025-06-05T09:00:00Z",
      "install_command": "curl -s https://example.com/install.sh | bash -s server_token_123456"
    }
  }
  ```

#### 获取服务器详情

- **URL**: `/servers/{id}`
- **方法**: `GET`
- **认证**: 需要
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "id": 2,
      "name": "Web Server 2",
      "ip": "192.168.1.101",
      "os_type": "CentOS 7",
      "hostname": "web2",
      "version": "1.0.0",
      "status": "online",
      "last_seen": "2025-06-05T09:30:00Z",
      "auto_renew": true,
      "created_at": "2025-06-05T09:00:00Z",
      "updated_at": "2025-06-05T09:30:00Z",
      "certificates_count": 3,
      "certificates": [
        {
          "id": 1,
          "domain": "example.com",
          "type": "single",
          "status": "valid",
          "expires_at": "2025-09-05T00:00:00Z"
        },
        ...
      ]
    }
  }
  ```

#### 更新服务器信息

- **URL**: `/servers/{id}`
- **方法**: `PUT`
- **认证**: 需要
- **请求体**:
  ```json
  {
    "name": "Web Server 2 - Updated",
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
      "name": "Web Server 2 - Updated",
      "auto_renew": false,
      "updated_at": "2025-06-05T10:00:00Z"
    }
  }
  ```

#### 删除服务器

- **URL**: `/servers/{id}`
- **方法**: `DELETE`
- **认证**: 需要
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": null
  }
  ```

#### 客户端注册服务器信息

- **URL**: `/servers/register`
- **方法**: `POST`
- **认证**: 需要（服务器令牌）
- **请求体**:
  ```json
  {
    "hostname": "web2",
    "ip": "192.168.1.101",
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
      "id": 2,
      "name": "Web Server 2",
      "auto_renew": true
    }
  }
  ```

#### 客户端发送心跳

- **URL**: `/servers/heartbeat`
- **方法**: `POST`
- **认证**: 需要（服务器令牌）
- **请求体**:
  ```json
  {
    "version": "1.0.0",
    "timestamp": 1717574400
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "server_time": 1717574405,
      "commands": []
    }
  }
  ```

### 证书API

#### 获取证书列表

- **URL**: `/certificates`
- **方法**: `GET`
- **认证**: 需要
- **参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `keyword`: 搜索关键词
  - `status`: 状态过滤
  - `server_id`: 服务器ID过滤
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "total": 10,
      "page": 1,
      "limit": 20,
      "items": [
        {
          "id": 1,
          "domain": "example.com",
          "type": "single",
          "server_id": 2,
          "server_name": "Web Server 2",
          "status": "valid",
          "expires_at": "2025-09-05T00:00:00Z",
          "created_at": "2025-06-05T09:00:00Z"
        },
        ...
      ]
    }
  }
  ```

#### 创建证书

- **URL**: `/certificates`
- **方法**: `POST`
- **认证**: 需要
- **请求体**:
  ```json
  {
    "domain": "api.example.com",
    "server_id": 2,
    "type": "single",
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
      "id": 2,
      "domain": "api.example.com",
      "type": "single",
      "status": "pending",
      "server_id": 2,
      "ca_type": "letsencrypt",
      "validation": {
        "type": "dns",
        "record": "_acme-challenge",
        "value": "randomvalue123",
        "instructions": "请添加以下DNS记录：_acme-challenge.api.example.com TXT randomvalue123"
      }
    }
  }
  ```

#### 获取证书详情

- **URL**: `/certificates/{id}`
- **方法**: `GET`
- **认证**: 需要
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "id": 2,
      "domain": "api.example.com",
      "type": "single",
      "server_id": 2,
      "status": "valid",
      "ca_type": "letsencrypt",
      "expires_at": "2025-09-05T00:00:00Z",
      "created_at": "2025-06-05T09:00:00Z",
      "updated_at": "2025-06-05T09:30:00Z",
      "server": {
        "id": 2,
        "name": "Web Server 2"
      },
      "deployments": [
        {
          "id": 1,
          "type": "nginx",
          "path": "/etc/nginx/certs/api.example.com.crt",
          "created_at": "2025-06-05T09:30:00Z"
        }
      ]
    }
  }
  ```

#### 更新证书信息

- **URL**: `/certificates/{id}`
- **方法**: `PUT`
- **认证**: 需要
- **请求体**:
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
      "id": 2,
      "domain": "api.example.com",
      "auto_renew": false,
      "updated_at": "2025-06-05T10:00:00Z"
    }
  }
  ```

#### 删除证书

- **URL**: `/certificates/{id}`
- **方法**: `DELETE`
- **认证**: 需要
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": null
  }
  ```

#### 续期证书

- **URL**: `/certificates/{id}/renew`
- **方法**: `POST`
- **认证**: 需要
- **请求体**: 无
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "id": 2,
      "domain": "api.example.com",
      "status": "renewing",
      "message": "证书续期任务已提交"
    }
  }
  ```

#### 同步证书信息

- **URL**: `/certificates/sync`
- **方法**: `POST`
- **认证**: 需要（服务器令牌）
- **请求体**:
  ```json
  {
    "certificates": [
      {
        "domain": "example.com",
        "path": "/etc/nginx/certs/example.com.crt",
        "key_path": "/etc/nginx/certs/example.com.key",
        "expires_at": "2025-09-05T00:00:00Z",
        "type": "single"
      },
      ...
    ]
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "synced": 3,
      "new": 1,
      "updated": 2
    }
  }
  ```

### 告警API

#### 获取告警列表

- **URL**: `/alerts`
- **方法**: `GET`
- **认证**: 需要
- **参数**:
  - `page`: 页码，默认1
  - `limit`: 每页数量，默认20
  - `status`: 状态过滤
  - `type`: 类型过滤
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "total": 5,
      "page": 1,
      "limit": 20,
      "items": [
        {
          "id": 1,
          "type": "expiry",
          "message": "证书 example.com 将在 15 天后过期",
          "status": "pending",
          "certificate_id": 1,
          "created_at": "2025-06-05T08:00:00Z",
          "certificate": {
            "domain": "example.com",
            "expires_at": "2025-06-20T00:00:00Z"
          }
        },
        ...
      ]
    }
  }
  ```

#### 更新告警状态

- **URL**: `/alerts/{id}`
- **方法**: `PUT`
- **认证**: 需要
- **请求体**:
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
      "updated_at": "2025-06-05T10:00:00Z"
    }
  }
  ```

### 系统设置API

#### 获取系统设置

- **URL**: `/settings`
- **方法**: `GET`
- **认证**: 需要（管理员）
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "renew_before_days": "15",
      "alert_before_days": "30",
      "default_ca": "letsencrypt"
    }
  }
  ```

#### 更新系统设置

- **URL**: `/settings`
- **方法**: `PUT`
- **认证**: 需要（管理员）
- **请求体**:
  ```json
  {
    "renew_before_days": "20",
    "alert_before_days": "25",
    "default_ca": "zerossl"
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "renew_before_days": "20",
      "alert_before_days": "25",
      "default_ca": "zerossl",
      "updated_at": "2025-06-05T10:00:00Z"
    }
  }
  ```

### 客户端API

#### 客户端首次注册

- **URL**: `/client/register`
- **方法**: `POST`
- **认证**: 需要（服务器令牌）
- **请求体**:
  ```json
  {
    "hostname": "web2",
    "ip": "192.168.1.101",
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
      "server_id": 2,
      "name": "Web Server 2",
      "auto_renew": true,
      "settings": {
        "default_ca": "letsencrypt",
        "renew_before_days": 15
      }
    }
  }
  ```

#### 获取客户端任务

- **URL**: `/client/tasks`
- **方法**: `GET`
- **认证**: 需要（服务器令牌）
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
        },
        ...
      ]
    }
  }
  ```

#### 更新客户端任务状态

- **URL**: `/client/tasks/{id}`
- **方法**: `PUT`
- **认证**: 需要（服务器令牌）
- **请求体**:
  ```json
  {
    "status": "completed",
    "result": {
      "success": true,
      "message": "证书续期成功",
      "certificate": {
        "id": 1,
        "domain": "example.com",
        "expires_at": "2025-09-05T00:00:00Z",
        "path": "/etc/nginx/certs/example.com.crt",
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

## 状态码

### HTTP状态码

- 200 OK: 请求成功
- 400 Bad Request: 请求参数错误
- 401 Unauthorized: 未认证或认证失败
- 403 Forbidden: 权限不足
- 404 Not Found: 资源不存在
- 409 Conflict: 资源冲突
- 500 Internal Server Error: 服务器内部错误

### 业务状态码

- 200: 成功
- 400: 请求参数错误
- 401: 未认证或认证失败
- 403: 权限不足
- 404: 资源不存在
- 409: 资源冲突
- 500: 服务器内部错误

## 数据模型

### 用户(User)

| 字段名      | 类型         | 说明                 |
|------------|--------------|---------------------|
| id         | INTEGER      | 主键，自增           |
| username   | VARCHAR(50)  | 用户名，唯一         |
| password   | VARCHAR(100) | 密码哈希             |
| email      | VARCHAR(100) | 电子邮箱             |
| role       | VARCHAR(20)  | 角色(admin/user)     |
| created_at | TIMESTAMP    | 创建时间             |
| updated_at | TIMESTAMP    | 更新时间             |

### 服务器(Server)

| 字段名       | 类型         | 说明                 |
|-------------|--------------|---------------------|
| id          | INTEGER      | 主键，自增           |
| name        | VARCHAR(100) | 服务器名称           |
| token       | VARCHAR(100) | 服务器令牌，唯一     |
| user_id     | INTEGER      | 所属用户ID           |
| ip          | VARCHAR(50)  | IP地址               |
| os_type     | VARCHAR(50)  | 操作系统类型         |
| hostname    | VARCHAR(100) | 主机名               |
| version     | VARCHAR(20)  | 客户端版本           |
| auto_renew  | BOOLEAN      | 是否自动续期         |
| last_seen   | TIMESTAMP    | 最后心跳时间         |
| status      | VARCHAR(20)  | 状态(online/offline) |
| created_at  | TIMESTAMP    | 创建时间             |
| updated_at  | TIMESTAMP    | 更新时间             |

### 证书(Certificate)

| 字段名       | 类型         | 说明                                  |
|-------------|--------------|--------------------------------------|
| id          | INTEGER      | 主键，自增                            |
| domain      | VARCHAR(255) | 域名                                  |
| type        | VARCHAR(20)  | 类型(single/wildcard/multi)           |
| server_id   | INTEGER      | 所属服务器ID                          |
| status      | VARCHAR(20)  | 状态(valid/expired/pending/error)     |
| ca_type     | VARCHAR(20)  | CA类型(letsencrypt/zerossl)           |
| certificate | TEXT         | 证书内容                              |
| private_key | TEXT         | 私钥内容                              |
| expires_at  | TIMESTAMP    | 过期时间                              |
| auto_renew  | BOOLEAN      | 是否自动续期                          |
| created_at  | TIMESTAMP    | 创建时间                              |
| updated_at  | TIMESTAMP    | 更新时间                              |

### 证书部署(Deployment)

| 字段名          | 类型         | 说明                 |
|----------------|--------------|---------------------|
| id             | INTEGER      | 主键，自增           |
| certificate_id | INTEGER      | 证书ID               |
| type           | VARCHAR(20)  | 部署类型(nginx/apache)|
| path           | VARCHAR(255) | 部署路径             |
| created_at     | TIMESTAMP    | 创建时间             |

### 告警(Alert)

| 字段名          | 类型         | 说明                                |
|----------------|--------------|-------------------------------------|
| id             | INTEGER      | 主键，自增                           |
| type           | VARCHAR(20)  | 类型(expiry/error/revoke)            |
| message        | TEXT         | 告警消息                             |
| status         | VARCHAR(20)  | 状态(pending/sent/resolved)          |
| certificate_id | INTEGER      | 相关证书ID                           |
| created_at     | TIMESTAMP    | 创建时间                             |
| updated_at     | TIMESTAMP    | 更新时间                             |

### 设置(Setting)

| 字段名      | 类型         | 说明                 |
|------------|--------------|---------------------|
| key        | VARCHAR(50)  | 设置键名，主键        |
| value      | TEXT         | 设置值               |
| created_at | TIMESTAMP    | 创建时间             |
| updated_at | TIMESTAMP    | 更新时间             |

## 版本历史

| 版本  | 日期       | 描述                           |
|------|------------|-------------------------------|
| 1.0.0 | 2025-06-05 | 初始版本                       |

## 附录

### 证书状态

- `valid`: 有效
- `expired`: 已过期
- `pending`: 待处理
- `renewing`: 续期中
- `error`: 错误

### 告警类型

- `expiry`: 过期预警
- `error`: 错误告警
- `revoke`: 吊销告警

### 告警状态

- `pending`: 待处理
- `sent`: 已发送
- `resolved`: 已解决

### 任务类型

- `renew`: 续期任务
- `deploy`: 部署任务
- `sync`: 同步任务
