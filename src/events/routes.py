from flask import Blueprint, request, jsonify, render_template, session
from events.services import EventService
from models import db, EventProject, Project, User, UserGroup, UserGroupMember
from email_service import send_email, build_event_notification_html

events_bp = Blueprint('events', __name__)

# 为了与 app.py 中的导入名称保持一致
event_blueprint = events_bp


@events_bp.route('/', methods=['POST'])
def create_event():
    data = request.get_json() or {}
    from flask import session
    user_id = session.get('user_id')
    if user_id:
        data['user_id'] = user_id
    event = EventService.create_event_from_dict(data)
    return jsonify(event), 201


@events_bp.route('/', methods=['GET'])
def list_events():
    tag = request.args.get('tag')
    events = EventService.get_all_events()
    if tag:
        events = [e for e in events if tag in (e.get('tags') or [])]
    return jsonify(events), 200


@events_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    event = EventService.get_event_by_id(event_id)
    if event:
        return jsonify(event), 200
    return jsonify({'message': 'Event not found'}), 404


@events_bp.route('/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    from flask import session
    user_id = session.get('user_id')
    success = EventService.delete_event(event_id, user_id)
    if success:
        return jsonify({'message': 'Event deleted'}), 204
    return jsonify({'message': '无权限或活动不存在'}), 403


@events_bp.route('/page', methods=['GET'])
def events_page():
    """活动列表网页版本，渲染 templates/events/list.html。"""
    events = EventService.get_all_events()
    return render_template('events/list.html', events=events)


@events_bp.route('/<int:event_id>/page', methods=['GET'])
def event_detail_page(event_id):
    event = EventService.get_event_by_id(event_id)
    if not event:
        return render_template('404.html', message='活动不存在'), 404
    return render_template('events/detail.html', event=event)


@events_bp.route('/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    data = request.get_json() or {}
    from flask import session
    user_id = session.get('user_id')
    updated = EventService.update_event(event_id, data, user_id)
    if updated:
        return jsonify({'message': 'Event updated'}), 200
    return jsonify({'message': '无权限或活动不存在'}), 403


@events_bp.route('/<int:event_id>/participants', methods=['GET'])
def get_participants(event_id):
    """获取活动参与对象列表。"""
    participants = EventService.get_participants(event_id)
    return jsonify(participants), 200


@events_bp.route('/<int:event_id>/participants', methods=['POST'])
def add_participant(event_id):
    """添加参与对象（用户或用户组），并发送邮件通知。"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录'}), 401
    data = request.get_json() or {}
    target_user_id = data.get('user_id')
    group_id = data.get('group_id')
    ok = EventService.add_participant(event_id, user_id=target_user_id, group_id=group_id)
    if not ok:
        return jsonify({'message': '添加失败，可能已存在'}), 400

    # 发送邮件通知
    event = EventService.get_event_by_id(event_id)
    emails = _collect_emails(target_user_id=target_user_id, group_id=group_id)
    notified = 0
    if emails and event:
        html = build_event_notification_html(event, action='invited')
        success, _ = send_email(emails, f"【AI 沙龙】活动邀请：{event['title']}", html)
        notified = success

    return jsonify({'message': '已添加参与对象', 'notified': notified}), 201


@events_bp.route('/<int:event_id>/notify', methods=['POST'])
def notify_participants(event_id):
    """向活动全部参与对象发送邮件通知。"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录'}), 401
    event = EventService.get_event_by_id(event_id)
    if not event:
        return jsonify({'message': '活动不存在'}), 404

    participants = EventService.get_participants(event_id)
    emails = set()
    for p in participants:
        if p['type'] == 'user':
            user = User.query.get(p['user_id'])
            if user and user.email:
                emails.add(user.email)
        elif p['type'] == 'group':
            members = UserGroupMember.query.filter_by(group_id=p['group_id']).all()
            for m in members:
                u = User.query.get(m.user_id)
                if u and u.email:
                    emails.add(u.email)

    if not emails:
        return jsonify({'message': '没有可通知的邮箱', 'notified': 0}), 200

    html = build_event_notification_html(event, action='notify')
    success, fail = send_email(list(emails), f"【AI 沙龙】活动通知：{event['title']}", html)
    return jsonify({'message': f'已通知 {success} 人，失败 {fail} 人', 'notified': success, 'failed': fail}), 200


def _collect_emails(target_user_id=None, group_id=None):
    """收集需要通知的邮箱列表。"""
    emails = set()
    if target_user_id:
        user = User.query.get(target_user_id)
        if user and user.email:
            emails.add(user.email)
    if group_id:
        members = UserGroupMember.query.filter_by(group_id=group_id).all()
        for m in members:
            u = User.query.get(m.user_id)
            if u and u.email:
                emails.add(u.email)
    return list(emails)


@events_bp.route('/<int:event_id>/participants/<int:participant_id>', methods=['DELETE'])
def remove_participant(event_id, participant_id):
    """移除参与对象。"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录'}), 401
    ok = EventService.remove_participant(event_id, participant_id)
    if ok:
        return jsonify({'message': '已移除'}), 200
    return jsonify({'message': '移除失败'}), 404


@events_bp.route('/<int:event_id>/comments', methods=['GET'])
def get_comments(event_id):
    comments = EventService.get_comments(event_id)
    return jsonify(comments), 200


@events_bp.route('/<int:event_id>/comments', methods=['POST'])
def add_comment(event_id):
    from flask import session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，不能评论'}), 401
    user = None
    from users.services import UserService
    user = UserService.get_user_by_id(user_id)
    if not user:
        return jsonify({'message': '用户不存在'}), 404
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'message': '评论内容不能为空'}), 400
    ok = EventService.add_comment(event_id, user_id, user['username'], content)
    if ok:
        return jsonify({'message': '评论成功'}), 201
    return jsonify({'message': '评论失败'}), 400


@events_bp.route('/<int:event_id>/projects', methods=['GET'])
def get_event_projects(event_id):
    """获取活动关联的项目列表。"""
    links = EventProject.query.filter_by(event_id=event_id).all()
    result = []
    for link in links:
        project = Project.query.get(link.project_id)
        if project:
            result.append({
                'id': project.id,
                'name': project.name,
                'summary': project.summary,
                'tags': project.tags or [],
                'github_url': project.github_url,
            })
    return jsonify(result), 200


@events_bp.route('/<int:event_id>/projects', methods=['POST'])
def add_event_project(event_id):
    """关联项目到活动。"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录'}), 401
    data = request.get_json() or {}
    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'message': '缺少 project_id'}), 400
    existing = EventProject.query.filter_by(event_id=event_id, project_id=project_id).first()
    if existing:
        return jsonify({'message': '已关联'}), 409
    ep = EventProject(event_id=event_id, project_id=project_id)
    db.session.add(ep)
    db.session.commit()
    return jsonify({'message': '关联成功'}), 201


@events_bp.route('/<int:event_id>/projects/<int:project_id>', methods=['DELETE'])
def remove_event_project(event_id, project_id):
    """取消活动与项目的关联。"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录'}), 401
    ep = EventProject.query.filter_by(event_id=event_id, project_id=project_id).first()
    if not ep:
        return jsonify({'message': '关联不存在'}), 404
    db.session.delete(ep)
    db.session.commit()
    return jsonify({'message': '已取消关联'}), 200