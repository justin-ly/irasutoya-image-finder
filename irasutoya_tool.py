import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time

def debug_scrape(keyword):
    """
    Diagnostic function to see what the server is actually sending back.
    """
    url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        st.write(f"DEBUG: Status Code for '{keyword}': {response.status_code}")
        
        # Show first 500 chars of HTML to see if we got the page
        st.code(response.text[:500], language='html')
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try finding ANY image in the body to see if the structure changed
        all_imgs = soup.find_all('img')
        st.write(f"DEBUG: Found {len(all_imgs)} images on the entire page.")
        
        # Look for potential image containers (if 'boxim' failed)
        # Often these are in 'div' tags with specific classes
        divs = soup.find_all('div')
        st.write(f"DEBUG: Found {len(divs)} divs. First 5 classes: {[d.get('class') for d in divs[:5]]}")
        
        return []
    except Exception as e:
        st.error(f"Error: {e}")
        return []

# --- Minimal UI to test ---
st.title("Debugger")
query = st.text_input("Enter a test term:")
if st.button("Run Diagnostic"):
    debug_scrape(query)
