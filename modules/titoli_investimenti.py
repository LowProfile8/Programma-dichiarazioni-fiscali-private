"""modules/titoli_investimenti.py — Modulo 2, sezione investimenti
(azioni, obbligazioni, fondi, prodotti strutturati). Sezione separata da
conti_correnti.py su richiesta esplicita, stesso pattern."""

import streamlit as st

from core import state
from core.models import ContoTitolo, DichiarazioneFiscale
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 2b — Azioni, obbligazioni, fondi")
    st.caption("Un blocco per ogni titolo o posizione di investimento.")

    mostra_esempio_documento(
        "attestato_titoli_esempio.png",
        "Attestato fiscale del deposito titoli al 31.12.",
    )

    if st.button("+ Aggiungi un titolo"):
        dichiarazione.titoli_investimenti.append(ContoTitolo(tipo="azioni"))
        st.rerun()

    for i, titolo in enumerate(dichiarazione.titoli_investimenti):
        with st.container(border=True):
            st.markdown(f"**Titolo {i + 1}**")

            file_allegato = st.file_uploader(
                "Attestato fiscale al 31.12 di questo deposito", type=["pdf", "png", "jpg", "jpeg"], key=f"ti_upload_{i}"
            )
            if file_allegato is not None:
                titolo.file_origine = file_allegato.name

            col1, col2 = st.columns(2)
            with col1:
                campo_con_fallback(
                    titolo.istituto, "Istituto/banca depositaria", key=f"ti_istituto_{i}",
                    descrizione_ricerca="Nome della banca depositaria nell'elenco titoli, Modulo 2, sezione investimenti"
                )
                titolo.tipo = st.selectbox(
                    "Tipo", ["azioni", "obbligazioni", "fondo d'investimento", "prodotto strutturato", "altro"],
                    index=["azioni", "obbligazioni", "fondo d'investimento", "prodotto strutturato", "altro"].index(titolo.tipo)
                    if titolo.tipo in ["azioni", "obbligazioni", "fondo d'investimento", "prodotto strutturato", "altro"] else 0,
                    key=f"ti_tipo_{i}",
                )
            with col2:
                campo_con_fallback(titolo.iban_numero_conto, "Numero deposito", key=f"ti_deposito_{i}")
                titolo.titolarita = st.radio(
                    "Titolarità", ["privato", "cointestato"], horizontal=True,
                    index=0 if titolo.titolarita == "privato" else 1, key=f"ti_tit_{i}",
                )

            campo_con_fallback(titolo.quantita_nominale, "Quantità nominale", key=f"ti_qta_{i}")
            campo_con_fallback(
                titolo.saldo_valore_31_12, "Valore al 31.12", key=f"ti_valore_{i}",
                descrizione_ricerca="Valore al 31.12 di questo titolo, colonna Sostanza del Modulo 2"
            )
            campo_con_fallback(
                titolo.interessi_redditi, "Dividendi/cedole ricevuti nell'anno", key=f"ti_redditi_{i}",
                descrizione_ricerca="Dividendi o cedole ricevuti nell'anno per questo titolo, colonna Reddito del Modulo 2"
            )

            if st.button("Rimuovi questo titolo", key=f"ti_rimuovi_{i}"):
                dichiarazione.titoli_investimenti.pop(i)
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
