import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator
import time
import nltk
from nltk.corpus import wordnet

# --- Setup NLTK ---
@st.cache_resource
def setup_nltk():
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
        nltk.download('omw-1.4')
setup_nltk()

# --- Helper Functions ---

def get_candidates(keyword_jp):
    """Fetches up to 5 image candidates."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        results = []
        for post in posts[:5]:
            try:
                link = post.find('a')['href']
                page_res = requests.get(link, headers=headers, timeout=5)
                soup_img = BeautifulSoup(page_res.text, 'html.parser')
                img_tag = soup_img.find('div', class_='separator').find('img')
                if img_tag: results.append(img_tag['src'])
            except: continue
        return results
    except: return []

def perform_search(word, override_term=None):
    """Tiered search: Manual Override -> Original Word -> Synonyms."""
    # 1. Manual Override (Always Translate to JP first!)
    if override_term:
        jp_term = GoogleTranslator(source='auto', target='ja').translate(override_term)
        results = get_candidates(jp_term)
        return results, jp_term
    
    # 2. Original Translation
    jp_word = GoogleTranslator(source='auto', target='ja').translate(word)
    results = get_candidates(jp_word)
    if results: return results, jp_word
    
    # 3. Synonyms
    en_word = GoogleTranslator(source='auto', target='en').translate(word)
    for syn in wordnet.synsets(en_word):
        for lemma in syn.lemmas():
            syn_en = lemma.name().replace('_', ' ')
            syn_jp = GoogleTranslator(source='en', target='ja').translate(syn_en)
            results = get_candidates(syn_jp)
            if results: return results, syn_jp
            
    return [], jp_word

# --- Streamlit UI ---

st.set_page_config(page_title="Irasutoya Smart Selector", layout="wide")
st.title("🎨 Irasutoya Smart Selector")

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []
if 'manual_input' not in st.session_state: st.session_state.manual_input = ""

uploaded_file = st.file_uploader("Upload Vocabulary List (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Which column is your vocabulary?", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1} of {len(words)}: **{current_word}**")
        
        # 1. Search Box ALWAYS visible
        st.write("---")
        with st.expander("🔍 Search Override (Type English or Japanese here)", expanded=True):
            new_term = st.text_input("Enter keyword:", value=st.session_state.manual_input)
            if st.button("Apply Search"):
                st.session_state.manual_input = new_term
                st.rerun()
            if st.button("Clear Override"):
                st.session_state.manual_input = ""
                st.rerun()

        # 2. Execute Search
        with st.spinner("Searching..."):
            results, used_term = perform_search(current_word, st.session_state.manual_input)
        
        # 3. Tracking/Status Tracker at the top
        st.success(f"Current active keyword: **{used_term}**")
        
        if not results:
            st.warning("No images found. Please try a different keyword in the box above.")
        else:
            cols = st.columns(len(results))
            for i, img_url in enumerate(results):
                with cols[i]:
                    st.image(img_url, use_container_width=True)
                    if st.button(f"Select #{i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img_url)
                        st.session_state.manual_input = "" # Clear for next word
                        st.session_state.index += 1
                        st.rerun()
            
            if st.button("Skip this word"):
                st.session_state.manual_input = ""
                st.session_state.selections.append("Skipped")
                st.session_state.index += 1
                st.rerun()
    else:
        st.success("All done!")
        final_df = pd.DataFrame({col: words, 'Selected_Image': st.session_state.selections})
        st.dataframe(final_df)
        csv = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download Result", csv, "curated_images.csv", "text/csv")
