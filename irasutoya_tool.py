import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator
import nltk
from nltk.corpus import wordnet

# --- Setup NLTK ---
@st.cache_resource
def setup_nltk():
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
        nltk.download('omw-1.4')
setup_nltk()

# --- UI Translation Dictionary ---
UI_TEXT = {
    "English": {
        "title": "🎨 Irasutoya Smart Selector",
        "upload": "Upload Vocabulary List (CSV/Excel)",
        "select_col": "Which column is your vocabulary?",
        "search_title": "🔍 Manual Search Override",
        "search_help": "Not finding the results? Enter a keyword (English or native) to force a search.",
        "search_label": "Enter keyword:",
        "update_btn": "Update Search",
        "searching": "Searching dynamically...",
        "searching_for": "Current search term: ",
        "no_results": "No images found. Please try a different keyword in the box above.",
        "select_btn": "Select #",
        "skip_btn": "Skip this word",
        "done": "All done!",
        "download": "📥 Download Result",
        "start_over": "Start Over",
        "all_done_msg": "All done! Here is your final list:"
    },
    "Traditional Chinese": {
        "title": "🎨 統計圖庫智能選擇器",
        "upload": "上傳詞彙列表 (CSV/Excel)",
        "select_col": "請問詞彙在哪個欄位？",
        "search_title": "🔍 手動搜尋調整",
        "search_help": "沒找到滿意的結果嗎？輸入關鍵字以手動強制搜尋。",
        "search_label": "輸入關鍵字:",
        "update_btn": "更新搜尋",
        "searching": "正在動態搜尋...",
        "searching_for": "當前搜尋詞: ",
        "no_results": "未找到圖片。請在上方輸入框輸入其他關鍵字。",
        "select_btn": "選擇 #",
        "skip_btn": "跳過此詞彙",
        "done": "完成！",
        "download": "📥 下載結果",
        "start_over": "重新開始",
        "all_done_msg": "完成！這是您的最終列表："
    }
}

# --- Helper Functions ---
def get_candidates(keyword_jp):
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        results = []
        for post in posts[:5]:
            try:
                link = post.find('a')['href']
                page_res = requests.get(link, headers=headers, timeout=5)
                soup_img = BeautifulSoup(page_res.text, 'html.parser')
                img_tag = soup_img.find('div', class_='separator').find('img')
                if img_tag: results.append(img_tag['src'])
            except: continue
        return results
    except: return []

def get_dynamic_related_terms(word):
    """Dynamically finds broader concepts (hypernyms) using NLTK."""
    en_word = GoogleTranslator(source='auto', target='en').translate(word)
    synsets = wordnet.synsets(en_word)
    related_terms = set()
    
    for syn in synsets:
        # Add hypernyms (Broader concepts like 'Truck' for 'Garbage Truck')
        for hyper in syn.hypernyms():
            related_terms.add(hyper.lemmas()[0].name().replace('_', ' '))
    
    # Translate back to Japanese
    jp_related = []
    for term in list(related_terms)[:3]: # Limit to 3 to keep it fast
        jp_related.append(GoogleTranslator(source='en', target='ja').translate(term))
    return jp_related

def perform_search(word, override_term=None):
    # 1. Manual Override
    if override_term:
        jp_term = GoogleTranslator(source='auto', target='ja').translate(override_term)
        return get_candidates(jp_term), jp_term
    
    # 2. Direct Translation Search
    jp_term = GoogleTranslator(source='auto', target='ja').translate(word)
    results = get_candidates(jp_term)
    if results:
        return results, jp_term

    # 3. Dynamic Expansion (If direct fails)
    related_terms = get_dynamic_related_terms(word)
    for related in related_terms:
        results = get_candidates(related)
        if results:
            return results, f"Related Concept: {related}"
            
    return [], jp_term

# --- Streamlit UI ---
st.set_page_config(page_title="Irasutoya Smart Selector", layout="wide")

lang = st.sidebar.selectbox("Language / 語言", ["English", "Traditional Chinese"])
t = UI_TEXT[lang]

st.title(t["title"])

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []
if 'manual_input' not in st.session_state: st.manual_input = ""

uploaded_file = st.file_uploader(t["upload"], type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox(t["select_col"], df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1} of {len(words)}: **{current_word}**")
        
        with st.expander(t["search_title"]):
            st.caption(t["search_help"])
            new_term = st.text_input(t["search_label"], value=st.session_state.manual_input)
            if st.button(t["update_btn"]):
                st.session_state.manual_input = new_term
                st.rerun()

        with st.spinner(t["searching"]):
            results, used_term = perform_search(current_word, st.session_state.manual_input)
        
        st.success(f"{t['searching_for']} **{used_term}**")
        
        if not results:
            st.warning(t["no_results"])
        else:
            cols = st.columns(5)
            for i, img_url in enumerate(results):
                with cols[i % 5]:
                    st.image(img_url, use_container_width=True)
                    if st.button(f"{t['select_btn']}{i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img_url)
                        st.session_state.manual_input = ""
                        st.session_state.index += 1
                        st.rerun()
            
            if st.button(t["skip_btn"]):
                st.session_state.manual_input = ""
                st.session_state.selections.append("Skipped")
                st.session_state.index += 1
                st.rerun()
    else:
        st.success(t["done"])
        st.write(t["all_done_msg"])
        final_df = pd.DataFrame({col: words, 'Selected_Image': st.session_state.selections})
        st.dataframe(final_df)
        csv = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(t["download"], csv, "curated_images.csv", "text/csv")
        if st.button(t["start_over"]):
            st.session_state.index = 0
            st.session_state.selections = []
            st.rerun()
