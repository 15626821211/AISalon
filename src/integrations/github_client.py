"""Git 仓库 API 集成——支持 GitHub / GitLab 内容拉取。"""

import base64
import re
from urllib.parse import quote, urlparse

import requests
from config import Config

# 不走代理的请求 session，避免公司 VPN/代理导致 SSL 错误
_no_proxy_session = requests.Session()
_no_proxy_session.trust_env = False

# 文件优先级和过滤配置
PRIORITY_FILES = ['README.md', 'readme.md', 'README.rst']
PRIORITY_DIRS = ['docs', 'doc', 'documentation']
CONFIG_FILES = ['package.json', 'pyproject.toml', 'requirements.txt', 'Dockerfile',
                'docker-compose.yml', 'setup.py', 'setup.cfg', 'Cargo.toml', 'go.mod',
                'pom.xml', 'build.gradle', 'Makefile', '.env.example']
CODE_DIRS = ['src', 'app', 'lib', 'core', 'main', 'api', 'server', 'backend', 'frontend',
             'modules', 'service', 'services', 'controller', 'domain', 'common', 'utils']
SKIP_DIRS = {'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
             'dist', 'build', '.next', '.nuxt', 'target', 'vendor', '.idea', '.vscode'}
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp',
                   '.woff', '.woff2', '.ttf', '.eot', '.mp3', '.mp4', '.zip',
                   '.tar', '.gz', '.exe', '.dll', '.so', '.pyc', '.class',
                   '.lock', '.min.js', '.min.css', '.map'}
MAX_CONTENT_SIZE = 400 * 1024  # 400KB


def parse_repo_url(url: str) -> dict:
    """解析仓库地址，支持 GitHub 与 GitLab。"""
    normalized = (url or '').strip().rstrip('/')
    if normalized.endswith('.git'):
        normalized = normalized[:-4]

    parsed = urlparse(normalized)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f'无法解析仓库 URL: {url}')

    path_parts = [part for part in parsed.path.split('/') if part]
    if len(path_parts) < 2:
        raise ValueError(f'无法解析仓库 URL: {url}')

    base_url = f'{parsed.scheme}://{parsed.netloc}'
    host = parsed.netloc.lower()

    if 'github.com' in host:
        owner, repo = path_parts[0], path_parts[1]
        return {
            'provider': 'github',
            'base_url': base_url,
            'owner': owner,
            'repo': repo,
            'project_path': f'{owner}/{repo}',
        }

    if 'gitlab' in host:
        project_path = '/'.join(path_parts)
        return {
            'provider': 'gitlab',
            'base_url': base_url,
            'owner': path_parts[-2],
            'repo': path_parts[-1],
            'project_path': project_path,
        }

    raise ValueError(f'暂不支持的仓库地址: {url}，目前支持 GitHub 和 GitLab')


def parse_github_url(url: str) -> tuple:
    """兼容旧接口：仅解析 GitHub URL。"""
    repo_info = parse_repo_url(url)
    if repo_info['provider'] != 'github':
        raise ValueError(f'不是 GitHub URL: {url}')
    return repo_info['owner'], repo_info['repo']


def _get_headers(provider: str) -> dict:
    """构造请求头，支持 GitHub / GitLab Token。"""
    if provider == 'github':
        headers = {'Accept': 'application/vnd.github.v3+json'}
        token = Config.GITHUB_TOKEN
        if token:
            headers['Authorization'] = f'token {token}'
        return headers

    headers = {'Accept': 'application/json'}
    token = Config.GITLAB_TOKEN
    if token:
        headers['PRIVATE-TOKEN'] = token
    return headers


