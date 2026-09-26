"""
modules/anagrafica.py — pagina 1 del Modulo 1: dati contribuente e figli.
Versione iniziale con i campi principali; i rami più fini della logica
(cura da terzi <14, figli agli studi, persone bisognose a carico,
informazioni complementari affitto) sono documentati nel documento di
progetto e vanno aggiunti in un secondo passaggio con lo stesso pattern
qui sotto, una volta validato questo primo pezzo.
"""

import streamlit as st

from core import state
from core.models import Contribuente, DichiarazioneFiscale, Figlio, GenereAttivita, StatoCivile


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("1. Dati anagrafici")

    c: Contribuente = dichiarazione.contribuente

    col1, col2 = st.columns(2)
    with col1:
        c.cognome = st.text_input("Cognome", value=c.cognome)
        c.data_nascita = st.date_input("Data di nascita", value=c.data_nascita)
        c.domicilio = st.text_input("Domicilio (comune)", value=c.domicilio)
    with col2:
        c.nome = st.text_input("Nome", value=c.nome)
        c.professione = st.text_input("Professione", value=c.professione)

    st.multiselect(
        "Genere di attività",
        options=list(GenereAttivita),
        format_func=lambda g: g.value,
        default=c.genere_attivita,
        key="genere_attivita_ms",
    )
    c.genere_attivita = st.session_state["genere_attivita_ms"]

    if GenereAttivita.DIPENDENTE in c.genere_attivita:
        c.luogo_lavoro = st.text_input(
            "Luogo di lavoro (ragione sociale, comune)", value=c.luogo_lavoro,
            help='Es. "La Fermata SA, Lugano" — solo testo, l\'indirizzo completo si raccoglie nel modulo Certificato di salario'
        )
        c.attivita_accessoria = st.text_input("Attività accessoria (se presente)", value=c.attivita_accessoria)

    st.divider()
    st.subheader("Figli minorenni, a tirocinio o agli studi")
    if st.button("+ Aggiungi figlio"):
        dichiarazione.figli.append(Figlio())
        st.rerun()

    for i, figlio in enumerate(dichiarazione.figli):
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                figlio.nome = st.text_input("Nome", value=figlio.nome, key=f"figlio_nome_{i}")
            with col2:
                figlio.anno_nascita = st.number_input(
                    "Anno di nascita", min_value=1990, max_value=dichiarazione.anno_fiscale,
                    value=figlio.anno_nascita or dichiarazione.anno_fiscale, key=f"figlio_anno_{i}"
                )
            with col3:
                if st.button("Rimuovi", key=f"figlio_rimuovi_{i}"):
                    dichiarazione.figli.pop(i)
                    st.rerun()

            eta = dichiarazione.anno_fiscale - figlio.anno_nascita if figlio.anno_nascita else None
            if eta is not None:
                st.caption(f"Età al 31.12.{dichiarazione.anno_fiscale}: {eta} anni")
                if eta < 14:
                    figlio.in_cura_da_terzi = st.checkbox(
                        "In cura da terzi durante l'orario di lavoro dei genitori (asilo, tata, doposcuola — non le rette scolastiche)",
                        value=bool(figlio.in_cura_da_terzi), key=f"figlio_cura_{i}",
                    )
                elif eta >= 18:
                    figlio.agli_studi = st.checkbox("Agli studi / in formazione", value=bool(figlio.agli_studi), key=f"figlio_studi_{i}")

    st.divider()
    _, col_next = st.columns([4, 1])
    with col_next:
        if st.button("Avanti →", type="primary"):
            state.go_next()
            st.rerun()
