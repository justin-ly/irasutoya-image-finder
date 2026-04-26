import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator
import time

# --- Helper Functions ---

def translate_to_japanese(text):
    """Translates Chinese or English to Japanese."""
    try:
        # It automatically detects source language
        translated = GoogleTranslator(source='auto', target='ja').translate(text)
        return translated
    except:
        return text # Fallback to original

def get_irasutoya_image(keyword_jp):
    """Scrapes the direct PNG link from Irasutoya."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the first image post
        post = soup.find('div', class_='boxim')
        if not post:
            return "No image found"
        
        post_link = post.find('a')['href']
        
        # Get high-res image from the post page
        post_res = requests.get(post_link, headers=headers, timeout=10)
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        
        # Extract the image URL
        img_tag = post_soup.find('div', class_='separator').find('img')
        return img_tag['src']
    except Exception:
        return "Error fetching image"

# --- Streamlit UI ---

st.set_page_config(page_title="Irasutoya Teacher Tool", page_icon="🏫")
st.title("🏫 Chinese Lesson Image Finder")
st.markdown("""
1. Upload a CSV/Excel with your vocabulary list.
2. The app translates your words to Japanese.
3. It finds the matching **Irasutoya** links for your slides.
""")

uploaded_file = st.file_uploader("Upload Vocabulary List", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Which column has the Chinese words?", df.columns)
    
    if st.button("Generate Image Links"):
        results = []
        progress_text = st.empty()
        bar = st.progress(0)
        
        for i, word in enumerate(df[col]):
            # 1. Translate
            word_jp = translate_to_japanese(str(word))
            progress_text.text(f"Processing: {word} → {word_jp}")
            
            # 2. Search
            link = get_irasutoya_image(word_jp)
            results.append(link)
            
            # 3. Update Progress
            bar.progress((i + 1) / len(df))
            time.sleep(0.5) # Gentle on their servers
            
        df['Japanese_Keyword'] = [translate_to_japanese(str(w)) for w in df[col]]
        df['Irasutoya_Link'] = results
        
        st.success("All done!")
        st.dataframe(df[[col, 'Japanese_Keyword', 'Irasutoya_Link']])
        
        csv = df.to_csv(index=False).encode('utf-8-sig') # Use utf-8-sig for Chinese characters
        st.download_button("📥 Download Result", csv, "irasutoya_links.csv", "text/csv")
