import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- Scraping Logic ---
def get_images(keyword):
    """Fetches images using explicit headers."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        return [p.find('img')['src'] for p in soup.find_all('div', class_='boxim')[:5] if p.find('img')]
    except: 
        return []

# --- UI Setup ---
st.set_page_config(layout="wide")

# Persistent State Initialization
if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

st.title("🎨 Irasutoya Smart Selector")
uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select vocabulary column", df.columns)
    words = df[col].tolist()

    # Progress
    progress = (st.session_state.index / len(words)) * 100
    st.progress(progress / 100)
    st.write(f"Processing word {st.session_state.index + 1} of {len(words)}")

    if st.session_state.index < len(words):
        word = str(words[st.session_state.index])
        
        # 1. FORCED TRANSLATION
        with st.spinner("Translating..."):
            try:
                ja_term = GoogleTranslator(source='auto', target='ja').translate(word)
            except:
                ja_term = word # Fallback
        
        st.subheader(f"Current: {word}")
        st.info(f"Targeting Japanese tag: **{ja_term}**")
        
        # 2. SEARCH QUEUE (Literal + Root)
        search_queue = [ja_term]
        if len(ja_term) > 2:
            search_queue.append(ja_term[:2])
            
        final_images = []
        
        # 3. SEARCH EXECUTION
        with st.status("Executing Search Queue...") as status:
            for term in search_queue:
                st.write(f"Searching: **{term}**")
                time.sleep(0.5) 
                imgs = get_images(term)
                if imgs:
                    final_images = imgs
                    status.update(label=f"Found results for: {term}", state="complete")
                    break
            else:
                status.update(label="No results found.", state="error")

        # 4. INTERACTION
        if final_images:
            cols = st.columns(5)
            for i, img in enumerate(final_images):
                with cols[i % 5]:
                    st.image(img, use_container_width=True)
                    if st.button(f"Select {i+1}", key=f"select_{i}"):
                        st.session_state.selections.append(img)
                        st.session_state.index += 1
                        st.rerun()
        
        # SKIP BUTTON
        if st.button("⏭ Skip to next word"):
            st.session_state.index += 1
            st.rerun()

    else:
        st.success("All words processed!")
        st.write("Selections:", st.session_state.selections)
