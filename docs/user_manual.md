# SSL证书自动化管理系统用户手册

## 📋 目录

- [系统概述](#系统概述)
- [核心管理脚本使用](#核心管理脚本使用)
- [Alpine优化工具使用](#alpine优化工具使用)
- [Web界面使用](#web界面使用)
- [常见问题](#常见问题)

## 1. 系统概述

SSL证书自动化管理系统是一个专为网站和服务器管理员设计的证书生命周期管理工具。本系统基于acme.sh开源项目，提供了友好的Web界面和强大的自动化功能，帮助用户轻松管理多台服务器上的SSL证书，实现自动检测、申请、续期和部署，大幅降低证书管理的人工成本和安全风险。

### 1.1 主要功能

- **自动续期与证书管理**：自动检测证书有效期并提前续期，支持多种类型证书（单域名、通配符、多域名）
- **多环境适配能力**：兼容主流Linux发行版和Web服务器，支持多种云服务商证书同步
- **部署与验证机制**：提供DNS验证和HTTP验证两种方式，自动扫描服务器配置
- **集中化管理**：通过Web控制台集中管理多台服务器的证书，提供详细的统计和监控
- **告警与通知**：证书即将过期或续期失败时发送告警通知

### 1.2 系统架构

系统由以下几个主要组件构成：

- **Web控制台**：提供用户界面，用于管理服务器、证书和系统设置
- **API服务**：处理前端请求，提供RESTful API接口
- **客户端脚本**：部署在各服务器上，负责证书扫描、申请和续期
- **数据库**：存储服务器、证书和用户信息

## 2. 核心管理脚本使用

系统提供了统一的核心管理脚本，整合了部署、验证、修复、测试等核心功能。

### 2.1 ssl-manager.sh 核心管理脚本

#### 脚本位置
```bash
scripts/ssl-manager.sh
```

#### 基本用法
```bash
# 查看帮助信息
./scripts/ssl-manager.sh help

# 部署系统
./scripts/ssl-manager.sh deploy --domain your-domain.com --email admin@your-domain.com

# 验证系统
./scripts/ssl-manager.sh verify --all

# 修复问题
./scripts/ssl-manager.sh fix --docker-compose

# 查看状态
./scripts/ssl-manager.sh status
```

#### 部署命令详解
```bash
# 基本部署
./scripts/ssl-manager.sh deploy --domain ssl.example.com --email admin@example.com

# 阿里云优化部署
./scripts/ssl-manager.sh deploy --domain ssl.example.com --email admin@example.com --aliyun --monitoring
```

#### 验证命令详解
```bash
# 全面验证
./scripts/ssl-manager.sh verify --all

# 分项验证
./scripts/ssl-manager.sh verify --docker    # 验证Docker环境
./scripts/ssl-manager.sh verify --compose   # 验证Docker Compose配置
./scripts/ssl-manager.sh verify --network   # 验证网络连接
```

#### 修复命令详解
```bash
./scripts/ssl-manager.sh fix --docker-compose   # 修复Docker Compose配置
./scripts/ssl-manager.sh fix --python-images    # 修复Python镜像问题
./scripts/ssl-manager.sh fix --alpine-sources   # 修复Alpine镜像源
./scripts/ssl-manager.sh fix --permissions      # 修复文件权限
```

### 2.2 alpine-optimizer.sh Alpine优化工具

#### 脚本位置
```bash
scripts/alpine-optimizer.sh
```

#### 基本用法
```bash
# 自动优化Alpine镜像源
./scripts/alpine-optimizer.sh optimize --auto

# 测试Alpine构建速度
./scripts/alpine-optimizer.sh test --build

# 验证优化效果
./scripts/alpine-optimizer.sh verify

# 恢复原始配置
./scripts/alpine-optimizer.sh restore
```

#### 优化命令详解
```bash
# 自动选择最快镜像源
./scripts/alpine-optimizer.sh optimize --auto

# 指定镜像源
./scripts/alpine-optimizer.sh optimize --aliyun  # 使用阿里云镜像源
./scripts/alpine-optimizer.sh optimize --ustc    # 使用中科大镜像源
./scripts/alpine-optimizer.sh optimize --tuna    # 使用清华镜像源
```

## 3. 快速入门

### 2.1 系统登录

1. 打开浏览器，访问系统URL（如 https://cert-manager.example.com）
2. 输入管理员提供的用户名和密码
3. 点击"登录"按钮进入系统

### 2.2 添加服务器

1. 在左侧菜单中点击"服务器管理"
2. 点击右上角"添加服务器"按钮
3. 填写服务器名称，点击"确定"
4. 系统会生成一个服务器令牌和安装命令
5. 复制安装命令，在目标服务器上执行

```bash
curl -s https://cert-manager.example.com/install.sh | bash -s YOUR_TOKEN
```

6. 安装完成后，服务器会自动在控制台中显示状态为"在线"

### 2.3 证书管理

#### 2.3.1 查看证书

1. 在左侧菜单中点击"证书管理"
2. 系统会显示所有服务器上的证书列表
3. 可以使用过滤器按域名、状态或服务器筛选证书

#### 2.3.2 申请新证书

1. 在证书管理页面，点击"申请证书"按钮
2. 选择目标服务器
3. 输入域名（支持通配符，如 *.example.com）
4. 选择验证方式（DNS或HTTP）
5. 点击"申请"按钮
6. 按照系统提示完成验证步骤
7. 验证成功后，证书会自动部署到服务器

#### 2.3.3 手动续期证书

1. 在证书列表中找到需要续期的证书
2. 点击"操作"列中的"续期"按钮
3. 确认续期操作
4. 系统会在后台执行续期任务，完成后自动更新证书状态

## 3. 功能详解

### 3.1 仪表盘

仪表盘提供系统整体状态的可视化视图，包括：

- 证书总数统计
- 即将过期证书数量
- 服务器状态分布
- 证书类型分布图表
- 最近告警列表
- 即将过期证书列表

### 3.2 服务器管理

#### 3.2.1 服务器列表

显示所有已添加的服务器，包括以下信息：

- 服务器名称
- IP地址
- 操作系统
- 状态（在线/离线）
- 最后心跳时间
- 证书数量
- 操作选项

#### 3.2.2 服务器详情

点击服务器名称可查看详细信息：

- 基本信息（名称、IP、系统版本等）
- 证书列表
- 心跳历史
- 操作日志

#### 3.2.3 服务器设置

可以修改以下服务器设置：

- 服务器名称
- 自动续期开关
- 告警通知设置

### 3.3 证书管理

#### 3.3.1 证书列表

显示所有证书，包括以下信息：

- 域名
- 证书类型（单域名/通配符/多域名）
- 状态（有效/即将过期/已过期）
- 过期时间
- 剩余有效期
- 所属服务器
- 操作选项

#### 3.3.2 证书详情

点击证书域名可查看详细信息：

- 基本信息（域名、类型、状态等）
- 证书内容（可查看完整证书信息）
- 部署位置
- 续期历史
- 相关告警

#### 3.3.3 证书操作

可以对证书执行以下操作：

- 续期：手动触发证书续期
- 下载：下载证书文件（支持多种格式）
- 部署：将证书部署到其他位置
- 删除：从系统中删除证书记录

### 3.4 告警管理

#### 3.4.1 告警列表

显示所有系统告警，包括：

- 告警类型（过期预警/续期失败/服务器离线等）
- 告警内容
- 告警时间
- 状态（未处理/已处理/已忽略）
- 相关资源（证书/服务器）

#### 3.4.2 告警设置

可以配置以下告警设置：

- 过期预警时间（默认15天）
- 告警通知方式（邮件/短信/webhook）
- 通知接收人

### 3.5 系统设置

#### 3.5.1 用户管理

管理员可以管理系统用户：

- 添加新用户
- 修改用户权限
- 重置用户密码
- 禁用/启用用户

#### 3.5.2 全局设置

配置系统全局参数：

- 默认CA提供商（Let's Encrypt/ZeroSSL等）
- 默认证书参数（密钥类型、长度等）
- 自动续期提前天数
- 系统日志保留时间

## 4. 高级功能

### 4.1 多云平台证书同步

系统支持将证书自动同步到各大云服务商：

1. 在系统设置中配置云服务商API凭证
2. 在证书详情页选择"同步到云服务"
3. 选择目标云服务商和服务类型
4. 点击"同步"按钮

支持的云服务商：
- 阿里云（CDN/SLB/OSS）
- 腾讯云（CDN/CLB）
- 华为云
- 火山引擎
- 优刻得

### 4.2 批量操作

系统支持对多个证书或服务器执行批量操作：

1. 在列表页使用复选框选择多个项目
2. 点击批量操作按钮
3. 选择要执行的操作（续期/同步/删除等）
4. 确认操作

### 4.3 API接口

系统提供完整的RESTful API，可以与其他系统集成：

1. 在用户设置中生成API密钥
2. 使用API密钥和文档中的接口说明进行集成
3. API文档可在系统中的"帮助"菜单下查看

## 5. 故障排除

### 5.1 常见问题

#### 5.1.1 客户端安装失败

**问题**：执行安装命令后报错或客户端未在控制台显示

**解决方法**：
1. 检查服务器网络连接
2. 确认令牌是否正确
3. 检查服务器防火墙设置
4. 查看安装日志：`cat /var/log/ssl-cert-manager.log`

#### 5.1.2 证书申请失败

**问题**：申请新证书时失败

**解决方法**：
1. 检查域名DNS解析是否正确
2. 确认验证记录是否正确添加
3. 检查域名是否达到Let's Encrypt速率限制
4. 查看详细错误日志

#### 5.1.3 自动续期未生效

**问题**：证书未自动续期

**解决方法**：
1. 确认服务器上的客户端是否正常运行
2. 检查服务器与控制台的连接状态
3. 查看续期任务日志
4. 确认证书路径是否变更

### 5.2 日志查看

系统日志位置：
- 控制台日志：系统设置 > 系统日志
- 客户端日志：`/var/log/ssl-cert-manager.log`
- API服务日志：`/var/log/ssl-cert-api.log`

### 5.3 联系支持

如遇到无法解决的问题，请联系技术支持：
- 邮件：support@example.com
- 电话：400-123-4567
- 工单系统：https://support.example.com

## 6. 附录

### 6.1 系统要求

- **控制台服务器**：
  - CPU: 2核+
  - 内存: 4GB+
  - 存储: 50GB+
  - 操作系统: Ubuntu 18.04+/CentOS 7+

- **客户端**：
  - 支持的操作系统: Ubuntu/Debian/CentOS/RHEL/TencentOS
  - 最小磁盘空间: 100MB
  - 依赖: curl, openssl, socat

- **浏览器兼容性**：
  - Chrome 80+
  - Firefox 78+
  - Edge 80+
  - Safari 14+

### 6.2 命令行工具

客户端提供命令行工具，可执行以下操作：

```bash
# 查看帮助
/usr/local/bin/ssl-cert-manager help

# 手动扫描证书
/usr/local/bin/ssl-cert-manager scan

# 手动同步证书
/usr/local/bin/ssl-cert-manager sync

# 查看客户端状态
/usr/local/bin/ssl-cert-manager status
```

### 6.3 快捷键

Web控制台支持以下快捷键：

- `Ctrl+/` 或 `Cmd+/`：显示快捷键帮助
- `Ctrl+F` 或 `Cmd+F`：搜索
- `Esc`：关闭弹窗
- `F5`：刷新数据

### 6.4 术语表

- **ACME**：自动证书管理环境（Automated Certificate Management Environment），Let's Encrypt使用的协议
- **CA**：证书颁发机构（Certificate Authority）
- **CSR**：证书签名请求（Certificate Signing Request）
- **DNS验证**：通过添加DNS记录验证域名所有权
- **HTTP验证**：通过在网站根目录放置特定文件验证域名所有权
- **SAN证书**：主题备用名称证书（Subject Alternative Name），支持多个域名的证书
- **泛域名证书**：支持所有子域名的证书，如 *.example.com
