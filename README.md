# Delivery Note Contact Tool

一个基于 Python 的 PDF / Excel 自动处理工具，主要用于：

- 从 PDF 中提取收货公司名称、联系人和运单信息
- 从多个 Excel 源文件中合并客户联系资料
- 将联系人、电话、HU 编号和总重量写回 PDF
- 自动将处理后的 PDF 输出到 `output/`，并将原始文件移动到 `archive/`

## 项目结构

```text
src/deliverynotechg/
  customer_excel.py
  pdf_contact.py
  pipeline.py
  job_runner.py
  web/
    config.py
    server.py
    store.py
scripts/
  verify_output.py
tests/
app.py
main.py
create_customer_excel.py
find_and_add_contact.py
PDFContactTool.spec
README.md
```

- `src/deliverynotechg/`: 核心业务代码
- `src/deliverynotechg/web/`: Web API 与任务存储
- `tests/`: 自动化测试
- `app.py`: PyInstaller 打包入口
- `main.py`: 本地开发入口

## 依赖

- Python 3.10+
- `fastapi`
- `uvicorn`
- `pandas`
- `pdfplumber`
- `PyPDF2`
- `reportlab`
- `openpyxl`
- `python-multipart`

## 本地运行

### 处理当前目录下的 PDF

```bash
python main.py
```

### 打包入口

```bash
python app.py
```

两个入口会调用相同的核心流程。`main.py` 更适合调试，`app.py` 更适合打包后运行。

## Web 服务

项目内置了一个简单的 Web API，可用于上传 PDF 和 Excel 文件并异步处理。

启动方式：

```bash
uvicorn src.deliverynotechg.web.server:app --host 0.0.0.0 --port 8000
```

主要接口：

- `GET /`
- `POST /api/process`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/download`

如果设置了 `DELIVERYNOTE_WEB_API_TOKEN`，请求需要带 `X-API-Key`。

## 输出目录

- `output/`: 处理后的 PDF
- `archive/`: 原始 PDF 归档
- `web_data/`: Web 任务数据库和上传文件

## 打包

使用 PyInstaller：

```bash
pyinstaller PDFContactTool.spec
```

打包产物会生成在 `dist/` 目录下。

## VPS 部署

如果你的 VPS 上已经有 nginx，推荐保留 nginx 作为入口层，只把 Python 服务放进 Docker Compose 里运行。详细方案见 [`docs/vps-deployment.md`](docs/vps-deployment.md)。

简要结构如下：

- nginx 反代到 `127.0.0.1:8000`
- Docker 容器运行 FastAPI 后端
- `data/` 目录挂载到宿主机，保存上传、输出和数据库
- 通过 `.env` 配置上传大小、保留时间和 API key

## 处理流程

1. 读取客户 Excel 并生成合并表
2. 扫描当前目录或 Web 上传的 PDF
3. 提取公司名、联系人、HU 信息和重量信息
4. 从 Excel 中匹配联系人与手机号
5. 将结果写回 PDF
6. 输出到 `output/`
7. 原始 PDF 归档到 `archive/`

## 注意事项

- 项目依赖固定命名的 Excel 文件，缺少文件会导致读取失败
- 如果系统字体不可用，PDF 字体效果可能与源文件略有差异
- Web 模式下的历史任务和上传文件会按配置自动清理
