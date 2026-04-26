import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- UI Text ---
UI_TEXT = {
    "English": {"title": "🎨 Irasutoya Smart Selector", "search_label": "Enter search keyword:", "searching": "Running Search Queue...", "select": "Select", "skip": "Skip", "status": "Searching for"},
    "Traditional Chinese": {"title": "🎨 統計圖庫智能選擇器", "search_label": "輸入搜尋關鍵字:", "searching": "正在執行搜尋佇列...", "select": "選擇", "skip": "跳過", "status": "正在搜尋"}
}

def get_images(keyword):
    """Fetches images from Irasutoya."""
    try:
        url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        return [p.find('img')['src'] for p in posts[:5] if p.find('img')]
    except: return []

def get_search_queue(word):
    """Generates an intelligent list of search terms."""
    # 1. Direct translation
    main_term = GoogleTranslator(source='auto', target='ja').translate(word)
    queue = [main_term]
    
    # 2. Concept Extraction (The "Smart" Fallback)
    en_word = GoogleTranslator(source='auto', target='en').translate(word).lower()
    
    # If it's a compound noun (like "Garbage truck"), add the parts back as roots
    # Examples: "Garbage truck" -> ["ゴミ収集車", "ゴミ"]
    if " " in en_word:
        parts = en_word.split()
        for part in parts:
            if len(part) > 3: # Ignore small words like 'a', 'the', 'on'
                fallback = GoogleTranslator(source='en', target='ja').translate(part)
                if fallback not in queue:
                    queue.append(fallback)
                    
    return queue

# --- UI ---
st.set_page_config(layout="wide")
if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

lang = st.sidebar.selectbox("Language / 語言", ["English", "Traditional Chinese"])
t = UI_TEXT[lang]

st.title(t["title"])
uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select column", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1}: {current_word}")
        
        # 1. Build the validated queue
        manual_override = st.text_input(t["search_label"])
        search_queue = [manual_override] if manual_override else get_search_queue(current_word)
        
        st.info(f"Search Queue: {' → '.join(search_queue)}")
        
        # 2. Run Loop
        final_images = []
        with st.status(t["searching"]) as status:
            for term in search_queue:
                st.write(f"{t['status']}: **{term}**...")
                imgs = get_images(term)
                if imgs:
                    final_images = imgs
                    status.update(label=f"Success! Found images for: {term}", state="complete")
                    break
            else:
                status.update(label="No results found.", state="error")

        # 3. Display
        if final_images:
            cols = st.columns(5)
            for i, img in enumerate(final_images):
                with cols[i % 5]:
                    st.image(img, use_container_width=True)
                    if st.button(f"{t['select']} {i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img)
                        st.session_state.index += 1
                        st.rerun()
        else:
            if st.button(t["skip"]):
                st.session_state.index += 1
                st.rerun()
