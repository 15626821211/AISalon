"""活动服务层——基于 SQLAlchemy ORM。"""

from datetime import datetime
from models import db, Event, EventParticipant, EventComment, User, UserGroup, UserGroupMember


class EventService:
    @staticmethod
    def create_event_from_dict(data: dict) -> dict:
        tags = data.get('tags') or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        # 解析时间
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        if isinstance(start_time, str) and start_time:
            try:
                start_time = datetime.fromisoformat(start_time)
            except ValueError:
                start_time = datetime.utcnow()
        else:
            start_time = datetime.utcnow()
        if isinstance(end_time, str) and end_time:
            try:
                end_time = datetime.fromisoformat(end_time)
            except ValueError:
                end_time = None
        else:
            end_time = None
        event = Event(
            title=data.get('title'),
            description=data.get('description'),
            location=data.get('location'),
            start_time=start_time,
            end_time=end_time,
            user_id=data.get('user_id'),
            tags=tags,
        )
        db.session.add(event)
        db.session.commit()
        return EventService.to_dict(event)

    @staticmethod
    def get_all_events():
        events = Event.query.order_by(Event.created_at.desc()).all()
        return [EventService.to_dict(e) for e in events]

    @staticmethod
    def get_event_by_id(event_id: int):
        event = Event.query.get(event_id)
        if event:
            return EventService.to_dict(event)
        return None

    @staticmethod
    def delete_event(event_id: int, user_id: int = None) -> bool:
        event = Event.query.get(event_id)
        if not event:
            return False
        if user_id is not None and event.user_id != user_id:
            return False
        db.session.delete(event)
        db.session.commit()
        return True

    @staticmethod
    def update_event(event_id: int, data: dict, user_id: int = None) -> bool:
        event = Event.query.get(event_id)
        if not event:
            return False
        if user_id is not None and event.user_id != user_id:
            return False
        if 'title' in data:
            event.title = data['title']
        if 'description' in data:
            event.description = data['description']
        if 'location' in data:
            event.location = data['location']
        if 'start_time' in data:
            st = data['start_time']
            if isinstance(st, str) and st:
                try:
                    event.start_time = datetime.fromisoformat(st)
                except ValueError:
                    pass
        if 'end_time' in data:
            et = data['end_time']
            if isinstance(et, str) and et:
                try:
                    event.end_time = datetime.fromisoformat(et)
                except ValueError:
                    pass
            elif not et:
                event.end_time = None
        if 'tags' in data:
            tags = data['tags']
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]
            event.tags = tags
        db.session.commit()
        return True

    @staticmethod
    def to_dict(event) -> dict:
        if isinstance(event, dict):
            return event
        creator = User.query.get(event.user_id) if event.user_id else None
        return {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'start_time': event.start_time.isoformat() if event.start_time else None,
            'end_time': event.end_time.isoformat() if event.end_time else None,
            'location': event.location,
            'user_id': event.user_id,
            'creator_name': creator.display_name or creator.username if creator else None,
            'creator_avatar': creator.avatar if creator else '🐱',
            'tags': event.tags or [],
        }

    @staticmethod
    def add_participant(event_id: int, user_id: int = None, group_id: int = None) -> bool:
        """添加参与对象（用户或用户组）。"""
        if not user_id and not group_id:
            return False
        existing = EventParticipant.query.filter_by(
            event_id=event_id, user_id=user_id, group_id=group_id
        ).first()
        if existing:
            return False
        p = EventParticipant(event_id=event_id, user_id=user_id, group_id=group_id)
        db.session.add(p)
        db.session.commit()
        return True

    @staticmethod
    def remove_participant(event_id: int, participant_id: int) -> bool:
        p = EventParticipant.query.filter_by(id=participant_id, event_id=event_id).first()
        if not p:
            return False
        db.session.delete(p)
        db.session.commit()
        return True

    @staticmethod
    def get_participants(event_id: int):
        """获取活动参与对象列表，展开用户和用户组。"""
        parts = EventParticipant.query.filter_by(event_id=event_id).all()
        result = []
        for p in parts:
            if p.user_id:
                user = User.query.get(p.user_id)
                if user:
                    result.append({
                        'id': p.id,
                        'type': 'user',
                        'user_id': user.id,
                        'name': user.display_name or user.username,
                        'avatar': user.avatar or '🐱',
                    })
            elif p.group_id:
                group = UserGroup.query.get(p.group_id)
                if group:
                    member_count = UserGroupMember.query.filter_by(group_id=group.id).count()
                    result.append({
                        'id': p.id,
                        'type': 'group',
                        'group_id': group.id,
                        'name': group.name,
                        'member_count': member_count,
                    })
        return result

    @staticmethod
    def get_user_participated_events(user_id: int):
        """获取用户参与的所有活动（直接参与 + 通过用户组参与）。"""
        # 直接参与
        direct = EventParticipant.query.filter_by(user_id=user_id).all()
        event_ids = {p.event_id for p in direct}
        # 通过用户组参与
        memberships = UserGroupMember.query.filter_by(user_id=user_id).all()
        group_ids = [m.group_id for m in memberships]
        if group_ids:
            group_parts = EventParticipant.query.filter(
                EventParticipant.group_id.in_(group_ids)
            ).all()
            event_ids.update(p.event_id for p in group_parts)
        events = Event.query.filter(Event.id.in_(event_ids)).all() if event_ids else []
        return [EventService.to_dict(e) for e in events]

    @staticmethod
    def get_events_by_user(user_id: int):
        """获取用户发起的所有活动。"""
        events = Event.query.filter_by(user_id=user_id).all()
        return [EventService.to_dict(e) for e in events]

    @staticmethod
    def add_comment(event_id: int, user_id: int, username: str, content: str) -> bool:
        if not content.strip():
            return False
        comment = EventComment(
            event_id=event_id,
            user_id=user_id,
            username=username,
            content=content.strip(),
        )
        db.session.add(comment)
        db.session.commit()
        return True

    @staticmethod
    def get_comments(event_id: int):
        comments = EventComment.query.filter_by(event_id=event_id).order_by(EventComment.created_at).all()
        return [{
            'user_id': c.user_id,
            'username': c.username,
            'content': c.content,
            'created_at': c.created_at.isoformat() if c.created_at else None,
        } for c in comments]