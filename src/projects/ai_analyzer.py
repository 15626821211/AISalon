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
    http_client = httpx.Client(proxy=None)
    return AzureOpenAI(
        api_key=api_key,
        azure_endpoint=Config.OPENAI_BASE_URL.rsplit('/openai', 1)[0] if '/openai' in Config.OPENAI_BASE_URL else Config.OPENAI_BASE_URL,
        api_version='2024-12-01-preview',
        http_client=http_client,
    )


def _call_llm(prompt: str, system_prompt: str = '') -> str:
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
            max_tokens=4096,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f'LLM 调用失败: {e}')
        raise


SYSTEM_PROMPT = '你是一个资深的技术专家和项目分析师。请用简体中文回答，内容专业、清晰、有条理。使用 Markdown 格式排版：用 ## 和 ### 作为标题层级，善用 **加粗**、列表、> 引用块等格式让内容丰富多样、层次分明。'


def step1_overview_and_design(readme_content: str, docs_content: str) -> dict:
    """Step 1: 项目概览 + 设计思路。"""
    prompt = f"""请基于以下项目文档，提炼出：
1. **项目概览**（summary）：用 2-3 句纯文本简洁概括项目是什么、解决什么问题、面向什么用户。不要使用 Markdown 格式，不要用标题和列表。
2. **设计思路**（design_thinking）：用 Markdown 格式阐述核心设计理念、架构决策和设计权衡，使用标题分段、列表和引用。

---
README:
{readme_content[:8000]}

---
其他文档:
{docs_content[:8000]}

请以 JSON 格式返回：{{"summary": "...", "design_thinking": "..."}}"""

    result = _call_llm(prompt, SYSTEM_PROMPT)
    try:
        return json.loads(_extract_json(result))
    except json.JSONDecodeError:
        return {'summary': result, 'design_thinking': ''}


def step2_tech_stack(config_content: str, code_sample: str) -> str:
    """Step 2: 技术选型分析。"""
    prompt = f"""请基于以下项目配置文件和代码片段，分析该项目的技术选型：
- 使用了哪些编程语言、框架、AI 模型、工具链？
- 为什么选择这些技术？有什么优劣？

---
配置文件:
{config_content[:6000]}

---
代码片段:
{code_sample[:6000]}

请用 Markdown 格式回答，使用 ## 标题分类（如语言、框架、数据库、工具链），每类用列表和加粗展示，附简要优劣点评。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step3_architecture(tree_summary: str, core_code: str) -> str:
    """Step 3: 架构描述。"""
    prompt = f"""请基于以下项目目录结构和核心模块代码，描述该项目的系统架构：
- 模块划分和职责
- 数据流向
- 核心组件之间的关系

---
目录结构:
{tree_summary[:4000]}

---
核心代码:
{core_code[:8000]}

请用 Markdown 格式回答，用 ## 标题区分各模块，用列表描述职责，用 > 引用块标注关键设计决策。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step4_key_code_snippets(code_files: list) -> list:
    """Step 4: 核心代码解读。"""
    code_text = ''
    for f in code_files[:10]:
        code_text += f"\n\n--- {f['path']} ---\n{f['content'][:3000]}"
        if len(code_text) > 15000:
            break

    prompt = f"""请从以下代码文件中，选出 3-5 个最具学习价值的代码片段，并为每个片段写出详细解读。

{code_text}

请以 JSON 数组格式返回：
[
  {{"file": "文件路径", "code": "关键代码片段", "explanation": "解读说明"}},
  ...
]"""

    result = _call_llm(prompt, SYSTEM_PROMPT)
    try:
        return json.loads(_extract_json(result))
    except json.JSONDecodeError:
        return [{'file': '', 'code': '', 'explanation': result}]


def step5_use_cases(summary: str, design: str, readme_content: str) -> str:
    """Step 5: 应用场景分析。"""
    prompt = f"""请基于以下项目信息，简要列出该项目的应用场景。要求简洁，每个要点一句话即可，不需要详细展开。

包含：
- 适用场景（3-5 个要点）
- 目标用户（一句话列举）

---
项目概览: {summary[:2000]}
设计思路: {design[:1000]}
README: {readme_content[:2000]}

请用 Markdown 格式，用简短的列表呈现，不要写长段落。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step5b_usage_guide(readme_content: str, config_content: str, tree_summary: str) -> str:
    """Step 5b: 使用指南——拉取工程、安装环境、部署运行。"""
    prompt = f"""请基于以下项目信息，编写一份详细的使用指南，帮助用户从零开始使用该项目。

必须包含以下章节：
1. **拉取项目** — git clone 命令及注意事项
2. **环境准备** — 所需的运行环境、语言版本、依赖工具
3. **安装依赖** — 具体的安装命令
4. **配置说明** — 需要配置的环境变量或配置文件
5. **启动运行** — 开发环境和生产环境的启动命令
6. **常见问题** — 可能遇到的问题及解决方法

---
README:
{readme_content[:5000]}

配置文件:
{config_content[:3000]}

目录结构:
{tree_summary[:2000]}

