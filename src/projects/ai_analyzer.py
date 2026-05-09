"""AI 分析引擎——调用 OpenAI 兼容 API 分步提炼项目知识卡片。"""

import json
import logging
import httpx
from openai import AzureOpenAI
from config import Config

logger = logging.getLogger(__name__)


def _get_client():
    """获取 Azure OpenAI 客户端。"""
    api_key = Config.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError('未配置 OPENAI_API_KEY')
    # 使用不走代理的 httpx 客户端，避免 VPN 导致 Azure 防火墙 403
    http_client = httpx.Client(proxy=None, trust_env=False, timeout=httpx.Timeout(300.0))
    return AzureOpenAI(
        api_key=api_key,
        azure_endpoint=Config.OPENAI_BASE_URL.rsplit('/openai', 1)[0] if '/openai' in Config.OPENAI_BASE_URL else Config.OPENAI_BASE_URL,
        api_version='2024-12-01-preview',
        http_client=http_client,
    )


def _call_llm(prompt: str, system_prompt: str = '', max_tokens: int = 8192) -> str:
    """调用 LLM，返回文本响应。"""
    client = _get_client()
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})
    try:
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=messages,
            temperature=0.3,
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        if finish_reason == 'length':
            logger.warning(f'LLM 响应被截断 (max_tokens={max_tokens})，finish_reason=length')
        return (content or '').strip()
    except Exception as e:
        logger.error(f'LLM 调用失败: {e}')
        raise


SYSTEM_PROMPT = '你是一个资深的技术专家和项目分析师。请用简体中文回答，内容专业、精炼、有条理。使用 Markdown 格式排版：用 ## 和 ### 作为标题层级，善用列表和加粗。注意：内容要精简扼要，每个要点 1-2 句话，不要长篇大论，但必须覆盖项目中的所有业务模块，不要遗漏。'


def step1_overview_and_design(readme_content: str, docs_content: str, tree_summary: str = '') -> dict:
    """Step 1: 项目概览 + 设计思路。"""
    prompt = f"""请基于以下项目文档和目录结构，提炼出：
1. **项目概览**（summary）：用 2-3 句纯文本简洁概括项目是什么、解决什么问题、面向什么用户。不要使用 Markdown 格式。
2. **设计思路**（design_thinking）：用 Markdown 格式，精炼地阐述核心设计理念和架构决策。
   - 必须基于目录结构列出项目中的**所有模块/子项目**及其职责（每个模块一句话）
   - README 只作参考，以目录结构为准发现所有模块
   - 每个要点 1-2 句话，不要长篇展开

---
README:
{readme_content[:6000]}

---
目录结构（以此为准发现所有模块）:
{tree_summary[:6000]}

请以 JSON 格式返回：{{"summary": "...", "design_thinking": "..."}}"""

    result = _call_llm(prompt, SYSTEM_PROMPT)
    try:
        return json.loads(_extract_json(result))
    except json.JSONDecodeError:
        return {'summary': result, 'design_thinking': ''}


def step2_tech_stack(config_content: str, code_sample: str) -> str:
    """Step 2: 技术选型分析。"""
    prompt = f"""请基于以下项目配置文件和来自不同模块的代码片段，精炼分析该项目的技术选型。

要求：
- 列出使用的编程语言、框架、中间件、数据库
- 注意代码来自不同模块/子项目，请综合分析各模块的技术栈差异
- 每项技术一句话点评优劣，不要长段落
- 如果能读出版本信息请标注

---
配置文件:
{config_content[:6000]}

---
代码片段（来自各模块）:
{code_sample[:8000]}

请用 Markdown 格式回答，使用 ## 标题分类，每类用列表展示，保持简洁。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step3_architecture(tree_summary: str, core_code: str) -> str:
    """Step 3: 架构描述。"""
    prompt = f"""请基于以下项目目录结构和来自各模块的核心代码，精炼描述该项目的系统架构。

关键要求：
- 必须遍历目录结构中的**每一个**一级目录/模块，逐一用 1-2 句话说明其职责
- 代码来自不同模块，请结合代码内容描述各模块的具体实现
- 不要遗漏任何模块，以目录结构为准，不要只看 README
- 简述模块间依赖关系和数据流向
- 如有分层架构（如 Controller-Service-Repository）简要说明

