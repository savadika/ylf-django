# UniDjango Framework

这是从原项目提取出的架构副本，只保留可复用的框架层，业务策略代码已移除。

## 目录结构

```text
.
├── UniDjango/                # Django 后端
│   ├── UniDjango/            # 项目配置（settings/urls/wsgi/asgi）
│   ├── user/                 # 用户、JWT 登录认证
│   ├── role/                 # 角色
│   ├── menu/                 # 菜单与角色菜单关联
│   ├── department/           # 部门
│   ├── log/                  # 请求日志与异常日志
│   └── utils/                # 通用工具（路由、过滤、分页、上传、媒体 URL）
├── frontend/                 # Vue 2 管理后台脚手架
│   └── src/
│       ├── api/              # 框架模块 API
│       ├── layout/           # 后台布局
│       ├── router/           # 基础路由与动态路由
│       └── store/            # Vuex（用户、权限、设置）
├── docker-compose.yml        # 生产环境编排
├── docker-compose-dev.yml    # 开发环境编排
└── .env.example              # 环境变量模板
```

## 已移除的内容

- 业务策略模块：quant、lof、etfArb、volume、bond、oversold、industry、chinext
- 前端业务页面：`frontend/src/views/bu` 及对应业务 API
- 数据库、Redis 数据、媒体上传文件、备份与回测结果
- `.env`、密钥、内部 IP 与 tushare/numpy 等业务依赖

## 快速开始

```bash
cp .env.example .env
# 按需修改 .env 中的端口、数据库密码、SECRET_KEY、JWT_SECRET_KEY
docker compose up -d
docker compose exec backend python manage.py init_admin --password '你的强密码'
```

访问前端：`http://127.0.0.1:9530`（默认 admin 账号）

更完整的启动、初始化和权限配置说明请查看 [OPERATION.md](OPERATION.md) 和 [STARTUP.md](STARTUP.md)。
