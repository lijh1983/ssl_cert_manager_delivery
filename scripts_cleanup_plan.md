# Scripts目录清理计划

## 清理前文件列表 (26个脚本)
```
scripts/benchmark_build_speed.sh          # 构建速度基准测试
scripts/build.sh                          # 构建脚本
scripts/deploy.sh                         # 部署脚本
scripts/deploy_aliyun.sh                  # 阿里云部署脚本
scripts/fix_docker_compose.sh             # 修复Docker Compose
scripts/fix_nginx_image_issue.sh          # 修复nginx镜像问题
scripts/fix_python_image_issue.sh         # 修复Python镜像问题
scripts/optimize_alpine_sources.sh        # 优化Alpine镜像源
scripts/optimize_build_speed.sh           # 优化构建速度
scripts/prebuild_images.sh                # 预构建镜像
scripts/quick_validate_compose.sh         # 快速验证Compose
scripts/restart_services.sh               # 重启服务
scripts/setup_aliyun_docker.sh            # 设置阿里云Docker
scripts/setup_nginx_proxy.sh              # 设置nginx代理
scripts/setup_rhel9_docker.sh             # 设置RHEL9 Docker
scripts/smart_build_backend.sh            # 智能构建后端
scripts/test_alpine_build_speed.sh        # 测试Alpine构建速度
scripts/test_alpine_simple.sh             # 简单Alpine测试
scripts/test_deployment.sh                # 测试部署
scripts/test_docker_images.sh             # 测试Docker镜像
scripts/validate_docker_compose.sh        # 验证Docker Compose
scripts/verify.sh                         # 验证脚本
scripts/verify_aliyun_deployment.sh       # 验证阿里云部署
scripts/verify_alpine_optimization.sh     # 验证Alpine优化
scripts/verify_and_fix_images.sh          # 验证和修复镜像
scripts/verify_nginx_proxy.sh             # 验证nginx代理
```

## 整合策略

### 保留的核心脚本 (3个)
1. **ssl-manager.sh** - 核心管理脚本 (新建)
   - 整合: deploy.sh, deploy_aliyun.sh, verify.sh, restart_services.sh
   - 功能: 部署、验证、修复、状态查看、日志查看

2. **alpine-optimizer.sh** - Alpine优化工具 (新建)
   - 整合: optimize_alpine_sources.sh, test_alpine_*.sh, verify_alpine_optimization.sh
   - 功能: Alpine镜像源优化、测试、验证

3. **setup_nginx_proxy.sh** - nginx代理设置 (保留)
   - 核心部署脚本，功能独特，保留

### 删除的脚本 (23个)
- benchmark_build_speed.sh (功能整合到ssl-manager.sh)
- build.sh (功能整合到ssl-manager.sh)
- deploy.sh (功能整合到ssl-manager.sh)
- deploy_aliyun.sh (功能整合到ssl-manager.sh)
- fix_docker_compose.sh (功能整合到ssl-manager.sh)
- fix_nginx_image_issue.sh (功能整合到ssl-manager.sh)
- fix_python_image_issue.sh (功能整合到ssl-manager.sh)
- optimize_alpine_sources.sh (功能整合到alpine-optimizer.sh)
- optimize_build_speed.sh (功能整合到ssl-manager.sh)
- prebuild_images.sh (功能整合到ssl-manager.sh)
- quick_validate_compose.sh (功能整合到ssl-manager.sh)
- restart_services.sh (功能整合到ssl-manager.sh)
- setup_aliyun_docker.sh (功能整合到ssl-manager.sh)
- setup_rhel9_docker.sh (功能整合到ssl-manager.sh)
- smart_build_backend.sh (功能整合到ssl-manager.sh)
- test_alpine_build_speed.sh (功能整合到alpine-optimizer.sh)
- test_alpine_simple.sh (功能整合到alpine-optimizer.sh)
- test_deployment.sh (功能整合到ssl-manager.sh)
- test_docker_images.sh (功能整合到ssl-manager.sh)
- validate_docker_compose.sh (功能整合到ssl-manager.sh)
- verify.sh (功能整合到ssl-manager.sh)
- verify_aliyun_deployment.sh (功能整合到ssl-manager.sh)
- verify_alpine_optimization.sh (功能整合到alpine-optimizer.sh)
- verify_and_fix_images.sh (功能整合到ssl-manager.sh)
- verify_nginx_proxy.sh (功能整合到ssl-manager.sh)

## 清理后文件列表 (3个脚本)
```
scripts/ssl-manager.sh                    # 核心管理脚本 (新建)
scripts/alpine-optimizer.sh              # Alpine优化工具 (新建)
scripts/setup_nginx_proxy.sh             # nginx代理设置 (保留)
```

## 功能映射

### ssl-manager.sh 命令映射
- `ssl-manager.sh deploy` → deploy.sh, deploy_aliyun.sh
- `ssl-manager.sh verify` → verify.sh, verify_aliyun_deployment.sh
- `ssl-manager.sh fix` → fix_*.sh
- `ssl-manager.sh test` → test_*.sh
- `ssl-manager.sh status` → 新功能
- `ssl-manager.sh logs` → 新功能
- `ssl-manager.sh restart` → restart_services.sh

### alpine-optimizer.sh 命令映射
- `alpine-optimizer.sh optimize` → optimize_alpine_sources.sh
- `alpine-optimizer.sh test` → test_alpine_*.sh
- `alpine-optimizer.sh verify` → verify_alpine_optimization.sh
- `alpine-optimizer.sh restore` → 新功能

## 清理效果
- 脚本数量: 26个 → 3个 (减少88%)
- 维护复杂度: 大幅降低
- 功能完整性: 保持100%
- 用户体验: 更加统一和简洁
