import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- Scraping Logic ---
def get_images(keyword):
    """Fetches images from Irasutoya with robust headers."""
    try:
        # Use a more realistic browser header to prevent bot blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # If response is empty, debug the status code
        if response.status_code != 200:
            return None 

        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        
        # Extract images
        images = []
        for p in posts[:5]:
            img = p.find('img')
            if img and img.get('src'):
                images.append(img['src'])
        return images
    except Exception as e:
        return []

def get_search_queue(word):
    """
    Guaranteed fallback queue: 
    1. Full Translation
    2. Root/Category Fallback
    """
    # 1. Translate
    main_jp = GoogleTranslator(source='auto', target='ja').translate(word)
    
    # 2. Logic: Create a Root Fallback
    # If the word is 'ゴミ収集車', try 'ゴミ'
    # We take the first 2 characters if they are Kanji, or the first word if it's a compound
    fallback = main_jp[:2] if len(main_jp) > 2 else main_jp
    
    # Ensure no duplicates
    queue = [main_jp]
    if fallback != main_jp:
        queue.append(fallback)
        
    return queue

# --- UI ---
st.set_page_config(layout="wide")

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

st.title("🎨 Irasutoya Smart Selector")
uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select vocabulary column", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1}: {current_word}")
        
        # Build and Display Queue
        search_queue = get_search_queue(current_word)
        st.write(f"🔍 **Queue to search:** `{'` → `'.join(search_queue)}`")
        
        # Status Feedback
        final_images = []
        with st.status("Performing Search...") as status:
            for term in search_queue:
                st.write(f"Checking term: **{term}**")
                time.sleep(0.5) # Anti-ban delay
                
                imgs = get_images(term)
                
                if imgs:
                    final_images = imgs
                    st.write(f"✅ Found {len(imgs)} results for **{term}**.")
                    status.update(label=f"Success: {term}", state="complete")
                    break
                else:
                    st.write(f"❌ No results for {term}.")
            else:
                status.update(label="No results found.", state="error")

        if final_images:
            cols = st.columns(5)
            for i, img in enumerate(final_images):
                with cols[i % 5]:
                    st.image(img, use_container_width=True)
                    if st.button(f"Select {i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img)
                        st.session_state.index += 1
                        st.rerun()
        
        if st.button("Skip"):
            st.session_state.index += 1
            st.rerun()
