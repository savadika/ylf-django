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
├── docker/
│   └── mysql/                # MySQL 镜像构建文件
├── docs/                     # 使用文档
├── scripts/                  # 开发/生产环境启动脚本
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

### 1. 先启动开发环境

```bash
./scripts/bootstrap.sh dev --password 'CommonPass123'
```

脚本会自动准备 `.env`、生成缺失的 Django/JWT 密钥、构建并启动开发环境、初始化 `admin` 账号。MySQL、Redis 和 `admin` 使用同一个密码。

开发环境使用源码挂载和热重载，适合日常开发。

### 2. 开发完成后切换到生产环境

同一台机器已经初始化过数据库时，只需要执行：

```bash
make dev-down
make prod
```

不要再次运行 `bootstrap.sh`，避免覆盖现有密码并重置管理员。

### 3. 全新生产服务器首次启动

```bash
./scripts/bootstrap.sh prod --password 'MyStrongPass123'
```

这个命令只用于全新生产服务器或空数据库环境。

常用 Makefile 命令：

```bash
make dev
make prod
make dev-down
make prod-down
```

更完整的说明请查看 [docs/OPERATION.md](docs/OPERATION.md)。