def _get_gitlab_session(repo_info: dict) -> requests.Session:
    """获取可访问 GitLab API 的会话，优先 token，其次账号密码登录。"""
    session = repo_info.get('_gitlab_session')
    if session is not None:
        return session

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 GitRepoFetcher/1.0'})

    if Config.GITLAB_TOKEN:
        session.headers.update(_get_headers('gitlab'))
        repo_info['_gitlab_session'] = session
        return session

    username = Config.GITLAB_USERNAME
    password = Config.GITLAB_PASSWORD
    if username and password:
        sign_in_url = f"{repo_info['base_url']}/users/sign_in"
        login_page = session.get(sign_in_url, timeout=30)
        login_page.raise_for_status()

        match = re.search(r'name="authenticity_token" value="([^"]+)"', login_page.text)
        if not match:
            raise RuntimeError('GitLab 登录页解析失败，未找到 authenticity_token')

        payload = {
            'authenticity_token': match.group(1),
            'user[login]': username,
            'user[password]': password,
            'user[remember_me]': '0',
        }
        headers = {'Referer': sign_in_url}
        response = session.post(sign_in_url, data=payload, headers=headers, allow_redirects=True, timeout=30)
        response.raise_for_status()

        session.headers.update({'Accept': 'application/json'})
        verify = session.get(f"{repo_info['base_url']}/api/v4/user", timeout=30)
        if verify.status_code != 200:
            raise RuntimeError('GitLab 账号密码登录失败，请检查 GITLAB_USERNAME / GITLAB_PASSWORD 是否正确')

    if not (Config.GITLAB_USERNAME and Config.GITLAB_PASSWORD):
        session.headers.update(_get_headers('gitlab'))

    repo_info['_gitlab_session'] = session
    return session


def _get_github_default_branch(repo_info: dict) -> str:
    url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}"
    resp = _no_proxy_session.get(url, headers=_get_headers('github'), timeout=30)
    if resp.status_code == 403:
        raise RuntimeError('GitHub API 速率限制，请设置 GITHUB_TOKEN 环境变量提升限额')
    if resp.status_code == 404:
        raise RuntimeError(f"GitHub 仓库不存在或无权限访问: {repo_info['project_path']}")
    resp.raise_for_status()
    return resp.json().get('default_branch') or 'main'


def _fetch_github_file_tree(repo_info: dict) -> list:
    branches = []
    default_branch = _get_github_default_branch(repo_info)
    if default_branch:
        branches.append(default_branch)
    branches.extend(['main', 'master'])

    seen = set()
    for branch in branches:
        if branch in seen:
            continue
        seen.add(branch)
        url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/git/trees/{branch}?recursive=1"
        resp = _no_proxy_session.get(url, headers=_get_headers('github'), timeout=30)
        if resp.status_code == 403:
            raise RuntimeError('GitHub API 速率限制，请设置 GITHUB_TOKEN 环境变量提升限额')
        if resp.status_code == 200:
            repo_info['branch'] = branch
            data = resp.json()
            return [item for item in data.get('tree', []) if item.get('type') == 'blob']

    raise RuntimeError(f"GitHub 仓库分支读取失败: {repo_info['project_path']}")


def _fetch_github_file_content(repo_info: dict, path: str) -> str:
    """获取 GitHub 单个文件内容（自动 base64 解码）。"""
    url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/contents/{path}"
    params = {}
    if repo_info.get('branch'):
        params['ref'] = repo_info['branch']
    resp = _no_proxy_session.get(url, headers=_get_headers('github'), params=params, timeout=30)
    if resp.status_code != 200:
        return ''
    data = resp.json()
    if data.get('encoding') == 'base64' and data.get('content'):
        try:
            return base64.b64decode(data['content']).decode('utf-8', errors='replace')
        except Exception:
            return ''
    return ''


def _get_gitlab_project_info(repo_info: dict) -> dict:
    session = _get_gitlab_session(repo_info)
    project_id = quote(repo_info['project_path'], safe='')
    url = f"{repo_info['base_url']}/api/v4/projects/{project_id}"
    resp = session.get(url, timeout=30)
    if resp.status_code in (401, 403):
        raise RuntimeError('GitLab API 鉴权失败，请配置 GITLAB_TOKEN，或提供可登录的 GITLAB_USERNAME / GITLAB_PASSWORD')
    if resp.status_code == 404:
        if not (Config.GITLAB_TOKEN or (Config.GITLAB_USERNAME and Config.GITLAB_PASSWORD)):
            raise RuntimeError(
                f"GitLab 仓库不存在或无权限访问: {repo_info['project_path']}。"
                '如果这是私有仓库，请在 .env 中设置 GITLAB_TOKEN，或提供 GITLAB_USERNAME / GITLAB_PASSWORD。'
            )
        raise RuntimeError(
            f"GitLab 仓库不存在或无权限访问: {repo_info['project_path']}。"
            '请确认仓库路径正确，且当前账号对该仓库有读取权限。'
        )
    if resp.status_code >= 500:
        raise RuntimeError(f"GitLab 服务异常（HTTP {resp.status_code}），请检查 GitLab 站点或网关是否可用")
    resp.raise_for_status()
    return resp.json()


