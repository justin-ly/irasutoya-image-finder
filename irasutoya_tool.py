import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator
import time

# --- Helper Functions ---

def translate_to_japanese(text):
    try:
        # We append 'イラスト' to force illustration results
        return GoogleTranslator(source='auto', target='ja').translate(text) + " イラスト"
    except:
        return text

def calculate_relevance(keyword, title):
    """Simple logic to score relevance by word overlap."""
    keyword_set = set(keyword.lower().split())
    title_set = set(title.lower().split())
    intersection = keyword_set.intersection(title_set)
    return len(intersection) / len(keyword_set) if len(keyword_set) > 0 else 0

def get_best_images(keyword_jp, original_keyword):
    """Fetches top 10, then ranks them by relevance logic."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        posts = soup.find_all('div', class_='boxim')
        results = []
        
        # Look at the top 10, not just top 3
        for post in posts[:10]:
            try:
                title = post.get_text(strip=True)
                post_link = post.find('a')['href']
                
                # Fetch the image
                post_res = requests.get(post_link, headers=headers, timeout=5)
                post_soup = BeautifulSoup(post_res.text, 'html.parser')
                img_tag = post_soup.find('div', class_='separator').find('img')
                img_url = img_tag['src'] if img_tag else "N/A"
                
                # Logic: Score the relevance
                score = calculate_relevance(original_keyword, title)
                results.append({"title": title, "url": img_url, "score": score})
            except:
                continue
        
        # Rank by score (high to low)
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:3] # Return top 3 ranked
    except:
        return []

# --- Streamlit UI ---

st.set_page_config(page_title="Irasutoya Logic-Based Finder", page_icon="🎯")
st.title("🎯 Irasutoya Pro: Logic-Based Search")

uploaded_file = st.file_uploader("Upload Vocabulary List (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Which column has your vocabulary?", df.columns)
    
    if st.button("Generate Logic-Optimized Search"):
        data = []
        progress_bar = st.progress(0)
        
        for i, word in enumerate(df[col]):
            # Translate & add 'Illustration' context
            word_jp = translate_to_japanese(str(word))
            
            # Logic Search
            ranked_results = get_best_images(word_jp, str(word))
            
            # Formatting for table
            row = [word]
            for res in ranked_results:
                row.append(res['url'])
            
            # Fill empty if < 3
            while len(row) < 4:
                row.append("No match found")
            
            data.append(row)
            progress_bar.progress((i + 1) / len(df))
            time.sleep(0.5) 
            
        final_df = pd.DataFrame(data, columns=[col, 'Link 1 (Best Match)', 'Link 2', 'Link 3'])
        st.success("Search complete using relevance logic!")
        st.dataframe(final_df)
        
        csv = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download Results", csv, "irasutoya_logic_results.csv", "text/csv")
