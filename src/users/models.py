"""ORM 模型从统一入口导入。"""

from models import User, db

__all__ = ['User', 'db']