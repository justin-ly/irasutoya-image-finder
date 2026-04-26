import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from deep_translator import GoogleTranslator
import time
import nltk
from nltk.corpus import wordnet

# Ensure required NLTK data is downloaded
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# --- Helper Functions ---

def get_synonyms(word):
    """Automatically generates English synonyms using NLTK."""
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace('_', ' '))
    return list(synonyms)

def get_candidates(keyword_jp):
    """Fetches up to 5 candidates."""
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

def search_dynamic(word):
    """Tries the word, then automatically tries English synonyms."""
    # 1. Primary Attempt
    jp_word = GoogleTranslator(source='auto', target='ja').translate(word)
    results = get_candidates(jp_word)
    if results: return results, jp_word
    
    # 2. Dynamic Fallback: Try Synonyms
    en_word = GoogleTranslator(source='auto', target='en').translate(word)
    synonyms = get_synonyms(en_word)
    
    for syn in synonyms[:5]: # Try first 5 synonyms
        syn_jp = GoogleTranslator(source='en', target='ja').translate(syn)
        results = get_candidates(syn_jp)
        if results: return results, syn_jp
        
    return [], jp_word

# --- Streamlit UI ---
st.set_page_config(page_title="Irasutoya Dynamic Selector", layout="wide")
st.title("🎨 Irasutoya Dynamic Selector")

# ... [Keep your existing UI logic here] ...
# Replace the old search call with:
# results, used_term = search_dynamic(current_word)
