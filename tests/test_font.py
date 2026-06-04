import pdfplumber

pdf = pdfplumber.open('ZSD_DELIVERY_NOTE_SF.pdf')
page = pdf.pages[0]
words = page.extract_words()

# 查找批次号标题
header_y = None
for word in words:
    if '批次号' in word.get('text', ''):
        header_y = word['top']
        print(f'批次号标题Y坐标: {header_y}')
        print(f'标题字体信息: {word}')
        break

# 查找标题行正下方的数字（批次号）
print(f'\n查找范围: Y坐标 {header_y+5:.2f} 到 {header_y+30:.2f}')
for word in words:
    if header_y + 5 < word['top'] < header_y + 30:
        text_word = word.get('text', '')
        if text_word.isdigit() and len(text_word) >= 6:
            print(f'找到数字: {text_word}')
            print(f'完整信息: {word}')
            print(f'  - 字体名称: {word.get("fontname", "未知")}')
            print(f'  - 字体大小: {word.get("size", "未知")}')
            print(f'  - 位置: x={word["x0"]:.2f}, y={word["top"]:.2f}')
            print()

pdf.close()