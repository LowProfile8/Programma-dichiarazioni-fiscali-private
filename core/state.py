"""core/state.py — passi del wizard e navigazione avanti/indietro."""

import streamlit as st

from core.models import DichiarazioneFiscale

STEPS = [
    "benvenuto",             # pagina iniziale: spiega cosa serve, poi "Inizia"
    "anagrafica",            # Modulo 1 — dati personali
    "certificato_salario",   # Modulo 1 — redditi da attività dipendente
    "conti_correnti",        # Modulo 2a — attestati bancari
    "titoli_investimenti",   # Modulo 2b — attestati titoli
    "spese_professionali",   # Modulo 4
    "debiti_donazioni",      # Modulo 5 (+ donazioni, Modulo 2)
    "oneri_assicurativi",    # Modulo 6
    "immobili",              # Modulo 7
    "veicoli",               # Modulo 1 — veicoli a motore e natanti
    "partecipazioni",        # Modulo 8
    "anno_precedente",       # facoltativo, ora alla fine
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


_DA_TENERE = {"_autenticato", "modalita", "anthropic_api_key"}   # sopravvivono a «Ricomincia da capo»


def pulisci_widget() -> None:
    """Cancella lo stato dei campi (non la dichiarazione): serve dopo aver aperto un progetto salvato,
    così i campi mostrano i valori caricati e non quelli scritti prima."""
    for key in list(st.session_state.keys()):
        if key not in _DA_TENERE and key not in (_K_DICH, _K_STEP):
            del st.session_state[key]


def reset_state() -> None:
    for key in list(st.session_state.keys()):
        if key not in _DA_TENERE:
            del st.session_state[key]
