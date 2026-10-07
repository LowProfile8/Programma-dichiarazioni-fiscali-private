"""modules/preventivo_tipo.py — scelta del tipo di preventivo, prima di compilarlo."""

import streamlit as st


def render(naviga) -> None:
    """naviga: funzione passata da app.py per cambiare vista (gestisce anche il popup di uscita)."""
    st.header("Che tipo di preventivo vuoi fare?")
    st.write("")

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(key="tipo_prev_dfpf_card", border=True):
            st.markdown("#### Preventivo DF PF")
            st.caption("Dichiarazione d'imposta delle persone fisiche.")
            if st.button("Scegli →", key="tipo_prev_dfpf"):
                naviga("preventivo")
    with col2:
        with st.container(key="tipo_prev_azienda_card", border=True):
            st.markdown("#### Preventivo contabilità aziendale")
            st.caption("Contabilità, fiscalità e personale per aziende.")
            if st.button("Scegli →", key="tipo_prev_azienda"):
                naviga("preventivo_azienda")
    with col3:
        with st.container(key="tipo_prev_altro_card", border=True):
            st.markdown("#### Altri Preventivi")
            st.caption("Preventivo libero: persona fisica o azienda, qualsiasi servizio.")
            if st.button("Scegli →", key="tipo_prev_altro"):
                naviga("preventivo_libero")
