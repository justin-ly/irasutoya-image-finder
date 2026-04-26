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
        "search_title": "🔍 Need a better match?",
        "search_help": "Not finding the results? Type a specific keyword here to refine the search.",
        "search_label": "Enter custom keyword:",
        "update_btn": "Update Search",
        "searching": "Searching...",
        "searching_for": "Current search term: ",
        "no_results": "No images found. Try a different, simpler keyword (e.g., 'truck' instead of 'garbage truck').",
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
        "search_title": "🔍 找不到合適的圖片？",
        "search_help": "沒找到滿意的結果嗎？嘗試輸入更簡單或具體的關鍵字。",
        "search_label": "輸入自訂關鍵字:",
        "update_btn": "更新搜尋",
        "searching": "正在搜尋...",
        "searching_for": "當前搜尋詞: ",
        "no_results": "未找到圖片。請嘗試更簡單的關鍵字 (例如: '垃圾' 而非 '垃圾車')。",
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

def perform_search(word, override_term=None):
    # 1. Manual Override (Priority)
    if override_term:
        jp_term = GoogleTranslator(source='auto', target='ja').translate(override_term)
        return get_candidates(jp_term), jp_term
    
    # 2. Direct Search (The "Missing Link" that fixes your issue)
    jp_term = GoogleTranslator(source='auto', target='ja').translate(word)
    results = get_candidates(jp_term)
    if results:
        return results, jp_term

    # 3. Fallback: English Synonyms (Only runs if direct search fails)
    en_word = GoogleTranslator(source='auto', target='en').translate(word)
    syn_results = []
    
    for syn in wordnet.synsets(en_word):
        for lemma in syn.lemmas():
            syn_en = lemma.name().replace('_', ' ')
            syn_jp = GoogleTranslator(source='en', target='ja').translate(syn_en)
            results = get_candidates(syn_jp)
            if results:
                syn_results.extend(results)
    
    unique_results = list(dict.fromkeys(syn_results))
    return unique_results[:10], f"Fallback Synonyms for {en_word}"

# --- Streamlit UI ---
st.set_page_config(page_title="Irasutoya Smart Selector", layout="wide")

lang = st.sidebar.selectbox("Language / 語言", ["English", "Traditional Chinese"])
t = UI_TEXT[lang]

st.title(t["title"])

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []
if 'manual_input' not in st.session_state: st.session_state.manual_input = ""

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