请用 Markdown 格式回答，每个章节用 ## 标题，命令用代码块包裹，步骤清晰可操作。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step6_lessons_learned(summary: str, design: str, tech: str, architecture: str) -> str:
    """Step 5: 经验教训总结。"""
    prompt = f"""基于以下项目分析结果，总结该项目的核心经验教训：
- 哪些做法值得借鉴？
- 踩了哪些坑？
- 有哪些可复用的最佳实践？

---
项目概览: {summary[:2000]}
设计思路: {design[:2000]}
技术选型: {tech[:2000]}
架构描述: {architecture[:2000]}

请用 Markdown 格式回答，用 ## 标题分段（如亮点、踩坑、最佳实践），善用 ✅ ⚠️ 💡 等 emoji 和加粗来突出重点。"""

    return _call_llm(prompt, SYSTEM_PROMPT)


def step7_diagrams(summary: str, design: str, tech: str, architecture: str, tree_summary: str) -> list:
    """Step 7: 生成 Mermaid 可视化图表（设计思路图、架构图、流程图、技术栈图）。"""
    prompt = f"""你是一个擅长用 Mermaid 画图的技术专家。请基于以下项目分析结果，生成 4 张 Mermaid 图表代码。

要求：
1. **设计思路图**（design）：用 `graph TD` 展示项目的核心设计理念、关键设计决策和各模块设计目标之间的关系
2. **架构图**（architecture）：用 `graph TD` 展示系统模块和组件之间的关系，包含数据流向箭头
3. **业务流程图**（flow）：用 `flowchart LR` 或 `sequenceDiagram` 展示系统核心业务流程或用户操作流程
4. **技术栈图**（tech）：用 `graph LR` 展示技术选型分类（语言、框架、数据库、工具等）

注意：
- 每张图代码必须是合法的 Mermaid 语法，可以直接渲染
- 节点文字用中文
- 保持简洁，每张图不超过 20 个节点
- 不要在 Mermaid 代码中使用括号字符如 ( ) [ ]，请用引号包裹节点文字

---
项目概览: {summary[:1500]}
设计思路: {design[:1500]}
技术选型: {tech[:1500]}
架构描述: {architecture[:1500]}
目录结构: {tree_summary[:2000]}

请以 JSON 数组格式返回，每个元素包含 title（图表标题）、type（diagram类型）、mermaid（Mermaid 代码）：
[
  {{"title": "设计思路图", "type": "design", "mermaid": "graph TD\\n  A[\\"..\\"] --> B[\\"..\\"]"}},
  {{"title": "系统架构图", "type": "architecture", "mermaid": "graph TD\\n  ..."}},
  {{"title": "业务流程图", "type": "flow", "mermaid": "flowchart LR\\n  ..."}},
  {{"title": "技术栈总览", "type": "tech", "mermaid": "graph LR\\n  ..."}}
]"""

    result = _call_llm(prompt, SYSTEM_PROMPT)
    try:
        diagrams = json.loads(_extract_json(result))
        if isinstance(diagrams, list):
            return diagrams
    except json.JSONDecodeError:
        pass
    return []


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

    for f in files:
        path = f['path'].lower()
        if 'readme' in path:
            readme_content += f['content'] + '\n'
        elif path.endswith('.md'):
            docs_content += f"\n--- {f['path']} ---\n{f['content']}"
        elif any(cfg in path for cfg in ['package.json', 'pyproject.toml', 'requirements.txt',
                                          'dockerfile', 'setup.py', 'cargo.toml', 'go.mod']):
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
        'diagrams': [],
        'status': 'partial',
    }

    try:
        # Step 1
        step1 = step1_overview_and_design(readme_content, docs_content)
        result['summary'] = step1.get('summary', '')
        result['design_thinking'] = step1.get('design_thinking', '')

        # Step 2
        code_sample = '\n'.join(f['content'][:2000] for f in code_files[:5])
        result['tech_stack'] = step2_tech_stack(config_content, code_sample)

        # Step 3
        core_code = '\n'.join(f"\n--- {f['path']} ---\n{f['content'][:2000]}" for f in code_files[:8])
        result['architecture'] = step3_architecture(tree_summary, core_code)

        # Step 4
        result['key_code_snippets'] = step4_key_code_snippets(code_files)

        # Step 5: 应用场景 + 使用指南
        result['use_cases'] = step5_use_cases(
            result['summary'], result['design_thinking'], readme_content
        )
        result['usage_guide'] = step5b_usage_guide(
            readme_content, config_content, tree_summary
        )

        # Step 6: 经验教训
        result['lessons_learned'] = step6_lessons_learned(
            result['summary'], result['design_thinking'],
            result['tech_stack'], result['architecture']
        )

        # Step 7: 生成 Mermaid 可视化图表
        result['diagrams'] = step7_diagrams(
            result['summary'], result['design_thinking'],
            result['tech_stack'], result['architecture'],
            tree_summary,
        )

        result['status'] = 'analyzed'
    except Exception as e:
        logger.error(f'项目分析失败: {e}')
        # 保留已完成步骤的结果，status 为 partial

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
