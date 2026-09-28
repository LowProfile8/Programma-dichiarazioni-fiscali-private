"""
core/ui_helpers.py

Due componenti riusabili in OGNI modulo del wizard, così le due decisioni
UX di oggi (fallback anno precedente, foto di esempio per gli allegati)
si scrivono una volta sola e si applicano ovunque, invece di essere
reinventate modulo per modulo.
"""

from pathlib import Path

import streamlit as st

import re

from core.calcoli import ALIQUOTA_IMPOSTA_PREVENTIVA, franchi, numero
from core.models import CampoValore

CARTELLA_ESEMPI = Path(__file__).parent.parent / "assets" / "esempi_documenti"


_RE_NUMERO_PURO = re.compile(r"^-?[\d'’ ]+([.,]\d+)?$")


def _formatta_se_numero(testo: str, decimali: int = 0) -> str:
    """'17000' -> "17'000"; '3450.8' -> "3'450.80" (se decimali=2); un nome o un
    indirizzo (non puramente numerico) viene lasciato invariato."""
    t = (testo or "").strip()
    if not t or not _RE_NUMERO_PURO.match(t):
        return t
    pulito = t.replace("'", "").replace("’", "").replace(" ", "").replace(",", ".")
    try:
        valore = float(pulito)
    except ValueError:
        return t
    segno = "-" if valore < 0 else ""
    valore = abs(valore)
    if decimali:
        intero, cent = divmod(round(valore * 10 ** decimali), 10 ** decimali)
        return f"{segno}{intero:,}".replace(",", "'") + f".{cent:0{decimali}d}"
    return f"{segno}{franchi(valore):,}".replace(",", "'")


def campo_con_fallback(
    campo: CampoValore,
    etichetta: str,
    key: str,
    descrizione_ricerca: str | None = None,   # non più usato (tolto il pulsante «Anno scorso»); resta per compatibilità
    aiuto: str | None = None,
    decimali: int = 0,   # 2 per i campi dove i centesimi contano davvero (interessi, dividendi lordi)
) -> None:
    """Disegna un text_input per un CampoValore e aggiorna 'campo' in place.
    I valori puramente numerici vengono riformattati con l'apostrofo delle
    migliaia e arrotondati (per eccesso/difetto) non appena l'utente esce dal
    campo; un nome o un indirizzo restano invariati."""
    valore_attuale = campo.valore or ""
    if key in st.session_state:
        nuovo_valore = st.text_input(etichetta, key=key, help=aiuto)
    else:
        nuovo_valore = st.text_input(etichetta, value=valore_attuale, key=key, help=aiuto)
    if nuovo_valore != valore_attuale:
        formattato = _formatta_se_numero(nuovo_valore, decimali)
        campo.valore = formattato
        campo.origine = "utente"
        campo.nota = None
        if formattato != nuovo_valore:
            st.session_state[key] = formattato
            st.rerun()


def mostra_esempio_documento(nome_file_esempio: str, didascalia: str = "Esempio del documento richiesto") -> None:
    """Un UNICO elemento cliccabile (non due sovrapposti) — un expander con
    stile ambra, distinto dal blu usato per le azioni — che mostra
    l'esempio del documento così l'utente vede COSA cercare."""
    percorso = CARTELLA_ESEMPI / nome_file_esempio
    st.markdown('<div class="blocco-esempio">', unsafe_allow_html=True)
    with st.expander("📎 Non sai quale documento allegare? Vedi un esempio"):
        if percorso.exists():
            try:
                st.image(str(percorso), caption=didascalia, width="stretch")
            except Exception:   # versioni più vecchie di Streamlit
                st.image(str(percorso), caption=didascalia, use_container_width=True)
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


_LOGO_ATHENA = Path(__file__).parent.parent / "assets" / "preventivo" / "logo_athena.png"
_LINK_ETAX = "https://www4.ti.ch/dfe/dc/dichiarazione/dichiarazione-elettronica"


def piede_pagina(con_avviso: bool = True) -> None:
    """Fondo pagina: logo Athena e, per la dichiarazione, l'avvertenza che il programma ufficiale è eTax del Cantone."""
    st.divider()
    col_logo, col_testo = st.columns([1, 3], vertical_alignment="center")
    with col_logo:
        if _LOGO_ATHENA.exists():
            st.image(str(_LOGO_ATHENA), width=130)
    with col_testo:
        if con_avviso:
            st.caption(
                "Questo programma è un **aiuto alla compilazione** e non sostituisce quello ufficiale. "
                "Il programma ufficiale del Cantone Ticino per la dichiarazione d'imposta (eTax PF) si può scaricare "
                f"al seguente link: [{_LINK_ETAX}]({_LINK_ETAX})"
            )
        else:
            st.caption("Athena Advisory Group Sagl · Strategy for your Wealth")
