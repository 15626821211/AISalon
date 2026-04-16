## Context

当前 AI 沙龙平台基于 Flask，采用内存 dict 存储用户和活动数据，密码明文保存，secret_key 硬编码。平台已有完整的活动管理（CRUD + 报名 + 评论 + 标签筛选）和用户系统（注册/登录/登出/个人中心）。

团队内部各小组的 AI 项目产出散落在公网 GitHub 和内部 Wiki（Confluence at 10.10.100.100:8090），成员学习其他组项目需逐个翻阅代码和文档，效率极低。

本次变更需在保留现有功能的基础上：1）迁移至 MySQL 持久化 + 安全加固；2）新增项目知识库模块，通过 GitHub API + 阿里云百炼 qwen-plus 自动提炼项目知识卡片。

## Goals / Non-Goals

**Goals:**
- 全平台数据持久化（MySQL + SQLAlchemy ORM），重启不丢数据
- 密码哈希存储，配置走环境变量
- 新增项目知识库模块：录入项目 → 拉取 GitHub 代码/文档 → AI 自动分析 → 知识卡片展示
- 知识卡片支持讨论区
- 代码规范：模块分层清晰、函数职责单一、统一错误处理、避免循环导入

**Non-Goals:**
- 不做 Wiki (Confluence) 内容自动抓取（Wiki 仅存链接，手动导航）
- 不做实时自动同步（手动触发分析）
- 不做用户角色/权限体系重构（沿用现有 session 机制）
- 不做前端框架切换（保持 Jinja2 模板 + 原生 JS）
- 不做 analytics 模块的正式集成

## Decisions

### D1: ORM 选型 — Flask-SQLAlchemy

**选择**: Flask-SQLAlchemy + PyMySQL 驱动
**替代方案**: 原始 SQL / Peewee / SQLModel
**理由**: Flask-SQLAlchemy 是 Flask 生态标配，项目 config.py 已有 SQLAlchemy 配置预留；PyMySQL 纯 Python 驱动，无需编译 C 扩展。

### D2: 数据库表设计

```
users
├── id (INT, PK, AUTO_INCREMENT)
├── username (VARCHAR(80), UNIQUE, NOT NULL)
├── password_hash (VARCHAR(256), NOT NULL)
└── created_at (DATETIME)

events
├── id (INT, PK, AUTO_INCREMENT)
├── title (VARCHAR(200), NOT NULL)
├── description (TEXT)
├── location (VARCHAR(200))
├── tags (JSON)
├── user_id (INT, FK → users.id)
├── start_time (DATETIME)
├── end_time (DATETIME, NULL)
└── created_at (DATETIME)

event_signups
├── id (INT, PK, AUTO_INCREMENT)
├── event_id (INT, FK → events.id)
├── user_id (INT, FK → users.id, NULL)
├── name (VARCHAR(100))
├── email (VARCHAR(200))
└── created_at (DATETIME)

event_comments
├── id (INT, PK, AUTO_INCREMENT)
├── event_id (INT, FK → events.id)
├── user_id (INT, FK → users.id)
├── username (VARCHAR(80))
├── content (TEXT)
└── created_at (DATETIME)

projects
├── id (INT, PK, AUTO_INCREMENT)
├── name (VARCHAR(200), NOT NULL)
├── team (VARCHAR(200))
├── github_url (VARCHAR(500), NOT NULL)
├── wiki_url (VARCHAR(500), NULL)
├── tags (JSON)
├── summary (TEXT)
├── design_thinking (TEXT)
├── tech_stack (TEXT)
├── architecture (TEXT)
├── key_code_snippets (JSON)
├── lessons_learned (TEXT)
├── status (VARCHAR(20), DEFAULT 'draft')
├── analyzed_at (DATETIME, NULL)
├── created_by (INT, FK → users.id)
└── created_at (DATETIME)

project_comments
├── id (INT, PK, AUTO_INCREMENT)
├── project_id (INT, FK → projects.id)
├── user_id (INT, FK → users.id)
├── username (VARCHAR(80))
├── content (TEXT)
└── created_at (DATETIME)
```

### D3: 密码哈希 — werkzeug

**选择**: `werkzeug.security.generate_password_hash` / `check_password_hash`
**替代方案**: bcrypt / passlib
**理由**: Flask 已内置 werkzeug，零额外依赖。

### D4: 环境变量管理 — python-dotenv

**选择**: `.env` 文件 + `python-dotenv`
**理由**: 开发简单，生产可用系统环境变量覆盖。