def _fetch_gitlab_file_tree(repo_info: dict) -> list:
    session = _get_gitlab_session(repo_info)
    project_info = _get_gitlab_project_info(repo_info)
    repo_info['branch'] = project_info.get('default_branch') or 'main'
    project_id = quote(repo_info['project_path'], safe='')
    url = f"{repo_info['base_url']}/api/v4/projects/{project_id}/repository/tree"

    tree = []
    page = 1
    while True:
        resp = session.get(
            url,
            params={
                'ref': repo_info['branch'],
                'recursive': True,
                'per_page': 100,
                'page': page,
            },
            timeout=30,
        )
        if resp.status_code in (401, 403):
            raise RuntimeError('GitLab API 鉴权失败，请检查 GitLab 账号权限或 GITLAB_TOKEN 配置')
        if resp.status_code >= 500:
            raise RuntimeError(f"GitLab 文件树读取失败（HTTP {resp.status_code}），请稍后重试或检查 GitLab 服务状态")
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        tree.extend(item for item in data if item.get('type') == 'blob')
        next_page = resp.headers.get('X-Next-Page')
        if not next_page:
            break
        page = int(next_page)

    return tree


def _fetch_gitlab_file_content(repo_info: dict, path: str) -> str:
    session = _get_gitlab_session(repo_info)
    project_id = quote(repo_info['project_path'], safe='')
    encoded_path = quote(path, safe='')
    url = f"{repo_info['base_url']}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw"
    resp = session.get(
        url,
        params={'ref': repo_info.get('branch', 'main')},
        timeout=30,
    )
    if resp.status_code >= 500:
        raise RuntimeError(f"GitLab 文件内容读取失败（HTTP {resp.status_code}），请稍后重试或检查 GitLab 服务状态")
    if resp.status_code != 200:
        return ''
    return resp.text


def _should_skip(path: str) -> bool:
    """判断文件是否应跳过。"""
    parts = path.split('/')
    for part in parts:
        if part in SKIP_DIRS:
            return True
    ext = '.' + path.rsplit('.', 1)[-1].lower() if '.' in path else ''
    if ext in SKIP_EXTENSIONS:
        return True
    return False


