# PROJECT KNOWLEDGE BASE

**Generated:** 2026-04-13
**Stack:** Flask + SQLAlchemy + Pandas

## OVERVIEW
Flask活动平台，用户注册/登录、事件管理、数据分析功能。内存存储 + SQLite可选。

## STRUCTURE
```
src/
├── app.py           # Flask入口，create_app()
├── config.py        # Config类
├── events/          # 事件模块
│   ├── models.py    # Event类(in-memory)
│   ├── routes.py    # 事件API + 页面路由
│   └── services.py  # EventService(in-memory存储)
├── users/           # 用户模块
│   ├── models.py    # User类(引用events.models)
│   ├── routes.py    # 用户API
│   └── services.py  # UserService
└── analytics/       # 数据分析(Pandas)
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| 添加新API | `src/events/routes.py`, `src/users/routes.py` |
| 用户认证 | `src/users/services.py` |
| 事件管理 | `src/events/services.py` |
| 数据分析 | `src/analytics/` |
| 配置 | `src/config.py`, `pyproject.toml` |

## CONVENTIONS
- Blueprint别名：`event_blueprint = events_bp`, `user_blueprint = users_bp`
- 路由前缀：`/events`, `/users`
- 页面路由：`/events/page`, `/events/<id>/page`
- API返回：JSON，状态码遵循REST
- 内存存储：EventService/UserService类维护内存dict

## ANTI-PATTERNS
- 注释使用中文（项目既定风格）
- 避免修改`src/events/models.py`的User类（被users模块引用）
- 测试文件在`tests/`目录

## COMMANDS
```bash
# 启动
python src/app.py

# 运行测试
pytest tests/

# 开发(vscode)
Ctrl+Shift+P → Tasks: run-app
```

## NOTES
- secret_key硬编码，生产环境需修改
- 内存存储，重启后数据丢失
- analytics模块为占位实现
