"""core/state.py — passi del wizard e navigazione avanti/indietro."""

import streamlit as st

from core.models import DichiarazioneFiscale

STEPS = [
    "benvenuto",             # pagina iniziale: spiega cosa serve, poi "Inizia"
    "anagrafica",            # Modulo 1
    "conti_correnti",        # Modulo 2a
    "titoli_investimenti",   # Modulo 2b
    "certificato_salario",   # dati per Modulo 4
    "spese_professionali",   # Modulo 4
    "debiti_donazioni",      # Modulo 5
    "oneri_assicurativi",    # Modulo 6
    "immobili",              # Modulo 7
    "partecipazioni",        # Modulo 8
    "anno_precedente",       # upload facoltativo, ora alla fine
    "riepilogo",
]

_K_DICH = "dichiarazione"
_K_STEP = "step_index"


def init_state(anno_fiscale: int) -> None:
    if _K_DICH not in st.session_state:
        st.session_state[_K_DICH] = DichiarazioneFiscale(anno_fiscale=anno_fiscale)
    if _K_STEP not in st.session_state:
        st.session_state[_K_STEP] = 0


def get_dichiarazione() -> DichiarazioneFiscale:
    return st.session_state[_K_DICH]


def current_step() -> str:
    return STEPS[st.session_state[_K_STEP]]


def go_next() -> None:
    idx = st.session_state[_K_STEP]
    if idx < len(STEPS) - 1:
        st.session_state[_K_STEP] = idx + 1


def go_back() -> None:
    idx = st.session_state[_K_STEP]
    if idx > 0:
        st.session_state[_K_STEP] = idx - 1


def reset_state() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
