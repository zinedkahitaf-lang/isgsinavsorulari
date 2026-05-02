import json
import os

JSON_PATH = r'C:\Users\zined\.gemini\antigravity\scratch\isg-sinav-app\exam_data.json'

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Fix 2014_mayis_c Q1 specifically
for exam in data['exams']:
    if exam['id'] == '2014_mayis_c':
        for q in exam['questions']:
            if q['number'] == 1:
                q['text'] = 'Aşağıdakilerden hangileri sapsız kullanılmaz?\nI-Keski II-Eğe III-Törpü'
                q['options'] = {'A': 'I', 'B': 'II', 'C': 'III', 'D': 'I-II', 'E': 'I-II-III'}
                print("Fixed Q1 of 2014_mayis_c")

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done.")
