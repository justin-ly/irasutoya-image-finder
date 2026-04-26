import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- Optimized Scraping & Logic ---

@st.cache_data(show_spinner=False)
def cached_translate(word, source='auto', target='ja'):
    try:
        return GoogleTranslator(source=source, target=target).translate(word)
    except:
        return word

@st.cache_data(show_spinner="Searching Irasutoya...")
def get_images(keyword):
    """Fetches images from Irasutoya with better error handling."""
    try:
        url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Irasutoya specific: thumbnails are usually inside 'boxim' divs
        posts = soup.find_all('div', class_='boxim')
        results = []
        for p in posts:
            img = p.find('img')
            if img and img.get('src'):
                # Convert thumbnail URL to slightly higher res if possible
                img_url = img['src'].replace('s72-c', 's400')
                results.append(img_url)
        return results[:10] # Return top 10 for variety
    except Exception as e:
        return []

@st.cache_data(show_spinner=False)
def generate_dynamic_queue(word):
    """
    Forces translation to Japanese and breaks the concept 
    into broader categories if the specific term fails.
    """
    queue = []
    
    # 1. Force the Primary Japanese Translation
    # This turns "垃圾車" into "ごみ収集車"
    primary_ja = cached_translate(word, target='ja')
    if primary_ja and primary_ja != word:
        queue.append(primary_ja)
    
    # 2. Add the original word just in case (sometimes Kanji matches)
    if word not in queue:
        queue.append(word)

    # 3. Conceptual Fallback (The "Decomposition" Logic)
    # Translate to English first to get root nouns
    en_concept = cached_translate(word, target='en').lower() # "garbage truck"
    parts = en_concept.split() # ["garbage", "truck"]

    if len(parts) > 1:
        for part in parts:
            if len(part) > 2:
                # Translate "garbage" -> "ごみ", "truck" -> "トラック"
                root_ja = cached_translate(part, source='en', target='ja')
                if root_ja not in queue:
                    queue.append(root_ja)
                    
    # 4. Global Broadener
    # If it's a vehicle, adding "vehicle" or "car" can help find related tags
    if "truck" in en_concept or "car" in en_concept:
        queue.append("車") # Japanese for Car/Vehicle
        
    return queue

# --- UI Setup ---
st.set_page_config(page_title="Irasutoya Smart Finder", layout="wide")

if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

st.title("🎨 Irasutoya Dynamic Smart Selector")

# Sidebar for progress and results
with st.sidebar:
    st.header("Progress")
    if st.session_state.selections:
        st.write(f"Selected: {len(st.session_state.selections)} images")
        df_results = pd.DataFrame(st.session_state.selections)
        st.download_button("Download Selection CSV", df_results.to_csv(index=False), "selections.csv")
    
    if st.button("Reset Process"):
        st.session_state.index = 0
        st.session_state.selections = []
        st.rerun()

uploaded_file = st.file_uploader("Upload CSV/Excel (First column should be keywords)", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    words = df[df.columns[0]].tolist()

    if st.session_state.index < len(words):
        current_word = words[st.session_state.index]
        
        # Progress Bar
        progress = st.session_state.index / len(words)
        st.progress(progress)
        st.subheader(f"Processing ({st.session_state.index + 1}/{len(words)}): **{current_word}**")
        
        # 1. Generate Queue
        search_queue = generate_dynamic_queue(current_word)
        
        # 2. Search Logic (with caching, this is now fast)
        final_images = []
        found_term = None
        
        with st.status(f"Searching variations for '{current_word}'...") as status:
            for term in search_queue:
                st.write(f"🔍 Trying: {term}")
                imgs = get_images(term)
                if imgs:
                    final_images = imgs
                    found_term = term
                    status.update(label=f"Found results for '{term}'", state="complete")
                    break
            else:
                status.update(label="No illustrations found.", state="error")

        # 3. Display Results
        if final_images:
            st.write(f"Displaying results for: **{found_term}**")
            cols = st.columns(4)
            for i, img in enumerate(final_images):
                with cols[i % 4]:
                    st.image(img, use_container_width=True)
                    if st.button(f"Select Image {i+1}", key=f"select_{i}"):
                        st.session_state.selections.append({"word": current_word, "url": img})
                        st.session_state.index += 1
                        st.rerun()
            
            if st.button("Skip this word ⏭️"):
                st.session_state.index += 1
                st.rerun()
        else:
            st.warning(f"Could not find any images for '{current_word}' or its variations.")
            if st.button("Skip"):
                st.session_state.index += 1
                st.rerun()
    else:
        st.balloons()
        st.success("✅ All words processed! Check the sidebar to download your list.")
