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
BORDO_CAMPO = "#DADDE3"       # bordo sottile e chiaro delle caselle e dei menu
SFONDO_SELEZIONE = "#E4F1FE"  # riga selezionata nei menu a tendina (azzurro molto chiaro)
SFONDO_HOVER = "#F2F8FE"
SFONDO_CARD = "#FFFFFF"
SFONDO_PAGINA = "#FBFBFD"
SIDEBAR_SFONDO = "#0D2140"    # blu scuro, come nella grafica di riferimento
SIDEBAR_ATTIVO = "#2862B4"
SIDEBAR_TESTO = "#C7D2E6"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background-color: {SFONDO_PAGINA} !important;
}}
/* La barra laterale è un overlay: si apre SOPRA la pagina invece di spingere
   di lato la parte centrale, che così resta ferma */
[data-testid="stSidebar"] {{
    background-color: {SIDEBAR_SFONDO} !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    height: 100vh !important;
    z-index: 999999 !important;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.25);
}}
/* La sidebar è "fixed" (tolta dal flusso normale), ma Streamlit continua a riservarle spazio e a
   spostare il contenuto principale quando si apre: costringiamo il contenuto a restare sempre alla
   stessa posizione, qualunque sia lo stato della barra laterale. */
[data-testid="stAppViewContainer"] {{
    margin-left: 0 !important; padding-left: 0 !important; transform: none !important;
}}
section[data-testid="stMain"], div[data-testid="stMain"], .main {{
    margin-left: 0 !important; padding-left: 0 !important; left: 0 !important;
    transform: none !important; width: 100% !important; position: relative !important;
}}
[data-testid="stSidebarCollapsedControl"] {{ z-index: 1000000 !important; }}

[data-testid="stSidebar"] * {{
    color: {SIDEBAR_TESTO} !important;
    text-align: left !important;
}}
[data-testid="stSidebar"] h3 {{ color: #FFFFFF !important; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12) !important; }}
/* Rinforzo: testo, didascalie e markdown restano bianchi/chiari e allineati a sinistra
   anche quando Streamlit applica le sue regole più specifiche */
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] div, [data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    color: {SIDEBAR_TESTO} !important;
    text-align: left !important;
}}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
    color: #8FA3C4 !important;   /* le etichette di sezione (DICHIARAZIONE FISCALE, ecc.) restano un filo più tenui */
    font-weight: 700 !important;
    letter-spacing: 0.04em;
    text-align: left !important;
}}
[data-testid="stSidebar"] .stLogo, [data-testid="stSidebar"] img {{
    display: block !important; margin-left: 0 !important;
}}
/* I pulsanti-voce del menu: il testo deve partire da sinistra. I pulsanti di Streamlit centrano
   il contenuto con un flex container interno: "text-align" da solo non basta, serve forzare
   "justify-content" su OGNI livello (button, e i suoi div/span interni). */
