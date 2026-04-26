import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- UI Translation Dictionary ---
UI_TEXT = {
    "English": {
        "title": "🎨 Irasutoya Smart Selector",
        "search_label": "Enter keyword:",
        "update_btn": "Update Search",
        "searching": "Searching...",
        "no_results": "No images found after trying multiple variations. Please try a different keyword.",
        "select_btn": "Select #",
        "skip_btn": "Skip this word",
        "done": "All done!"
    },
    "Traditional Chinese": {
        "title": "🎨 統計圖庫智能選擇器",
        "search_label": "輸入關鍵字:",
        "update_btn": "更新搜尋",
        "searching": "正在進行多重搜尋...",
        "no_results": "嘗試多種關鍵字後仍未找到圖片。請更換其他關鍵字。",
        "select_btn": "選擇 #",
        "skip_btn": "跳過此詞彙",
        "done": "完成！"
    }
}

# --- Helper Functions ---
def get_candidates(keyword_jp):
    """Fetches images from Irasutoya (Japanese input only)."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=5)
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

def perform_cascading_search(word, override_term=None):
    """
    Loops through variations to find results. 
    1. Manual Override (if provided)
    2. Direct Translation
    3. Truncated Concept (e.g., '垃圾車' -> '垃圾')
    4. First Character (e.g., '垃圾' -> '垃')
    """
    # Use override if provided
    search_term = override_term if override_term else word
    
    # 1. Prepare List of Variations (Always in Japanese)
    base_jp = GoogleTranslator(source='auto', target='ja').translate(search_term)
    
    variations = [base_jp]
    # Add variations (e.g., try truncating the word to get to the core concept)
    if len(base_jp) > 2:
        variations.append(base_jp[:2]) # First 2 chars (core concept)
    
    # 2. The Search Loop
    for var in variations:
        results = get_candidates(var)
        if results:
            return results, var # Return immediately on success
            
    return [], base_jp

# --- Streamlit UI ---
st.set_page_config(page_title="Irasutoya Selector", layout="wide")

# Initialize State
if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []
if 'manual_input' not in st.session_state: st.session_state.manual_input = ""

# Language Switcher
lang = st.sidebar.selectbox("Language / 語言", ["English", "Traditional Chinese"])
t = UI_TEXT[lang]

st.title(t["title"])

uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select vocabulary column", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1}: **{current_word}**")
        
        # Override Input
        st.session_state.manual_input = st.text_input(t["search_label"], value=st.session_state.manual_input)
        if st.button(t["update_btn"]):
            st.rerun()

        # Run Search Loop
        with st.spinner(t["searching"]):
            results, used_term = perform_cascading_search(current_word, st.session_state.manual_input)
        
        st.info(f"Using term: **{used_term}**")
        
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
        st.download_button("Download", pd.DataFrame({'Word': words, 'Img': st.session_state.selections}).to_csv(index=False), "results.csv")
