# src/users/

## OVERVIEW
用户管理模块 - 注册/登录/会话/个人资料。

## KEY FILES
| File | Role |
|------|------|
| `models.py` | User类(引用events.models) |
| `routes.py` | REST API |
| `services.py` | UserService内存存储 |

## ROUTES
| Method | Path | Description |
|--------|------|------------|
| POST | `/users/register` | 注册 |
| POST | `/users/login` | 登录 |
| POST | `/users/logout` | 登出 |
| GET | `/users/me` | 当前用户 |
| GET | `/users/users` | 用户列表 |
| GET | `/users/profile` | 个人资料(含报名/发起的活动) |

## CONVENTIONS
- session['user_id']存储登录状态
- 返回用户: `{id, username}`
- 400: 注册失败 | 401: 未登录/密码错误 | 404: 用户不存在

## ANTI-PATTERNS
- 不要在users.models重新定义User（引用events.models）
- service层处理业务逻辑