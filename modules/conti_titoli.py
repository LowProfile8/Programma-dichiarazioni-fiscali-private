"""modules/conti_titoli.py — Modulo 2: loop di conti/titoli, stesso pattern
del certificato di salario (esempio documento + fallback anno precedente)."""

import streamlit as st

from core import state
from core.models import ContoTitolo, DichiarazioneFiscale
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 2 — Conti correnti e titoli")

    st.write("**Hai conti correnti, di risparmio o investimenti (azioni, obbligazioni, fondi)?**")

    if st.button("+ Aggiungi un conto o titolo"):
        dichiarazione.conti_titoli.append(ContoTitolo())
        st.rerun()

    for i, conto in enumerate(dichiarazione.conti_titoli):
        with st.container(border=True):
            st.markdown(f"**Posizione {i + 1}**")

            mostra_esempio_documento(
                "scheda_stima_ufficiale_esempio.png" if False else "certificato_salario_esempio.png",
                "Esempio generico — per un conto bancario serve l'attestato fiscale al 31.12, non il semplice estratto conto.",
            )

            file_allegato = st.file_uploader("Attestato fiscale al 31.12", type=["pdf", "png", "jpg", "jpeg"], key=f"conto_upload_{i}")
            if file_allegato is not None:
                conto.file_origine = file_allegato.name

            col1, col2 = st.columns(2)
            with col1:
                campo_con_fallback(
                    conto.istituto, "Istituto", key=f"conto_istituto_{i}",
                    descrizione_ricerca="Nome della banca o istituto finanziario nell'elenco titoli, Modulo 2"
                )
                conto.tipo = st.selectbox(
                    "Tipo", ["conto corrente", "conto risparmio", "azioni", "obbligazioni", "fondo", "altro"],
                    index=["conto corrente", "conto risparmio", "azioni", "obbligazioni", "fondo", "altro"].index(conto.tipo),
                    key=f"conto_tipo_{i}",
                )
            with col2:
                campo_con_fallback(conto.iban_numero_conto, "IBAN / numero conto", key=f"conto_iban_{i}")
                conto.titolarita = st.radio("Titolarità", ["privato", "cointestato"], index=0 if conto.titolarita == "privato" else 1, key=f"conto_tit_{i}", horizontal=True)

            campo_con_fallback(
                conto.saldo_valore_31_12, "Saldo/valore al 31.12", key=f"conto_saldo_{i}",
                descrizione_ricerca=f"Saldo al 31.12 del conto o titolo presso l'istituto indicato, colonna Sostanza del Modulo 2"
            )
            campo_con_fallback(
                conto.interessi_redditi, "Interessi/dividendi ricevuti nell'anno", key=f"conto_interessi_{i}",
                descrizione_ricerca="Interessi o dividendi ricevuti nell'anno per questo conto/titolo, colonna Reddito del Modulo 2"
            )

            if conto.tipo in ("azioni", "obbligazioni", "fondo"):
                campo_con_fallback(conto.quantita_nominale, "Quantità nominale", key=f"conto_qta_{i}")

            if st.button("Rimuovi questa posizione", key=f"conto_rimuovi_{i}"):
                dichiarazione.conti_titoli.pop(i)
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
