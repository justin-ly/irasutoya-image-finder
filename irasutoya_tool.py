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
        nltk.download('omw-1.4') # Necessary for WordNet multi-language support

setup_nltk()

# --- Helper Functions ---

def get_synonyms(word):
    """Automatically generates English synonyms using NLTK WordNet."""
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            # Add synonym and replace underscores
            synonyms.add(lemma.name().replace('_', ' '))
    return list(synonyms)

def get_candidates(keyword_jp):
    """Fetches up to 5 image candidates from Irasutoya search."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('div', class_='boxim')
        results = []
        for post in posts[:5]:
            try:
                # Navigate to the post page
                link = post.find('a')['href']
                page_res = requests.get(link, headers=headers, timeout=5)
                soup_img = BeautifulSoup(page_res.text, 'html.parser')
                img_tag = soup_img.find('div', class_='separator').find('img')
                if img_tag: 
                    results.append(img_tag['src'])
            except: continue
        return results
    except: return []

def search_dynamic(word):
    """Tries original, then cascades through English synonyms until a result is found."""
    # 1. Primary Attempt
    jp_word = GoogleTranslator(source='auto', target='ja').translate(word)
    results = get_candidates(jp_word)
    if results: return results, jp_word
    
    # 2. Dynamic Fallback: Translate to English -> Get Synonyms -> Search JP Synonyms
    en_word = GoogleTranslator(source='auto', target='en').translate(word)
    synonyms = get_synonyms(en_word)
    
    for syn in synonyms[:5]: # Try first 5 synonyms to avoid hanging the app
        syn_jp = GoogleTranslator(source='en', target='ja').translate(syn)
        results = get_candidates(syn_jp)
        if results: return results, syn_jp
        
    return [], jp_word

# --- Streamlit UI ---

st.set_page_config(page_title="Irasutoya Dynamic Selector", layout="wide")
st.title("🎨 Irasutoya Dynamic Selector")
st.markdown("Upload your vocab list and pick the best image for each word.")

# Initialize session state for tracking progress
if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

uploaded_file = st.file_uploader("Upload your Vocabulary List (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_file:
    # Read file
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Select the column containing your vocabulary:", df.columns)
    words = df[col].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        st.subheader(f"Word {st.session_state.index + 1} of {len(words)}: **{current_word}**")
        
        # Smart Search
        with st.spinner(f"Searching for images for '{current_word}'..."):
            results, used_term = search_dynamic(current_word)
        
        if not results:
            st.warning(f"No results found for '{current_word}' (or related synonyms).")
            if st.button("Continue to next word"):
                st.session_state.selections.append("Not found")
                st.session_state.index += 1
                st.rerun()
        else:
            st.caption(f"Search context used: {used_term}")
            cols = st.columns(len(results))
            choice = None
            
            for i, img_url in enumerate(results):
                with cols[i]:
                    st.image(img_url, use_container_width=True)
                    if st.button(f"Select #{i+1}", key=f"btn_{i}"):
                        choice = img_url
            
            if choice:
                st.session_state.selections.append(choice)
                st.session_state.index += 1
                st.rerun()
                
            if st.button("Skip this word"):
                st.session_state.selections.append("Skipped")
                st.session_state.index += 1
                st.rerun()
    else:
        st.success("All done! Here is your final list:")
        final_df = pd.DataFrame({col: words, 'Selected_Image': st.session_state.selections})
        st.dataframe(final_df)
        
        csv = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download Result", csv, "curated_images.csv", "text/csv")
        
        if st.button("Start Over"):
            st.session_state.index = 0
            st.session_state.selections = []
            st.rerun()