---
目录结构:
{tree_summary[:6000]}

---
各模块核心代码:
{core_code[:10000]}

请用 Markdown 格式回答，用 ## 标题区分各模块，每个模块用 1-2 句话描述，保持精炼。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step4_key_code_snippets(code_files: list) -> list:
    """Step 4: 核心代码解读。"""
    code_text = ''
    for f in code_files[:20]:
        code_text += f"\n\n--- {f['path']} ---\n{f['content'][:4000]}"
        if len(code_text) > 25000:
            break

    prompt = f"""请从以下来自不同模块的代码文件中，选出 5-8 个最具代表性的代码片段，并简要解读。

要求：
- 代码来自不同模块/子项目，**每个模块至少选 1 个**代码片段
- 优先选择业务核心逻辑（Controller、Service、核心算法）
- 每个片段的解读限 2-3 句话，说明做了什么、为什么这么设计
- 代码片段保持精简，只截取关键部分

{code_text}

请以 JSON 数组格式返回（5-8 个片段，覆盖不同模块）：
[
  {{"file": "文件路径", "code": "关键代码片段", "explanation": "解读说明"}},
  ...
]"""

    result = _call_llm(prompt, SYSTEM_PROMPT)
    try:
        parsed = json.loads(_extract_json(result))
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
    except json.JSONDecodeError:
        pass
    # 二次尝试：直接解析整个结果
    try:
        parsed = json.loads(result)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    # 最终回退：将整段文本作为一条解读
    return [{'file': '', 'code': '', 'explanation': result}]


def step5_use_cases(summary: str, design: str, readme_content: str) -> str:
    """Step 5: 应用场景分析。"""
    prompt = f"""请基于以下项目信息，用列表简要列出应用场景和目标用户。

- 适用场景（3-5 个要点，每点一句话）
- 目标用户（一句话）

---
项目概览: {summary[:1500]}
README: {readme_content[:1500]}

请用 Markdown 列表，不要写段落。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step5b_usage_guide(readme_content: str, config_content: str, tree_summary: str) -> str:
    """Step 5b: 使用指南——拉取工程、安装环境、部署运行。"""
    prompt = f"""请基于以下项目信息，编写一份精炼的使用指南。

包含以下章节（每章 3-5 行即可）：
1. **环境准备** — 所需环境和工具
2. **安装依赖** — 安装命令
3. **配置说明** — 关键配置项
4. **启动运行** — 开发/生产启动命令

---
README:
{readme_content[:4000]}

配置文件:
{config_content[:2000]}

请用 Markdown 格式，命令用代码块包裹，保持精炼可操作。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step6_lessons_learned(summary: str, design: str, tech: str, architecture: str) -> str:
    """Step 5: 经验教训总结。"""
    prompt = f"""基于以下项目分析结果，总结核心经验教训（每部分 3-5 个要点，每点一句话）：

- ✅ 值得借鉴的做法
- ⚠️ 需要注意的问题
- 💡 可复用的最佳实践

---
项目概览: {summary[:1500]}
技术选型: {tech[:1500]}
架构描述: {architecture[:1500]}

请用 Markdown 列表，保持精炼。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step6b_directory_structure(tree_summary: str, readme_content: str) -> str:
    """Step 6b: 生成带注释的目录结构说明。"""
    prompt = f"""请基于以下项目的目录结构信息，生成一份精简的带注释的目录结构说明。

要求：
1. 用树形结构展示所有一级和二级目录，每个目录后用 `#` 注释说明作用
2. **不要遗漏任何一级目录/模块**
3. 忽略 .gitignore、LICENSE、__pycache__、node_modules 等
4. 树形结构之后，用列表对每个一级目录做一句话功能说明

---
目录结构:
{tree_summary[:8000]}

---
README:
{readme_content[:2000]}