变量清单:
```
SECRET_KEY=<random-string>
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/ai_salon
DASHSCOPE_API_KEY=<api-key>
GITHUB_TOKEN=<optional-for-rate-limit>
```

### D5: GitHub 集成 — REST API + requests

**选择**: GitHub REST API v3 + `requests` 库
**替代方案**: PyGithub / git clone
**理由**: requests 更轻量，只需读取文件树和内容，不需要完整 clone。

核心接口:
- `GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1` → 文件树
- `GET /repos/{owner}/{repo}/contents/{path}` → 文件内容
- 读取 README.md + 文档目录 + 关键配置文件 + 核心代码文件

文件筛选策略:
- 优先: README.md, docs/*, *.md
- 配置: package.json, pyproject.toml, requirements.txt, Dockerfile
- 代码: 按目录结构采样核心模块（src/*, app/*, lib/*）
- 跳过: node_modules, .git, __pycache__, 二进制文件, 图片
- 总内容上限: 约 100KB 文本（qwen-plus 128K context 安全范围内）

### D6: AI 分析引擎 — DashScope 兼容 OpenAI 格式

**选择**: 阿里云百炼 qwen-plus，通过 OpenAI SDK 兼容接口调用
**配置**:
```python
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "qwen-plus"
```

分析流程（分步 Prompt，避免单次输出过长）:
```
Step 1: 项目概览 + 设计思路
  Input: README + 文档摘要
  Output: summary, design_thinking

Step 2: 技术选型分析
  Input: 配置文件 + 代码框架文件
  Output: tech_stack

Step 3: 架构描述
  Input: 目录结构 + 核心模块代码
  Output: architecture

Step 4: 核心代码解读
  Input: 核心代码文件（按重要性排序）
  Output: key_code_snippets (JSON array)

Step 5: 经验教训总结
  Input: 前 4 步结果 + 原始 README
  Output: lessons_learned
```

### D7: 模块目录结构

```
src/
├── app.py                      # 注册 projects Blueprint
├── models.py                   # [新增] 统一 ORM 模型定义
├── config.py                   # [改造] 环境变量配置
├── events/
│   ├── routes.py               # [改造] 适配 ORM
│   └── services.py             # [改造] 适配 ORM
├── users/
│   ├── routes.py               # [改造] 密码哈希
│   └── services.py             # [改造] 适配 ORM
├── projects/                   # [新增]
│   ├── __init__.py
│   ├── routes.py               # 项目 API + 页面路由
│   ├── services.py             # 项目 CRUD + 分析调度
│   └── ai_analyzer.py          # LLM 调用封装
├── integrations/               # [新增]
│   ├── __init__.py
│   └── github_client.py        # GitHub API 封装
└── templates/
    └── projects/
        ├── list.html            # 项目列表页
        └── detail.html          # 知识卡片详情页
```

ORM 模型统一放在 `src/models.py`，避免循环导入。

### D8: 代码规范约束

- 所有 route 函数加 try/except，统一返回 JSON 错误
- Service 层不直接引用 Flask session/request
- 环境变量通过 Config 类集中管理
- 导入顺序: stdlib → third-party → local
- 中文注释（项目既定风格）

## Risks / Trade-offs

- **[MySQL 依赖]** → 开发者需本地安装 MySQL。Mitigation: 文档说明 + 建库脚本
- **[GitHub API 限流]** → 未认证 60 req/hr。Mitigation: 支持可选 GITHUB_TOKEN 提升至 5000/hr；项目只有 5-10 个，手动触发频率极低
- **[LLM 输出质量]** → AI 分析结果可能不准。Mitigation: 分析结果标记 status，支持手动编辑/重新分析
- **[内存→MySQL 迁移]** → 现有数据（内存中）重启后丢失，无迁移需求。属于全新建库，风险低
- **[大仓库分析]** → 代码量超出上下文限制。Mitigation: 文件筛选策略 + 内容截断至 100KB

## Migration Plan

1. 安装依赖: `pip install flask-sqlalchemy pymysql python-dotenv openai requests werkzeug`
2. 创建 `.env` 文件配置环境变量
3. 创建 MySQL 数据库: `CREATE DATABASE ai_salon CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
4. 启动应用时自动 `db.create_all()` 建表
5. 现有内存数据无需迁移（重启后本就丢失）
6. 回滚策略: git revert 即可，新表可 DROP

## Open Questions

- 是否需要为分析结果增加版本历史（当前设计为覆盖式更新）？
- 是否需要 GitHub OAuth 登录（当前仅用 Token 读取公开仓库）？
