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


安装git
```bash
dnf install git 
```


## 1   Rocky Linux 环境初始化

如果部署在 Rocky Linux 10.x 虚拟机，首次执行：

```bash
sudo bash scripts/setup-rocky.sh
```


### 2  Docker 镜像加速（国内服务器建议）

先执行一键脚本配置国内镜像加速

```bash
sudo bash scripts/switch-docker-mirror.sh
```

然后拉取docker镜像
```bash
docker pull redis:7-alpine
docker pull mysql:8.0
docker pull python:3.12-slim
docker pull node:22-alpine
docker pull node:22
docker pull nginx:stable-alpine
```


查看当前镜像是否全部拉取

```bash
docker images
```


git源码下载
```bash
git clone https://用户名:密码@github.com/用户名/仓库名.git
```

### 3 启动开发环境

```bash
./scripts/bootstrap.sh dev --password 'CommonPass123' --host-ip 172.16.100.55
```



### 4 安装agent

安装node +npm

```bash
dnf install nodejs 
```

npm更换源+ 接入deepseek

```bash
npm config set registry https://registry.npmmirror.com
npm install -g @openai/codex
bash <(curl -fsSL https://cdn.deepseek.com/api-docs/codex-deepseek-setup.sh)
```













### 其他

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
