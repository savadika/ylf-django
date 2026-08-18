# UniDjango 启动文档

本文档说明如何从零启动当前版本的 UniDjango 框架，包括环境准备、配置、迁移、初始管理员创建和常见问题排查。

## 1. 前置条件

建议使用 Docker 和 Docker Compose 启动，当前编排文件已经在容器启动前自动执行数据库迁移。

- Docker
- Docker Compose v2
- 至少 2 GB 可用内存
- 开放端口：前端、后端、MySQL、Redis

## 2. 目录结构

```text
.
├── UniDjango/                 # Django 后端
├── frontend/                  # Vue 2 管理后台
├── docker-compose.yml         # 生产环境编排
├── docker-compose-dev.yml     # 开发环境编排
├── Makefile                   # 一键验证 / 常用命令
├── .env.example               # 环境变量模板
└── STARTUP.md                 # 本文档
```

## 3. 准备环境变量

在项目根目录复制模板：

```bash
cd UniDjango-framework
cp .env.example .env
```

编辑 `.env`，至少修改以下配置：

```dotenv
DJANGO_SECRET_KEY=请填写一段足够长的随机字符串
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
MYSQL_ROOT_PASSWORD=请填写数据库密码
REDIS_PASSWORD=请填写 Redis 密码
SERVER_HOST=127.0.0.1
SERVER_PROTOCOL=http
```

生产环境注意事项：

- `DJANGO_SECRET_KEY` 不能为空，否则后端在 `DEBUG=False` 时会拒绝启动
- `JWT_SECRET_KEY` 同样不能为空（与 `DJANGO_SECRET_KEY` 分离，用于签发登录令牌），生产环境缺失也会拒绝启动
- 不要把 `MYSQL_ROOT_PASSWORD` 和 `REDIS_PASSWORD` 提交到代码仓库
- 如果部署到服务器，请把 `SERVER_HOST` 改成服务器域名或 IP

## 4. 开发环境启动

开发环境使用源码挂载和热重载：

```bash
cd UniDjango-framework
docker compose -f docker-compose-dev.yml up -d
```

查看日志：

```bash
docker compose -f docker-compose-dev.yml logs -f backend
docker compose -f docker-compose-dev.yml logs -f frontend
```

开发环境默认端口：

| 服务 | 地址 |
|------|------|
| 前端 | http://127.0.0.1:9530 |
| 后端 | http://127.0.0.1:8002 |
| MySQL | 127.0.0.1:3309 |
| Redis | 127.0.0.1:6380 |

停止服务：

```bash
docker compose -f docker-compose-dev.yml down
```

## 5. 生产环境启动

生产环境使用 Nginx 托管前端，Gunicorn 运行后端：

```bash
cd UniDjango-framework
docker compose up -d
```

生产环境默认端口：

| 服务 | 地址 |
|------|------|
| 前端 | http://127.0.0.1:9530 |
| 后端 | http://127.0.0.1:8002 |
| MySQL | 127.0.0.1:3309 |
| Redis | 127.0.0.1:6380 |

前端生产构建默认通过 `/prod-api` 反向代理到后端，不需要浏览器直接访问 8002。

查看状态：

```bash
docker compose ps
docker compose logs -f backend
```

## 6. 数据库迁移

当前版本已经在后端容器启动命令中自动执行：

```bash
python manage.py migrate --noinput
```

因此正常使用 Docker Compose 时无需手动迁移。

如果需要在本地直接运行 Django，请先安装依赖并执行：

```bash
cd UniDjango
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## 7. 创建初始管理员和权限

框架当前不包含默认管理员数据。启动完成后，用一条管理命令即可创建管理员、默认部门、超级管理员角色和 `*:*:*` 通配权限：

```bash
docker compose exec backend python manage.py init_admin --password '请填写强密码'
```

或交互式输入密码（更安全，不留在命令行历史）：

```bash
docker compose exec backend python manage.py init_admin
```

该命令是幂等的，会创建/更新：部门「总部」、角色「超级管理员」、admin 用户（绑定该角色）、「全部权限」按钮（`perms=*:*:*`）。执行完成后，用 `admin` 和刚才设置的密码登录前端。

## 8. 权限说明

当前后端已经启用 action 级权限。除了 `*:*:*` 通配权限，各模块使用以下权限码：

| 模块 | 权限码 |
|------|--------|
| 用户 | `system:user:list`、`system:user:query`、`system:user:add`、`system:user:edit`、`system:user:delete` |
| 角色 | `system:role:list`、`system:role:query`、`system:role:add`、`system:role:edit`、`system:role:delete`、`system:role:permission` |
| 菜单 | `system:menu:list`、`system:menu:query`、`system:menu:add`、`system:menu:edit`、`system:menu:delete` |
| 部门 | `system:department:list`、`system:department:query`、`system:department:add`、`system:department:edit`、`system:department:delete` |
| 日志 | `system:log:list`、`system:log:query` |

只有用户角色关联的菜单中带有对应 `perms` 值时，接口才会放行。

## 9. 上传限制

上传接口已改为登录后可访问，并限制：

- 只允许 jpg、jpeg、png、gif、webp
- 单文件最大 2MB
- 单次最多 5 个文件

如需上传其他文件类型，请修改后端 `UniDjango/utils/upload.py` 中的 `ALLOWED_EXTENSIONS`，并评估安全策略。

## 10. 常见问题

### 后端启动失败：DJANGO_SECRET_KEY 环境变量未设置

说明生产模式检测到 `DEBUG=False`，但没有设置 `DJANGO_SECRET_KEY`。请编辑 `.env`，填写强随机密钥后重新启动。

### 访问接口返回 403

通常是当前用户没有对应 action 权限。请检查用户是否已分配角色，以及角色是否已绑定包含对应 `perms` 的菜单。

### 登录失败次数过多

当前限制为同一用户名 + IP 连续失败 5 次后锁定 5 分钟。锁定期间返回 HTTP 429。可以等待 5 分钟后重试，或重启 Redis 清除缓存后重试。

### 上传文件失败

请确认已登录，且文件类型和大小符合限制。上传接口现在要求登录，不能匿名上传。

### MySQL 镜像构建或启动失败

当前 MySQL 使用官方镜像，不再依赖缺失的 `backup.sql`。请确认 `.env` 中的 `MYSQL_ROOT_PASSWORD` 和 `MYSQL_DATABASE` 已设置。

### 前端页面空白或路由 404

确认前端已正确构建，并检查 `docker compose logs frontend`。生产环境前端应通过 `/prod-api` 访问后端，不要直接在浏览器访问 8002 作为 API 地址。

## 11. 推荐启动顺序

```bash
cd UniDjango-framework
cp .env.example .env
# 编辑 .env，设置密钥和密码
docker compose -f docker-compose-dev.yml up -d
docker compose -f docker-compose-dev.yml logs -f backend
```

看到迁移完成并启动开发服务器后，再打开 `http://127.0.0.1:9530`。

### 一键验证

项目根目录提供了 `Makefile`，可一键跑通「系统检查 → 迁移 → 单元测试」：

```bash
make verify
```

`verify` 会先启动服务并等待 MySQL 就绪，再依次执行 `check`、`migrate`、`test`。也支持单独执行：

```bash
make check      # python manage.py check
make migrate    # python manage.py migrate --noinput
make test       # python manage.py test
make test TEST=user   # 只跑 user 模块测试
```

生产编排用 `make COMPOSE_FILE=docker-compose.yml verify`。
