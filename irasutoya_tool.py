import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- 1. Robust Scraper ---
def get_images(keyword):
    """
    Fetches images by filtering for 'irasutoya' in the URL.
    This bypasses CSS class-name changes that usually break scrapers.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Filter all images on the page for relevant Irasutoya URLs
        found_images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and "irasutoya" in src and "http" in src:
                # Filter out UI elements (buttons, icons, avatars)
                if not any(x in src for x in ["button", "icon", "avatar", "logo"]):
                    found_images.append(src)
        
        return list(set(found_images))[:5] # Return unique top 5
    except Exception as e:
        return []

# --- 2. Dynamic Logic ---
def generate_search_queue(word):
    """
    Generates up to 5 related Japanese terms via English bridging.
    """
    try:
        # Bridge via English to get distinct synonyms
        en_translation = GoogleTranslator(source='auto', target='en').translate(word).lower()
        base_concepts = [en_translation]
        
        # Add expansion logic for common terms
        if " " in en_translation:
            base_concepts.extend(en_translation.split())
            
        # Translate to Japanese
        queue = []
        for concept in base_concepts[:5]:
            ja_term = GoogleTranslator(source='en', target='ja').translate(concept)
            if ja_term not in queue:
                queue.append(ja_term)
        return queue
    except:
        return [word] # Fallback

# --- 3. UI Setup ---
st.set_page_config(layout="wide")

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

st.title("🎨 Irasutoya Smart Selector")
uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select vocabulary column", df.columns)
    words = df[col].tolist()

    # Progress Bar
    st.progress(st.session_state.index / len(words))
    
    if st.session_state.index < len(words):
        word = str(words[st.session_state.index])
        
        # Build and display queue
        search_queue = generate_search_queue(word)
        st.subheader(f"Word: {word}")
        st.write(f"🔍 **Searching Japanese terms:** `{'` → `'.join(search_queue)}`")
        
        # Search Execution
        final_images = []
        with st.status("Executing Search Queue...") as status:
            for term in search_queue:
                st.write(f"Checking: **{term}**")
                time.sleep(0.5) 
                imgs = get_images(term)
                if imgs:
                    final_images = imgs
                    status.update(label=f"Success! Found images for: {term}", state="complete")
                    break
            else:
                status.update(label="No results found for any variation.", state="error")

        # Display images and controls
        if final_images:
            cols = st.columns(5)
            for i, img in enumerate(final_images):
                with cols[i % 5]:
                    st.image(img, use_container_width=True)
                    if st.button(f"Select {i+1}", key=f"sel_{i}"):
                        st.session_state.selections.append(img)
                        st.session_state.index += 1
                        st.rerun()
        
        # Skip button
        if st.button("⏭ Skip to next word"):
            st.session_state.index += 1
            st.rerun()
            
    else:
        st.success("All words processed!")
        st.write("### Your Selections:")
        st.write(st.session_state.selections)
