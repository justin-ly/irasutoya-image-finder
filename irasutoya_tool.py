import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- UI Translation ---
UI_TEXT = {
    "English": {"title": "🎨 Irasutoya Smart Selector", "search_label": "Enter keyword:", "searching": "Searching...", "no_results": "No images found.", "select_btn": "Select #"},
    "Traditional Chinese": {"title": "🎨 統計圖庫智能選擇器", "search_label": "輸入關鍵字:", "searching": "正在深度搜尋...", "no_results": "未找到相關圖片。", "select_btn": "選擇 #"}
}

# --- Core Logic ---
def get_candidates(keyword_jp):
    """Fetch images from Irasutoya."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        response = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        results = []
        for post in posts[:5]:
            img = post.find('img')
            if img: results.append(img['src'])
        return results
    except: return []

def perform_search(word, manual_override=None):
    """Cascading search logic."""
    # 1. Manual Override
    if manual_override:
        return get_candidates(manual_override), manual_override

    # 2. Build Search Priority List
    jp_word = GoogleTranslator(source='auto', target='ja').translate(word)
    
    # Priority list: Full Term -> Core Concept (First 2 chars)
    search_queries = [jp_word]
    if len(jp_word) >= 2:
        search_queries.append(jp_word[:2]) # E.g., '垃圾' from '垃圾車'
    
    # 3. Execution Loop
    for q in search_queries:
        res = get_candidates(q)
        if res:
            return res, q
            
    return [], jp_word

# --- App UI ---
st.set_page_config(layout="wide")

# State Initialization (Fixed the Attribute Error)
if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []
if 'manual_override' not in st.session_state: st.session_state.manual_override = ""

lang = st.sidebar.selectbox("Language / 語言", ["English", "Traditional Chinese"])
t = UI_TEXT[lang]

st.title(t["title"])

uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select column", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1}: {word}")
        
        # Override Input
        new_val = st.text_input(t["search_label"], value=st.session_state.manual_override)
        if st.button("Update"):
            st.session_state.manual_override = new_val
            st.rerun()

        with st.spinner(t["searching"]):
            results, used_term = perform_search(word, st.session_state.manual_override)
        
        st.info(f"Searched: **{used_term}**")
        
        if not results:
            st.warning(t["no_results"])
        else:
            cols = st.columns(5)
            for i, img_url in enumerate(results):
                with cols[i % 5]:
                    st.image(img_url, use_container_width=True)
                    if st.button(f"{t['select_btn']}{i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img_url)
                        st.session_state.manual_override = ""
                        st.session_state.index += 1
                        st.rerun()
    else:
        st.success("Done!")
        # ... (Download logic remains the same)
