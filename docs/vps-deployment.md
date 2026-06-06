# VPS 部署方案

这份方案适用于“VPS 上已经有 nginx 在运行”的情况。目标是保留现有 nginx，只为这个项目新增一个独立站点，把 Python 服务放进 Docker Compose 里运行。

## 架构

- nginx：负责域名、HTTPS、上传限制、反向代理
- Docker Compose：负责启动和重启 Python 服务
- Python 容器：负责接收上传、处理 PDF/Excel、生成输出文件
- 宿主机磁盘：负责持久化 `uploads`、`output`、`archive`、SQLite 数据库

## 推荐目录

```text
/opt/dn-change/
  docker-compose.yml
  Dockerfile
  requirements.txt
  .env
  data/
    web_data/
      uploads/
      jobs.db
    output/
    archive/
```

## 环境变量

建议在 `/opt/dn-change/.env` 中配置：

```env
DELIVERYNOTE_WEB_API_TOKEN=
DELIVERYNOTE_WEB_MAX_UPLOAD_SIZE_MB=25
DELIVERYNOTE_WEB_JOB_RETENTION_HOURS=24
DELIVERYNOTE_WEB_CLEANUP_INTERVAL_SECONDS=300
```

如果要启用简单鉴权，就给 `DELIVERYNOTE_WEB_API_TOKEN` 设一个值。

## 启动方式

```bash
docker compose up -d --build
```

后端只监听本机端口 `127.0.0.1:8000`，nginx 再反代到这个地址。

## nginx 配置要点

- `client_max_body_size` 设大一点，避免上传被拦截
- `proxy_read_timeout` 和 `proxy_send_timeout` 设长一点，避免 PDF 处理中途断开
- 维持 `X-Forwarded-*` 头，方便以后排查问题

## 部署步骤

1. 把项目代码放到 VPS，例如 `/opt/dn-change`
2. 准备 `.env`
3. 创建 `data/` 目录
4. 运行 `docker compose up -d --build`
5. 把 nginx 站点配置指向 `127.0.0.1:8000`
6. 重载 nginx
7. 用浏览器访问域名测试上传和下载

## 回滚方式

- 回滚代码：切回上一个 git commit
- 回滚镜像：`docker compose down` 后重新 `up -d --build`
- 回滚数据：因为数据挂载在宿主机，容器重建不会影响历史文件
