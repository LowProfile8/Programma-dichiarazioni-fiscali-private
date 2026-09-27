"""
core/stile.py

Tutto lo stile visivo dell'app in un unico posto, richiamato una sola volta
da app.py. Deliberatamente leggero sui trucchi CSS via data-testid (fragili,
si rompono ad ogni aggiornamento di Streamlit): qui usiamo soprattutto il
tema nativo (.streamlit/config.toml) più un piccolo strato di CSS mirato
solo dove il tema nativo non arriva (font per i titoli, intestazione,
bordo dei container).

Se in futuro serve modificare i colori, il posto giusto è PRIMA
.streamlit/config.toml (cambia tutta l'app in automatico), e solo se non
basta, questo file.
"""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Titoli in nero/antracite, non blu: il blu navy resta solo su bottoni,
   bordi e accenti — usarlo anche per il testo dei titoli riduceva il
   contrasto percepito (blu scuro su sfondo chiaro "sembra" meno leggibile
   del nero pieno, anche a parità di contrasto tecnico). */
h1, h2, h3 {
    font-family: 'Source Serif 4', Georgia, serif !important;
    font-weight: 600 !important;
    color: #15181D !important;
    letter-spacing: -0.01em;
}

/* Intestazione istituzionale in cima alla pagina */
.intestazione-studio {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    border-bottom: 2px solid #A98A4B;
    padding-bottom: 0.6rem;
    margin-bottom: 1.4rem;
}
.intestazione-studio .nome-studio {
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: #15181D;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.intestazione-studio .sottotitolo {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: #6B7280;
}

/* Contenitori (st.container(border=True)) più "a scheda", meno arrotondati */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 4px !important;
    border-color: #D9DCE1 !important;
}

/* Pulsanti: squadrati e istituzionali, non troppo arrotondati */
.stButton > button {
    border-radius: 3px;
    font-weight: 500;
}
.stButton > button[kind="primary"] {
    background-color: #16305C;
    border-color: #16305C;
}
.stButton > button[kind="primary"]:hover {
    background-color: #0F2242;
    border-color: #0F2242;
}

/* Barra di avanzamento con l'accento oro invece del blu default */
div[data-testid="stProgress"] > div > div > div {
    background-color: #A98A4B !important;
}
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
