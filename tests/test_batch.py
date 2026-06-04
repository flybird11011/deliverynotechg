import pdfplumber

pdf = pdfplumber.open('ZSD_DELIVERY_NOTE_SF.pdf')
page = pdf.pages[0]
words = page.extract_words()
text = page.extract_text()
lines = text.split('\n')

# 查找批次号标题行
for i, line in enumerate(lines):
    if '批次号' in line or 'Batch' in line:
        print(f'找到批次号标题行: 第{i}行 - {line}')

# 获取标题行的Y坐标
header_y = None
for word in words:
    if '批次号' in word.get('text', ''):
        header_y = word['top']
        print(f'标题行Y坐标: {header_y}')
        break

# 在标题行下方查找数字
batch_number_positions = []
if header_y:
    for word in words:
        if word['top'] < header_y - 5:
            text_word = word.get('text', '')
            if text_word.isdigit() and len(text_word) >= 6:
                already_added = False
                for pos in batch_number_positions:
                    if abs(pos['y'] - word['top']) < 5:
                        already_added = True
                        break
                if not already_added:
                    batch_number_positions.append({
                        'text': text_word,
                        'x': word['x0'],
                        'y': word['top'],
                        'font_size': word.get('size', 10)
                    })

print('')
print('找到的批次号:')
for i, pos in enumerate(batch_number_positions):
    print(f'{i+1}. 内容: {pos["text"]}, 位置: x={pos["x"]:.2f}, y={pos["y"]:.2f}, 字体大小: {pos["font_size"]}')