import streamlit as st
import fitz
import pandas as pd
import json
import requests
import google.generativeai as genai

# ==========================================
# CONFIGURAÇÃO DA API DO GEMINI (COM PROTEÇÃO)
# ==========================================
try:
    # Tenta carregar dos secrets do Streamlit
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = None

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        st.write(m.name)
