"""
modules/anno_precedente.py

Primo step, sempre facoltativo: caricare la dichiarazione dell'anno
precedente sblocca il pulsante "↩️ Anno scorso" su ogni campo di valore
del resto del wizard (vedi core/ui_helpers.campo_con_fallback).
"""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale
from core.ui_helpers import mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Dichiarazione dell'anno precedente (facoltativo)")
    st.caption(
        "Se la carichi, ovunque nel programma potrai usare il pulsante "
        "\"↩️ Anno scorso\" per recuperare un valore quando non lo hai a "
        "portata di mano — verrà sempre segnalato con ⚠️ come valore da "
        "rivalutare, mai inserito come definitivo."
    )

    mostra_esempio_documento(
        "dichiarazione_anno_precedente_esempio.png",
        "La dichiarazione d'imposta completa (tutte le pagine, non solo il Modulo 1) generata da eTax.",
    )

    file_caricato = st.file_uploader(
        "Dichiarazione d'imposta dell'anno precedente (PDF completo)", type=["pdf"], key="upload_anno_precedente"
    )

    if file_caricato is not None:
        st.session_state["pdf_anno_precedente_bytes"] = file_caricato.getvalue()
        st.success(f"Caricata: {file_caricato.name} — il fallback \"Anno scorso\" è ora attivo nel resto del wizard.")
    elif "pdf_anno_precedente_bytes" in st.session_state:
        st.info("Dichiarazione dell'anno precedente già caricata in questa sessione.")

    st.divider()
    col_skip, col_next = st.columns([1, 1])
    with col_skip:
        if st.button("Salta questo passo"):
            state.go_next()
            st.rerun()
    with col_next:
        if st.button("Avanti →", type="primary"):
            state.go_next()
            st.rerun()
