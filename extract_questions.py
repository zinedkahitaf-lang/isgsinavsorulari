"""
İSG Çıkmış Sınav Soruları PDF'den JSON'a Dönüştürücü
=====================================================
Bu script, İş Güvenliği Uzmanlığı sınav sorularını PDF'den çıkarıp
yapılandırılmış JSON formatına dönüştürür.
"""

import fitz  # PyMuPDF
import re
import json
import os

PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "IS-GUVENLIGI-UZMANLIGI-ABC-2014-2024-MAYIS_250511_230604 (1).pdf")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "exam_data.json")

# Sınav bölümleri: (başlık, sınıf, başlangıç_sayfa, cevap_anahtarı_sayfa, soru_sayısı, süre_dk)
EXAM_SECTIONS = [
    ("Mayıs 2014", "C", 0, 6, 60, 90),
    ("Aralık 2014", "C", 7, 14, 60, 90),
    ("Mayıs 2015", "C", 15, 22, 50, 75),
    ("Mayıs 2015", "B", 23, 30, 50, 75),
    ("Mayıs 2015", "A", 31, 38, 50, 75),
    ("Aralık 2015", "C", 39, 46, 50, 75),
    ("Aralık 2015", "B", 47, 54, 50, 75),
    ("Mayıs 2016", "C", 55, 62, 50, 75),
    ("Mayıs 2016", "B", 63, 70, 50, 75),
    ("Aralık 2016", "C", 71, 78, 50, 75),
    ("Aralık 2016", "B", 79, 86, 50, 75),
    ("Nisan 2017", "C", 87, 94, 50, 75),
    ("Nisan 2017", "B", 95, 103, 50, 75),
    ("Aralık 2017", "C", 104, 112, 50, 75),
    ("Aralık 2017", "B", 113, 121, 50, 75),
    ("Mayıs 2018", "C", 122, 130, 50, 75),
    ("Mayıs 2018", "B", 131, 139, 50, 75),
    ("Mayıs 2018", "A", 140, 148, 50, 75),
    ("Aralık 2018", "C", 149, 157, 50, 75),
    ("Aralık 2018", "B", 158, 166, 50, 75),
    ("Aralık 2018", "A", 167, 175, 50, 75),
    ("Mayıs 2019", "C", 176, 183, 50, 75),
    ("Mayıs 2019", "B", 184, 192, 50, 75),
    ("Mayıs 2019", "A", 193, 201, 50, 75),
    ("Aralık 2019", "C", 202, 210, 50, 75),
    ("Aralık 2019", "B", 211, 219, 50, 75),
    ("Aralık 2019", "A", 220, 227, 50, 75),
    ("Kasım 2020", "C", 228, 236, 50, 75),
    ("Kasım 2020", "B", 237, 245, 50, 75),
    ("Kasım 2020", "A", 246, 254, 50, 75),
]


def extract_answer_key(doc, answer_page_idx, question_count):
    """Cevap anahtarı sayfasından doğru cevapları çıkar."""
    page = doc[answer_page_idx]
    text = page.get_text().strip()
    
    # "CEVAP ANAHTARI" başlığını kaldır
    text = text.replace("CEVAP ANAHTARI", "").strip()
    
    # Tüm metin parçalarını al
    tokens = text.split()
    
    answers = {}
    i = 0
    while i < len(tokens) - 1:
        token = tokens[i].strip()
        # Sayı mı kontrol et
        try:
            num = int(token)
            if 1 <= num <= question_count:
                # Sonraki token cevap harfi olmalı
                next_token = tokens[i + 1].strip().upper()
                if next_token in ['A', 'B', 'C', 'D', 'E']:
                    answers[num] = next_token
                    i += 2
                    continue
        except ValueError:
            pass
        i += 1
    
    return answers


def extract_questions_from_pages(doc, start_page, end_page):
    """Belirtilen sayfa aralığından soruları çıkar."""
    # Tüm soru sayfalarının metnini birleştir
    full_text = ""
    for i in range(start_page, end_page + 1):
        page_text = doc[i].get_text()
        full_text += page_text + "\n"
    
    # Başlık bilgilerini kaldır (ilk sayfadaki)
    # "Sınav Süresi:" ve "Soru sayısı:" satırlarını atla
    lines = full_text.split('\n')
    clean_lines = []
    skip_header = True
    for line in lines:
        if skip_header:
            if re.match(r'^\s*1\s*[\-\)]+', line):
                skip_header = False
                clean_lines.append(line)
        else:
            clean_lines.append(line)
    
    full_text = '\n'.join(clean_lines)
    
    # Soruları bul: "1-)" veya "1)" formatında
    # Soru başlangıçlarını tespit et
    question_pattern = r'(\d+)\s*[\-]*\)\s*'
    
    # Tüm soru başlangıç pozisyonlarını bul
    question_starts = []
    for match in re.finditer(question_pattern, full_text):
        q_num = int(match.group(1))
        if q_num >= 1:
            question_starts.append((q_num, match.start(), match.end()))
    
    # Tekrarlayan soru numaralarını temizle - sadece ilk oluşumu al
    seen = set()
    unique_starts = []
    for q_num, start, end in question_starts:
        if q_num not in seen:
            seen.add(q_num)
            unique_starts.append((q_num, start, end))
    
    questions = []
    for idx, (q_num, start, q_text_start) in enumerate(unique_starts):
        # Soru metninin sonu: bir sonraki sorunun başlangıcı
        if idx + 1 < len(unique_starts):
            q_end = unique_starts[idx + 1][1]
        else:
            q_end = len(full_text)
        
        q_block = full_text[q_text_start:q_end].strip()
        
        # Şıkları ayır
        question_data = parse_question_block(q_num, q_block)
        if question_data:
            questions.append(question_data)
    
    return questions


