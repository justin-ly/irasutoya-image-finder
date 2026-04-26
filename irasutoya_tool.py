import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- Language Settings ---
UI_TEXT = {
    "English": {
        "title": "🎨 Irasutoya Smart Selector",
        "upload": "Upload Vocabulary List",
        "search_label": "Enter search keyword:",
        "update_btn": "Update Search",
        "searching": "Searching...",
        "status_trying": "Trying search term: ",
        "no_results": "No images found after trying all terms.",
        "select": "Select",
        "done": "All Done!"
    },
    "Traditional Chinese": {
        "title": "🎨 統計圖庫智能選擇器",
        "upload": "上傳詞彙列表",
        "search_label": "輸入搜尋關鍵字:",
        "update_btn": "更新搜尋",
        "searching": "正在執行搜尋...",
        "status_trying": "嘗試搜尋詞: ",
        "no_results": "嘗試所有相關詞彙後仍無結果。",
        "select": "選擇",
        "done": "完成！"
    }
}

# --- Search Logic ---
def get_images_from_irasutoya(keyword_ja):
    """Fetches images for a specific Japanese keyword."""
    try:
        url = f"https://www.irasutoya.com/search?q={quote(keyword_ja)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Irasutoya results are in class 'boxim'
        posts = soup.find_all('div', class_='boxim')
        images = []
        for post in posts[:5]:
            img = post.find('img')
            if img and img.get('src'):
                images.append(img['src'])
        return images
    except:
        return []

def get_related_terms(word):
    """
    Returns a sequence of terms to try.
    1. Direct Translation
    2. Common associated Japanese terms
    """
    # Translate current word to JP
    jp_word = GoogleTranslator(source='auto', target='ja').translate(word)
    
    # Pre-defined associations for common tricky terms
    associations = {
        "ゴミ": ["ゴミ", "ゴミ収集車", "パッカー車"],
        "垃圾": ["ゴミ", "ゴミ収集車", "パッカー車"],
        "学校": ["学校", "教室", "校舎"],
        "病院": ["病院", "医師", "看護師"]
    }
    
    # Return: [Original Translation, + Associated Terms]
    queue = [jp_word]
    if jp_word in associations:
        queue.extend(associations[jp_word])
    
    # Remove duplicates but keep order
    return list(dict.fromkeys(queue))

# --- UI Setup ---
st.set_page_config(layout="wide")

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []
if 'manual_override' not in st.session_state: st.session_state.manual_override = ""

# Sidebar for Language
lang = st.sidebar.selectbox("Language / 語言", ["English", "Traditional Chinese"])
t = UI_TEXT[lang]

st.title(t["title"])

uploaded_file = st.file_uploader(t["upload"], type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select vocabulary column", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1}: {word}")
        
        # Manual Input
        manual_in = st.text_input(t["search_label"], value=st.session_state.manual_override)
        if st.button(t["update_btn"]):
            st.session_state.manual_override = manual_in
            st.rerun()

        # Search Loop with Status
        final_images = []
        
        if st.session_state.manual_override:
            # If manual override exists, only search that
            with st.status(t["searching"]) as status:
                st.write(f"{t['status_trying']} {st.session_state.manual_override}")
                final_images = get_images_from_irasutoya(st.session_state.manual_override)
                status.update(label="Search Complete", state="complete")
        else:
            # Otherwise, run the cascade loop
            terms_to_try = get_related_terms(word)
            with st.status(t["searching"]) as status:
                for term in terms_to_try:
                    st.write(f"{t['status_trying']} {term}")
                    final_images = get_images_from_irasutoya(term)
                    if final_images:
                        status.update(label=f"Found results for: {term}", state="complete")
                        break
                else:
                    status.update(label="No results", state="error")

        # Display Results
        if not final_images:
            st.warning(t["no_results"])
        else:
            cols = st.columns(5)
            for i, img in enumerate(final_images):
                with cols[i % 5]:
                    st.image(img, use_container_width=True)
                    if st.button(f"{t['select']} {i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img)
                        st.session_state.manual_override = ""
                        st.session_state.index += 1
                        st.rerun()
            
            if st.button("Skip"):
                st.session_state.manual_override = ""
                st.session_state.index += 1
                st.rerun()