请用 Markdown 格式回答，先展示树形结构（用代码块），再用列表做模块说明。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step7_diagrams(summary: str, design: str, tech: str, architecture: str, tree_summary: str) -> list:
    """Step 7: 逐张生成 Mermaid 可视化图表，每张单独调用避免响应截断。"""
    common_rules = """注意：
- 兼容 Mermaid v10.9.1 语法
- 节点 ID 用英文字母，节点文字用中文放在方括号内，如: A[用户请求] --> B[API网关]
- 节点文字中禁止: 双引号 单引号 反引号 圆括号 方括号 花括号 竖线 尖括号 分号 和号 井号（用中文替代）
- 边标签用 -->|标签| 语法
- subgraph 标题只用简单中文
- 每张图 6-10 个节点，保持简洁
- 不用 ::: 样式，不用 direction 声明
- sequenceDiagram 参与者名称用英文，消息文字用中文"""

    context = f"""\n项目概览: {summary[:400]}\n架构描述: {architecture[:600]}\n目录结构: {tree_summary[:600]}"""

    diagram_specs = [
        ('design', '设计思路图', '用 `graph TD` 展示项目核心设计理念和各模块设计目标之间的关系'),
        ('architecture', '系统架构图', '用 `graph TD` 加 subgraph 展示系统模块和组件之间的关系，包含数据流向'),
        ('flow', '业务流程图', '用 `sequenceDiagram` 展示核心业务流程中各模块的调用顺序'),
        ('tech', '技术栈图', '用 `graph LR` 加 subgraph 展示技术选型分类'),
        ('dependency', '模块依赖图', '用 `graph LR` 展示各业务模块之间的依赖和调用关系'),
        ('callgraph', '调用链路图', '用 `sequenceDiagram` 展示一个典型 API 请求从入口到数据库的完整调用链路'),
        ('deployment', '部署架构图', '用 `graph TD` 加 subgraph 展示生产环境部署拓扑'),
    ]

    all_diagrams = []
    for dtype, title, desc in diagram_specs:
        try:
            prompt = f"""请生成 1 张「{title}」的 Mermaid 代码。要求：{desc}。
{common_rules}
{context}

请以 JSON 格式返回（不要 markdown 代码块包裹）：
{{"title": "{title}", "type": "{dtype}", "mermaid": "graph TD\\n  A[...] --> B[...]"}}"""

            result = _call_llm(prompt, SYSTEM_PROMPT, max_tokens=2048)
            parsed = json.loads(_extract_json(result))
            if isinstance(parsed, dict) and 'mermaid' in parsed:
                all_diagrams.append(parsed)
            elif isinstance(parsed, list) and parsed:
                all_diagrams.append(parsed[0])
        except Exception as e:
            logger.warning(f'Step 7 图表「{title}」生成失败: {e}')
            continue

    return all_diagrams


