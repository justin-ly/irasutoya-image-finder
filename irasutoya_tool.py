import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator
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

def get_variations(word):
    """Generates a list of related search terms to cast a wider net."""
    variations = [word]
    
    # 1. Decomposition (e.g., 'Garbage Truck' -> 'Garbage')
    words = word.split()
    if len(words) > 1:
        variations.extend(words)
        
    # 2. Synonyms
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            variations.append(lemma.name().replace('_', ' '))
            
    return list(set(variations))[:6] # Limit to 6 to keep it fast

def perform_search(word, override_term=None):
    """Aggressive search that checks multiple variations."""
    # 1. Manual Override
    if override_term:
        jp_term = GoogleTranslator(source='auto', target='ja').translate(override_term)
        return get_candidates(jp_term), jp_term
    
    # 2. Multi-Pass Search
    all_results = []
    en_word = GoogleTranslator(source='auto', target='en').translate(word)
    variations = get_variations(en_word)
    
    for var in variations:
        var_jp = GoogleTranslator(source='en', target='ja').translate(var)
        results = get_candidates(var_jp)
        if results:
            all_results.extend(results)
            
    # Remove duplicates while keeping order
    unique_results = list(dict.fromkeys(all_results))
    return unique_results[:10], f"Multiple terms (Roots: {', '.join(variations[:3])})"

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
        
        # Search Box
        with st.expander("🔍 Search Options", expanded=True):
            new_term = st.text_input("Refine search (e.g., 'garbage', 'truck'):", value=st.session_state.manual_input)
            if st.button("Update Search"):
                st.session_state.manual_input = new_term
                st.rerun()

        # Execute Search
        with st.spinner("Searching widely..."):
            results, used_term = perform_search(current_word, st.session_state.manual_input)
        
        st.success(f"Searching for: **{used_term}**")
        
        if not results:
            st.warning("No images found. Please type a specific keyword in the box above.")
        else:
            # Display results in a grid
            cols = st.columns(5)
            for i, img_url in enumerate(results):
                with cols[i % 5]:
                    st.image(img_url, use_container_width=True)
                    if st.button(f"Select #{i+1}", key=f"btn_{i}"):
                        st.session_state.selections.append(img_url)
                        st.session_state.manual_input = ""
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
