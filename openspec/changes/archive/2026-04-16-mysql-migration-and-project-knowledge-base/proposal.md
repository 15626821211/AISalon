## Why

当前 AI 沙龙平台采用全内存存储，重启即丢失数据；密码明文存储存在安全隐患。同时，团队各小组产出的 AI 项目散落在 GitHub 和 Wiki 中，成员需要逐个翻阅冗长的代码和文档才能理解项目，严重影响学习效率和积极性。

需要：1）将数据层迁移至 MySQL 实现持久化并加固安全基础；2）新增"项目知识库"模块，通过 GitHub API 拉取项目代码和文档，调用阿里云百炼大模型（qwen-plus）自动提炼知识卡片，让团队成员快速理解每个 AI 项目的设计思路、技术选型和核心代码。

## What Changes

- **BREAKING** 存储层从内存 dict 迁移至 MySQL（SQLAlchemy ORM），User/Event/Signup/Comment 全部建表持久化
- **BREAKING** 密码从明文改为 werkzeug 哈希存储，注册/登录逻辑相应调整
- 配置管理改用环境变量（SECRET_KEY、DASHSCOPE_API_KEY、DATABASE_URL）
- 新增 `projects` 模块：项目 CRUD、项目列表页、项目知识卡片详情页
- 新增 `integrations/github_client`：通过 GitHub REST API 拉取仓库文件树和内容
- 新增 `projects/ai_analyzer`：调用阿里云百炼 DashScope API（qwen-plus），分步提炼项目概览、设计思路、技术选型、架构描述、核心代码解读、经验教训
- 新增项目知识卡片详情页，含讨论区（复用评论机制）
- 导航栏新增"项目知识库"入口
- 修复现有测试（test_events / test_users 调用了不存在的方法）

## Capabilities

### New Capabilities
- `mysql-persistence`: 全平台 MySQL 持久化，SQLAlchemy ORM 模型定义、数据库初始化、现有 Service 层改写
- `password-security`: 密码哈希存储与验证（werkzeug）
- `env-config`: 环境变量配置管理（secret_key、数据库连接串、API key）
- `project-knowledge-base`: 项目知识库模块——项目 CRUD、列表页、知识卡片详情页、讨论区
- `github-integration`: GitHub REST API 集成——拉取仓库文件树、读取代码和文档内容
- `ai-analysis-engine`: AI 分析引擎——调用百炼 DashScope API 分步提炼知识卡片内容

### Modified Capabilities
（无现有 spec，全部为新增）

## Impact

- **代码**: `src/events/`、`src/users/`、`src/app.py`、`src/config.py` 全部改动；新增 `src/projects/`、`src/integrations/`
- **数据库**: 新建 MySQL 数据库 `ai_salon`，含 users/events/signups/comments/projects/project_comments 表
- **依赖**: 新增 `pymysql`、`flask-sqlalchemy`、`openai`（DashScope 兼容）、`requests`（GitHub API）、`python-dotenv`
- **API**: 新增 `/projects/` 系列接口（CRUD + 分析触发 + 评论）
- **前端**: 新增项目列表页和知识卡片详情页模板，导航栏增加入口
- **测试**: 现有测试需适配新 ORM 层，新增 projects 模块测试
- **配置**: 需要 `.env` 文件或环境变量提供 MySQL 连接串和 API key
