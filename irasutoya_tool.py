import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- Functions ---
def get_candidates(keyword_jp):
    """Fetches top 5 candidates."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        results = []
        for post in posts[:5]:
            try:
                img_tag = BeautifulSoup(requests.get(post.find('a')['href'], headers=headers, timeout=5).text, 'html.parser').find('div', class_='separator').find('img')
                if img_tag: results.append(img_tag['src'])
            except: continue
        return results
    except: return []

# --- UI Logic ---
st.set_page_config(page_title="Irasutoya Selector", layout="wide")
st.title("🎨 Interactive Irasutoya Selector")

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

uploaded_file = st.file_uploader("Upload your list (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select vocabulary column", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1} of {len(words)}: **{current_word}**")
        
        jp_word = GoogleTranslator(source='auto', target='ja').translate(str(current_word)) + " イラスト"
        candidates = get_candidates(jp_word)

        if not candidates:
            st.warning("No images found. Skipping...")
            if st.button("Skip"):
                st.session_state.selections.append("Not found")
                st.session_state.index += 1
                st.rerun()
        else:
            cols = st.columns(len(candidates))
            choice = None
            for i, img_url in enumerate(candidates):
                with cols[i]:
                    st.image(img_url, use_container_width=True)
                    if st.button(f"Select #{i+1}", key=f"btn_{i}"):
                        choice = img_url
            
            if choice:
                st.session_state.selections.append(choice)
                st.session_state.index += 1
                st.rerun()
    else:
        st.success("All done! Here is your final list:")
        final_df = pd.DataFrame({col: words, 'Selected_Image': st.session_state.selections})
        st.dataframe(final_df)
        csv = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download Spreadsheet", csv, "curated_images.csv", "text/csv")
        if st.button("Start Over"):
            st.session_state.index = 0
            st.session_state.selections = []
            st.rerun()
