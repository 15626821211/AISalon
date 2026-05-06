"""统一 SQLAlchemy ORM 模型定义，避免循环导入。"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    display_name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(20), default='🐱')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    events = db.relationship('Event', backref='creator', lazy=True)
    event_comments = db.relationship('EventComment', backref='user', lazy=True)
    projects = db.relationship('Project', backref='creator', lazy=True)
    project_comments = db.relationship('ProjectComment', backref='user', lazy=True)


class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    tags = db.Column(db.JSON, default=list)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    participants = db.relationship('EventParticipant', backref='event', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('EventComment', backref='event', lazy=True, cascade='all, delete-orphan')


class EventParticipant(db.Model):
    """活动参与对象：可以是用户或用户组。"""
    __tablename__ = 'event_participants'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserGroup(db.Model):
    """用户组。"""
    __tablename__ = 'user_groups'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('UserGroupMember', backref='group', lazy=True, cascade='all, delete-orphan')


class UserGroupMember(db.Model):
    """用户组成员。"""
    __tablename__ = 'user_group_members'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='uq_group_member'),)


class EventComment(db.Model):
    __tablename__ = 'event_comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    team = db.Column(db.String(200))
    github_url = db.Column(db.String(500), nullable=False)
    wiki_url = db.Column(db.String(500), nullable=True)
    tags = db.Column(db.JSON, default=list)
    summary = db.Column(db.Text)
    use_cases = db.Column(db.Text)
    design_thinking = db.Column(db.Text)
    tech_stack = db.Column(db.Text)
    architecture = db.Column(db.Text)
    key_code_snippets = db.Column(db.JSON, default=list)
    lessons_learned = db.Column(db.Text)
    usage_guide = db.Column(db.Text)
    directory_structure = db.Column(db.Text)
    diagrams = db.Column(db.JSON, default=list)
    status = db.Column(db.String(20), default='draft')
    analyzed_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    comments = db.relationship('ProjectComment', backref='project', lazy=True, cascade='all, delete-orphan')


class ProjectComment(db.Model):
    __tablename__ = 'project_comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProjectLike(db.Model):
    __tablename__ = 'project_likes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='uq_project_like'),)


class EventProject(db.Model):
    """活动与项目的关联关系。"""
    __tablename__ = 'event_projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('event_id', 'project_id', name='uq_event_project'),)
