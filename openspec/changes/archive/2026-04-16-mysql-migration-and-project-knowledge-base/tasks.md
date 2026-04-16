## 1. 环境与配置

- [x] 1.1 安装依赖：`pip install flask-sqlalchemy pymysql python-dotenv openai requests werkzeug` 并更新 `requirements.txt`
- [x] 1.2 创建 `.env` 文件，配置 `SECRET_KEY`、`DATABASE_URL=mysql+pymysql://root:root@localhost:3306/ai_salon`、`DASHSCOPE_API_KEY`、`GITHUB_TOKEN`（可选）
- [x] 1.3 改造 `src/config.py`：通过 `python-dotenv` 加载 `.env`，Config 类读取环境变量，去除硬编码
- [x] 1.4 创建 MySQL 数据库 `ai_salon`（`CREATE DATABASE ai_salon CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`）

## 2. 统一 ORM 模型定义

- [x] 2.1 新建 `src/models.py`，定义 SQLAlchemy 模型：User、Event、EventSignup、EventComment、Project、ProjectComment，字段与 design.md 表结构一致
- [x] 2.2 在 `src/app.py` 中初始化 `db = SQLAlchemy()`，绑定 app，启动时 `db.create_all()` 自动建表
- [x] 2.3 删除 `src/events/models.py` 和 `src/users/models.py` 中的旧 User/Event 类定义，改为从 `src/models.py` 导入

## 3. 密码安全

- [x] 3.1 改造 `UserService.register()`：使用 `generate_password_hash()` 存储密码哈希
- [x] 3.2 改造 `UserService.login()`：使用 `check_password_hash()` 验证密码
- [x] 3.3 移除所有密码明文比较逻辑

## 4. 用户模块 ORM 适配

- [x] 4.1 重写 `src/users/services.py`：所有方法改用 SQLAlchemy session 操作（`db.session.add()`、`db.session.commit()`、`User.query`）
- [x] 4.2 重写 `src/users/routes.py`：适配新 Service 返回值，保持 API 行为不变
- [x] 4.3 验证注册、登录、登出、获取当前用户、个人中心等功能正常

## 5. 活动模块 ORM 适配

- [x] 5.1 重写 `src/events/services.py`：移除内存存储 (`_events`, `_event_signups`, `_event_comments`)，改用 ORM 操作
- [x] 5.2 重写 `src/events/routes.py`：适配新 Service，保持所有 API 行为不变
- [x] 5.3 验证活动 CRUD、报名、评论、标签筛选、权限控制等功能正常

## 6. GitHub 集成模块

- [x] 6.1 新建 `src/integrations/__init__.py`
- [x] 6.2 新建 `src/integrations/github_client.py`：实现 `parse_github_url(url)`、`fetch_file_tree(owner, repo)`、`fetch_file_content(owner, repo, path)`、`select_files(tree)` 方法
- [x] 6.3 实现智能文件选择策略：优先 README → docs → 配置文件 → 核心代码，跳过 node_modules/__pycache__/二进制文件，总内容上限 100KB
- [x] 6.4 支持可选 `GITHUB_TOKEN` 提升 API 速率限制

## 7. AI 分析引擎

- [x] 7.1 新建 `src/projects/__init__.py`
- [x] 7.2 新建 `src/projects/ai_analyzer.py`：封装 DashScope API 调用，base_url 配置为百炼兼容接口，model 为 qwen-plus
- [x] 7.3 实现 5 步分析流水线：Step1(概览+设计思路) → Step2(技术选型) → Step3(架构描述) → Step4(核心代码解读) → Step5(经验教训)
- [x] 7.4 所有 Prompt 指定输出中文（简体中文）
- [x] 7.5 处理部分失败场景：某步失败时保存已完成结果，status 设为 "partial"

## 8. 项目知识库模块

- [x] 8.1 新建 `src/projects/services.py`：实现 ProjectService（CRUD + 分析调度），包括 `create_project`、`get_all_projects`、`get_project_by_id`、`update_project`、`delete_project`、`analyze_project`
- [x] 8.2 新建 `src/projects/routes.py`：实现项目 API 路由（POST/GET/PUT/DELETE `/projects/`，POST `/projects/<id>/analyze`，GET/POST `/projects/<id>/comments`）
- [x] 8.3 实现项目页面路由：`GET /projects/page`（列表页）、`GET /projects/<id>/page`（知识卡片详情页）
- [x] 8.4 在 `src/app.py` 中注册 projects Blueprint，前缀 `/projects`

## 9. 前端模板

- [x] 9.1 新建 `src/templates/projects/list.html`：项目列表页（卡片网格 + 标签筛选 + 创建项目弹窗）
- [x] 9.2 新建 `src/templates/projects/detail.html`：知识卡片详情页（6 大分析板块 + 讨论区 + 分析按钮 + 原始资料链接）
- [x] 9.3 更新 `src/templates/base.html`：导航栏添加"项目知识库"入口（登录后可见）
- [x] 9.4 核心代码解读板块支持代码高亮展示（`<pre><code>` 格式）
- [x] 9.5 分析状态可视化：draft 显示"待分析"、analyzed 显示"已分析"、partial 显示"分析不完整"

## 10. 样式美化

- [x] 10.1 更新 `src/static/styles.css`：新增项目卡片、知识卡片、分析状态标签、代码块等样式，与现有星空主题一致
- [x] 10.2 知识卡片详情页各板块分区清晰、可折叠或 tab 切换

## 11. 测试修复与新增

- [x] 11.1 修复 `tests/test_events.py`：适配新 ORM 接口，使用测试数据库或 mock
- [x] 11.2 修复 `tests/test_users.py`：移除 `update_user`/`delete_user` 等不存在方法的测试，适配新接口
- [x] 11.3 新增 `tests/test_projects.py`：覆盖项目 CRUD、分析触发、评论等核心场景

## 12. 最终集成验证

- [x] 12.1 启动应用，验证数据库自动建表
- [x] 12.2 端到端验证：注册 → 登录 → 创建活动 → 报名 → 评论 → 创建项目 → 触发分析 → 查看知识卡片 → 讨论
- [x] 12.3 验证数据持久化：重启应用后数据仍存在
- [x] 12.4 代码规范检查：无硬编码敏感信息、无循环导入、统一错误处理
