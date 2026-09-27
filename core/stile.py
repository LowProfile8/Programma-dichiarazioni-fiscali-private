"""
core/stile.py — stile visivo dell'app, v2: "fiduciaria tech moderna".

Cambiato rispetto alla prima versione: via il font serif e l'oro (troppo
"studio legale anni '90"), dentro un look pulito da prodotto SaaS moderno —
sfondo quasi bianco, testo scuro, un solo accento vivo (blu indaco),
schede con ombra leggera invece di solo bordo, angoli arrotondati.
"""

import streamlit as st

ACCENTO = "#2451E0"
ACCENTO_SCURO = "#1B3EB3"
TESTO = "#14161A"
TESTO_SECONDARIO = "#5B6472"
BORDO = "#E6E8EC"
SFONDO_CARD = "#FFFFFF"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, sans-serif;
}}

h1, h2, h3 {{
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    color: {TESTO} !important;
    letter-spacing: -0.02em;
}}

.intestazione-studio {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.9rem 0 1.1rem 0;
    margin-bottom: 1.6rem;
    border-bottom: 1px solid {BORDO};
}}
.intestazione-studio .nome-studio {{
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    font-weight: 800;
    color: {TESTO};
    letter-spacing: -0.01em;
}}
.intestazione-studio .sottotitolo {{
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: {TESTO_SECONDARIO};
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 12px !important;
    border: 1px solid {BORDO} !important;
    box-shadow: 0 1px 3px rgba(20, 22, 26, 0.04), 0 1px 2px rgba(20, 22, 26, 0.03);
    background-color: {SFONDO_CARD};
}}

.stButton > button {{
    border-radius: 8px;
    font-weight: 600;
    border-color: {BORDO};
}}
.stButton > button[kind="primary"] {{
    background-color: {ACCENTO};
    border-color: {ACCENTO};
}}
.stButton > button[kind="primary"]:hover {{
    background-color: {ACCENTO_SCURO};
    border-color: {ACCENTO_SCURO};
}}

div[data-testid="stProgress"] > div > div > div {{
    background-color: {ACCENTO} !important;
    border-radius: 6px;
}}
div[data-testid="stProgress"] > div > div {{
    border-radius: 6px;
    background-color: {BORDO} !important;
}}

.stTextInput input, .stNumberInput input, div[data-baseweb="select"] > div {{
    border-radius: 8px !important;
}}

[data-testid="stFileUploaderDropzone"] {{
    border-radius: 10px;
    background-color: {SFONDO_CARD};
}}
</style>
"""


def applica_stile() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def intestazione(nome_studio: str, sottotitolo: str) -> None:
    st.markdown(
        f"""
        <div class="intestazione-studio">
            <span class="nome-studio">{nome_studio}</span>
            <span class="sottotitolo">{sottotitolo}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
