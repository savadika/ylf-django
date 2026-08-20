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
├── scripts/                  # 环境初始化与启动脚本
├── docker-compose.yml        # 生产环境编排
├── docker-compose-dev.yml    # 开发环境编排
└── .env.example              # 环境变量模板
```


## Rocky Linux 环境初始化

如果部署在 Rocky Linux 10.x 虚拟机，首次执行：

```bash
sudo bash scripts/setup-rocky.sh
```

该脚本会安装 Docker、Docker Compose 插件、Git、curl，并开放 `9530` 和 `8002` 端口。执行完成后退出并重新登录，让 docker 组权限生效。

这套项目使用 Docker Compose 运行，因此主机上只需要 Docker 和 Docker Compose。Django、Vue、MySQL、Redis 都由镜像提供，**不需要在 Rocky Linux 主机上单独安装**。

### Docker 镜像加速（国内服务器建议）

如果服务器访问 Docker Hub 超时，例如运行 bootstrap 时出现：

```text
Image redis:7-alpine Error failed to resolve reference "docker.io/library/redis:7-alpine"
dial tcp ... i/o timeout
```

先执行一键脚本配置国内镜像加速，并预拉取 UniDjango 所需镜像：

```bash
sudo bash scripts/fix-docker-mirror.sh
```

脚本会先探测可用的国内镜像站并按响应速度排序，备份并合并 `/etc/docker/daemon.json`，重启 Docker，然后逐个镜像源拉取 Redis、MySQL、Python、Node、Nginx 等依赖镜像。单个镜像源默认最多等待 300 秒，超时会自动切换到下一个镜像源。

如果拉取大镜像时长时间卡在 `Downloading` 或 `Pulling fs layer`，先按 `Ctrl+C` 结束，再用更短的单源超时重试：

```bash
sudo bash scripts/fix-docker-mirror.sh --timeout 120
```

常用选项：

```text
--no-pull      只配置镜像加速器，不拉取镜像
--force        即使未探测到可用镜像站，也强制写入配置
--timeout 秒   单个镜像源拉取超时，默认 300 秒
```

配置完成后再执行下面的快速开始命令。

## 快速开始

### 1. 开发先启动开发环境

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
