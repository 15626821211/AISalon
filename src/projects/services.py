"""项目知识库服务层——CRUD + 分析调度。"""

import json
from datetime import datetime
from models import db, Project, ProjectComment, ProjectLike
from integrations.github_client import fetch_repo_content
from projects.ai_analyzer import analyze_project


class ProjectService:
    @staticmethod
    def create_project(data: dict) -> dict:
        tags = data.get('tags') or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        project = Project(
            name=data.get('name'),
            team=data.get('team', ''),
            github_url=data.get('github_url'),
            wiki_url=data.get('wiki_url', ''),
            tags=tags,
            created_by=data.get('created_by'),
        )
        db.session.add(project)
        db.session.commit()
        return ProjectService.to_dict(project)

    @staticmethod
    def get_all_projects():
        projects = Project.query.order_by(Project.created_at.desc()).all()
        return [ProjectService.to_dict(p) for p in projects]

    @staticmethod
    def get_project_by_id(project_id: int):
        project = Project.query.get(project_id)
        if project:
            return ProjectService.to_dict(project)
        return None

    @staticmethod
    def update_project(project_id: int, data: dict, user_id: int = None) -> bool:
        project = Project.query.get(project_id)
        if not project:
            return False
        if user_id is not None and project.created_by != user_id:
            return False
        if 'name' in data:
            project.name = data['name']
        if 'team' in data:
            project.team = data['team']
        if 'github_url' in data:
            project.github_url = data['github_url']
        if 'wiki_url' in data:
            project.wiki_url = data['wiki_url']
        if 'tags' in data:
            tags = data['tags']
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]
            project.tags = tags
        db.session.commit()
        return True

    @staticmethod
    def delete_project(project_id: int, user_id: int = None) -> bool:
        project = Project.query.get(project_id)
        if not project:
            return False
        if user_id is not None and project.created_by != user_id:
            return False
        db.session.delete(project)
        db.session.commit()
        return True

    @staticmethod
    def analyze(project_id: int, user_id: int = None) -> dict:
        """触发 AI 分析，拉取仓库内容并调用 LLM。"""
        project = Project.query.get(project_id)
        if not project:
            return {'error': '项目不存在', 'status_code': 404}
        if user_id is not None and project.created_by != user_id:
            return {'error': '只有项目创建者可触发分析', 'status_code': 403}

        # 拉取仓库内容（支持 GitHub / GitLab）
        try:
            repo_content = fetch_repo_content(project.github_url)
        except Exception as e:
            return {'error': f'仓库内容拉取失败: {str(e)}', 'status_code': 400}

        # AI 分析
        try:
            result = analyze_project(repo_content)
        except Exception as e:
            return {'error': f'AI 分析失败: {str(e)}', 'status_code': 502}

        # 更新项目记录（确保 Text 字段为字符串）
        def _str(val):
            return json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val) if val else ''

        project.summary = _str(result.get('summary', ''))
        project.use_cases = _str(result.get('use_cases', ''))
        project.design_thinking = _str(result.get('design_thinking', ''))
        project.tech_stack = _str(result.get('tech_stack', ''))
        project.architecture = _str(result.get('architecture', ''))
        project.key_code_snippets = result.get('key_code_snippets', [])
        # 修复 key_code_snippets 中 explanation 包含整个 JSON 的情况
        if (isinstance(project.key_code_snippets, list) and len(project.key_code_snippets) == 1
                and not project.key_code_snippets[0].get('file')
                and not project.key_code_snippets[0].get('code')):
            raw = project.key_code_snippets[0].get('explanation', '')
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    project.key_code_snippets = parsed
            except (json.JSONDecodeError, TypeError):
                pass
        project.lessons_learned = _str(result.get('lessons_learned', ''))
        project.usage_guide = _str(result.get('usage_guide', ''))
        project.directory_structure = _str(result.get('directory_structure', ''))
        project.diagrams = result.get('diagrams', [])
        # 保存拉取的代码文件，供AI助手对话时检索
        project.code_files = repo_content.get('files', [])
        project.status = result.get('status', 'partial')
        project.analyzed_at = datetime.utcnow()
        db.session.commit()

        return ProjectService.to_dict(project)

    @staticmethod
    def add_comment(project_id: int, user_id: int, username: str, content: str) -> bool:
        if not content.strip():
            return False
        comment = ProjectComment(
            project_id=project_id,
            user_id=user_id,
            username=username,
            content=content.strip(),
        )
        db.session.add(comment)
        db.session.commit()
        return True

    @staticmethod
    def get_comments(project_id: int):
        comments = ProjectComment.query.filter_by(project_id=project_id).order_by(ProjectComment.created_at).all()
        return [{
            'user_id': c.user_id,
            'username': c.username,
            'content': c.content,
            'created_at': c.created_at.isoformat() if c.created_at else None,
        } for c in comments]

    @staticmethod
    def to_dict(project) -> dict:
        if isinstance(project, dict):
            return project
        return {
            'id': project.id,
            'name': project.name,
            'team': project.team,
            'github_url': project.github_url,
            'wiki_url': project.wiki_url,
            'tags': project.tags or [],
            'summary': project.summary,
            'use_cases': project.use_cases,
            'design_thinking': project.design_thinking,
            'tech_stack': project.tech_stack,
            'architecture': project.architecture,
            'key_code_snippets': project.key_code_snippets or [],
            'lessons_learned': project.lessons_learned,
            'usage_guide': project.usage_guide,
            'directory_structure': project.directory_structure,
            'diagrams': project.diagrams or [],
            'status': project.status,
            'analyzed_at': project.analyzed_at.isoformat() if project.analyzed_at else None,
            'created_by': project.created_by,
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'like_count': ProjectLike.query.filter_by(project_id=project.id).count(),
        }

    @staticmethod
    def toggle_like(project_id: int, user_id: int) -> dict:
        """切换点赞状态，返回 {liked, like_count}。"""
        existing = ProjectLike.query.filter_by(project_id=project_id, user_id=user_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            liked = False
        else:
            db.session.add(ProjectLike(project_id=project_id, user_id=user_id))
            db.session.commit()
            liked = True
        count = ProjectLike.query.filter_by(project_id=project_id).count()
        return {'liked': liked, 'like_count': count}

    @staticmethod
    def is_liked_by(project_id: int, user_id: int) -> bool:
        return ProjectLike.query.filter_by(project_id=project_id, user_id=user_id).first() is not None
