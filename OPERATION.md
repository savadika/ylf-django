# UniDjango 操作文档

本文档说明如何在克隆代码后把系统跑起来，以及日常如何使用、配置权限、排查常见问题。

## 目录

1. [系统简介](#1-系统简介)
2. [快速开始（从零到登录）](#2-快速开始从零到登录)
3. [初始化命令 init_admin](#3-初始化命令-init_admin)
4. [权限模型与配置](#4-权限模型与配置)
5. [日常操作](#5-日常操作)
6. [常用命令](#6-常用命令)
7. [常见问题](#7-常见问题)

---

## 1. 系统简介

| 项 | 说明 |
|----|------|
| 技术栈 | Django 5 + DRF + Vue 2 + MySQL 8 + Redis 7 |
| 部署方式 | Docker Compose（前端 Nginx / 后端 Gunicorn） |
| 认证 | JWT（`/user/gen_token` 登录换取 token） |
| 权限 | RBAC，精确到按钮级（用户 → 角色 → 菜单 → 权限码） |
| 业务模块 | 用户、角色、菜单、部门、日志 |

端口（默认，见 `.env`）：

| 服务 | 地址 |
|------|------|
| 前端管理后台 | http://127.0.0.1:9530 |
| 后端 API | http://127.0.0.1:8002（仅绑定宿主机 127.0.0.1，不对外暴露） |
| MySQL | 127.0.0.1:3309 |
| Redis | 127.0.0.1:6380 |

> Swagger / ReDoc 接口文档只在 `DEBUG=True`（开发模式）开启；生产环境已关闭，不提供 `/swagger/`、`/redoc/`。

---

## 2. 快速开始（从零到登录）

> 前置条件：已安装 Docker 和 Docker Compose v2。

```bash
# 1. 进入项目目录
cd UniDjango-framework

# 2. 准备环境变量
cp .env.example .env
#    编辑 .env，至少填写：
#      DJANGO_SECRET_KEY   一段足够长的随机字符串
#      JWT_SECRET_KEY      与上面不同的随机字符串（JWT 专用）
#      MYSQL_ROOT_PASSWORD 数据库密码
#      REDIS_PASSWORD      Redis 密码
#      DJANGO_ALLOWED_HOSTS 加上你的服务器 IP/域名（如 172.16.100.54）

# 3. 启动（首次会自动执行 migrate 建表）
docker compose up -d

# 4. 初始化管理员（见第 3 节）
docker compose exec backend python manage.py init_admin --password '你的强密码'

# 5. 验证
make verify    # 依次执行 check → migrate → test
```

打开 `http://127.0.0.1:9530`，用 `admin` 和刚才设置的密码登录。

> **注意**：数据库数据（`db_data/`）不随代码提交，克隆下来是空库，所以必须执行第 4 步初始化管理员；否则系统里没有任何账号，无法登录。

---

## 3. 初始化命令 init_admin

一条命令完成新系统的初始引导：默认部门、超级管理员角色、admin 用户、`*:*:*` 通配权限。命令是幂等的（重复执行安全）。

```bash
# 直接指定密码
docker compose exec backend python manage.py init_admin --password 'StrongPass123'

# 交互式输入密码（更安全，不留在命令行历史里）
docker compose exec backend python manage.py init_admin

# 指定用户名和邮箱
docker compose exec backend python manage.py init_admin \
  --username admin --email admin@example.com --password 'StrongPass123'
```

参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--username` | admin | 管理员用户名 |
| `--password` | — | 密码，至少 8 位；不传则交互输入 |
| `--email` | admin@example.com | 管理员邮箱 |

执行成功后会创建/更新：部门「总部」、角色「超级管理员」、admin 用户（绑定该角色）、「全部权限」按钮（`perms=*:*:*`），从而让 admin 拥有全部接口权限。

---

## 4. 权限模型与配置

### 4.1 权限链路

```
sys_user ── sys_user_role ── sys_role ── sys_role_menu ── sys_menu
（用户）      （用户-角色）      （角色）      （角色-菜单）       （菜单，perms 存权限码）
```

- 侧边栏菜单、接口访问权限**都由数据库里的菜单 + 绑定关系动态生成**，改数据库即可，无需改代码。
- `sys_menu.menu_type` 区分类型：`M` 目录、`C` 页面、`F` 按钮（权限点）。

### 4.2 权限码约定

权限码对应后端接口动作（DRF action）：

| 按钮名 | 权限码 | 控制的内容 |
|--------|--------|-----------|
| 列表 | `system:xxx:list` | 能不能打开列表页（搜索 + 表格是同一接口） |
| 查看详情 | `system:xxx:query` | 能不能看单条记录详情 |
| 新增 | `system:xxx:add` | 新增 |
| 编辑 | `system:xxx:edit` | 编辑 |
| 删除 | `system:xxx:delete` | 删除 |

通配权限 `*:*:*` 直接放行所有接口（admin 默认拥有）。

### 4.3 给角色配置权限

在「角色管理」页，编辑某个角色的权限（勾选菜单树）：

1. 勾选**页面菜单**（`C` 类型）+ 该页面的一组**按钮**（`F` 类型）一起勾，才能完整使用该页面。
2. 只勾「列表」= 能看列表；只勾「查看详情」= 只能看单条；「列表」和「查看详情」互相独立。
3. 常见「只读」配置：勾 `列表 + 查看详情`，不勾 `新增/编辑/删除`。

> ⚠️ 若只勾了页面菜单、漏了「列表」按钮，会出现「菜单能看到、接口却 403」——因为列表页数据接口要求 `system:xxx:list`。

---

## 5. 日常操作

### 5.1 登录与退出

- 前端登录页输入用户名密码，登录后进入首页。
- 点击右上角退出登录。

### 5.2 各模块

| 模块 | 说明 |
|------|------|
| 用户管理 | 用户的增删改查、分配部门与角色、设密码 |
| 角色管理 | 角色的增删改查、分配菜单权限（授权） |
| 菜单管理 | 菜单树维护（目录/页面/按钮、路径、组件、权限码） |
| 部门管理 | 部门增删改查 |
| 日志管理 | 查看请求日志和异常日志（INFO/ERROR） |

> 新增菜单/按钮后，需要到「角色管理」里把新菜单绑定给对应角色，用户刷新后侧边栏和接口权限才会生效。

---

## 6. 常用命令

项目根目录提供了 `Makefile`：

```bash
make verify          # 一键验证：up → 等 MySQL → check → migrate → test
make check           # Django 系统检查
make migrate         # 执行数据库迁移
make test            # 跑测试（可加 TEST=user 指定模块）
make up / make down  # 启动 / 停止
make logs            # 看后端日志
make shell           # 进 Django shell
```

其他常用：

```bash
# 初始化管理员
docker compose exec backend python manage.py init_admin --password 'xxx'

# 创建迁移（改了模型后）
docker compose exec backend python manage.py makemigrations

# 查看容器状态
docker compose ps

# 查看后端/前端日志
docker compose logs -f backend
docker compose logs -f frontend
```

---

## 7. 常见问题

### 登录返回 400

通常是 `DJANGO_ALLOWED_HOSTS` 没包含你访问用的 IP/域名。把服务器 IP 加到 `.env` 的 `DJANGO_ALLOWED_HOSTS`，再 `docker compose up -d backend` 重启后端。

### 访问接口返回 403

当前用户没有对应 action 权限。检查：用户是否分配了角色、角色是否绑定了包含对应 `perms` 的按钮菜单。参照 [4.3](#43-给角色配置权限)。

### 登录失败次数过多

同一「用户名 + IP」连续失败 5 次后锁定 5 分钟，返回 429。等 5 分钟或重启 Redis 清缓存。

### 列表时间显示成 `2026-08-13T14:46:04...`

正常情况下前端已用 `parseTime` 格式化成 `年-月-日 时:分:秒`。若仍显示原始格式，硬刷新浏览器（Ctrl+Shift+R）清缓存。

### 状态显示成数字 1/0

正常情况下「状态」列显示「正常/禁用」。若显示数字，硬刷新清缓存即可。

### 前端页面空白或 404

确认前端已构建，检查 `docker compose logs frontend`。生产环境应通过前端（9530）访问，前端会把 `/prod-api` 反代到后端，不要直接在浏览器访问 8002 作为 API 地址。

### 改了代码不生效

- 生产模式（`docker-compose.yml`）代码是打进镜像的，需 `docker compose build` 后 `up -d` 重建。
- 开发模式（`docker-compose-dev.yml`）源码挂载 + 热重载，一般自动生效。

---

## 附：克隆后启动清单

```bash
cd UniDjango-framework
cp .env.example .env          # 填密钥/密码/服务器 IP
docker compose up -d          # 启动 + 自动建表
docker compose exec backend python manage.py init_admin --password 'xxx'   # 初始化 admin
make verify                   # 自检
```

打开 `http://127.0.0.1:9530`，用 `admin` 登录。
