"""
core/ui_helpers.py

Due componenti riusabili in OGNI modulo del wizard, così le due decisioni
UX di oggi (fallback anno precedente, foto di esempio per gli allegati)
si scrivono una volta sola e si applicano ovunque, invece di essere
reinventate modulo per modulo.
"""

from pathlib import Path

import streamlit as st

from core.anno_precedente import cerca_valore_anno_precedente
from core.models import CampoValore

CARTELLA_ESEMPI = Path(__file__).parent.parent / "assets" / "esempi_documenti"


def campo_con_fallback(
    campo: CampoValore,
    etichetta: str,
    key: str,
    descrizione_ricerca: str | None = None,
    aiuto: str | None = None,
) -> None:
    """Disegna un text_input per un CampoValore, con un pulsante opzionale
    'Non lo so, guarda l'anno scorso' se è stata caricata una dichiarazione
    precedente in sessione. Aggiorna 'campo' in place.

    descrizione_ricerca: frase in linguaggio naturale usata per cercare il
        valore nel PDF dell'anno scorso (es. "saldo al 31.12 del conto
        corrente UBS"). Se omessa, usa 'etichetta'.
    """
    pdf_anno_precedente = st.session_state.get("pdf_anno_precedente_bytes")
    api_key = st.session_state.get("anthropic_api_key", "")

    col_input, col_fallback = st.columns([4, 1]) if pdf_anno_precedente else (st.container(), None)

    with col_input:
        valore_attuale = campo.valore or ""
        nuovo_valore = st.text_input(etichetta, value=valore_attuale, key=key, help=aiuto)
        if nuovo_valore != valore_attuale:
            campo.valore = nuovo_valore
            campo.origine = "utente"
            campo.nota = None

    if campo.da_rivedere:
        st.warning(
            f"⚠️ Valore dell'anno scorso — **da rivalutare**."
            + (f" _(trovato in: {campo.nota})_" if campo.nota else ""),
            icon="⚠️",
        )

    if pdf_anno_precedente and col_fallback is not None:
        with col_fallback:
            st.write("")  # allinea verticalmente col text_input
            if st.button("↩️ Anno scorso", key=f"fallback_{key}", help="Cerca questo valore nella dichiarazione dell'anno precedente"):
                if not api_key:
                    st.error("Serve la chiave API nella sidebar per cercare nel PDF dell'anno scorso.")
                else:
                    with st.spinner("Cerco nella dichiarazione dell'anno scorso..."):
                        risultato = cerca_valore_anno_precedente(
                            pdf_bytes=pdf_anno_precedente,
                            nome_file="dichiarazione_anno_precedente.pdf",
                            descrizione_campo=descrizione_ricerca or etichetta,
                            api_key=api_key,
                        )
                    if risultato.errore:
                        st.error(risultato.errore)
                    elif not risultato.trovato:
                        st.info("Non l'ho trovato nella dichiarazione dell'anno scorso.")
                    else:
                        campo.valore = risultato.valore
                        campo.origine = "anno_precedente"
                        campo.nota = risultato.contesto
                        st.rerun()


def mostra_esempio_documento(nome_file_esempio: str, didascalia: str = "Esempio del documento richiesto") -> None:
    """Mostra, subito sotto il pulsante di upload, un blocco color ambra
    (distinto dal blu usato per le azioni) con l'esempio del documento —
    così l'utente vede COSA cercare, non solo il nome scritto."""
    percorso = CARTELLA_ESEMPI / nome_file_esempio
    st.markdown(
        '<div class="blocco-esempio"><span class="etichetta">📎 Non sai quale documento allegare?</span></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Vedi un esempio"):
        if percorso.exists():
            st.image(str(percorso), caption=didascalia, use_container_width=True)
        else:
            st.caption("(Immagine di esempio non ancora disponibile per questo documento)")
