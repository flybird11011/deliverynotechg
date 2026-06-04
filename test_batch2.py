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
        break

# 查找标题行正下方的数字（批次号）
batch_number_positions = []
if header_y:
    print(f'\n查找范围: Y坐标 {header_y-25:.2f} 到 {header_y-5:.2f}')
    for word in words:
        if header_y - 25 < word['top'] < header_y - 5:
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

print('\n找到的批次号:')
for i, pos in enumerate(batch_number_positions):
    print(f'{i+1}. 内容: {pos["text"]}, 位置: x={pos["x"]:.2f}, y={pos["y"]:.2f}, 字体大小: {pos["font_size"]}')