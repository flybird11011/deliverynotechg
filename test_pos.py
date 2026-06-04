import pdfplumber

pdf = pdfplumber.open('ZSD_DELIVERY_NOTE_SF.pdf')
page = pdf.pages[0]
words = page.extract_words()

# 打印标题行附近的所有单词（Y坐标接近456）
print('标题行附近的单词（Y坐标440-480）:')
for word in words:
    if 440 < word['top'] < 480:
        print(f'内容: {word["text"]}, Y坐标: {word["top"]:.2f}, X坐标: {word["x0"]:.2f}')

print('')
print('表格数据行（Y坐标380-440）:')
for word in words:
    if 380 < word['top'] < 440:
        print(f'内容: {word["text"]}, Y坐标: {word["top"]:.2f}, X坐标: {word["x0"]:.2f}')