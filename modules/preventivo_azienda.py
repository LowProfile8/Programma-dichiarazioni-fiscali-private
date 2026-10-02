"""modules/preventivo_azienda.py — interfaccia del preventivo «tenuta contabilità aziendale»."""

from datetime import date
from urllib.parse import quote_plus

import streamlit as st

from core import archivio_docs
from core.preventivo import fine_mese
from core.preventivo_azienda import (
    FORME_GIURIDICHE, RATE_PER_MODALITA, DatiPreventivoAzienda, genera_preventivo_azienda,
)


def render() -> None:
    oggi = date.today()
    st.header("Preventivo — Tenuta contabilità aziendale")
    st.caption("Preventivo di due pagine (servizi offerti + documentazione necessaria), con lo stile dello studio.")

    with st.container(border=True):
        st.markdown("**Azienda**")
        ragione_sociale = st.text_input("Ragione sociale", key="pa_ragione")
        sede_legale = st.text_input("Sede legale (via e numero)", key="pa_sede", placeholder="es. Via Industria 10")
        col_npa, col_comune = st.columns([1, 3])
        with col_npa:
            npa = st.text_input("NPA", key="pa_npa", max_chars=4)
        with col_comune:
            comune = st.text_input("Comune", key="pa_comune")
        forma_giuridica = st.selectbox(
            "Forma giuridica", FORME_GIURIDICHE, key="pa_forma",
            index=FORME_GIURIDICHE.index("Società a garanzia limitata (Sagl)"),
        )
        if forma_giuridica == "Ditta Individuale":
            st.caption("Nel preventivo comparirà «dichiarazione fiscale delle PF» (non «delle PG»).")

        numero_idi = st.text_input(
            "Numero IDI (facoltativo)", key="pa_idi", placeholder="es. CHE-123.456.789",
        )
        if ragione_sociale.strip():
            st.link_button(
                "Cerca su Zefix (registro di commercio)",
                f"https://www.zefix.ch/it/search/entity/list?name={quote_plus(ragione_sociale.strip())}&searchType=exact",
                key="pa_link_zefix",
            )

    with st.container(border=True):
        st.markdown("**Preventivo**")
        col_es, col_prezzo = st.columns(2)
        with col_es:
            esercizio = int(st.number_input(
                "Per quale esercizio fiscale?", min_value=2000, max_value=2100, value=2025, step=1, format="%d",
                key="pa_esercizio",
            ))
        with col_prezzo:
            prezzo = st.text_input("Prezzo annuo (CHF, IVA esclusa)", key="pa_prezzo", placeholder="es. 12'000")
        etichette_iva = {"esente": "Esente", "8.1": "8.1%", "2.6": "2.6%"}
        col_iva, col_modalita = st.columns(2)
        with col_iva:
            iva = st.selectbox("IVA applicabile", list(etichette_iva), format_func=lambda k: etichette_iva[k], key="pa_iva")
        with col_modalita:
            modalita_pagamento = st.selectbox("Modalità di pagamento", list(RATE_PER_MODALITA), key="pa_modalita")
        validita = st.date_input(
            "Valido fino al", value=fine_mese(oggi), key="pa_validita", format="DD/MM/YYYY",
        )

        opzione_sede_legale = st.checkbox(
            "Aggiungere l'opzione «tenuta della sede legale per il cliente»?", key="pa_opzione_sede",
        )
        prezzo_sede_legale = ""
        if opzione_sede_legale:
            prezzo_sede_legale = st.text_input(
                "Supplemento mensile per la sede legale (CHF, IVA esclusa)", key="pa_prezzo_sede", placeholder="es. 150",
            )

    mancanti = [campo for campo, valore in (
        ("ragione sociale", ragione_sociale), ("sede legale", sede_legale), ("NPA", npa), ("comune", comune),
        ("prezzo", prezzo),
    ) if not str(valore).strip()]
    if opzione_sede_legale and not prezzo_sede_legale.strip():
        mancanti.append("supplemento sede legale")

    dati = DatiPreventivoAzienda(
        ragione_sociale=ragione_sociale.strip(), sede_legale=sede_legale.strip(), npa=npa.strip(),
        comune=comune.strip(), numero_idi=numero_idi.strip(), forma_giuridica=forma_giuridica, esercizio=esercizio,
        prezzo=prezzo, iva=iva, modalita_pagamento=modalita_pagamento, opzione_sede_legale=opzione_sede_legale,
        prezzo_sede_legale=prezzo_sede_legale, validita=validita, data=oggi,
    )
    if mancanti:
        st.caption("Da compilare: " + ", ".join(mancanti) + ".")
    if st.button("Genera preventivo", type="primary", disabled=bool(mancanti), key="pa_genera"):
        st.session_state["pa_dati"] = dati
        st.session_state["pa_pdf"] = genera_preventivo_azienda(dati)
        st.session_state["pa_nome_file"] = f"Preventivo_contabilita_{ragione_sociale}_{esercizio}.pdf".replace(" ", "_")
        st.session_state["pa_doc_id"] = archivio_docs._slug(f"preventivo-azienda-{ragione_sociale}-{esercizio}")
        st.session_state["pa_titolo_archivio"] = f"{ragione_sociale} — contabilità {esercizio}"
        st.session_state["pa_extra"] = {"cliente": ragione_sociale.strip(), "sottotipo": "azienda", "accettato": False}
        st.session_state["pa_salvato"] = False

    if "pa_pdf" in st.session_state:
        st.success("Preventivo pronto. Scaricalo per controllarlo quante volte vuoi: finisce in archivio solo quando premi «Salva preventivo».")
        col_scarica, col_salva = st.columns([1, 1])
        with col_scarica:
            st.download_button(
                ".pdf", data=st.session_state["pa_pdf"],
                file_name=st.session_state["pa_nome_file"], mime="application/pdf", key="pa_scarica",
            )
        with col_salva:
            with st.container(key="salva_progetto"):
                if st.button("Salva preventivo", key="pa_salva"):
                    archivio_docs.salva(
                        "preventivo", dati, st.session_state["pa_pdf"],
                        st.session_state["pa_titolo_archivio"], doc_id=st.session_state["pa_doc_id"],
                        **st.session_state["pa_extra"],
                    )
                    st.session_state["pa_salvato"] = True
                    st.toast(f"Preventivo salvato: {st.session_state['pa_titolo_archivio']}")
        if st.session_state.get("pa_salvato"):
            st.caption("✓ Salvato nell'archivio preventivi.")
