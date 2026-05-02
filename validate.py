import json
import fitz

JSON_PATH = r'C:\Users\zined\.gemini\antigravity\scratch\isg-sinav-app\exam_data.json'
PDF_PATH = r'C:\Users\zined\.gemini\antigravity\scratch\IS-GUVENLIGI-UZMANLIGI-ABC-2014-2024-MAYIS_250511_230604 (1).pdf'

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

doc = fitz.open(PDF_PATH)

# Test exams: 1st, 15th, 30th
test_indices = [0, 14, 29]
answer_pages = [6, 121, 254] # Based on the extract script

for i, idx in enumerate(test_indices):
    exam = data['exams'][idx]
    print(f'=== KONTROL: {exam["title"]} ===')
    
    # Get answers from JSON
    json_answers = {}
    for q in exam['questions']:
        if q.get('answer'):
            json_answers[q['number']] = q['answer']
            
    print(f'JSON\'da {len(json_answers)} cevap var.')
    
    keys = sorted(list(json_answers.keys()))
    if keys:
        first_5 = {k: json_answers[k] for k in keys[:5]}
        last_5 = {k: json_answers[k] for k in keys[-5:]}
        print(f'JSON İlk 5: {first_5}')
        print(f'JSON Son 5: {last_5}')
        
    print('--- PDF\'den Ham Metin ---')
    page_text = doc[answer_pages[i]].get_text().strip()
    # Print first 200 chars and last 200 chars to compare
    print('BAŞI:', page_text[:200].replace('\n', ' '))
    print('SONU:', page_text[-200:].replace('\n', ' '))
    print('\n')

doc.close()