def parse_question_block(q_num, block):
    """Bir soru bloğunu parse eder: soru metni ve şıkları ayırır."""
    
    # Şıkları bul: A), B), C), D), E) formatlarında
    # Şık desenleri
    option_pattern = r'\n\s*([A-E])\s*[\)\-\.]'
    
    # Şık pozisyonlarını bul
    option_matches = list(re.finditer(option_pattern, '\n' + block))
    
    if not option_matches:
        # Alternatif format: A) B) C) D) E) aynı satırda
        option_pattern2 = r'(?:^|\s)([A-E])\s*[\)\-]'
        option_matches = list(re.finditer(option_pattern2, block))
    
    if len(option_matches) < 2:
        # Şık bulunamadı, ham metin olarak döndür
        return {
            "number": q_num,
            "text": block.strip(),
            "options": {},
            "answer": ""
        }
    
    # İlk şıktan öncesi soru metni
    first_option_pos = option_matches[0].start()
    # '\n' eklediğimiz için -1
    adjusted_pos = max(0, first_option_pos - 1)
    question_text = block[:adjusted_pos].strip()
    
    # Şıkları çıkar
    options = {}
    for i, match in enumerate(option_matches):
        letter = match.group(1)
        opt_start = match.end()
        
        if i + 1 < len(option_matches):
            opt_end = option_matches[i + 1].start() - 1  # -1 for the \n we added
        else:
            opt_end = len(block)
        
        # Şık metnini al ve temizle
        opt_text = block[max(0, opt_start-1):opt_end].strip()
        # Başındaki ")" veya "-" karakterini kaldır
        opt_text = re.sub(r'^[\)\-\.\s]+', '', opt_text).strip()
        # Satır sonlarını düzelt
        opt_text = re.sub(r'\s+', ' ', opt_text).strip()
        
        if letter in ['A', 'B', 'C', 'D', 'E']:
            options[letter] = opt_text
    
    # Soru metnini temizle
    question_text = re.sub(r'\s+', ' ', question_text).strip()
    
    return {
        "number": q_num,
        "text": question_text,
        "options": options,
        "answer": ""
    }


def main():
    print("İSG Sınav Soruları PDF'den JSON'a dönüştürülüyor...")
    print(f"PDF: {PDF_PATH}")
    
    if not os.path.exists(PDF_PATH):
        print(f"HATA: PDF dosyası bulunamadı: {PDF_PATH}")
        return
    
    doc = fitz.open(PDF_PATH)
    print(f"Toplam sayfa: {len(doc)}")
    
    all_exams = []
    
    for exam_info in EXAM_SECTIONS:
        period, cls, start_page, answer_page, q_count, duration = exam_info
        
        # Sınav ID oluştur
        period_parts = period.split()
        month = period_parts[0].lower()
        year = period_parts[1]
        exam_id = f"{year}_{month}_{cls.lower()}"
        
        title = f"{period} {cls} Sınıfı İş Güvenliği Uzmanlığı Sınavı"
        
        print(f"\n{'='*60}")
        print(f"İşleniyor: {title}")
        print(f"  Sayfa aralığı: {start_page+1}-{answer_page+1}")
        
        # Cevap anahtarını çıkar
        answers = extract_answer_key(doc, answer_page, q_count)
        print(f"  Cevap anahtarı: {len(answers)} cevap bulundu")
        
        # Soruları çıkar (cevap anahtarı sayfası hariç)
        questions = extract_questions_from_pages(doc, start_page, answer_page - 1)
        print(f"  Sorular: {len(questions)} soru çıkarıldı")
        
        # Cevapları sorulara eşle
        for q in questions:
            q_num = q["number"]
            if q_num in answers:
                q["answer"] = answers[q_num]
        
        # Cevabı olan soru sayısı
        answered = sum(1 for q in questions if q["answer"])
        print(f"  Cevaplı sorular: {answered}")
        
        exam_data = {
            "id": exam_id,
            "period": period,
            "class": cls,
            "title": title,
            "duration_minutes": duration,
            "question_count": q_count,
            "questions": questions
        }
        
        all_exams.append(exam_data)
    
    doc.close()
    
    # JSON olarak kaydet
    output = {"exams": all_exams}
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Tamamlandı! {len(all_exams)} sınav işlendi.")
    print(f"JSON dosyası: {OUTPUT_PATH}")
    
    # Özet istatistikler
    total_q = sum(len(e["questions"]) for e in all_exams)
    total_answered = sum(1 for e in all_exams for q in e["questions"] if q["answer"])
    print(f"Toplam soru: {total_q}")
    print(f"Cevaplı soru: {total_answered}")


if __name__ == "__main__":
    main()
