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
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Only return if we actually find something
        return [p.find('img')['src'] for p in soup.find_all('div', class_='boxim')[:5] if p.find('img')]
    except: return []

def generate_search_queue(word):
    """
    Generates 5 robust Japanese search terms by bridging through English.
    """
    # 1. Bridge to English to generate variations
    en_translation = GoogleTranslator(source='auto', target='en').translate(word).lower()
    
    # 2. Generate 5 variations based on the English root
    # This ensures we get synonyms (e.g., "Trash", "Waste", "Truck")
    base_concepts = [en_translation]
    if " " in en_translation:
        base_concepts.extend(en_translation.split())
    if "truck" in en_translation: base_concepts.append("vehicle")
    if "garbage" in en_translation: base_concepts.extend(["trash", "waste"])
    
    # 3. Translate all variations back to Japanese
    queue = []
    for concept in base_concepts[:5]:
        try:
            ja_term = GoogleTranslator(source='en', target='ja').translate(concept)
            if ja_term not in queue:
                queue.append(ja_term)
        except: continue
        
    return queue

# --- UI Setup ---
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
        word = str(words[st.session_state.index])
        
        # Build Queue
        search_queue = generate_search_queue(word)
        
        st.subheader(f"Word: {word}")
        st.write(f"🔍 **Searching in Japanese for:** {', '.join(search_queue)}")
        
        # Search Execution
        final_images = []
        with st.status("Executing...") as status:
            for term in search_queue:
                st.write(f"Attempting: {term}")
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
                    if st.button(f"Select {i+1}", key=f"sel_{i}"):
                        st.session_state.selections.append(img)
                        st.session_state.index += 1
                        st.rerun()
        
        if st.button("⏭ Skip"):
            st.session_state.index += 1
            st.rerun()
