# 活动平台项目

该项目是一个基于 Flask 的活动平台，旨在提供用户管理和事件管理功能。用户可以注册、登录并查看活动，而管理员可以创建、查看和管理活动。

## 项目结构

```
event-platform
├── src
│   ├── app.py                # 应用程序的入口点
│   ├── config.py             # 应用程序配置
│   ├── requirements.txt       # 项目依赖库
│   ├── events                 # 事件相关功能
│   │   ├── __init__.py
│   │   ├── models.py          # 事件数据库模型
│   │   ├── routes.py          # 事件路由
│   │   └── services.py        # 事件业务逻辑
│   ├── users                  # 用户相关功能
│   │   ├── __init__.py
│   │   ├── models.py          # 用户数据库模型
│   │   ├── routes.py          # 用户路由
│   │   └── services.py        # 用户业务逻辑
│   ├── analytics              # 数据分析功能
│   │   ├── __init__.py
│   │   ├── data_loader.py      # 数据加载
│   │   ├── analysis.py         # 数据分析
│   │   └── visualization.py     # 数据可视化
│   ├── templates              # HTML 模板
│   │   ├── base.html          # 基础模板
│   │   ├── events             # 事件相关模板
│   │   │   ├── list.html
│   │   │   └── detail.html
│   │   └── users              # 用户相关模板
│   │       ├── login.html
│   │       └── profile.html
│   └── types                  # 类型定义
│       └── index.py
├── tests                      # 测试
│   ├── __init__.py
│   ├── test_events.py         # 事件单元测试
│   └── test_users.py          # 用户单元测试
├── README.md                  # 项目文档
└── pyproject.toml             # 项目配置文件
```

## 安装依赖

在项目根目录下运行以下命令以安装所需的依赖：

```
pip install -r src/requirements.txt
```

## 启动应用

在 `src` 目录下运行以下命令以启动 Flask 应用：

```
python app.py
```

## 贡献

欢迎任何形式的贡献！请提交问题或拉取请求以帮助改进项目。