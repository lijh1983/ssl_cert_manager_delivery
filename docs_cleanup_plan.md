# Docs目录清理计划

## 清理前文件列表 (9个文档)
```
docs/ALIYUN_DEPLOYMENT.md          # 阿里云部署指南 (保留)
docs/DEPLOYMENT.md                 # 通用部署指南 (保留，整合其他部署文档)
docs/NGINX_PROXY_SETUP.md          # nginx代理设置 (整合到DEPLOYMENT.md)
docs/PROJECT_STRUCTURE.md          # 项目结构说明 (保留)
docs/RHEL9_DEPLOYMENT_FIX.md       # RHEL9部署修复 (整合到ALIYUN_DEPLOYMENT.md)
docs/api_reference.md              # API参考文档 (保留)
docs/deployment_guide.md           # 部署指南 (与DEPLOYMENT.md重复，删除)
docs/developer_guide.md            # 开发指南 (保留)
docs/user_manual.md                # 用户手册 (保留)
```

## 整合策略

### 保留的核心文档 (5个)
1. **DEPLOYMENT.md** - 综合部署指南 (更新)
   - 整合: deployment_guide.md, NGINX_PROXY_SETUP.md
   - 内容: 通用部署、Docker部署、nginx配置

2. **ALIYUN_DEPLOYMENT.md** - 阿里云专用部署指南 (更新)
   - 整合: RHEL9_DEPLOYMENT_FIX.md
   - 内容: 阿里云优化、RHEL9修复、镜像源配置

3. **PROJECT_STRUCTURE.md** - 项目结构说明 (保留)
   - 内容: 目录结构、文件说明、架构图

4. **api_reference.md** - API参考文档 (保留)
   - 内容: API接口文档、参数说明

5. **user_manual.md** - 用户手册 (更新)
   - 整合: developer_guide.md的用户相关部分
   - 内容: 使用指南、常见问题

### 删除的文档 (4个)
- deployment_guide.md (内容整合到DEPLOYMENT.md)
- NGINX_PROXY_SETUP.md (内容整合到DEPLOYMENT.md)
- RHEL9_DEPLOYMENT_FIX.md (内容整合到ALIYUN_DEPLOYMENT.md)
- developer_guide.md (开发相关内容移到项目wiki)

## 清理后文件列表 (5个文档)
```
docs/DEPLOYMENT.md                 # 综合部署指南 (更新)
docs/ALIYUN_DEPLOYMENT.md          # 阿里云专用部署指南 (更新)
docs/PROJECT_STRUCTURE.md          # 项目结构说明 (保留)
docs/api_reference.md              # API参考文档 (保留)
docs/user_manual.md                # 用户手册 (更新)
```

## 内容整合详情

### DEPLOYMENT.md 整合内容
- 保留原有的Docker部署内容
- 整合deployment_guide.md的传统部署方式
- 整合NGINX_PROXY_SETUP.md的nginx配置
- 添加新的脚本使用说明

### ALIYUN_DEPLOYMENT.md 整合内容
- 保留原有的阿里云优化内容
- 整合RHEL9_DEPLOYMENT_FIX.md的RHEL9修复方案
- 添加Alpine镜像源优化说明
- 更新脚本使用方法

### user_manual.md 整合内容
- 保留原有的用户操作指南
- 整合developer_guide.md中的用户相关内容
- 添加新脚本的使用说明
- 更新常见问题解答

## 清理效果
- 文档数量: 9个 → 5个 (减少44%)
- 内容重复: 大幅减少
- 维护成本: 显著降低
- 用户体验: 更加清晰和统一
