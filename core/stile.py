"""
core/stile.py — v3, ispirato allo stile Apple: molto spazio bianco,
tipografia con gerarchia chiara, colore usato con parsimonia (solo per i
pulsanti di azione e gli avvisi, mai come decorazione). Un solo posto da
cui cambiare l'aspetto di tutta l'app.
"""

import streamlit as st

ACCENTO = "#4BA3F7"          # azzurro chiaro: bottoni e selezioni
ACCENTO_TESTO = "#0A66C2"     # blu leggibile per testi selezionati
GRIGIO_BTN = "#E6E7EB"
GRIGIO_BTN_HOVER = "#D9DBE1"
ACCENTO_SCURO = "#3593EC"
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
    border: 1px solid {ACCENTO} !important;
    color: #FFFFFF !important;
    white-space: nowrap;
}}
.stButton > button:hover, .stButton > button:focus, .stButton > button:focus-visible,
.stButton > button:active {{
    background-color: {ACCENTO_SCURO} !important;
    border-color: {ACCENTO_SCURO} !important;
    color: #FFFFFF !important;
    box-shadow: none !important;
    outline: none !important;
}}
.stButton > button p {{ color: #FFFFFF !important; }}

/* Pulsanti «secondari»: Rimuovi… e Ricomincia da capo — grigio chiaro, così «Avanti» invita di più */
[class*="rimuovi"] .stButton > button, [class*="_rm"] .stButton > button, [class*="st-key-rm_"] .stButton > button,
[class*="st-key-reset"] .stButton > button {{
    background-color: {GRIGIO_BTN} !important;
    border-color: {GRIGIO_BTN} !important;
    color: #3C3C43 !important;
}}
[class*="rimuovi"] .stButton > button:hover, [class*="_rm"] .stButton > button:hover,
[class*="st-key-rm_"] .stButton > button:hover, [class*="st-key-reset"] .stButton > button:hover,
[class*="rimuovi"] .stButton > button:active, [class*="_rm"] .stButton > button:active,
[class*="st-key-reset"] .stButton > button:active {{
    background-color: {GRIGIO_BTN_HOVER} !important;
    border-color: {GRIGIO_BTN_HOVER} !important;
    color: #1D1D1F !important;
}}
[class*="rimuovi"] .stButton > button p, [class*="_rm"] .stButton > button p,
[class*="st-key-rm_"] .stButton > button p, [class*="st-key-reset"] .stButton > button p {{ color: #3C3C43 !important; }}

/* Selezioni (menu a tendina, tag, spunte, opzioni): blu invece del rosso predefinito */
[data-baseweb="tag"] {{ background-color: {ACCENTO} !important; color: #FFFFFF !important; }}
[data-baseweb="tag"] span, [data-baseweb="tag"] svg {{ color: #FFFFFF !important; fill: #FFFFFF !important; }}
[data-baseweb="menu"] li[aria-selected="true"], [data-baseweb="menu"] li[aria-selected="true"] * {{
    color: {ACCENTO_TESTO} !important; font-weight: 600;
}}
[data-baseweb="menu"] li:hover, [data-baseweb="menu"] li[data-highlighted="true"] {{
    background-color: #E8F3FF !important;
}}
[data-baseweb="menu"] li:hover *, [data-baseweb="menu"] li[data-highlighted="true"] * {{ color: {ACCENTO_TESTO} !important; }}
[data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"] > div,
[data-baseweb="checkbox"] span[aria-checked="true"], label[data-baseweb="checkbox"] > span:first-child {{
    background-color: {ACCENTO} !important; border-color: {ACCENTO} !important;
}}
[data-baseweb="radio"] div[role="radio"][aria-checked="true"] > div {{ background-color: {ACCENTO} !important; border-color: {ACCENTO} !important; }}
input:focus, textarea:focus, [data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within > div,
[data-baseweb="textarea"]:focus-within {{ border-color: {ACCENTO} !important; box-shadow: 0 0 0 1px {ACCENTO} !important; }}
a, a:hover {{ color: {ACCENTO_TESTO} !important; }}

/* Barra fissa in basso: «Ricomincia da capo» a sinistra e impostazioni (ingranaggio) a destra */
.st-key-barra_fissa {{
    position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
    width: min(736px, 100%); z-index: 999;
    background: {SFONDO_PAGINA}; border-top: 1px solid {BORDO};
    padding: 0.6rem 1rem 0.7rem 1rem;
}}
.st-key-barra_fissa [data-testid="stHorizontalBlock"] {{ align-items: center; }}
[data-testid="stMainBlockContainer"], .block-container {{ padding-bottom: 6rem !important; }}

/* Valori principali del riepilogo: più piccoli e su più righe, mai troncati */
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div {{
    font-size: 1.55rem !important; white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {{ white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }}

/* Popover ("Impostazioni avanzate"): stessa impostazione dei bottoni */
[data-testid="stPopover"] > div > button {{
    background-color: {GRIGIO_BTN} !important;
    border: 1px solid {GRIGIO_BTN} !important;
    color: #3C3C43 !important;
    min-width: 2.6rem;
}}
[data-testid="stPopover"] > div > button:hover, [data-testid="stPopover"] > div > button:focus,
[data-testid="stPopover"] > div > button:active {{
    background-color: {GRIGIO_BTN_HOVER} !important;
    border-color: {GRIGIO_BTN_HOVER} !important;
    color: #1D1D1F !important;
}}
[data-testid="stPopover"] > div > button svg:last-child {{ display: none; }}

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
