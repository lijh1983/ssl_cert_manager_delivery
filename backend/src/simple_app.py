"""
简化的Flask应用，用于验证后端服务健康检查
"""
import os
from flask import Flask, jsonify
from models.database_postgres import test_postgres_connection

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        # 测试PostgreSQL连接
        db_status = test_postgres_connection()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected' if db_status else 'disconnected',
            'timestamp': '2025-01-10T11:00:00Z'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': '2025-01-10T11:00:00Z'
        }), 500

@app.route('/ready', methods=['GET'])
def readiness_check():
    """就绪检查端点"""
    try:
        # 测试PostgreSQL连接
        db_status = test_postgres_connection()
        
        if db_status:
            return jsonify({
                'status': 'ready',
                'database': 'connected',
                'timestamp': '2025-01-10T11:00:00Z'
            }), 200
        else:
            return jsonify({
                'status': 'not ready',
                'database': 'disconnected',
                'timestamp': '2025-01-10T11:00:00Z'
            }), 503
    except Exception as e:
        return jsonify({
            'status': 'not ready',
            'error': str(e),
            'timestamp': '2025-01-10T11:00:00Z'
        }), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
