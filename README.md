# Delivery Note Contact Tool

涓€涓熀浜?Python 鐨?PDF / Excel 鑷姩澶勭悊宸ュ叿锛屼富瑕佺敤浜庯細

- 浠?PDF 涓彁鍙栨敹璐у叕鍙稿悕绉般€佽仈绯讳汉鍜岃繍鍗曚俊鎭?- 浠庡涓?Excel 婧愭枃浠朵腑鍚堝苟瀹㈡埛鑱旂郴璧勬枡
- 灏嗚仈绯讳汉銆佺數璇濄€丠U 缂栧彿鍜屾€婚噸閲忓啓鍥?PDF
- 鑷姩灏嗗鐞嗗悗鐨?PDF 杈撳嚭鍒?`output/`锛屽師濮嬫枃浠剁Щ鍔ㄥ埌 `archive/`

## 椤圭洰缁撴瀯

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

- `src/deliverynotechg/`锛氭牳蹇冧笟鍔′唬鐮?- `scripts/`锛氫竴娆℃€ф鏌ュ拰楠岃瘉鑴氭湰
- `tests/`锛氭祴璇曞拰瀹為獙鑴氭湰
- `app.py`: packaged entry point for PyInstaller.
- `main.py`: local development / direct run entry point.

- Python
- `pandas`
- `pdfplumber`
- `PyPDF2`
- `reportlab`
- `PyInstaller`锛堢敤浜庢墦鍖咃級

## 杩愯鍓嶅噯澶?
璇风‘淇濆綋鍓嶇洰褰曚笅瀛樺湪杩欎簺婧愭暟鎹枃浠讹細

- `PT AR001 BP_Customer Master V5 20260226.xlsx`
- `PT International Address - Customer V4 20260225.xlsx`
- `PT AR001_BP_Contact_Person and Relationships V4 20260225.xlsx`
- 闇€瑕佸鐞嗙殑 PDF 鏂囦欢

> 绋嬪簭浼氬湪闇€瑕佹椂鑷姩鐢熸垚 `customer_combined.xlsx`銆?
## 鍚姩鏂瑰紡

### 方法一：本地入口

```bash
python main.py
```

### 方法二：打包入口

```bash
python app.py
```

两个入口都会触发相同的核心流程，只是 `main.py` 更适合开发调试，`app.py` 更适合打包后的运行。

### 方法三：运行兼容入口

```bash
python create_customer_excel.py
python find_and_add_contact.py
```

杩欎袱涓剼鏈幇鍦ㄦ槸鍏煎鍖呰锛屽垎鍒皟鐢ㄥ寘鍐呯殑鏍稿績瀹炵幇銆?
## 鎵撳寘鏂瑰紡

浣跨敤 PyInstaller锛?
```bash
pyinstaller PDFContactTool.spec
```

鎵撳寘浜х墿浼氱敓鎴愬湪 `dist/` 鐩綍涓嬨€?

## VPS 部署

如果 VPS 上已经有 nginx，推荐保留 nginx 作为入口层，只把 Python 服务放进 Docker Compose 里运行。详细方案见 [`docs/vps-deployment.md`](docs/vps-deployment.md)。

简要结构如下：

- nginx 反代到 `127.0.0.1:8000`
- Docker 容器运行 FastAPI 后端
- `data/` 目录挂载到宿主机，保存上传、输出和数据库
- 通过 `.env` 配置上传大小、保留时间和 API key
## 澶勭悊娴佺▼

1. 璇诲彇澶氫釜 Excel 婧愭枃浠?2. 鐢熸垚 `customer_combined.xlsx`
3. 鎵弿褰撳墠鐩綍涓殑 PDF 鏂囦欢
4. 鎻愬彇鍏徃鍚嶃€佽仈绯讳汉銆佽繍鍗曞彿銆侀噸閲忕瓑淇℃伅
5. 灏嗗尮閰嶅埌鐨勬暟鎹啓鍥?PDF
6. 灏嗙粨鏋滆緭鍑哄埌 `output/`
7. 灏嗗師濮?PDF 绉诲姩鍒?`archive/`

## 娉ㄦ剰浜嬮」

- 椤圭洰渚濊禆鍥哄畾鍚嶇О鐨?Excel 鏂囦欢锛屾枃浠跺悕涓嶄竴鑷翠細瀵艰嚧璇诲彇澶辫触
- 涓枃瀛椾綋鏂囦欢 `simhei.ttf` 濡傛灉涓嶅瓨鍦紝绋嬪簭浼氬洖閫€鍒伴粯璁ゅ瓧浣?- 褰撳墠浠撳簱閲屼笉鍖呭惈鍘熷鏁版嵁鏂囦欢锛屼娇鐢ㄦ椂闇€瑕佹墜鍔ㄦ斁鍥炴湰鍦扮洰褰?
