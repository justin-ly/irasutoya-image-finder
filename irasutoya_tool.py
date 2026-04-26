import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- Core Logic ---
def get_candidates(keyword_jp):
    """Fetch images from Irasutoya."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        # Timeout is short to keep the "loop" feeling fast
        response = requests.get(search_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        results = []
        for post in posts[:5]:
            img = post.find('img')
            if img: results.append(img['src'])
        return results
    except Exception as e:
        return []

def perform_search_loop(word, manual_override=None):
    """
    Explicitly loops through a priority queue of search terms.
    """
    # 1. Manual Override
    if manual_override:
        return get_candidates(manual_override), [manual_override]

    # 2. Build explicit search queue
    # Convert word to EN first to get the base concept, then translate to JA
    en_word = GoogleTranslator(source='auto', target='en').translate(word)
    jp_word = GoogleTranslator(source='en', target='ja').translate(en_word)
    
    # Generate variations: 
    # [Exact JP Translation, Base Concept (EN -> JP)]
    queue = [jp_word]
    if " " in en_word:
        # If it's a phrase (Garbage Truck), add the core word (Garbage)
        core_word = en_word.split()[-1]
        core_jp = GoogleTranslator(source='en', target='ja').translate(core_word)
        queue.append(core_jp)
    
    # 3. Execution Loop
    tried_terms = []
    for q in queue:
        tried_terms.append(q)
        res = get_candidates(q)
        if res:
            return res, tried_terms # Return results and the list of attempts
            
    return [], tried_terms

# --- App UI ---
st.set_page_config(layout="wide")

# Init state
if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []
if 'manual_override' not in st.session_state: st.session_state.manual_override = ""

st.title("🎨 Irasutoya Smart Selector")

uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select column", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1}: {word}")
        
        # Override Input
        new_val = st.text_input("Enter keyword:", value=st.session_state.manual_override)
        if st.button("Update"):
            st.session_state.manual_override = new_val
            st.rerun()

        with st.spinner("Searching..."):
            results, attempts = perform_search_loop(word, st.session_state.manual_override)
        
        # Visual feedback for the loop
        st.write(f"Attempts made: **{' → '.join(attempts)}**")
        
        if not results:
            st.warning("No images found after trying: " + ", ".join(attempts))
        else:
            cols = st.columns(5)
            for i, img_url in enumerate(results):
                with cols[i % 5]:
                    st.image(img_url, use_container_width=True)
                    if st.button(f"Select {i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img_url)
                        st.session_state.manual_override = ""
                        st.session_state.index += 1
                        st.rerun()
