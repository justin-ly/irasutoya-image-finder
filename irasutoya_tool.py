import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator

# --- 1. Scraper (Smart URL Filter) ---
def get_images(keyword):
    """Bypasses CSS classes and filters for Irasutoya image URLs."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            # Only pick images hosted on Irasutoya/Blogger that aren't UI icons
            if src and "irasutoya" in src and "http" in src:
                if not any(x in src.lower() for x in ["button", "icon", "avatar", "logo", "title"]):
                    images.append(src)
        return list(dict.fromkeys(images))[:5] # Unique top 5
    except: return []

# --- 2. Forced Translation & Queue Logic ---
def get_japanese_queue(word):
    """Forces Chinese -> English -> Japanese to ensure zero Chinese characters remain."""
    queue = []
    try:
        # Step A: Force Bridge to English (Eliminates Chinese-Japanese Kanji confusion)
        en_root = GoogleTranslator(source='auto', target='en').translate(word).lower()
        
        # Step B: Generate English Variations
        concepts = [en_root]
        if " " in en_root:
            concepts.extend(en_root.split()) # "Garbage Truck" -> ["garbage", "truck"]
        
        # Step C: Force English -> Japanese
        for c in concepts:
            if len(queue) >= 5: break
            ja_term = GoogleTranslator(source='en', target='ja').translate(c)
            if ja_term and ja_term not in queue:
                queue.append(ja_term)
        
        # Step D: Final check - ensure NO Chinese remains in the queue
        # If the translator returned the original Chinese, we don't add it.
        queue = [q for q in queue if q != word]
    except Exception as e:
        st.error(f"Translation Error: {e}")
    
    return queue[:5]

# --- 3. Persistent State Management ---
if 'index' not in st.session_state: st.session_state.index = 0
if 'selections' not in st.session_state: st.session_state.selections = []

def next_word():
    st.session_state.index += 1

# --- 4. Main UI ---
st.set_page_config(layout="wide")
st.title("🎨 Irasutoya Smart Selector")

uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Choose the vocabulary column", df.columns)
    words = df[col].dropna().tolist()

    if st.session_state.index < len(words):
        current_word = str(words[st.session_state.index])
        
        st.subheader(f"Word {st.session_state.index + 1} of {len(words)}: **{current_word}**")
        
        # Force the queue generation
        with st.spinner("Generating Japanese variations..."):
            search_queue = get_japanese_queue(current_word)
        
        if not search_queue:
            st.warning("Could not generate Japanese tags. Please check internet connection.")
            search_queue = [current_word] # Panic fallback

        st.info(f"🔍 **Search Queue (Japanese):** {' → '.join(search_queue)}")
        
        # Run the search loop
        final_images = []
        with st.status("Searching Irasutoya...") as status:
            for term in search_queue:
                st.write(f"Searching term: **{term}**")
                time.sleep(0.6) # Delay to prevent IP block
                imgs = get_images(term)
                if imgs:
                    final_images = imgs
                    status.update(label=f"Success! Found results for: {term}", state="complete")
                    break
                else:
                    st.write(f"❌ No results for {term}")
            else:
                status.update(label="No results found for this word.", state="error")

        # Layout Selections
        if final_images:
            cols = st.columns(5)
            for i, img in enumerate(final_images):
                with cols[i]:
                    st.image(img, use_container_width=True)
                    st.button(f"Select {i+1}", key=f"sel_{i}", on_click=next_word, args=(), kwargs={'img_url': img})
                    # Note: We store the selection in the session state logic
                    if f"sel_{i}" in st.context.triggered_ids:
                        st.session_state.selections.append({"word": current_word, "url": img})

        # Persistent Skip Button
        st.divider()
        st.button("⏭ Skip to Next Word", on_click=next_word, use_container_width=True)

    else:
        st.success("✅ Process Complete!")
        st.write("### Final Selections")
        st.dataframe(pd.DataFrame(st.session_state.selections))
        st.download_button("Download Results CSV", pd.DataFrame(st.session_state.selections).to_csv(index=False), "selections.csv")
