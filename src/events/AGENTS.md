# src/events/

## OVERVIEW
事件管理模块 - 创建/查询/删除/签到活动。

## KEY FILES
| File | Role |
|------|------|
| `models.py` | Event, User类定义 |
| `routes.py` | REST API + 页面路由 |
| `services.py` | EventService内存存储 |

## ROUTES
| Method | Path | Description |
|--------|------|------------|
| POST | `/events/` | 创建活动 |
| GET | `/events/` | 列表(支持tag过滤) |
| GET | `/events/<id>` | 详情 |
| PUT | `/events/<id>` | 更新 |
| DELETE | `/events/<id>` | 删除 |
| POST | `/events/<id>/signup` | 签到报名 |
| GET | `/events/<id>/signups` | 获取签到列表 |
| GET | `/events/<id>/comments` | 评论列表 |
| POST | `/events/<id>/comments` | 添加评论 |
| GET | `/events/page` | 活动列表页 |
| GET | `/events/<id>/page` | 活动详情页 |

## CONVENTIONS
- session.get('user_id')获取当前用户
- 返回JSON: `{id, title, description, start_time, end_time, location, tags}`
- 400: 参数不完整 | 401: 未登录 | 403: 无权限 | 404: 不存在

## ANTI-PATTERNS
- 避免修改events.models的User类（users模块依赖）