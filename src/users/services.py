"""用户服务层——基于 SQLAlchemy ORM。"""

from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, UserGroup, UserGroupMember


class UserService:
    @staticmethod
    def register(username, password, email=None, display_name=None):
        """注册新用户，密码哈希存储。"""
        if not username or not password:
            return None
        if User.query.filter_by(username=username).first():
            return None
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            display_name=display_name,
        )
        db.session.add(user)
        db.session.commit()
        return UserService.to_dict(user)

    @staticmethod
    def login(username, password):
        """登录验证，使用哈希比对。"""
        if not username or not password:
            return None
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            return UserService.to_dict(user)
        return None

    @staticmethod
    def get_user_by_id(user_id):
        user = User.query.get(user_id)
        if user:
            return UserService.to_dict(user)
        return None

    @staticmethod
    def get_all_users():
        users = User.query.all()
        return [UserService.to_dict(u) for u in users]

    @staticmethod
    def to_dict(user):
        if isinstance(user, dict):
            return user
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email or '',
            'display_name': user.display_name or '',
            'avatar': getattr(user, 'avatar', '🐱') or '🐱',
            'is_admin': getattr(user, 'is_admin', False),
        }

    @staticmethod
    def update_user(user_id, data):
        """更新用户信息。"""
        user = User.query.get(user_id)
        if not user:
            return None
        if 'display_name' in data:
            user.display_name = data['display_name']
        if 'email' in data:
            user.email = data['email']
        if 'password' in data and data['password']:
            user.password_hash = generate_password_hash(data['password'])
        db.session.commit()
        return UserService.to_dict(user)

    @staticmethod
    def delete_user(user_id):
        user = User.query.get(user_id)
        if not user or user.is_admin:
            return False
        db.session.delete(user)
        db.session.commit()
        return True

    @staticmethod
    def is_admin(user_id):
        user = User.query.get(user_id)
        return user and user.is_admin

    # ===== 用户组管理 =====
    @staticmethod
    def create_group(name, description=''):
        if UserGroup.query.filter_by(name=name).first():
            return None
        group = UserGroup(name=name, description=description)
        db.session.add(group)
        db.session.commit()
        return UserService.group_to_dict(group)

    @staticmethod
    def get_all_groups():
        groups = UserGroup.query.all()
        return [UserService.group_to_dict(g) for g in groups]

    @staticmethod
    def delete_group(group_id):
        group = UserGroup.query.get(group_id)
        if not group:
            return False
        db.session.delete(group)
        db.session.commit()
        return True

    @staticmethod
    def add_group_member(group_id, user_id):
        existing = UserGroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
        if existing:
            return False
        m = UserGroupMember(group_id=group_id, user_id=user_id)
        db.session.add(m)
        db.session.commit()
        return True

    @staticmethod
    def remove_group_member(group_id, user_id):
        m = UserGroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
        if not m:
            return False
        db.session.delete(m)
        db.session.commit()
        return True

    @staticmethod
    def get_group_members(group_id):
        members = UserGroupMember.query.filter_by(group_id=group_id).all()
        result = []
        for m in members:
            user = User.query.get(m.user_id)
            if user:
                result.append(UserService.to_dict(user))
        return result

    @staticmethod
    def group_to_dict(group):
        member_count = UserGroupMember.query.filter_by(group_id=group.id).count()
        return {
            'id': group.id,
            'name': group.name,
            'description': group.description or '',
            'member_count': member_count,
        }