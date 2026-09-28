"""
modules/conti_correnti.py — Modulo 2, sezione conti correnti/risparmio.

Separato da titoli_investimenti.py su richiesta esplicita: stessa logica
di fondo, ma sono due tipi di posizione concettualmente diversi per chi
compila (un conto vs. un titolo), quindi due sezioni distinte del wizard.

NOTA: mostra_esempio_documento punta a "attestato_conto_esempio.png", che
NON è ancora tra le immagini caricate — manca un vero esempio di attestato
fiscale bancario (quelli visti finora nelle dichiarazioni di esempio
contenevano dati reali dei clienti, non riutilizzabili come immagine
pubblica del sito). Il componente mostra comunque un avviso pulito finché
non arriva un'immagine vera, invece di rompersi.
"""

import streamlit as st

from core import state
from core.models import ContoTitolo, DichiarazioneFiscale
from core.ui_helpers import campo_con_fallback, domanda_imposta_preventiva, mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 2a — Conti correnti e di risparmio")
    st.caption("Un blocco per ogni conto (anche se sono conti diversi presso la stessa banca).")

    if st.button("+ Aggiungi un conto"):
        dichiarazione.conti_correnti.append(ContoTitolo(tipo="Conti correnti"))
        st.rerun()

    for i, conto in enumerate(dichiarazione.conti_correnti):
        with st.container(border=True):
            st.markdown(f"**Conto {i + 1}**")

            file_allegato = st.file_uploader(
                "Attestato fiscale al 31.12 di questo conto", type=["pdf", "png", "jpg", "jpeg"], key=f"cc_upload_{i}"
            )
            if file_allegato is not None:
                conto.file_origine = file_allegato.name
            mostra_esempio_documento(
                "attestato_conto_esempio.png",
                "Attestato fiscale al 31.12 del conto — non il semplice estratto movimenti.",
            )

            col1, col2 = st.columns(2)
            with col1:
                campo_con_fallback(
                    conto.istituto, "Istituto", key=f"cc_istituto_{i}",
                    descrizione_ricerca="Nome della banca nell'elenco titoli, Modulo 2, riga conti correnti/risparmio"
                )
                opzioni_tipo_conto = [
                    "Conti correnti",
                    "Conti per garanzia affitto",
                    "Conti risparmio/libretto",
                    "Conto corrente postale",
                    "Conto privato",
                ]
                conto.tipo = st.selectbox(
                    "Tipo di conto", opzioni_tipo_conto,
                    index=opzioni_tipo_conto.index(conto.tipo) if conto.tipo in opzioni_tipo_conto else 0,
                    key=f"cc_tipo_{i}",
                )
            with col2:
                campo_con_fallback(conto.iban_numero_conto, "IBAN / numero conto", key=f"cc_iban_{i}")
                conto.titolarita = st.radio(
                    "Titolarità", ["privato", "cointestato"], horizontal=True,
                    index=0 if conto.titolarita == "privato" else 1, key=f"cc_tit_{i}",
                    help="Cointestato = il conto è intestato anche a un'altra persona, es. coniuge o figlio",
                )
                if conto.titolarita == "cointestato":
                    conto.quota_proprieta = st.number_input(
                        "Tua quota % di proprietà su questo conto", min_value=0.0, max_value=100.0,
                        value=float(conto.quota_proprieta), key=f"cc_quota_{i}",
                        help="Es. 50% se diviso a metà con l'altro/a cointestatario/a",
                    )

            campo_con_fallback(
                conto.saldo_valore_31_12, "Saldo al 31.12", key=f"cc_saldo_{i}",
                descrizione_ricerca="Saldo al 31.12 di questo conto, colonna Sostanza del Modulo 2"
            )
            campo_con_fallback(
                conto.interessi_redditi, "Interessi ricevuti nell'anno", key=f"cc_interessi_{i}", decimali=2,
                descrizione_ricerca="Interessi ricevuti nell'anno per questo conto, colonna Reddito del Modulo 2",
                aiuto="Se il conto non ha maturato interessi lascia vuoto o metti 0",
            )
            domanda_imposta_preventiva(conto, key=f"cc_ip_{i}")

            if st.button("Rimuovi questo conto", key=f"cc_rimuovi_{i}"):
                dichiarazione.conti_correnti.pop(i)
                st.rerun()

    st.divider()
    col_back, _, col_next = st.columns([1, 3, 1])
    with col_back:
        if st.button("← Indietro"):
            state.go_back()
            st.rerun()
    with col_next:
        if st.button("Avanti →", type="primary"):
            state.go_next()
            st.rerun()
