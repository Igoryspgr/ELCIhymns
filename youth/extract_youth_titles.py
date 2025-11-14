from pdfminer.high_level import extract_text
import re

pdf_path = r"C:\Users\LENOVO\Downloads\youth\8-211_ocred.pdf"
output_path = "songs_youth.txt"

# Извлекаем текст с помощью pdfminer
text = extract_text(pdf_path)

# Регулярка для строк с номером и названием гимна
pattern = re.compile(r"^\s*(\d{1,4})\s+([А-ЯЁA-Z][^\n\r]{2,100})$", re.MULTILINE)

matches = pattern.findall(text)

results = [f"youth;{num};{title.strip()}" for num, title in matches]
unique_results = sorted(set(results), key=lambda x: int(x.split(";")[1]))

with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(unique_results))

print("✅ Готово! Проверь файл:", output_path)
