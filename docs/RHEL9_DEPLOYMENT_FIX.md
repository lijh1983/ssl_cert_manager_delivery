# RHEL/CentOS 9 部署问题解决方案

本文档专门解决在RHEL/CentOS 9系统上部署SSL证书管理系统时遇到的具体问题。

## 🔧 问题1解决方案：部署脚本参数错误

### 问题描述
```bash
./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring --enable-nginx
# 错误: [ERROR] 未知参数: --enable-nginx
```

### 解决方案
已修正 `scripts/deploy_aliyun.sh` 脚本，现在支持 `--enable-nginx` 参数。

#### 修正内容
1. 添加了 `--enable-nginx` 参数解析
2. 添加了 `start_nginx()` 函数
3. 更新了帮助信息

#### 正确的使用方法
```bash
# 基础部署
./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring

# 完整部署（包含生产级nginx）
./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring --enable-nginx

# 查看所有支持的参数
./scripts/deploy_aliyun.sh --help
```

#### 支持的参数列表
- `--domain DOMAIN`: 设置域名
- `--email EMAIL`: 设置ACME邮箱
- `--enable-monitoring`: 启用监控服务
- `--enable-nginx`: 启用生产级nginx
- `--skip-build`: 跳过镜像构建
- `--help`: 显示帮助信息

## 🔧 问题2解决方案：RHEL 9包安装失败

### 问题描述
```bash
No match for argument: htop
No match for argument: nethogs
Error: Unable to find a match: htop nethogs
```

### 根本原因
RHEL/CentOS 9使用dnf包管理器，某些工具包需要从EPEL仓库安装，且包名可能有所不同。

### 解决方案

#### 方案1：使用专用的RHEL 9优化脚本（推荐）
```bash
# 1. 运行RHEL 9专用Docker环境配置脚本
chmod +x scripts/setup_rhel9_docker.sh
sudo ./scripts/setup_rhel9_docker.sh

# 2. 然后运行部署脚本
./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring
```

#### 方案2：手动安装缺失的包
```bash
# 启用EPEL仓库
sudo dnf install -y epel-release

# 安装基础工具
sudo dnf install -y curl wget git htop iotop net-tools

# 安装nethogs（可能需要EPEL）
sudo dnf install -y nethogs
```

#### 方案3：配置阿里云软件源
```bash
# 配置阿里云CentOS Stream 9源
sudo tee /etc/yum.repos.d/aliyun-centos.repo > /dev/null <<EOF
[aliyun-baseos]
name=AliyunLinux-BaseOS
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/BaseOS/x86_64/os/
gpgcheck=0
enabled=1

[aliyun-appstream]
name=AliyunLinux-AppStream
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/AppStream/x86_64/os/
gpgcheck=0
enabled=1

[aliyun-epel]
name=Extra Packages for Enterprise Linux 9
baseurl=https://mirrors.aliyun.com/epel/9/Everything/x86_64/
gpgcheck=0
enabled=1
EOF

# 清理并重建缓存
sudo dnf clean all
sudo dnf makecache

# 安装工具
sudo dnf install -y htop iotop nethogs
```

## 🚀 完整的部署流程

### 步骤1：系统环境检查
```bash
# 运行验证脚本
chmod +x scripts/verify_aliyun_deployment.sh
./scripts/verify_aliyun_deployment.sh
```

### 步骤2：Docker环境配置
```bash
# 运行RHEL 9专用配置脚本
chmod +x scripts/setup_rhel9_docker.sh
sudo ./scripts/setup_rhel9_docker.sh
```

### 步骤3：部署应用
```bash
# 基础部署
./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring

# 或完整部署
./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --enable-monitoring --enable-nginx
```

### 步骤4：验证部署
```bash
# 检查服务状态
docker-compose -f docker-compose.aliyun.yml ps

# 检查健康状态
curl http://localhost:8000/health
curl http://localhost:80/health

# 查看日志
docker-compose -f docker-compose.aliyun.yml logs -f
```

## 🔍 验证修复是否成功

### 1. 验证参数支持
```bash
# 应该显示帮助信息，包含--enable-nginx参数
./scripts/deploy_aliyun.sh --help
```

### 2. 验证包安装
```bash
# 检查工具是否安装成功
htop --version
iotop --version
nethogs -V 2>/dev/null || echo "nethogs可能需要root权限运行"
```

### 3. 验证Docker环境
```bash
# 检查Docker版本和状态
docker --version
docker-compose --version
systemctl status docker

# 测试镜像拉取
docker pull registry.cn-hangzhou.aliyuncs.com/library/hello-world:latest
```

### 4. 验证网络连接
```bash
# 测试阿里云镜像源连接
curl -I https://registry.cn-hangzhou.aliyuncs.com

# 测试GitHub连接
curl -I https://github.com
```

## 🎯 针对您服务器的具体配置

### 服务器信息
- 实例ID: i-7xvhr9e4wz506y4t6qtd
- 区域: cn-guangzhou
- 操作系统: CentOS/RHEL 9
- 域名: ssl.gzyggl.com

### 推荐的部署命令
```bash
# 1. 环境准备
sudo ./scripts/setup_rhel9_docker.sh

# 2. 验证环境
./scripts/verify_aliyun_deployment.sh

# 3. 部署应用
./scripts/deploy_aliyun.sh --domain ssl.gzyggl.com --email admin@gzyggl.com --enable-monitoring

# 4. 访问应用
# 前端: http://ssl.gzyggl.com
# 后端: http://ssl.gzyggl.com:8000
# 监控: http://ssl.gzyggl.com:3000
```

## 🔧 常见问题排查

### 问题：Docker服务启动失败
```bash
# 检查服务状态
sudo systemctl status docker

# 重启Docker服务
sudo systemctl restart docker

# 查看Docker日志
sudo journalctl -u docker -f
```

### 问题：端口被占用
```bash
# 检查端口占用
sudo ss -tlnp | grep -E ':(80|443|8000|3000|9090)'

# 停止占用端口的服务
sudo systemctl stop httpd nginx 2>/dev/null || true
```

### 问题：防火墙阻止访问
```bash
# 开放必要端口
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 问题：DNS解析失败
```bash
# 检查域名解析
nslookup ssl.gzyggl.com

# 临时使用IP访问进行测试
curl http://$(curl -s ifconfig.me):8000/health
```

## 📞 获取支持

如果仍然遇到问题，请提供以下信息：

1. 运行 `./scripts/verify_aliyun_deployment.sh` 的完整输出
2. 错误日志：`docker-compose logs`
3. 系统信息：`uname -a && cat /etc/os-release`
4. Docker信息：`docker info`

通过这些修复，您应该能够成功在RHEL/CentOS 9系统上部署SSL证书管理系统。