def select_files(tree: list) -> list:
    """根据优先级策略选择文件，返回路径列表。"""
    readme = []
    docs = []
    configs = []
    code = []
    other = []

    for item in tree:
        path = item.get('path', '')
        if _should_skip(path):
            continue
        filename = path.split('/')[-1]
        # README
        if filename.lower() in [f.lower() for f in PRIORITY_FILES]:
            readme.append(path)
        # 文档目录
        elif any(path.startswith(d + '/') for d in PRIORITY_DIRS) and path.endswith('.md'):
            docs.append(path)
        # 配置文件
        elif filename in CONFIG_FILES:
            configs.append(path)
        # 核心代码目录（顶层匹配或任意层级含 src/）或代码文件扩展名
        elif any(path.startswith(d + '/') for d in CODE_DIRS) or '/src/' in path or path.endswith(('.java', '.py', '.go', '.rs', '.ts', '.js', '.kt')):
            code.append(path)
        # 根目录 .md 文件
        elif '/' not in path and path.endswith('.md'):
            docs.append(path)
        else:
            other.append(path)

    # 对 code 列表进行智能排序：优先 Controller/Service/核心文件，同时分散各模块
    def _code_priority(p):
        lower = p.lower()
        if 'controller' in lower or 'resource' in lower:
            return 0
        if 'service' in lower and 'impl' not in lower:
            return 1
        if 'service' in lower:
            return 2
        if 'config' in lower or 'application' in lower:
            return 3
        if 'model' in lower or 'entity' in lower or 'dto' in lower:
            return 4
        if 'repository' in lower or 'dao' in lower or 'mapper' in lower:
            return 5
        return 6

    # 按模块分组，每个模块取 top 文件，确保覆盖所有模块
    from collections import defaultdict
    module_files = defaultdict(list)
    for p in code:
        # 提取一级目录作为模块名
        module = p.split('/')[0] if '/' in p else '_root'
        module_files[module].append(p)
    # 每个模块内部按优先级排序
    for mod in module_files:
        module_files[mod].sort(key=_code_priority)
    # 轮询各模块，确保每个模块都有代码被选中
    balanced_code = []
    max_per_module = max(10, 80 // max(len(module_files), 1))
    for mod in sorted(module_files.keys()):
        balanced_code.extend(module_files[mod][:max_per_module])
    # 再按全局优先级排序
    balanced_code.sort(key=_code_priority)

    # 按优先级合并：README → 代码（优先） → 配置（限量） → 文档 → 其他
    # 对于 Java 多模块项目，限制 pom.xml 等配置文件数量，优先保证代码文件
    root_configs = [c for c in configs if '/' not in c]  # 根目录配置
    sub_configs = [c for c in configs if '/' in c]  # 子模块配置
    selected = readme + root_configs + balanced_code[:80] + sub_configs[:5] + docs[:15] + other[:10]
    return selected


def _build_tree_string(tree: list) -> str:
    """将文件列表构建为树形目录结构字符串（├── / └── 样式）。"""
    # 构建嵌套 dict 表示目录树
    root = {}
    for item in tree:
        path = item.get('path', '')
        if _should_skip(path):
            continue
        parts = path.split('/')
        node = root
        for part in parts:
            node = node.setdefault(part, {})

    lines = []
    _max_depth = 4  # 最多展示4层深度

    def _render(node, prefix, depth):
        if depth > _max_depth:
            if node:
                lines.append(f'{prefix}...')
            return
        entries = sorted(node.keys(), key=lambda k: (not bool(node[k]), k))
        for i, name in enumerate(entries):
            is_last = (i == len(entries) - 1)
            connector = '└── ' if is_last else '├── '
            children = node[name]
            if children:
                lines.append(f'{prefix}{connector}{name}/')
                extension = '    ' if is_last else '│   '
                _render(children, prefix + extension, depth + 1)
            else:
                lines.append(f'{prefix}{connector}{name}')

    _render(root, '', 0)
    return '\n'.join(lines)


def _build_repo_content(tree: list, content_loader) -> dict:
    """基于文件树和内容加载器组装分析输入。"""
    # 构建树形目录结构摘要
    tree_summary = _build_tree_string(tree)

    selected_paths = select_files(tree)

    files = []
    total_size = 0
    for path in selected_paths:
        if total_size >= MAX_CONTENT_SIZE:
            break
        content = content_loader(path)
        if content:
            content_bytes = len(content.encode('utf-8'))
            if total_size + content_bytes > MAX_CONTENT_SIZE:
                remaining = MAX_CONTENT_SIZE - total_size
                content = content[:remaining]
            files.append({'path': path, 'content': content})
            total_size += len(content.encode('utf-8'))

    return {
        'tree_summary': tree_summary,
        'files': files,
    }


def fetch_repo_content(repo_url: str) -> dict:
    """
    主入口：解析 URL → 拉取文件树 → 智能选择 → 读取内容。
    返回: {'tree_summary': str, 'files': [{'path': str, 'content': str}]}
    """
    repo_info = parse_repo_url(repo_url)

    if repo_info['provider'] == 'github':
        tree = _fetch_github_file_tree(repo_info)
        return _build_repo_content(tree, lambda path: _fetch_github_file_content(repo_info, path))

    if repo_info['provider'] == 'gitlab':
        tree = _fetch_gitlab_file_tree(repo_info)
        return _build_repo_content(tree, lambda path: _fetch_gitlab_file_content(repo_info, path))

    raise ValueError(f"暂不支持的仓库类型: {repo_url}")
