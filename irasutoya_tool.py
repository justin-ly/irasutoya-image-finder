import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator
from textblob import TextBlob
import time

# --- Helper Functions ---

def translate_to_japanese(text):
    try:
        return GoogleTranslator(source='auto', target='ja').translate(text)
    except:
        return text

def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except:
        return text

def get_sentiment(word):
    en_word = translate_to_english(word)
    analysis = TextBlob(en_word)
    if analysis.sentiment.polarity > 0.1: return "Positive"
    elif analysis.sentiment.polarity < -0.1: return "Negative"
    else: return "Neutral"

def get_top_3_images(keyword_jp):
    """Scrapes up to 3 direct PNG links from Irasutoya search results."""
    try:
        search_url = f"https://www.irasutoya.com/search?q={quote(keyword_jp)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        posts = soup.find_all('div', class_='boxim')
        links = []
        
        for post in posts[:3]: # Limit to top 3
            try:
                post_link = post.find('a')['href']
                post_res = requests.get(post_link, headers=headers, timeout=5)
                post_soup = BeautifulSoup(post_res.text, 'html.parser')
                img_tag = post_soup.find('div', class_='separator').find('img')
                links.append(img_tag['src'])
            except:
                links.append("N/A")
        
        # Pad with N/A if fewer than 3 found
        while len(links) < 3:
            links.append("N/A")
            
        return links
    except Exception:
        return ["Error", "Error", "Error"]

# --- Streamlit UI ---

st.set_page_config(page_title="Irasutoya Bulk Pro", page_icon="🎨")
st.title("🎨 Irasutoya Bulk Image Finder (Pro Edition)")

uploaded_file = st.file_uploader("Upload your Vocabulary List (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    col = st.selectbox("Which column has your vocabulary?", df.columns)
    
    if st.button("Generate Pro Search"):
        results = []
        sentiments = []
        
        progress_bar = st.progress(0)
        
        for i, word in enumerate(df[col]):
            # 1. Analyze Sentiment
            sent = get_sentiment(str(word))
            sentiments.append(sent)
            
            # 2. Translate and Search
            word_jp = translate_to_japanese(str(word))
            links = get_top_3_images(word_jp)
            results.append(links)
            
            progress_bar.progress((i + 1) / len(df))
            time.sleep(0.5) 
            
        # Build new DataFrame
        output_df = pd.DataFrame(results, columns=['Link 1', 'Link 2', 'Link 3'])
        output_df.insert(0, col, df[col])
        output_df.insert(1, 'Sentiment', sentiments)
        
        st.success("Search complete!")
        st.dataframe(output_df)
        
        csv = output_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download Results", csv, "irasutoya_pro_results.csv", "text/csv")
