"""
用户模型模块，处理用户相关的数据操作
"""
import datetime
import bcrypt
from typing import Dict, List, Any, Optional
from .database import db

class User:
    """用户模型类"""
    
    def __init__(self, id: int = None, username: str = None, email: str = None, 
                 password_hash: str = None, role: str = None, 
                 created_at: str = None, updated_at: str = None):
        """初始化用户对象"""
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at
        self.updated_at = updated_at
    
    @staticmethod
    def hash_password(password: str) -> str:
        """对密码进行哈希处理"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码是否正确"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @classmethod
    def get_by_id(cls, user_id: int) -> Optional['User']:
        """根据ID获取用户"""
        db.connect()
        user_data = db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        db.close()
        
        if not user_data:
            return None
        
        return cls(**user_data)
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """根据用户名获取用户"""
        db.connect()
        user_data = db.fetchone("SELECT * FROM users WHERE username = ?", (username,))
        db.close()
        
        if not user_data:
            return None
        
        return cls(**user_data)
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """根据邮箱获取用户"""
        db.connect()
        user_data = db.fetchone("SELECT * FROM users WHERE email = ?", (email,))
        db.close()
        
        if not user_data:
            return None
        
        return cls(**user_data)
    
    @classmethod
    def get_all(cls, page: int = 1, limit: int = 20, keyword: str = None) -> tuple:
        """获取所有用户"""
        db.connect()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if keyword:
            conditions.append("(username LIKE ? OR email LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 计算总数
        count_sql = f"SELECT COUNT(*) as total FROM users{where_clause}"
        count_result = db.fetchone(count_sql, tuple(params))
        total = count_result['total'] if count_result else 0
        
        # 分页查询
        offset = (page - 1) * limit
        sql = f"SELECT * FROM users{where_clause} ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        users_data = db.fetchall(sql, tuple(params))
        db.close()
        
        users = [cls(**user_data) for user_data in users_data]
        return users, total
    
    def save(self) -> int:
        """保存用户信息"""
        db.connect()
        now = datetime.datetime.now().isoformat()
        
        if self.id:
            # 更新现有用户
            data = {
                'username': self.username,
                'email': self.email,
                'role': self.role,
                'updated_at': now
            }
            
            # 如果有新密码，更新密码
            if hasattr(self, 'password') and self.password:
                data['password_hash'] = self.hash_password(self.password)
            
            db.update('users', data, 'id = ?', (self.id,))
            user_id = self.id
        else:
            # 创建新用户
            data = {
                'username': self.username,
                'email': self.email,
                'password_hash': self.password_hash,
                'role': self.role,
                'created_at': now,
                'updated_at': now
            }
            user_id = db.insert('users', data)
            self.id = user_id
        
        db.commit()
        db.close()
        return user_id
    
    def delete(self) -> bool:
        """删除用户"""
        if not self.id:
            return False
        
        db.connect()
        result = db.delete('users', 'id = ?', (self.id,))
        db.commit()
        db.close()
        
        return result > 0
    
    def to_dict(self, exclude_fields: List[str] = None) -> Dict[str, Any]:
        """将用户对象转换为字典"""
        exclude_fields = exclude_fields or ['password_hash']
        
        user_dict = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        # 排除指定字段
        for field in exclude_fields:
            if field in user_dict:
                del user_dict[field]
        
        return user_dict
    
    @classmethod
    def create(cls, username: str, email: str, password: str, role: str = 'user') -> 'User':
        """创建新用户"""
        # 检查用户名是否已存在
        existing_user = cls.get_by_username(username)
        if existing_user:
            raise ValueError(f"用户名 '{username}' 已存在")
        
        # 检查邮箱是否已存在
        existing_email = cls.get_by_email(email)
        if existing_email:
            raise ValueError(f"邮箱 '{email}' 已被使用")
        
        # 创建新用户
        password_hash = cls.hash_password(password)
        user = cls(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role
        )
        user.save()
        
        return user
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['User']:
        """用户认证"""
        user = cls.get_by_username(username)
        
        if not user:
            return None
        
        if not cls.verify_password(password, user.password_hash):
            return None
        
        return user
    
    def is_admin(self) -> bool:
        """检查用户是否为管理员"""
        return self.role == 'admin'
