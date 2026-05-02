import streamlit as st
import json
import time
import os
from openai import OpenAI

# Set page config
st.set_page_config(
    page_title="İSG Sınav Simülatörü",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
st.markdown("""
<style>
    .stProgress .st-bo {
        background-color: #4CAF50;
    }
    .question-box {
        padding: 20px;
        border-radius: 10px;
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 20px;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    .correct-answer {
        color: #4CAF50;
        font-weight: bold;
    }
    .wrong-answer {
        color: #F44336;
        font-weight: bold;
    }
    .missing-answer {
        color: #FFC107;
        font-weight: bold;
    }
    .explanation-box {
        padding: 15px;
        border-left: 5px solid #2196F3;
        background-color: rgba(33, 150, 243, 0.1);
        border-radius: 0 5px 5px 0;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Define path to JSON
DATA_PATH = os.path.join(os.path.dirname(__file__), "exam_data.json")

@st.cache_data
def load_exam_data():
    if not os.path.exists(DATA_PATH):
        return None
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

data = load_exam_data()

if not data:
    st.error("Sınav verisi bulunamadı. Lütfen önce 'extract_questions.py' scriptini çalıştırın.")
    st.stop()

# Initialize session state
if 'current_exam_id' not in st.session_state:
    st.session_state.current_exam_id = None
if 'exam_started' not in st.session_state:
    st.session_state.exam_started = False
if 'exam_finished' not in st.session_state:
    st.session_state.exam_finished = False
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'current_q_index' not in st.session_state:
    st.session_state.current_q_index = 0
if 'learning_mode' not in st.session_state:
    st.session_state.learning_mode = False
if 'explanations' not in st.session_state:
    st.session_state.explanations = {}

# Build exam options for sidebar
exam_options = {}
periods = []
classes = set()

for exam in data.get("exams", []):
    exam_id = exam.get("id")
    period = exam.get("period")
    cls = exam.get("class")
    
    if period not in periods:
        periods.append(period)
    classes.add(cls)
    
    if period not in exam_options:
        exam_options[period] = {}
    exam_options[period][cls] = exam

def start_exam(exam_id, is_learning_mode=False):
    st.session_state.current_exam_id = exam_id
    st.session_state.exam_started = True
    st.session_state.exam_finished = False
    st.session_state.user_answers = {}
    st.session_state.explanations = {}
    st.session_state.start_time = time.time()
    st.session_state.current_q_index = 0
    st.session_state.learning_mode = is_learning_mode

def finish_exam():
    st.session_state.exam_finished = True

def get_current_exam():
    if not st.session_state.current_exam_id:
        return None
    for exam in data.get("exams", []):
        if exam.get("id") == st.session_state.current_exam_id:
            return exam
    return None

def generate_explanation(api_key, question, user_ans, correct_ans):
    """Call OpenAI API to generate an explanation"""
    try:
        client = OpenAI(api_key=api_key)
        
        # Prepare context
        q_text = question["text"]
        opts = "\n".join([f"{k}) {v}" for k, v in question["options"].items()])
        
        prompt = f"""
Sen uzman bir İş Güvenliği Uzmanısın (A Sınıfı). Adaylara İSG sınavı sorularını açıklıyorsun.
Aşağıdaki soru ÖSYM tarafından sorulmuş orijinal bir çıkmış İSG Uzmanlık Sınavı sorusudur.

SORU:
{q_text}

ŞIKLAR:
{opts}

Kullanıcının İşaretlediği Cevap: {user_ans}
ÖSYM'nin Belirlediği Doğru Cevap: {correct_ans}

GÖREV:
1. Doğru cevabın ({correct_ans}) neden doğru olduğunu ilgili kanun, yönetmelik veya bilimsel gerçeklere dayanarak kısaca açıkla.
2. Eğer kullanıcı yanlış cevap verdiyse ({user_ans}), bu çeldiricinin neden yanlış olduğunu kısaca belirt.
3. Açıklaman çok uzun olmasın (max 2-3 paragraf), akılda kalıcı ve öğretici olsun. İş Güvenliği jargonu kullan ama anlaşılır olsun.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sen tecrübeli ve eğitici bir İş Güvenliği Uzmanısın."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Açıklama üretilirken bir hata oluştu: {str(e)}"

# Sidebar Configuration
with st.sidebar:
    st.title("🎓 İSG Sınav Seçimi")
    st.markdown("---")
    
    # API Key Input
    api_key_input = ""
    if "OPENAI_API_KEY" in st.secrets:
        api_key_input = st.secrets["OPENAI_API_KEY"]
    else:
        api_key_input = st.text_input("OpenAI API Key (Öğrenme Modu İçin)", type="password", help="Dinamik soru açıklamaları için geçerli bir OpenAI API anahtarı giriniz. Eğer anahtarınız yoksa Sınav Modunu kullanabilirsiniz.")
    
    st.markdown("---")
    
    if not st.session_state.exam_started or st.session_state.exam_finished:
        selected_period = st.selectbox("Dönem Seçiniz", periods)
        available_classes = list(exam_options.get(selected_period, {}).keys())
        selected_class = st.selectbox("Sınıf Seçiniz", sorted(available_classes))
        
        selected_exam = exam_options.get(selected_period, {}).get(selected_class)
        
        if selected_exam:
            st.info(f"Süre: {selected_exam['duration_minutes']} Dakika\n\nSoru: {selected_exam['question_count']} Adet")
            
            mode = st.radio("Mod Seçimi", ["Öğrenme Modu (Anında Çözüm)", "Gerçek Sınav Modu (Süreli)"])
            
            if st.button("Sınava Başla", use_container_width=True, type="primary"):
                if mode.startswith("Öğrenme") and not api_key_input:
                    st.error("Öğrenme modu için OpenAI API Key girmeniz gerekmektedir.")
                else:
                    is_learning = mode.startswith("Öğrenme")
                    # Save API key to session state for later use
                    st.session_state.openai_api_key = api_key_input
                    start_exam(selected_exam['id'], is_learning)
                    st.rerun()
    else:
        current_exam = get_current_exam()
        if current_exam:
            st.info(f"**Sınav:** {current_exam['title']}")
            if st.session_state.learning_mode:
                st.success("🧠 Öğrenme Modu Aktif")
            else:
                st.warning("⏱️ Sınav Modu Aktif")
            
            if not st.session_state.learning_mode:
                # Timer logic only for normal exam mode
                elapsed_time = time.time() - st.session_state.start_time
                total_time = current_exam['duration_minutes'] * 60
                remaining_time = max(0, total_time - elapsed_time)
                
                mins, secs = divmod(int(remaining_time), 60)
                time_format = f"{mins:02d}:{secs:02d}"
                
                st.metric("Kalan Süre", time_format)
                progress = max(0, min(1, remaining_time / total_time))
                st.progress(progress)
                
                if remaining_time <= 0 and not st.session_state.exam_finished:
                    st.warning("Süre doldu!")
                    finish_exam()
                    st.rerun()
                    
            st.markdown("---")
            
            # Question Grid Navigation
            st.write("**Sorular**")
            cols = st.columns(5)
            for i in range(current_exam['question_count']):
                col_idx = i % 5
                
                # Check status
                status_color = "secondary"
                if i in st.session_state.user_answers:
                    status_color = "primary"
                
                if i == st.session_state.current_q_index:
                    button_label = f"📍 {i+1}"
                else:
                    button_label = f"{i+1}"
                    
                if cols[col_idx].button(button_label, key=f"nav_{i}", use_container_width=True):
                    st.session_state.current_q_index = i
                    st.rerun()
            
            st.markdown("---")
            if st.button("Sınavı Bitir", use_container_width=True, type="primary"):
                finish_exam()
                st.rerun()

# Main Area
if not st.session_state.exam_started:
    st.title("İSG Sınav Simülatörüne Hoşgeldiniz! 🚀")
    st.write("Lütfen soldaki menüden çözmek istediğiniz sınav dönemi ve **sınıfını (A, B, C)** seçerek modunuzu belirleyip 'Sınava Başla' butonuna tıklayın.")
    st.write("Sınavlar ÖSYM tarafından sorulmuş orijinal çıkmış sorulardan oluşmaktadır.")
    
    st.markdown("### 📊 Sisteme Yüklü Sınav İstatistikleri")
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Sınav", len(data.get("exams", [])))
    
    total_q = sum(len(e["questions"]) for e in data.get("exams", []))
    col2.metric("Toplam Soru", total_q)
    
    periods_count = len(periods)
    col3.metric("Toplam Dönem", periods_count)
    
    st.markdown("---")
    st.markdown("### 💡 Modlar Hakkında")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Gerçek Sınav Modu:** ÖSYM standartlarında, süreye karşı yarışırsınız. Doğru/Yanlış cevaplarınızı sınav bitiminde görürsünüz.")
    with col2:
        st.success("**Öğrenme Modu:** Soruyu cevapladığınız anda doğru mu yanlış mı yaptığınızı görürsünüz. Üstelik OpenAI destekli Yapay Zeka, soruyu sizin için detaylıca açıklar!")

    st.markdown("---")
    st.markdown("### 👨‍💻 Geliştirici Notu")
    st.info("Not: Bu uygulama İş Güvenliği Uzmanı **Fatih AKDENİZ** tarafından geliştirilmiştir.")
    
elif st.session_state.exam_started and not st.session_state.exam_finished:
    current_exam = get_current_exam()
    if not current_exam:
        st.error("Sınav yüklenirken hata oluştu.")
        st.stop()
        
    questions = current_exam.get("questions", [])
    if not questions:
        st.warning("Bu sınav için soru bulunamadı.")
        st.stop()
        
    current_q = questions[st.session_state.current_q_index]
    
    st.subheader(f"Soru {current_q['number']}")
    
    st.markdown(f'<div class="question-box">{current_q["text"]}</div>', unsafe_allow_html=True)
    
    options = current_q.get("options", {})
    if options:
        current_ans = st.session_state.user_answers.get(st.session_state.current_q_index)
        correct_ans = current_q.get("answer")
        
        # Prepare options for radio
        option_list = []
        for k, v in options.items():
             option_list.append(f"{k}) {v}")
             
        # Find index for radio button
        default_index = None
        if current_ans:
            for idx, opt_key in enumerate(options.keys()):
                if opt_key == current_ans:
                    default_index = idx
                    break
        
        # In learning mode, if already answered, disable the radio button
        disabled_radio = st.session_state.learning_mode and current_ans is not None
        
        choice = st.radio("Cevabınız:", option_list, index=default_index, key=f"q_{st.session_state.current_q_index}", label_visibility="collapsed", disabled=disabled_radio)
        
        # Handle new answer
        if choice and not disabled_radio:
            selected_letter = choice[0]
            st.session_state.user_answers[st.session_state.current_q_index] = selected_letter
            
            # If in learning mode and just answered, immediately fetch explanation
            if st.session_state.learning_mode:
                with st.spinner("Yapay Zeka cevabınızı analiz ediyor ve açıklama üretiyor..."):
                    api_key = st.session_state.openai_api_key
                    explanation = generate_explanation(api_key, current_q, selected_letter, correct_ans)
                    st.session_state.explanations[st.session_state.current_q_index] = explanation
                st.rerun()
            else:
                pass # Normal mode just saves

        # Display immediate feedback if in learning mode
        if st.session_state.learning_mode and current_ans:
            st.markdown("---")
            if current_ans == correct_ans:
                st.success(f"✅ **Tebrikler, Doğru Cevap!** ({correct_ans})")
            else:
                st.error(f"❌ **Yanlış Cevap.** Sizin cevabınız: **{current_ans}**, Doğru Cevap: **{correct_ans}**")
                
            explanation = st.session_state.explanations.get(st.session_state.current_q_index)
            if explanation:
                st.markdown("#### 📖 Çözüm Açıklaması")
                st.markdown(f'<div class="explanation-box">{explanation}</div>', unsafe_allow_html=True)
                
    else:
        st.info("Bu soru metin formatında çözülemiyor. Lütfen geçiniz.")
        
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.session_state.current_q_index > 0:
            if st.button("⬅️ Önceki Soru", use_container_width=True):
                st.session_state.current_q_index -= 1
                st.rerun()
                
    with col3:
        if st.session_state.current_q_index < len(questions) - 1:
            if st.button("Sonraki Soru ➡️", use_container_width=True):
                st.session_state.current_q_index += 1
                st.rerun()
                
elif st.session_state.exam_finished:
    current_exam = get_current_exam()
    st.title("📊 Sınav Sonucu")
    st.subheader(current_exam['title'])
    
    questions = current_exam.get("questions", [])
    total_questions = len(questions)
    
    correct_count = 0
    wrong_count = 0
    empty_count = 0
    
    for i, q in enumerate(questions):
        user_ans = st.session_state.user_answers.get(i)
        correct_ans = q.get("answer")
        
        if not user_ans:
            empty_count += 1
        elif user_ans == correct_ans:
            correct_count += 1
        else:
            wrong_count += 1
            
    score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Puan", f"{score:.2f}")
    col2.metric("Doğru", correct_count)
    col3.metric("Yanlış", wrong_count)
    col4.metric("Boş", empty_count)
    
    st.markdown("---")
    st.subheader("📋 Soru Analizi")
    
    for i, q in enumerate(questions):
        user_ans = st.session_state.user_answers.get(i)
        correct_ans = q.get("answer")
        
        with st.expander(f"Soru {q['number']} - {'✅ Doğru' if user_ans == correct_ans else '❌ Yanlış' if user_ans else '⚠️ Boş'}"):
            st.markdown(f"**Soru:** {q['text']}")
            
            options = q.get("options", {})
            for k, v in options.items():
                st.write(f"{k}) {v}")
                
            st.markdown("---")
            
            if user_ans:
                st.write(f"Senin Cevabın: **{user_ans}**")
            else:
                st.markdown('<span class="missing-answer">Cevaplanmadı</span>', unsafe_allow_html=True)
                
            if correct_ans:
                st.markdown(f"Doğru Cevap: <span class='correct-answer'>{correct_ans}</span>", unsafe_allow_html=True)
            else:
                st.write("Doğru Cevap: PDF'den okunamadı")
                
            # If in learning mode, show the generated explanation in summary too
            explanation = st.session_state.explanations.get(i)
            if explanation:
                st.markdown("#### Çözüm Açıklaması")
                st.info(explanation)

    if st.button("Yeni Sınav Seç", type="primary"):
        st.session_state.exam_started = False
        st.session_state.exam_finished = False
        st.rerun()