def analyze_project(repo_content: dict) -> dict:
    """
    完整 5 步分析流水线。
    参数: repo_content — github_client.fetch_repo_content() 的返回值
    返回: 分析结果 dict，包含 summary, design_thinking, tech_stack, architecture, key_code_snippets, lessons_learned, status
    """
    files = repo_content.get('files', [])
    tree_summary = repo_content.get('tree_summary', '')

    # 分类文件内容
    readme_content = ''
    docs_content = ''
    config_content = ''
    code_files = []

    config_filenames = {'package.json', 'pyproject.toml', 'requirements.txt',
                         'dockerfile', 'docker-compose.yml', 'setup.py', 'setup.cfg',
                         'cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
                         'makefile', '.env.example', 'application.yml',
                         'application.yaml', 'application.properties'}
    for f in files:
        path_lower = f['path'].lower()
        filename = f['path'].split('/')[-1].lower()
        if 'readme' in path_lower:
            readme_content += f['content'] + '\n'
        elif path_lower.endswith('.md'):
            docs_content += f"\n--- {f['path']} ---\n{f['content']}"
        elif filename in config_filenames or (path_lower.endswith(('.xml', '.properties', '.yml', '.yaml')) and '/src/' not in path_lower):
            config_content += f"\n--- {f['path']} ---\n{f['content']}"
        else:
            code_files.append(f)

    result = {
        'summary': '',
        'use_cases': '',
        'design_thinking': '',
        'tech_stack': '',
        'architecture': '',
        'key_code_snippets': [],
        'lessons_learned': '',
        'usage_guide': '',
        'directory_structure': '',
        'diagrams': [],
        'status': 'partial',
    }

    # 按模块分组代码文件，确保各步骤均匀覆盖所有模块
    from collections import defaultdict
    module_code = defaultdict(list)
    for f in code_files:
        module = f['path'].split('/')[0] if '/' in f['path'] else '_root'
        module_code[module].append(f)

    def _balanced_sample(n_files: int, max_chars: int) -> list:
        """从各模块轮询采样代码文件，确保覆盖所有模块。"""
        sampled = []
        per_module = max(2, n_files // max(len(module_code), 1))
        for mod in sorted(module_code.keys()):
            sampled.extend(module_code[mod][:per_module])
        # 去重并截断到 n_files
        seen = set()
        unique = []
        for f in sampled:
            if f['path'] not in seen:
                seen.add(f['path'])
                unique.append(f)
        return unique[:n_files]

    try:
        # Step 1
        step1 = step1_overview_and_design(readme_content, docs_content, tree_summary)
        result['summary'] = step1.get('summary', '')
        result['design_thinking'] = step1.get('design_thinking', '')
    except Exception as e:
        logger.error(f'Step 1 项目概览分析失败: {e}')

    try:
        # Step 2：均匀采样各模块代码用于技术选型
        step2_files = _balanced_sample(12, 8000)
        code_sample = '\n'.join(f"--- {f['path']} ---\n{f['content'][:3000]}" for f in step2_files)
        result['tech_stack'] = step2_tech_stack(config_content, code_sample)
    except Exception as e:
        logger.error(f'Step 2 技术选型分析失败: {e}')

    try:
        # Step 3：均匀采样各模块代码用于架构分析
        step3_files = _balanced_sample(18, 10000)
        core_code = '\n'.join(f"\n--- {f['path']} ---\n{f['content'][:3000]}" for f in step3_files)
        result['architecture'] = step3_architecture(tree_summary, core_code)
    except Exception as e:
        logger.error(f'Step 3 架构分析失败: {e}')

    try:
        # Step 4：均匀采样各模块代码用于核心代码解读
        step4_files = _balanced_sample(24, 25000)
        result['key_code_snippets'] = step4_key_code_snippets(step4_files)
    except Exception as e:
        logger.error(f'Step 4 核心代码分析失败: {e}')

    try:
        # Step 5: 应用场景 + 使用指南
        result['use_cases'] = step5_use_cases(
            result['summary'], result['design_thinking'], readme_content
        )
    except Exception as e:
        logger.error(f'Step 5 应用场景分析失败: {e}')

    try:
        result['usage_guide'] = step5b_usage_guide(
            readme_content, config_content, tree_summary
        )
    except Exception as e:
        logger.error(f'Step 5b 使用指南生成失败: {e}')

    try:
        # Step 6: 经验教训
        result['lessons_learned'] = step6_lessons_learned(
            result['summary'], result['design_thinking'],
            result['tech_stack'], result['architecture']
        )
    except Exception as e:
        logger.error(f'Step 6 经验教训分析失败: {e}')

    try:
        # Step 6b: 目录结构说明
        result['directory_structure'] = step6b_directory_structure(tree_summary, readme_content)
    except Exception as e:
        logger.error(f'Step 6b 目录结构分析失败: {e}')

    try:
        # Step 7: 生成 Mermaid 可视化图表
        result['diagrams'] = step7_diagrams(
            result['summary'], result['design_thinking'],
            result['tech_stack'], result['architecture'],
            tree_summary,
        )
    except Exception as e:
        logger.error(f'Step 7 图表生成失败: {e}')

    # 判断整体状态：有 summary 即认为分析成功
    if result['summary']:
        result['status'] = 'analyzed'

    return result


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 块。"""
    # 尝试找 ```json ... ``` 块
    import re
    match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 尝试找 { ... } 或 [ ... ]
    for start, end in [('{', '}'), ('[', ']')]:
        idx_start = text.find(start)
        idx_end = text.rfind(end)
        if idx_start != -1 and idx_end != -1 and idx_end > idx_start:
            return text[idx_start:idx_end + 1]
    return text
