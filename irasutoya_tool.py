import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- Scraping & Logic ---
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

def generate_dynamic_queue(word):
    """
    Dynamically creates a search queue for ANY word by 
    decomposing it into its English roots and translating them back to Japanese.
    """
    queue = []
    
    # 1. Direct translation
    direct_ja = GoogleTranslator(source='auto', target='ja').translate(word)
    queue.append(direct_ja)
    
    # 2. Extract English roots for better "tag" matching
    en_translation = GoogleTranslator(source='auto', target='en').translate(word).lower()
    parts = en_translation.split()
    
    # 3. Add root concepts to the queue if they add diversity
    for part in parts:
        if len(part) > 3: # Ignore articles/short words
            root_ja = GoogleTranslator(source='en', target='ja').translate(part)
            if root_ja not in queue:
                queue.append(root_ja)
                
    return queue

# --- UI ---
st.set_page_config(layout="wide")

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

st.title("🎨 Irasutoya Dynamic Smart Selector")
uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    words = df[df.columns[0]].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1}: {current_word}")
        
        # Build Dynamic Queue
        search_queue = generate_dynamic_queue(current_word)
        st.write(f"**Search Queue Strategy:** {' → '.join(search_queue)}")
        
        final_images = []
        # Use status for live updates
        with st.status("Executing Search Queue...") as status:
            for term in search_queue:
                st.write(f"Attempting search for: **{term}**")
                # Wait 0.5s to be polite and ensure status updates are visible
                time.sleep(0.5) 
                
                imgs = get_images(term)
                if imgs:
                    final_images = imgs
                    status.update(label=f"Success! Found images for: {term}", state="complete")
                    break
                else:
                    st.write(f"No results for {term}...")
            else:
                status.update(label="No results found for any variation.", state="error")

        if final_images:
            cols = st.columns(5)
            for i, img in enumerate(final_images):
                with cols[i % 5]:
                    st.image(img, use_container_width=True)
                    if st.button(f"Select {i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img)
                        st.session_state.index += 1
                        st.rerun()
        else:
            if st.button("Skip"):
                st.session_state.index += 1
                st.rerun()
