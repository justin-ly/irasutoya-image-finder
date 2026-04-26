import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- Scraping Logic ---
def get_images(keyword):
    """Fetches images from Irasutoya with explicit Japanese search query."""
    try:
        # Use Japanese-specific headers to ensure the site handles the encoding correctly
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Charset": "utf-8"
        }
        url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
        
        response = requests.get(url, headers=headers, timeout=10)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        return [p.find('img')['src'] for p in posts[:5] if p.find('img')]
    except: 
        return []

def get_translated_queue(word):
    """
    Forces translation to Japanese and returns a fallback queue.
    """
    # Force translation to Japanese
    try:
        ja_term = GoogleTranslator(source='auto', target='ja').translate(word)
    except:
        ja_term = word # Fallback to original if translation fails
        
    # Standard Irasutoya Fallbacks (The 'Golden' tags that always work)
    # If the translated term is 'ゴミ収集車', we ensure 'ゴミ' is in the queue.
    queue = [ja_term]
    
    # Logic to add root fallbacks
    if "収集" in ja_term: # Garbage truck case
        queue.append("ゴミ")
    elif "学校" in ja_term:
        queue.append("学校")
    elif "病院" in ja_term:
        queue.append("病院")
    elif len(ja_term) > 2:
        queue.append(ja_term[:2]) # Last resort root
        
    return queue

# --- UI ---
st.set_page_config(layout="wide")

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

st.title("🎨 Irasutoya Smart Selector (Fixed)")
uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select vocabulary column", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        word = words[st.session_state.index]
        st.subheader(f"Word: {word}")
        
        # Build Queue
        search_queue = get_translated_queue(word)
        st.write(f"🔍 **Translation logic:** {word} -> `{'` → `'.join(search_queue)}`")
        
        # Search
        final_images = []
        with st.status("Executing Search...") as status:
            for term in search_queue:
                st.write(f"Sending to Irasutoya: **{term}**")
                time.sleep(0.5)
                
                imgs = get_images(term)
                if imgs:
                    final_images = imgs
                    status.update(label=f"Success! Found: {term}", state="complete")
                    break
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
