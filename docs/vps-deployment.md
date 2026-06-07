# VPS 部署方案

这份文档适用于 VPS 上已经有 nginx 在运行的情况。目标是保留现有 nginx，只为这个项目新增一个独立站点，把 Python 服务放进 Docker Compose 里运行。

## 部署结构

- nginx：负责域名、HTTPS、上传限制、反向代理
- Docker Compose：负责启动和重启 Python 服务
- Python 容器：负责接收上传、处理 PDF/Excel、生成输出文件
- 宿主机磁盘：负责持久化 `uploads`、`output`、`archive`、SQLite 数据库

## 推荐目录

建议在 VPS 上使用如下目录：

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

## 一次性准备

下面以 Ubuntu / Debian 系统为例。

### 1. 安装基础软件

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

### 2. 拉取项目代码

```bash
cd /opt
sudo git clone https://github.com/flybird11011/deliverynotechg.git dn-change
cd /opt/dn-change
sudo git checkout feature/web-portal
```

如果你已经把代码放在别的目录，就直接进入那个目录即可。

### 3. 创建数据目录

```bash
sudo mkdir -p /opt/dn-change/data/web_data/uploads
sudo mkdir -p /opt/dn-change/data/output
sudo mkdir -p /opt/dn-change/data/archive
```

## `.env` 怎么填

在 `/opt/dn-change/.env` 中放这些环境变量：

```env
DELIVERYNOTE_WEB_API_TOKEN=
DELIVERYNOTE_WEB_MAX_UPLOAD_SIZE_MB=25
DELIVERYNOTE_WEB_JOB_RETENTION_HOURS=24
DELIVERYNOTE_WEB_CLEANUP_INTERVAL_SECONDS=300
```

说明：
- `DELIVERYNOTE_WEB_API_TOKEN`：可选。留空表示不启用简单鉴权；如果要启用，就填一个足够随机的字符串。
- `DELIVERYNOTE_WEB_MAX_UPLOAD_SIZE_MB`：单个上传文件大小上限，默认 25 MB。
- `DELIVERYNOTE_WEB_JOB_RETENTION_HOURS`：任务和文件保留时间，默认 24 小时。
- `DELIVERYNOTE_WEB_CLEANUP_INTERVAL_SECONDS`：后台清理任务执行间隔，默认 300 秒。

## Docker Compose 怎么启动

在项目根目录执行：

```bash
sudo docker-compose up -d --build
```

查看容器状态：

```bash
sudo docker-compose ps
```

查看日志：

```bash
sudo docker-compose logs -f
```

如果要停止：

```bash
sudo docker-compose down
```

## nginx 站点怎么加

保留你现有的 nginx 主配置，只新增一个站点配置文件，例如：

```bash
sudo nano /etc/nginx/sites-available/dn-change.conf
```

写入下面内容，把 `pdf.example.com` 改成你的真实域名：

```nginx
server {
    listen 80;
    server_name pdf.example.com;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/dn-change.conf /etc/nginx/sites-enabled/dn-change.conf
```

检查 nginx 配置：

```bash
sudo nginx -t
```

重载 nginx：

```bash
sudo systemctl reload nginx
```

如果你已经有 HTTPS 证书，只需要把这个 server block 再补上 `listen 443 ssl;` 和证书配置即可。

## 如何验证是否成功

### 1. 确认后端容器在跑

```bash
sudo docker compose ps
```

你应该能看到容器状态是 `Up`。

### 2. 本机直接访问后端

```bash
curl http://127.0.0.1:9000/
```

如果返回 HTML 页面，说明 FastAPI 已经起来了。

### 3. 通过域名访问

```bash
curl http://pdf.example.com/
```

如果 nginx 已经生效，应该能看到同样的首页内容。

### 4. 测试上传接口

如果没有启用 API key：

```bash
curl -F "excel=@customer_combined.xlsx" -F "pdf=@input.pdf" http://pdf.example.com/api/process
```

如果启用了 API key：

```bash
curl -H "X-API-Key: your-secret-token" -F "excel=@customer_combined.xlsx" -F "pdf=@input.pdf" http://pdf.example.com/api/process
```

接口返回后会得到 `job_id`。

### 5. 查询任务状态

```bash
curl http://pdf.example.com/api/jobs/<job_id>
```

当 `status` 变成 `done`，表示处理完成。

### 6. 下载结果

```bash
curl -o output.pdf http://pdf.example.com/api/jobs/<job_id>/download
```

如果能下载到 PDF 文件，说明整条链路已经跑通。

## 常见排查

### 9000 端口被占用

```bash
sudo ss -ltnp | grep :9000
```

如果有别的进程占用 9000，就先停掉那个进程，或者把 `docker-compose.yml` 里的宿主机端口换成别的端口。

### nginx 反代失败

检查：
- `proxy_pass` 是否指向 `127.0.0.1:9000`
- `nginx -t` 是否通过
- 容器是否真的在运行

### 上传失败

检查：
- nginx 的 `client_max_body_size`
- `.env` 中的 `DELIVERYNOTE_WEB_MAX_UPLOAD_SIZE_MB`
- 文件后缀是否为 `.pdf` 和 `.xlsx`

### 处理很慢或中断

检查：
- nginx 的 `proxy_read_timeout`
- 容器日志里是否有异常
- 输入 PDF 和 Excel 是否完整

## 回滚方式

- 回滚代码：切回上一个 git commit
- 回滚镜像：`sudo docker compose down` 后重新 `up -d --build`
- 回滚数据：因为数据挂载在宿主机，容器重建不会影响历史文件
