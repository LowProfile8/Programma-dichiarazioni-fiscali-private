"""
modules/anno_precedente.py — penultimo passo, sempre facoltativo.

Serve a un controllo di coerenza finale: si chiede il totale della sostanza
in titoli e conti dell'anno scorso (Modulo 2, riga «Totale», colonna
«Sostanza») e il riepilogo lo confronta con quello di quest'anno, segnalando
le differenze importanti.
"""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Dichiarazione dell'anno precedente (facoltativo)")
    st.caption(
        "Se hai a portata di mano la dichiarazione dell'anno scorso, ci serve per un controllo finale: "
        "confrontiamo i totali di quest'anno con quelli dell'anno scorso e ti segnaliamo le differenze importanti."
    )

    with st.container(border=True):
        st.markdown("**1. Dichiarazione da allegare**")
        file_caricato = st.file_uploader(
            "Dichiarazione d'imposta dell'anno precedente (PDF completo)", type=["pdf"], key="upload_anno_precedente"
        )
        mostra_esempio_documento(
            "dichiarazione_anno_precedente_esempio.png",
            "La dichiarazione d'imposta completa (tutte le pagine, non solo il Modulo 1) generata da eTax.",
        )
        if file_caricato is not None:
            st.session_state["pdf_anno_precedente_bytes"] = file_caricato.getvalue()
            st.success(f"Caricata: {file_caricato.name}")
        elif "pdf_anno_precedente_bytes" in st.session_state:
            st.info("Dichiarazione dell'anno precedente già caricata in questa sessione.")

        st.divider()
        st.markdown("**2. Somma dei tuoi titoli e conti dell'anno scorso**")
        st.write(
            "Nel **Modulo 2** della dichiarazione dell'anno scorso (l'«Elenco dei titoli e di altri collocamenti "
            "di capitali») cerca la riga **Totale** e riporta qui l'importo della colonna **Sostanza** "
            "(nell'esempio è cerchiato in rosso)."
        )
        campo = dichiarazione.sostanza_titoli_anno_precedente
        nuovo = st.text_input(
            "Totale della sostanza in titoli e conti dell'anno scorso (Fr.)", value=campo.valore or "",
        )   # senza chiave: si aggiorna anche se il valore viene inserito nel calcolo del dispendio
        if nuovo != (campo.valore or ""):
            campo.valore, campo.origine = nuovo, "utente"
        mostra_esempio_documento(
            "modulo2_totale_anno_precedente_esempio.png",
            "Modulo 2: il valore da riportare è il «Totale» della colonna «Sostanza» (cerchiato in rosso).",
        )

    st.divider()
    if st.button("Salta questo passo (non ho questi dati a portata di mano)"):
        state.go_next()
        st.rerun()
