import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import streamlit as st

def inspect_page_structure(keyword):
    url = f"https://www.irasutoya.com/search?q={quote(keyword)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Let's see what the divs actually look like
    st.subheader(f"Analyzing results for: {keyword}")
    
    # Find all divs that contain images
    # We will print the class names of the first 10 divs that contain an image
    count = 0
    for div in soup.find_all('div'):
        if div.find('img'):
            st.write(f"Found image in div with class: {div.get('class')}")
            count += 1
            if count >= 10: break

st.title("Class Name Inspector")
query = st.text_input("Enter a test term (e.g. 猫):")
if st.button("Inspect"):
    inspect_page_structure(query)
