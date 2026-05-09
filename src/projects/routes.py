"""项目知识库路由——API + 页面。"""

import json
from flask import Blueprint, request, jsonify, render_template, session
from config import Config
from projects.services import ProjectService
from users.services import UserService

projects_bp = Blueprint('projects', __name__)

# 为了与 app.py 中的导入名称保持一致
project_blueprint = projects_bp


# === API 路由 ===

@projects_bp.route('/', methods=['POST'])
def create_project():
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'message': '未登录'}), 401
        data['created_by'] = user_id
        project = ProjectService.create_project(data)
        return jsonify(project), 201
    except Exception as e:
        return jsonify({'message': f'创建项目异常: {str(e)}'}), 500


@projects_bp.route('/', methods=['GET'])
def list_projects():
    tag = request.args.get('tag')
    projects = ProjectService.get_all_projects()
    if tag:
        projects = [p for p in projects if tag in (p.get('tags') or [])]
    return jsonify(projects), 200


@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = ProjectService.get_project_by_id(project_id)
    if project:
        return jsonify(project), 200
    return jsonify({'message': '项目不存在'}), 404


@projects_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')
        updated = ProjectService.update_project(project_id, data, user_id)
        if updated:
            return jsonify({'message': '项目已更新'}), 200
        return jsonify({'message': '无权限或项目不存在'}), 403
    except Exception as e:
        return jsonify({'message': f'更新异常: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    try:
        user_id = session.get('user_id')
        success = ProjectService.delete_project(project_id, user_id)
        if success:
            return jsonify({'message': '项目已删除'}), 204
        return jsonify({'message': '无权限或项目不存在'}), 403
    except Exception as e:
        return jsonify({'message': f'删除异常: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>/analyze', methods=['POST'])
def analyze_project(project_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'message': '未登录'}), 401
        result = ProjectService.analyze(project_id, user_id)
        if 'error' in result:
            return jsonify({'message': result['error']}), result.get('status_code', 400)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': f'分析异常: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>/comments', methods=['GET'])
def get_project_comments(project_id):
    comments = ProjectService.get_comments(project_id)
    return jsonify(comments), 200


@projects_bp.route('/<int:project_id>/comments', methods=['POST'])
def add_project_comment(project_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'message': '未登录，不能评论'}), 401
        user = UserService.get_user_by_id(user_id)
        if not user:
            return jsonify({'message': '用户不存在'}), 404
        data = request.get_json() or {}
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'message': '评论内容不能为空'}), 400
        ok = ProjectService.add_comment(project_id, user_id, user['username'], content)
        if ok:
            return jsonify({'message': '评论成功'}), 201
        return jsonify({'message': '评论失败'}), 400
    except Exception as e:
        return jsonify({'message': f'评论异常: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>/like', methods=['POST'])
def toggle_like(project_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录'}), 401
    result = ProjectService.toggle_like(project_id, user_id)
    return jsonify(result), 200


@projects_bp.route('/<int:project_id>/like', methods=['GET'])
def get_like_status(project_id):
    from models import ProjectLike
    user_id = session.get('user_id')
    count = ProjectLike.query.filter_by(project_id=project_id).count()
    liked = ProjectService.is_liked_by(project_id, user_id) if user_id else False
    return jsonify({'liked': liked, 'like_count': count}), 200


@projects_bp.route('/<int:project_id>/chat', methods=['POST'])
def project_chat(project_id):
    """AI 智能体：基于项目内容回答问题。"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '请先登录'}), 401
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'message': '问题不能为空'}), 400

    project = ProjectService.get_project_by_id(project_id)
    if not project:
        return jsonify({'message': '项目不存在'}), 404

    from projects.ai_analyzer import _call_llm
    # 组装项目上下文
    context_parts = []
    if project.get('summary'):
        context_parts.append(f"项目概览：{project['summary']}")
    if project.get('use_cases'):
        context_parts.append(f"应用场景：{project['use_cases'][:2000]}")
    if project.get('design_thinking'):
        context_parts.append(f"设计思路：{project['design_thinking'][:2000]}")
    if project.get('tech_stack'):
        context_parts.append(f"技术选型：{project['tech_stack'][:2000]}")
    if project.get('architecture'):
        context_parts.append(f"架构描述：{project['architecture'][:2000]}")
    if project.get('usage_guide'):
        context_parts.append(f"使用指南：{project['usage_guide'][:2000]}")
    if project.get('lessons_learned'):
        context_parts.append(f"经验教训：{project['lessons_learned'][:2000]}")
    if project.get('key_code_snippets'):
        snippets_text = '\n'.join(
            f"文件: {s.get('file','')}\n代码: {s.get('code','')[:500]}\n解读: {s.get('explanation','')}"
            for s in (project['key_code_snippets'] or [])[:5]
        )
        context_parts.append(f"核心代码：{snippets_text}")

    # 检索用户问题中提及的代码文件，提供给 LLM
    # 直接从数据库模型读取 code_files，避免 to_dict 携带大量代码数据
    from models import Project as ProjectModel
    project_model = ProjectModel.query.get(project_id)
    code_files = (project_model.code_files or []) if project_model else []
    if code_files:
        q_lower = question.lower()
        # 分级匹配：精确路径 > 文件名 > 路径片段
        exact_match = []
        fname_match = []
        for f in code_files:
            fpath = f.get('path', '')
            fname = fpath.split('/')[-1].lower()
            if fpath.lower() in q_lower:
                exact_match.append(f)
            elif fname in q_lower and len(fname) > 5:
                fname_match.append(f)
        # 优先使用精确匹配，其次文件名匹配
        matched_files = exact_match or fname_match
        # 限制总大小，避免超出 token 限制
        file_context = ''
        total_len = 0
        for f in matched_files[:5]:
            content = f.get('content', '')[:8000]
            file_context += f"\n\n--- 文件: {f['path']} ---\n{content}"
            total_len += len(content)
            if total_len > 25000:
                break
        if file_context:
            context_parts.append(f"用户提到的代码文件内容：{file_context}")
        # 如果没有精确匹配，提供文件列表供参考
        elif code_files:
            file_list = '\n'.join(f.get('path', '') for f in code_files)
            context_parts.append(f"项目包含的代码文件列表（用户可以指定文件名让我查看）：\n{file_list}")

    project_context = '\n\n'.join(context_parts)

    system_prompt = f"""你是项目「{project['name']}」的 AI 智能助手。请基于以下项目资料回答问题。
如果资料中包含了用户提到的代码文件内容，请直接基于代码进行分析和解读。
如果用户询问的文件不在资料中，告诉用户"该文件未被收录到分析范围，建议重新分析项目以获取更多文件"。
如果用户的问题与本项目无关，请礼貌地拒绝。
请用简体中文回答，使用 Markdown 格式排版。

---
{project_context}"""

    try:
        answer = _call_llm(question, system_prompt)
        return jsonify({'answer': answer}), 200
    except Exception as e:
        return jsonify({'message': f'AI 回答失败: {str(e)}'}), 500


# === 页面路由 ===

@projects_bp.route('/page', methods=['GET'])
def projects_page():
    """项目列表页。"""
    tag = request.args.get('tag')
    projects = ProjectService.get_all_projects()
    if tag:
        projects = [p for p in projects if tag in (p.get('tags') or [])]
    return render_template('projects/list.html', projects=projects)


@projects_bp.route('/search/page', methods=['GET'])
def search_page():
    """AI 搜索页面。"""
    return render_template('projects/search.html')


@projects_bp.route('/search', methods=['POST'])
def ai_search():
    """AI 驱动的 GitHub 项目搜索。"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '请先登录'}), 401
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'message': '请输入搜索描述'}), 400

    from projects.ai_analyzer import _call_llm
    import httpx as _httpx

    # Step 1: LLM 将自然语言转为 GitHub 搜索关键词
    keyword_prompt = f"""用户想找的项目：{query}

请将用户的自然语言描述转换为 GitHub 搜索关键词（英文）。
要求：
- 只返回搜索关键词，不要解释
- 用空格分隔，最多 5 个关键词
- 如果用户描述的是中文概念，翻译为对应的英文技术术语

示例：
用户：我想找一个用Python做的Web爬虫框架 → python web scraping framework
用户：基于React的后台管理系统模板 → react admin dashboard template"""

    try:
        keywords = _call_llm(keyword_prompt, '你是一个搜索关键词提取专家。只返回关键词，不要其他内容。')
        keywords = keywords.strip().strip('"\'')
    except Exception as e:
        return jsonify({'message': f'AI 关键词提取失败: {str(e)}'}), 500

    # Step 2: 调用 GitHub Search API
    headers = {'Accept': 'application/vnd.github.v3+json'}
    github_token = Config.GITHUB_TOKEN
    if github_token:
        headers['Authorization'] = f'token {github_token}'

    try:
        resp = _httpx.get(
            'https://api.github.com/search/repositories',
            params={'q': keywords, 'sort': 'stars', 'order': 'desc', 'per_page': 10},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return jsonify({'message': f'GitHub 搜索失败: {str(e)}', 'keywords': keywords}), 502

    # Step 3: 格式化结果
    results = []
    for repo in data.get('items', []):
        results.append({
            'name': repo['full_name'],
            'url': repo['html_url'],
            'description': repo.get('description', ''),
            'stars': repo.get('stargazers_count', 0),
            'language': repo.get('language', ''),
            'topics': repo.get('topics', [])[:5],
            'updated_at': repo.get('updated_at', '')[:10],
        })

    # Step 4: LLM 翻译描述 + 推荐
    if results:
        desc_list = '\n'.join(
            f"{i+1}. {r['name']}: {r['description'][:120]}"
            for i, r in enumerate(results)
        )
        translate_prompt = f"""请将以下 GitHub 项目的英文描述翻译为简洁的中文（每条不超过 30 字），并对前 5 个项目给出 1-2 句推荐说明。

用户需求：{query}

项目列表：
{desc_list}

请以 JSON 格式返回：
{{"descriptions": ["中文描述1", "中文描述2", ...], "recommendation": "推荐说明"}}"""
        try:
            translate_result = _call_llm(translate_prompt, '你是翻译和推荐专家。只返回 JSON。')
            from projects.ai_analyzer import _extract_json
            parsed = json.loads(_extract_json(translate_result))
            cn_descs = parsed.get('descriptions', [])
            for i, r in enumerate(results):
                if i < len(cn_descs) and cn_descs[i]:
                    r['description'] = cn_descs[i]
            recommendation = parsed.get('recommendation', '')
            if isinstance(recommendation, list):
                recommendation = '\n'.join(str(x) for x in recommendation)
        except Exception:
            recommendation = ''
    else:
        recommendation = '未找到相关项目，请尝试换个描述方式。'

    return jsonify({
        'keywords': keywords,
        'recommendation': recommendation,
        'results': results,
    }), 200


@projects_bp.route('/search/add', methods=['POST'])
def add_from_search():
    """从搜索结果添加项目到知识库。"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '请先登录'}), 401
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    github_url = data.get('url', '').strip()
    if not name or not github_url:
        return jsonify({'message': '参数不完整'}), 400

    # 检查是否已存在
    from models import Project
    existing = Project.query.filter_by(github_url=github_url).first()
    if existing:
        return jsonify({'message': '该项目已在知识库中', 'project_id': existing.id}), 409

    project_data = {
        'name': name.split('/')[-1] if '/' in name else name,
        'github_url': github_url,
        'team': data.get('language', ''),
        'tags': data.get('topics', []),
        'created_by': user_id,
    }
    project = ProjectService.create_project(project_data)
    return jsonify(project), 201


@projects_bp.route('/<int:project_id>/page', methods=['GET'])
def project_detail_page(project_id):
    """项目知识卡片详情页。"""
    project = ProjectService.get_project_by_id(project_id)
    if not project:
        return render_template('404.html', message='项目不存在'), 404
    return render_template('projects/detail.html', project=project)
