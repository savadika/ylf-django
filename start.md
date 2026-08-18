# UniDjango 项目启动指南

## 开发模式（推荐日常使用）

源码挂载，修改即时生效，无需重建镜像：

```bash
cd UniDjango-framework
docker compose -f docker-compose-dev.yml up -d
```

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 Vue | 9530 | webpack-dev-server 热重载 |
| 后端 Django | 8002 | runserver 自动重载 |
| 数据库 MySQL | 3309 | 持久化在 `./db_data` |

访问地址：`http://127.0.0.1:9530`

## 生产模式

Nginx 静态托管 + Gunicorn，需重建镜像：

```bash
cd UniDjango-framework
docker compose up -d
```


| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 Vue | 9530 | Nginx 静态文件 |
| 后端 Django | 8002 | Gunicorn |
| 数据库 MySQL | 3309 | — |

## 常用命令

```bash
# 查看容器状态
docker ps | grep framework

# 查看后端日志
docker logs framework-django --tail 50

# 查看前端日志
docker logs framework-vue --tail 20

# 重启后端（源码已自动重载，一般不需要）
docker compose -f docker-compose-dev.yml restart backend

# 重启前端
docker compose -f docker-compose-dev.yml restart frontend

# 停止所有服务
docker compose -f docker-compose-dev.yml down

# 修改 Dockerfile 或 requirements.txt 后重建
docker compose -f docker-compose-dev.yml build backend
docker compose -f docker-compose-dev.yml up -d backend
```

## 环境变量

所有配置在 `.env` 文件中，修改后执行 `docker compose -f docker-compose-dev.yml up -d` 重新加载。

关键配置项：
- `SERVER_HOST` — 服务器 IP/域名
- `MYSQL_ROOT_PASSWORD` — 数据库密码
