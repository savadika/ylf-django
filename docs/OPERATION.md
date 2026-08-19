# UniDjango 使用文档

本文档按三个部分说明：

1. 开发阶段怎么用
2. 生产阶段怎么用
3. 内部的对应关系

## 1. 开发阶段怎么用

### 1.0 Rocky Linux 基础环境（仅首次）

如果是 Rocky Linux 10.x 虚拟机，先执行：

```bash
sudo bash scripts/setup-rocky.sh
```

脚本会安装 Docker、Docker Compose 插件、Git、curl，并开放前端和后端端口。

执行完后退出并重新登录，使 docker 组权限生效。

这套项目通过 Docker Compose 运行，主机只需要 Docker 和 Docker Compose。Django、Vue、MySQL、Redis 都运行在容器中，不需要在 Rocky Linux 主机上单独安装。

### 1.1 首次启动开发环境

```bash
./scripts/bootstrap.sh dev --password 'CommonPass123'
```

脚本会：

1. 自动创建 `.env`
2. 生成缺失的 `DJANGO_SECRET_KEY` 和 `JWT_SECRET_KEY`
3. 使用统一密码配置 MySQL、Redis 和 admin
4. 构建并启动开发环境
5. 初始化 `admin` 账号

### 1.2 日常开发

以后启动开发环境：

```bash
make dev
```

或者：

```bash
./scripts/dev.sh
```

开发环境特点：

- 后端使用 `runserver`
- 前端使用 Vue dev server
- 源码挂载，修改代码后自动热重载
- 开启 Swagger 文档

查看后端日志：

```bash
make dev-logs
```

运行测试：

```bash
make test
```

只测试某个模块：

```bash
make test TEST=user
```

### 1.3 停止开发环境

```bash
make dev-down
```

### 1.4 开发完成，切换到生产

```bash
make dev-down
make prod
```

如果同一台机器已经初始化过数据库，切换时只需要执行 `make prod`，不要再次运行 `bootstrap.sh`。

## 2. 生产阶段怎么用

### 2.1 全新生产环境首次启动

以下命令只用于全新生产服务器或空数据库环境，不是开发切生产时使用。

```bash
./scripts/bootstrap.sh prod --password '你的统一密码'
```

脚本会完成：

1. 准备 `.env`
2. 生成缺失的 Django/JWT 密钥
3. 配置统一密码
4. 构建并启动生产环境
5. 初始化 admin 和默认菜单

### 2.2 已经初始化过的生产环境

不要再次运行 `bootstrap.sh`，否则可能覆盖现有 MySQL/Redis 密码并重置管理员。

正常启动或更新生产环境：

```bash
make prod
```

或者：

```bash
./scripts/prod.sh
```

`make prod` 会重新构建镜像并启动容器。

### 2.3 查看日志

```bash
make prod-logs
```

### 2.4 停止生产环境

```bash
make prod-down
```

### 2.5 局域网或公网访问

编辑 `.env`：

```dotenv
DJANGO_ALLOWED_HOSTS=你的服务器IP或域名
SERVER_HOST=你的服务器IP或域名
```

然后重新启动：

```bash
make prod
```

## 3. 内部的对应关系

### 3.1 目录与作用

```text
.
├── UniDjango/                 # Django 后端
├── frontend/                  # Vue 2 管理后台
├── docker/
│   └── mysql/                 # MySQL 镜像构建文件
├── docs/
│   └── OPERATION.md           # 本文档
├── scripts/
│   ├── bootstrap.sh           # 从零一键启动
│   ├── dev.sh                 # 启动开发环境
│   ├── prod.sh                # 构建并启动生产环境
│   └── setup-rocky.sh         # Rocky Linux 基础环境初始化
├── docker-compose.yml         # 生产环境编排
├── docker-compose-dev.yml     # 开发环境编排
├── Makefile                   # 常用命令封装
├── README.md
└── .env.example               # 环境变量模板
```

### 3.2 Compose 文件与运行模式

| 用途 | 编排文件 | 后端 | 前端 |
|------|----------|------|------|
| 开发环境 | `docker-compose-dev.yml` | Django `runserver` | Vue dev server |
| 生产环境 | `docker-compose.yml` | Gunicorn | Nginx 静态托管 |

两个环境共用相同的容器名和端口，因此不能同时运行。

组件由镜像提供：

- MySQL：`mysql:8.0`
- Redis：`redis:7-alpine`
- Django：由 `UniDjango/Dockerfile` 基于 `python:3.12-slim` 构建
- Vue：由 `frontend/Dockerfile` 基于 `node:22-alpine` 构建
- 生产前端：最终运行在 `nginx:stable-alpine`

### 3.3 服务与端口

| 服务 | 默认端口 | 说明 |
|------|----------|------|
| 前端 | `9530` | 浏览器访问入口 |
| 后端 | `8002` | 生产环境仅绑定宿主机回环地址 |
| MySQL | `3309` | 数据持久化在 `db_data/` |
| Redis | `6380` | 数据持久化在 `redis_data/` |

### 3.4 请求链路

生产环境：

```text
浏览器
  └─> http://127.0.0.1:9530
        └─> Nginx 前端
              ├── /                Vue 静态页面
              ├── /prod-api/      反代到 backend:8000
              └── /media/         直接托管上传媒体文件
```

开发环境：

```text
浏览器
  ├─> http://127.0.0.1:9530      Vue dev server
  └─> http://127.0.0.1:8002      Django runserver
```

### 3.5 数据与持久化

| 数据 | 目录或卷 |
|------|----------|
| MySQL 数据 | `db_data/` |
| Redis 数据 | `redis_data/` |
| 上传媒体文件 | `UniDjango/media/` |

这些目录已加入 `.gitignore`，不会提交到 Git。

### 3.6 关键环境变量

| 变量 | 作用 |
|------|------|
| `DJANGO_SECRET_KEY` | Django 签名密钥 |
| `JWT_SECRET_KEY` | JWT 签名密钥 |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码 |
| `REDIS_PASSWORD` | Redis 密码 |
| `DJANGO_ALLOWED_HOSTS` | 允许访问后端的域名/IP |
| `SERVER_HOST` | 前端访问的服务器地址 |
| `SERVER_PROTOCOL` | HTTP 或 HTTPS |

### 3.7 账号与权限关系

```text
sys_user ── sys_user_role ── sys_role ── sys_role_menu ── sys_menu
（用户）      （用户-角色）      （角色）      （角色-菜单）       （菜单，perms 存权限码）
```

菜单类型：

- `M`：目录
- `C`：页面
- `F`：按钮权限点

### 3.8 上传限制

- 只允许 jpg、jpeg、png、gif、webp
- 单文件最大 2MB
- 单次最多 5 个文件

如需调整，修改 `UniDjango/utils/upload.py` 中的 `ALLOWED_EXTENSIONS`。