[data-testid="stSidebar"] .stButton > button {{
    background-color: transparent !important; border: none !important; color: {SIDEBAR_TESTO} !important;
    font-weight: 500 !important; padding: 0.5rem 0.7rem !important; border-radius: 8px !important;
    display: flex !important; justify-content: flex-start !important; text-align: left !important;
}}
[data-testid="stSidebar"] .stButton > button > div,
[data-testid="stSidebar"] .stButton > button [data-testid="stMarkdownContainer"] {{
    display: flex !important; justify-content: flex-start !important; width: 100% !important;
    text-align: left !important;
}}
[data-testid="stSidebar"] .stButton > button p {{
    color: {SIDEBAR_TESTO} !important; text-align: left !important; width: 100%;
}}
[data-testid="stSidebar"] .stButton > button:hover {{ background-color: rgba(255,255,255,0.08) !important; }}
[data-testid="stSidebar"] .stButton > button:hover p {{ color: #FFFFFF !important; }}
/* voce attiva (programma in cui ci si trova adesso): pillola blu piena, come nella grafica */
[data-testid="stSidebar"] .st-key-side_attivo .stButton > button {{
    background-color: {SIDEBAR_ATTIVO} !important;
}}
[data-testid="stSidebar"] .st-key-side_attivo .stButton > button p {{ color: #FFFFFF !important; font-weight: 600 !important; }}
[data-testid="stSidebar"] [data-testid="stExpander"] {{ border-color: rgba(255,255,255,0.15) !important; }}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {{ color: {SIDEBAR_TESTO} !important; }}
[data-testid="stSidebar"] input {{ color: {TESTO} !important; }}

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
[data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"] > div,
[data-baseweb="checkbox"] span[aria-checked="true"], label[data-baseweb="checkbox"] > span:first-child {{
    background-color: {ACCENTO} !important; border-color: {ACCENTO} !important;
}}
[data-baseweb="radio"] div[role="radio"][aria-checked="true"] > div {{ background-color: {ACCENTO} !important; border-color: {ACCENTO} !important; }}
a, a:hover {{ color: {ACCENTO_TESTO} !important; }}

/* Barra fissa in basso: «Ricomincia da capo» a sinistra e impostazioni (ingranaggio) a destra */
.st-key-barra_fissa {{
    padding: 0.4rem 0 0.2rem 0;
}}
.st-key-barra_fissa [data-testid="stHorizontalBlock"] {{ align-items: center; }}
/* Indietro/Avanti/Ricomincia/Salva: testo sempre leggibile, mai troncato in puntini */
.st-key-barra_fissa .stButton > button {{
    white-space: nowrap !important; overflow: visible !important; text-overflow: unset !important;
    padding: 0.5rem 0.8rem !important; font-size: 0.88rem !important; width: 100% !important;
    min-width: 0 !important;
}}
.st-key-barra_fissa .stButton > button p {{
    white-space: nowrap !important; overflow: visible !important; text-overflow: unset !important;
    font-size: 0.88rem !important;
}}
/* Ricomincia: grigio. Salva progetto: verde chiaro. Diversi dal blu di "Avanti" */
.st-key-reset_tutto .stButton > button {{
    background-color: {GRIGIO_BTN} !important; border-color: {GRIGIO_BTN} !important; color: #3C3C43 !important;
}}
.st-key-reset_tutto .stButton > button:hover {{ background-color: {GRIGIO_BTN_HOVER} !important; border-color: {GRIGIO_BTN_HOVER} !important; }}
.st-key-salva_progetto .stButton > button {{
    background-color: #DFF5E3 !important; border-color: #BCE8C4 !important; color: #1E5E2E !important;
}}
.st-key-salva_progetto .stButton > button p {{ color: #1E5E2E !important; }}
.st-key-salva_progetto .stButton > button:hover {{ background-color: #CDEED3 !important; border-color: #A9DFB3 !important; }}

/* Piè di pagina fisso in fondo allo schermo: logo e avvertenza, al posto della vecchia barra tasti */
.st-key-piede_fisso {{
    position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
    width: min(736px, 100%); z-index: 998;
    background: {SFONDO_PAGINA}; border-top: 1px solid {BORDO};
    padding: 0.5rem 1rem 0.6rem 1rem;
}}
.st-key-piede_fisso [data-testid="stHorizontalBlock"] {{ align-items: center; }}
[data-testid="stMainBlockContainer"], .block-container {{ padding-bottom: 6.5rem !important; }}

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

/* ── Caselle di inserimento: sfondo bianco e UN SOLO bordo sottile e chiaro ── */
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {{
    background-color: #FFFFFF !important;
    border: 1px solid {BORDO_CAMPO} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    outline: none !important;
    color: {TESTO} !important;
}}
div[data-baseweb="base-input"] {{
    background-color: transparent !important; border: none !important; box-shadow: none !important; outline: none !important;
}}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
    background-color: transparent !important; color: {TESTO} !important;
    border: none !important; box-shadow: none !important; outline: none !important;
}}
.stTextInput input::placeholder, .stNumberInput input::placeholder, .stTextArea textarea::placeholder {{
    color: {TESTO_SECONDARIO} !important; opacity: 0.7;
}}
div[data-baseweb="input"]:hover, div[data-baseweb="textarea"]:hover, div[data-baseweb="select"]:hover > div {{
    border-color: #C4C9D1 !important;
}}
div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within,
div[data-baseweb="select"]:focus-within > div {{
    border-color: {ACCENTO} !important;
    box-shadow: 0 0 0 3px rgba(75, 163, 247, 0.16) !important;
}}
div[data-baseweb="select"] span, div[data-baseweb="select"] div {{ color: {TESTO} !important; }}
div[data-baseweb="select"] svg {{ fill: {TESTO_SECONDARIO} !important; }}
.stNumberInput button {{ background-color: transparent !important; color: {TESTO_SECONDARIO} !important; border: none !important; }}
.stNumberInput button:hover {{ background-color: {SFONDO_HOVER} !important; color: {ACCENTO_TESTO} !important; }}

/* ── Menu a tendina (si apre in un livello a parte della pagina): bianco, selezione azzurra ── */
[data-baseweb="popover"] > div, [data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] ul, [data-baseweb="popover"] [role="listbox"] {{
    background-color: #FFFFFF !important; color: {TESTO} !important;
}}
[data-baseweb="popover"] > div {{
    border: 1px solid {BORDO_CAMPO} !important; border-radius: 12px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.10) !important; overflow: hidden;
}}
li[role="option"], [data-baseweb="menu"] li {{
    background-color: #FFFFFF !important; color: {TESTO} !important;
}}
li[role="option"] div, li[role="option"] span, [data-baseweb="menu"] li div, [data-baseweb="menu"] li span {{
    background-color: transparent !important; color: inherit !important;
}}
li[role="option"]:hover, li[role="option"][data-highlighted="true"], [data-baseweb="menu"] li:hover {{
    background-color: {SFONDO_HOVER} !important; color: {ACCENTO_TESTO} !important;
}}
li[role="option"][aria-selected="true"], [data-baseweb="menu"] li[aria-selected="true"] {{
    background-color: {SFONDO_SELEZIONE} !important; color: {ACCENTO_TESTO} !important; font-weight: 600;
}}
/* calendario del campo data */
[data-baseweb="calendar"], [data-baseweb="calendar"] div {{ background-color: #FFFFFF; color: {TESTO}; }}
[data-baseweb="calendar"] [aria-selected="true"], [data-baseweb="calendar"] [aria-selected="true"] div {{
    background-color: {ACCENTO} !important; color: #FFFFFF !important;
}}
[data-testid="stPopoverBody"] {{ background-color: #FFFFFF !important; }}
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

/* Homepage: la card della Dichiarazione fiscale è più grande ed evidenziata,
   così è la scelta più spontanea fra le quattro */
.st-key-home_df_card h3 {{ font-size: 1.5rem !important; margin-top: 0; }}
.st-key-home_df .stButton > button, .st-key-home_df_card .stButton > button {{
    font-size: 1.05rem !important; padding: 0.7rem 1.4rem !important;
}}
.hero-etichetta {{
    display: inline-block; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em;
    color: {ACCENTO_TESTO}; background: #FFFFFF; border-radius: 6px; padding: 2px 8px; margin-bottom: 6px;
}}
.tile-icona {{
    width: 52px; height: 52px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; margin-bottom: 8px;
}}
.tile-icona-verde {{ background: #DCFCE7; }}
.tile-icona-blu {{ background: #DBEAFE; }}
.tile-icona-viola {{ background: #F3E8FF; }}
.st-key-home_stats_card [data-testid="stMetricValue"] {{ font-size: 1.9rem !important; }}

/* Pulsante circolare "→" delle card della home, invece di un tasto rettangolare col testo */
.tasto-freccia .stButton > button {{
    width: 38px !important; height: 38px !important; border-radius: 50% !important;
    padding: 0 !important; font-size: 1.05rem !important; line-height: 1 !important;
    background-color: {ACCENTO} !important; border-color: {ACCENTO} !important;
}}

/* Fascia grande in alto per la dichiarazione fiscale (hero), come nella grafica di riferimento */
.st-key-home_df_card, .st-key-home_df_card [data-testid="stVerticalBlockBorderWrapper"] {{
    background: linear-gradient(135deg, #EAF3FF 0%, #F7FBFF 60%, #FFFFFF 100%) !important;
    border: 1px solid {ACCENTO} !important; border-radius: 18px !important; padding: 0.6rem 0.4rem !important;
}}
/* ══════════════════════════════════════════════════════════════════════
   SCHERMATA DI ACCESSO — blocco messo per ultimo apposta, così le sue regole
   vincono sempre sulle regole generali di sfondo bianco/testo scuro definite
   più sopra (a parità di "!important" vince chi arriva dopo nel foglio di
   stile). Un marcatore invisibile (.accesso-marcatore) dice al CSS "siamo
   nella schermata di accesso": da lì ricoloriamo sfondo e testo con :has(),
   senza toccare le altre pagine. Centrata con le colonne native di
   Streamlit, non con "position: fixed" (si era rivelato inaffidabile).
   ══════════════════════════════════════════════════════════════════════ */
body:has(.accesso-marcatore) [data-testid="stAppViewContainer"],
body:has(.accesso-marcatore) [data-testid="stMain"],
body:has(.accesso-marcatore) [data-testid="stHeader"],
body:has(.accesso-marcatore) .block-container {{
    background-color: {SIDEBAR_SFONDO} !important;
}}
body:has(.accesso-marcatore) [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
body:has(.accesso-marcatore) .block-container {{ padding-top: 18vh !important; }}
body:has(.accesso-marcatore) [data-testid="stHorizontalBlock"] {{ align-items: end !important; }}

/* Tutte le scritte di questa pagina: bianche (vince sulla regola generale h1/h2/h3/p color:TESTO) */
body:has(.accesso-marcatore) .accesso-titolo,
body:has(.accesso-marcatore) [data-testid="stMarkdownContainer"] .accesso-titolo {{
    color: #FFFFFF !important; font-weight: 700 !important; font-size: 1rem !important;
    margin: 0 0 0.35rem 0 !important; text-align: left !important;
}}
body:has(.accesso-marcatore) .accesso-errore,
body:has(.accesso-marcatore) [data-testid="stMarkdownContainer"] .accesso-errore {{
    color: #FFD9D9 !important; font-size: 0.85rem !important; margin-top: 0.6rem !important; text-align: left !important;
}}

/* La casella: il tentativo di renderla azzurra non ha retto in modo affidabile (Chrome, sui
   campi password, ripristina il proprio sfondo). Soluzione più semplice: la lasciamo chiara e
   scriviamo il testo in nero, così si legge comunque qualunque sia lo sfondo mostrato. */
body:has(.accesso-marcatore) .stTextInput input,
body:has(.accesso-marcatore) div[data-baseweb="input"] input,
body:has(.accesso-marcatore) div[data-baseweb="base-input"] input {{
    color: #000000 !important; -webkit-text-fill-color: #000000 !important; caret-color: #000000 !important;
}}
/* Il tasto "→": un azzurro diverso (più scuro) da quello della casella, così si riconosce come tasto */
body:has(.accesso-marcatore) .stButton > button {{
    background-color: {ACCENTO_SCURO} !important; border: none !important;
    color: #FFFFFF !important; font-weight: 700 !important; font-size: 1.05rem !important;
    padding: 0.5rem 0 !important; width: 100% !important;
}}
body:has(.accesso-marcatore) .stButton > button:hover {{ background-color: #2678CE !important; }}
body:has(.accesso-marcatore) .stButton > button p {{ color: #FFFFFF !important; }}

/* Tasto "Altri preventivi →" accanto a Home: allineato a destra, stessa altezza di Home
   (niente wrapper markdown che sfalsi l'allineamento verticale), arancione con testo bianco. */
.st-key-tasto_altri_preventivi .stButton {{ display: flex; justify-content: flex-end; }}
.st-key-tasto_altri_preventivi .stButton > button {{
    background-color: #F97316 !important; border-color: #F97316 !important; color: #FFFFFF !important;
}}
.st-key-tasto_altri_preventivi .stButton > button p {{ color: #FFFFFF !important; }}
.st-key-tasto_altri_preventivi .stButton > button:hover {{ background-color: #EA6A0C !important; border-color: #EA6A0C !important; }}

/* Pagina di scelta del tipo di preventivo: tre card con bordo colorato */
.st-key-tipo_prev_dfpf_card {{ border: 2px solid #9333EA !important; border-radius: 12px !important; }}
.st-key-tipo_prev_azienda_card {{ border: 2px solid #2563EB !important; border-radius: 12px !important; }}
.st-key-tipo_prev_altro_card {{ border: 2px solid #F97316 !important; border-radius: 12px !important; }}

/* Stato Supabase: angolo in basso a sinistra, fissato allo schermo (non dentro il normale
   flusso della barra laterale, che potrebbe essere più corta del contenuto sopra di essa). */
.st-key-stato_cloud_fisso {{
    position: fixed !important;
    bottom: 14px !important;
    left: 18px !important;
    z-index: 1000000 !important;
    max-width: 230px;
}}
.st-key-stato_cloud_fisso [data-testid="stCaptionContainer"] p {{
    color: #C7D2E6 !important; font-size: 0.68rem !important;
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
