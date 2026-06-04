# Delivery Note Contact Tool

一个基于 Python 的 PDF / Excel 自动处理工具，主要用于：

- 从 PDF 中提取收货公司名称、联系人和运单信息
- 从多个 Excel 源文件中合并客户联系资料
- 将联系人、电话、HU 编号和总重量写回 PDF
- 自动将处理后的 PDF 输出到 `output/`，原始文件移动到 `archive/`

## 项目结构

```text
src/deliverynotechg/
  customer_excel.py
  pdf_contact.py
  pipeline.py
scripts/
  inspect/
    check_file1.py
    check_file2_contact.py
  verify_output.py
tests/
  test_batch.py
  test_batch2.py
  test_batch3.py
  test_font.py
  test_pos.py
app.py
main.py
create_customer_excel.py
find_and_add_contact.py
PDFContactTool.spec
README.md
```

- `src/deliverynotechg/`：核心业务代码
- `scripts/`：一次性检查和验证脚本
- `tests/`：测试和实验脚本
- `app.py`、`main.py`：顶层启动入口

## 技术栈

- Python
- `pandas`
- `pdfplumber`
- `PyPDF2`
- `reportlab`
- `PyInstaller`（用于打包）

## 运行前准备

请确保当前目录下存在这些源数据文件：

- `PT AR001 BP_Customer Master V5 20260226.xlsx`
- `PT International Address - Customer V4 20260225.xlsx`
- `PT AR001_BP_Contact_Person and Relationships V4 20260225.xlsx`
- 需要处理的 PDF 文件

> 程序会在需要时自动生成 `customer_combined.xlsx`。

## 启动方式

### 方式一：运行主入口

```bash
python app.py
```

### 方式二：运行轻量入口

```bash
python main.py
```

两种方式都会触发相同的核心处理流程，只是组织方式略有不同。

### 方式三：运行兼容入口

```bash
python create_customer_excel.py
python find_and_add_contact.py
```

这两个脚本现在是兼容包装，分别调用包内的核心实现。

## 打包方式

使用 PyInstaller：

```bash
pyinstaller PDFContactTool.spec
```

打包产物会生成在 `dist/` 目录下。

## 处理流程

1. 读取多个 Excel 源文件
2. 生成 `customer_combined.xlsx`
3. 扫描当前目录中的 PDF 文件
4. 提取公司名、联系人、运单号、重量等信息
5. 将匹配到的数据写回 PDF
6. 将结果输出到 `output/`
7. 将原始 PDF 移动到 `archive/`

## 注意事项

- 项目依赖固定名称的 Excel 文件，文件名不一致会导致读取失败
- 中文字体文件 `simhei.ttf` 如果不存在，程序会回退到默认字体
- 当前仓库里不包含原始数据文件，使用时需要手动放回本地目录
