# SSL证书管理系统 - Gunicorn生产环境配置

import os
import multiprocessing

# 基本配置
bind = "0.0.0.0:5000"
backlog = 2048

# 工作进程配置
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'gevent')
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', 1000))
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', 50))
preload_app = True

# 超时配置
timeout = int(os.getenv('GUNICORN_TIMEOUT', 30))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', 2))
graceful_timeout = int(os.getenv('GUNICORN_GRACEFUL_TIMEOUT', 30))

# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 日志配置
accesslog = '/app/logs/gunicorn_access.log'
errorlog = '/app/logs/gunicorn_error.log'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# 进程命名
proc_name = 'ssl_manager_backend'

# PID文件
pidfile = '/tmp/gunicorn.pid'

# 钩子函数
def on_starting(server):
    server.log.info("SSL证书管理系统后端服务启动中...")

def when_ready(server):
    server.log.info("SSL证书管理系统后端服务已就绪")

def on_exit(server):
    server.log.info("SSL证书管理系统后端服务已停止")
