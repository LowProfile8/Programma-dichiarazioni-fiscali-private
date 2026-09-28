"""
core/stile.py — v3, ispirato allo stile Apple: molto spazio bianco,
tipografia con gerarchia chiara, colore usato con parsimonia (solo per i
pulsanti di azione e gli avvisi, mai come decorazione). Un solo posto da
cui cambiare l'aspetto di tutta l'app.
"""

import streamlit as st

ACCENTO = "#0A66FF"          # blu, SOLO per bottoni primari e link d'azione
ACCENTO_SCURO = "#0A4FC4"
ESEMPIO_ACCENTO = "#B8860B"  # ambra/oro caldo, solo per il blocco "esempio documento"
ESEMPIO_SFONDO = "#FFF9EC"
TESTO = "#1D1D1F"            # quasi nero, non nero puro — più morbido alla vista
TESTO_SECONDARIO = "#6E6E73"
BORDO = "#E5E5E7"
SFONDO_CARD = "#FFFFFF"
SFONDO_PAGINA = "#FBFBFD"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background-color: {SFONDO_PAGINA} !important;
}}
[data-testid="stSidebar"] {{
    background-color: {SFONDO_PAGINA} !important;
}}
[data-testid="stSidebar"] * {{
    color: {TESTO} !important;
}}

/* Titoli: gerarchia netta, mai blu — il colore resta solo per le azioni */
h1 {{
    font-weight: 800 !important;
    font-size: 2.4rem !important;
    color: {TESTO} !important;
    letter-spacing: -0.03em;
    margin-bottom: 0.3rem !important;
}}
h2 {{
    font-weight: 700 !important;
    font-size: 1.5rem !important;
    color: {TESTO} !important;
    letter-spacing: -0.02em;
    margin-top: 2.2rem !important;
}}
h3 {{
    font-weight: 600 !important;
    color: {TESTO} !important;
}}

/* Paragrafo introduttivo grande, stile "hero" Apple */
.testo-hero {{
    font-size: 1.15rem;
    line-height: 1.6;
    color: {TESTO_SECONDARIO};
    max-width: 640px;
    margin-bottom: 2.5rem;
}}

/* Intestazione dello studio: minimale, un rigo sottile */
.intestazione-studio {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.1rem 0 1.3rem 0;
    margin-bottom: 2.2rem;
    border-bottom: 1px solid {BORDO};
}}
.intestazione-studio .nome-studio {{
    font-size: 0.95rem;
    font-weight: 800;
    color: {TESTO};
    letter-spacing: -0.01em;
}}
.intestazione-studio .sottotitolo {{
    font-size: 0.8rem;
    color: {TESTO_SECONDARIO};
}}

/* Schede: molto spazio interno, ombra leggerissima, mai bordi pesanti */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 16px !important;
    border: 1px solid {BORDO} !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    background-color: {SFONDO_CARD};
    padding: 0.4rem;
}}

/* Pulsanti: arrotondati, blu solo se primary */
.stButton > button {{
    border-radius: 10px;
    font-weight: 600;
    padding: 0.5rem 1.3rem;
    background-color: {ACCENTO} !important;
    border-color: {ACCENTO} !important;
    color: #FFFFFF !important;
}}
.stButton > button:hover {{
    background-color: {ACCENTO_SCURO} !important;
    border-color: {ACCENTO_SCURO} !important;
    color: #FFFFFF !important;
}}
.stButton > button:focus:not(:active) {{
    color: #FFFFFF !important;
    background-color: {ACCENTO} !important;
}}

/* Popover ("Impostazioni avanzate"): stessa impostazione dei bottoni */
[data-testid="stPopover"] > div > button {{
    background-color: #FFFFFF !important;
    border: 1px solid {BORDO} !important;
    color: {TESTO} !important;
}}
[data-testid="stPopover"] > div > button:hover {{
    border-color: {ACCENTO} !important;
    color: {ACCENTO} !important;
}}

/* Campi di inserimento: SEMPRE sfondo chiaro e testo scuro, indipendentemente
   dal tema di base che Streamlit Cloud potrebbe applicare */
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea,
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div,
div[data-baseweb="textarea"], div[data-baseweb="base-input"] {{
    background-color: {SFONDO_CARD} !important;
    color: {TESTO} !important;
    border-color: {BORDO} !important;
}}
.stTextInput input::placeholder, .stNumberInput input::placeholder, .stTextArea textarea::placeholder {{
    color: {TESTO_SECONDARIO} !important;
}}
div[data-baseweb="select"] span, div[data-baseweb="select"] div {{
    color: {TESTO} !important;
}}
label, .stMarkdown, .stMarkdown p, .stMarkdown li, .stCaption, p, li {{
    color: {TESTO} !important;
}}
.stCheckbox label, .stRadio label {{
    color: {TESTO} !important;
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
    border-radius: 10px !important;
}}

[data-testid="stFileUploaderDropzone"] {{
    border-radius: 12px;
    background-color: {SFONDO_CARD};
}}

/* Blocco "esempio documento": un UNICO elemento cliccabile color ambra,
   distinto dal blu d'azione — l'expander stesso, non un box + expander */
.blocco-esempio {{
    margin-top: 0.6rem;
    margin-bottom: 1rem;
}}
.blocco-esempio [data-testid="stExpander"] {{
    background-color: {ESEMPIO_SFONDO} !important;
    border: 1px solid #F0DFAF !important;
    border-radius: 12px !important;
}}
.blocco-esempio [data-testid="stExpander"] summary {{
    color: {ESEMPIO_ACCENTO} !important;
    font-weight: 700 !important;
}}
.blocco-esempio [data-testid="stExpander"] summary p {{
    color: {ESEMPIO_ACCENTO} !important;
    font-weight: 700 !important;
}}

/* Box informativo (st.info) in blu tenue, coerente con l'accento */
div[data-testid="stAlertContainer"] {{
    border-radius: 12px;
}}

/* Nasconde la scritta "Press Enter to apply" (e simili) sotto i campi */
[data-testid="InputInstructions"], div[data-testid="InputInstructions"] {{
    display: none !important;
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


def testo_hero(testo: str) -> None:
    """Paragrafo introduttivo grande, in stile 'hero' — per i sottotitoli
    importanti (es. la frase di benvenuto)."""
    st.markdown(f'<p class="testo-hero">{testo}</p>', unsafe_allow_html=True)
