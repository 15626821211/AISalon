from flask import Blueprint, request, jsonify, session
from users.services import UserService

users_bp = Blueprint('users', __name__)

# 为了与 app.py 中的导入名称保持一致
user_blueprint = users_bp


@users_bp.route('/register', methods=['POST'])
def register():
    """仅 admin 可注册新用户。"""
    try:
        current_user_id = session.get('user_id')
        if not current_user_id or not UserService.is_admin(current_user_id):
            return jsonify({'message': '仅管理员可创建账号'}), 403
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()
        display_name = data.get('display_name', '').strip()
        if not username or not password or not email or not display_name:
            return jsonify({'message': '账号、密码、邮箱、姓名均不能为空'}), 400
        user = UserService.register(username, password, email=email, display_name=display_name)
        if user:
            return jsonify({'message': '创建成功', 'user': user}), 201
        return jsonify({'message': '创建失败，用户名已存在'}), 400
    except Exception as e:
        return jsonify({'message': f'注册异常: {str(e)}'}), 500


@users_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        user = UserService.login(username, password)
        if user:
            session['user_id'] = user['id']
            return jsonify({'message': '登录成功', 'user': {'id': user['id'], 'username': user['username']}}), 200
        return jsonify({'message': '用户名或密码错误'}), 401
    except Exception as e:
        return jsonify({'message': f'登录异常: {str(e)}'}), 500


@users_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': '已退出登录'}), 200


@users_bp.route('/me', methods=['GET'])
def get_me():
    user_id = session.get('user_id')
    if user_id:
        user = UserService.get_user_by_id(user_id)
        if user:
            return jsonify(user), 200
    return jsonify({'message': '未登录'}), 401


@users_bp.route('/avatar', methods=['PUT'])
def update_avatar():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录'}), 401
    data = request.get_json() or {}
    avatar = data.get('avatar', '').strip()
    if not avatar:
        return jsonify({'message': '头像不能为空'}), 400
    from models import db, User
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': '用户不存在'}), 404
    user.avatar = avatar
    db.session.commit()
    return jsonify({'message': '头像已更新', 'avatar': avatar}), 200


@users_bp.route('/users', methods=['GET'])
def list_users():
    users = UserService.get_all_users()
    return jsonify(users), 200


@users_bp.route('/profile', methods=['GET'])
def profile():
    from flask import render_template
    user_id = session.get('user_id')
    if not user_id:
        return render_template('users/login.html'), 401
    user = UserService.get_user_by_id(user_id)
    if not user:
        return render_template('users/login.html'), 404
    # 获取参与和发起的活动
    from events.services import EventService
    from models import Project, ProjectLike
    participated_events = EventService.get_user_participated_events(user_id)
    created_events = EventService.get_events_by_user(user_id)
    # 获取项目数据
    my_projects = Project.query.filter_by(created_by=user_id).all()
    liked_projects = Project.query.join(ProjectLike, Project.id == ProjectLike.project_id).filter(ProjectLike.user_id == user_id).all()
    return render_template('users/profile.html',
        user=user,
        participated_events=participated_events,
        created_events=created_events,
        my_projects=my_projects,
        liked_projects=liked_projects,
    )


# ===== 用户管理（admin only）=====
@users_bp.route('/manage/users', methods=['GET'])
def manage_users():
    user_id = session.get('user_id')
    if not user_id or not UserService.is_admin(user_id):
        return jsonify({'message': '仅管理员可访问'}), 403
    users = UserService.get_all_users()
    return jsonify(users), 200


@users_bp.route('/manage/users/<int:target_id>', methods=['PUT'])
def manage_update_user(target_id):
    user_id = session.get('user_id')
    if not user_id or not UserService.is_admin(user_id):
        return jsonify({'message': '仅管理员可操作'}), 403
    data = request.get_json() or {}
    user = UserService.update_user(target_id, data)
    if user:
        return jsonify(user), 200
    return jsonify({'message': '用户不存在'}), 404


@users_bp.route('/manage/users/<int:target_id>', methods=['DELETE'])
def manage_delete_user(target_id):
    user_id = session.get('user_id')
    if not user_id or not UserService.is_admin(user_id):
        return jsonify({'message': '仅管理员可操作'}), 403
    ok = UserService.delete_user(target_id)
    if ok:
        return jsonify({'message': '已删除'}), 200
    return jsonify({'message': '删除失败'}), 400


# ===== 用户组管理（admin only）=====
@users_bp.route('/groups', methods=['GET'])
def list_groups():
    groups = UserService.get_all_groups()
    return jsonify(groups), 200


@users_bp.route('/groups', methods=['POST'])
def create_group():
    user_id = session.get('user_id')
    if not user_id or not UserService.is_admin(user_id):
        return jsonify({'message': '仅管理员可操作'}), 403
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    if not name:
        return jsonify({'message': '组名不能为空'}), 400
    group = UserService.create_group(name, description)
    if group:
        return jsonify(group), 201
    return jsonify({'message': '创建失败，组名已存在'}), 400


@users_bp.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    user_id = session.get('user_id')
    if not user_id or not UserService.is_admin(user_id):
        return jsonify({'message': '仅管理员可操作'}), 403
    ok = UserService.delete_group(group_id)
    if ok:
        return jsonify({'message': '已删除'}), 200
    return jsonify({'message': '删除失败'}), 400


@users_bp.route('/groups/<int:group_id>/members', methods=['GET'])
def get_group_members(group_id):
    members = UserService.get_group_members(group_id)
    return jsonify(members), 200


@users_bp.route('/groups/<int:group_id>/members', methods=['POST'])
def add_group_member(group_id):
    user_id = session.get('user_id')
    if not user_id or not UserService.is_admin(user_id):
        return jsonify({'message': '仅管理员可操作'}), 403
    data = request.get_json() or {}
    target_user_id = data.get('user_id')
    if not target_user_id:
        return jsonify({'message': '缺少 user_id'}), 400
    ok = UserService.add_group_member(group_id, target_user_id)
    if ok:
        return jsonify({'message': '已添加'}), 201
    return jsonify({'message': '添加失败'}), 400


@users_bp.route('/groups/<int:group_id>/members/<int:member_user_id>', methods=['DELETE'])
def remove_group_member(group_id, member_user_id):
    user_id = session.get('user_id')
    if not user_id or not UserService.is_admin(user_id):
        return jsonify({'message': '仅管理员可操作'}), 403
    ok = UserService.remove_group_member(group_id, member_user_id)
    if ok:
        return jsonify({'message': '已移除'}), 200
    return jsonify({'message': '移除失败'}), 400


@users_bp.route('/admin', methods=['GET'])
def admin_page():
    from flask import render_template
    user_id = session.get('user_id')
    if not user_id or not UserService.is_admin(user_id):
        return render_template('404.html', message='无权限'), 403
    return render_template('users/admin.html')