"""
core/ui_helpers.py

Due componenti riusabili in OGNI modulo del wizard, così le due decisioni
UX di oggi (fallback anno precedente, foto di esempio per gli allegati)
si scrivono una volta sola e si applicano ovunque, invece di essere
reinventate modulo per modulo.
"""

from pathlib import Path

import streamlit as st

from core.calcoli import ALIQUOTA_IMPOSTA_PREVENTIVA, numero
from core.models import CampoValore

CARTELLA_ESEMPI = Path(__file__).parent.parent / "assets" / "esempi_documenti"


def campo_con_fallback(
    campo: CampoValore,
    etichetta: str,
    key: str,
    descrizione_ricerca: str | None = None,   # non più usato (tolto il pulsante «Anno scorso»); resta per compatibilità
    aiuto: str | None = None,
) -> None:
    """Disegna un text_input per un CampoValore e aggiorna 'campo' in place.
    (Il nome resta per non toccare tutti i moduli: il pulsante «Anno scorso»
    è stato rimosso su richiesta.)"""
    valore_attuale = campo.valore or ""
    if key in st.session_state:
        nuovo_valore = st.text_input(etichetta, key=key, help=aiuto)
    else:
        nuovo_valore = st.text_input(etichetta, value=valore_attuale, key=key, help=aiuto)
    if nuovo_valore != valore_attuale:
        campo.valore = nuovo_valore
        campo.origine = "utente"
        campo.nota = None


def mostra_esempio_documento(nome_file_esempio: str, didascalia: str = "Esempio del documento richiesto") -> None:
    """Un UNICO elemento cliccabile (non due sovrapposti) — un expander con
    stile ambra, distinto dal blu usato per le azioni — che mostra
    l'esempio del documento così l'utente vede COSA cercare."""
    percorso = CARTELLA_ESEMPI / nome_file_esempio
    st.markdown('<div class="blocco-esempio">', unsafe_allow_html=True)
    with st.expander("📎 Non sai quale documento allegare? Vedi un esempio"):
        if percorso.exists():
            try:
                st.image(str(percorso), caption=didascalia, use_container_width=True)
            except Exception:
                st.image(str(percorso), caption=didascalia, width="stretch")
        else:
            st.caption("(Immagine di esempio non ancora disponibile per questo documento)")
    st.markdown('</div>', unsafe_allow_html=True)


def domanda_imposta_preventiva(pos, key: str) -> None:
    """Se sono stati inseriti interessi/redditi, chiede se sono soggetti a
    imposta preventiva (la risposta sta sull'attestato allegato): decide la
    colonna del Modulo 2 — A (soggetti) o B (non soggetti)."""
    if numero(pos.interessi_redditi) <= 0:
        pos.interessi_soggetti_ip = None
        return
    indice = None if pos.interessi_soggetti_ip is None else (0 if pos.interessi_soggetti_ip else 1)
    scelta = st.radio(
        "Questi interessi sono soggetti a imposta preventiva?", ["Sì", "No"], index=indice,
        horizontal=True, key=key,
        help="Lo trovi scritto sull'attestato fiscale che hai allegato (cerca «imposta preventiva», il 35%).",
    )
    pos.interessi_soggetti_ip = None if scelta is None else (scelta == "Sì")
    if pos.interessi_soggetti_ip:
        credito = numero(pos.interessi_redditi) * ALIQUOTA_IMPOSTA_PREVENTIVA
        st.caption(
            f"Imposta preventiva da recuperare su questo importo (35% del lordo): "
            f"Fr. {credito:,.2f}".replace(",", "'") + ". Si somma a quella dei dividendi (Modulo 8) e va nel credito d'imposta "
            "in basso a destra della prima pagina del Modulo 1."
        )
