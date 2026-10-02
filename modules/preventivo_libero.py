"""modules/preventivo_libero.py — interfaccia di "Altri Preventivi"."""

from datetime import date

import streamlit as st

from core import archivio_docs
from core.preventivo import fine_mese
from core.preventivo_libero import MODALITA_PAGAMENTO, DatiPreventivoLibero, genera_preventivo_libero


def render() -> None:
    oggi = date.today()
    st.header("Altri Preventivi")
    st.caption("Preventivo libero, in stile lettera come gli altri: per una persona fisica o un'azienda, con qualsiasi servizio.")

    with st.container(border=True):
        st.markdown("**Cliente**")
        azienda = st.checkbox("È un'azienda (ragione sociale)", key="pl_azienda")
        if azienda:
            ragione_sociale = st.text_input("Ragione sociale", key="pl_ragione")
            cognome = nome = ""
        else:
            nome_completo = st.text_input(
                "Nome e cognome", key="pl_nome_completo",
                placeholder="es. Mario Rossi — oppure «Luigi Longobardi e Anna D'Orsi»",
            )
            cognome, nome, ragione_sociale = "", nome_completo, ""
        via = st.text_input("Indirizzo (via e numero)", key="pl_via", placeholder="es. Via Nassa 5")
        col_npa, col_comune = st.columns([1, 3])
        with col_npa:
            npa = st.text_input("NPA", key="pl_npa", max_chars=4)
        with col_comune:
            comune = st.text_input("Comune", key="pl_comune")

    with st.container(border=True):
        st.markdown("**Prestazione**")
        oggetto = st.text_input(
            "Oggetto del preventivo", key="pl_oggetto",
            placeholder="es. Preventivo per Servizi di Consulenza - Ristrutturazione Finanziaria...",
        )
        descrizione = st.text_area(
            "Servizi offerti", key="pl_descrizione", height=120,
            placeholder="Una riga per ogni punto: ogni riga diventa un punto elenco separato nel preventivo.",
        )
        col_prezzo, col_iva = st.columns(2)
        with col_prezzo:
            prezzo = st.text_input("Prezzo (CHF, IVA esclusa)", key="pl_prezzo", placeholder="es. 1'000")
        with col_iva:
            etichette_iva = {"esente": "Esente", "8.1": "8.1%", "2.6": "2.6%"}
            iva = st.selectbox("IVA applicabile", list(etichette_iva), format_func=lambda k: etichette_iva[k], key="pl_iva")
        col_modalita, col_validita = st.columns(2)
        with col_modalita:
            modalita_pagamento = st.selectbox("Modalità di pagamento", MODALITA_PAGAMENTO, key="pl_modalita")
        with col_validita:
            validita = st.date_input(
                "Valido fino al", value=fine_mese(oggi), key="pl_validita", format="DD/MM/YYYY",
            )

    nome_cliente = ragione_sociale.strip() if azienda else nome.strip()
    mancanti = [campo for campo, valore in (
        ("cliente", nome_cliente), ("indirizzo", via), ("NPA", npa), ("comune", comune),
        ("oggetto", oggetto), ("prezzo", prezzo),
    ) if not str(valore).strip()]

    dati = DatiPreventivoLibero(
        cliente_azienda=azienda, cliente_ragione_sociale=ragione_sociale, cliente_cognome=cognome,
        cliente_nome=nome, cliente_via=via.strip(), cliente_npa=npa.strip(), cliente_comune=comune.strip(),
        oggetto=oggetto.strip(), descrizione=descrizione, prezzo=prezzo, iva=iva,
        modalita_pagamento=modalita_pagamento, validita=validita, data=oggi,
    )
    if mancanti:
        st.caption("Da compilare: " + ", ".join(mancanti) + ".")
    if st.button("Genera preventivo", type="primary", disabled=bool(mancanti), key="pl_genera"):
        pdf = genera_preventivo_libero(dati)
        st.session_state["pl_pdf"] = pdf
        st.session_state["pl_nome_file"] = f"Preventivo_{nome_cliente}.pdf".replace(" ", "_")
        id_stabile = archivio_docs._slug(f"preventivo-libero-{nome_cliente}-{oggetto}")
        archivio_docs.salva(
            "preventivo", dati, pdf, f"{nome_cliente} — {oggetto[:50]}", doc_id=id_stabile,
            cliente=nome_cliente, sottotipo="libero", accettato=False,
        )

    if "pl_pdf" in st.session_state:
        st.success("Preventivo pronto.")
        st.download_button(
            "Scarica il preventivo (PDF)", data=st.session_state["pl_pdf"],
            file_name=st.session_state["pl_nome_file"], mime="application/pdf", key="pl_scarica",
        )
