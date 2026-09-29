"""
modules/fatturazione.py — modalità «Fatturazione».

Scheda cliente (persona o azienda) + prestazione + IVA + termine di
pagamento. Il numero di fattura proposto è AAAAMMGG-XXX (XXX = prime tre
consonanti del nome del cliente); modificabile a mano.
"""

from datetime import date, datetime

import streamlit as st

from core import archivio_docs
from core.fattura import ALIQUOTE_IVA, TERMINI_PAGAMENTO, DatiFattura, genera_fattura, suggerisci_numero_fattura


def _oggi() -> date:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Zurich")).date()
    except Exception:
        return date.today()


def render() -> None:
    oggi = _oggi()
    st.header("Fatturazione")
    st.caption(f"Fattura di una pagina, con i dati bancari dello studio già compilati. Data odierna: {oggi:%d.%m.%Y}.")

    with st.container(border=True):
        st.markdown("**Cliente**")
        azienda = st.checkbox("È un'azienda (ragione sociale)", key="fatt_azienda")
        if azienda:
            ragione_sociale = st.text_input("Ragione sociale", key="fatt_ragione")
            cognome = nome = ""
        else:
            col1, col2 = st.columns(2)
            with col1:
                cognome = st.text_input("Cognome", key="fatt_cognome")
            with col2:
                nome = st.text_input("Nome", key="fatt_nome")
            ragione_sociale = ""
        via = st.text_input("Indirizzo di residenza (via e numero)", key="fatt_via", placeholder="es. Via Nassa 5")
        col_npa, col_comune = st.columns([1, 3])
        with col_npa:
            npa = st.text_input("NPA", key="fatt_npa", max_chars=4)
        with col_comune:
            comune = st.text_input("Comune", key="fatt_comune")

    nome_cliente = ragione_sociale.strip() if azienda else f"{nome} {cognome}".strip()

    with st.container(border=True):
        st.markdown("**Prestazione**")
        titolo = st.text_input(
            "Titolo della fattura", key="fatt_titolo", placeholder="es. Prestazioni Settembre 2025",
        )
        descrizione = st.text_area(
            "Descrizione (facoltativa)", key="fatt_descrizione", height=80,
            placeholder="Dettagli della prestazione, se servono oltre al titolo",
        )
        periodo = st.text_input(
            "Periodo (facoltativo)", key="fatt_periodo", placeholder="es. 01.09.2025-30.09.2025",
        )
        col_data, col_prezzo = st.columns(2)
        with col_data:
            data_fattura = st.date_input("Data della fattura", value=oggi, key="fatt_data", format="DD/MM/YYYY")
        with col_prezzo:
            prezzo = st.text_input("Prezzo della prestazione (CHF, IVA esclusa)", key="fatt_prezzo", placeholder="es. 2'000")

        col_iva, col_termine = st.columns(2)
        with col_iva:
            etichette_iva = {"esente": "Esente", "8.1": "8.1%", "2.5": "2.5%"}
            iva = st.selectbox(
                "IVA applicabile", list(etichette_iva), format_func=lambda k: etichette_iva[k], key="fatt_iva",
            )
        with col_termine:
            termine_scelto = st.selectbox("Termine di pagamento", TERMINI_PAGAMENTO, key="fatt_termine_scelta")
        termine_pagamento = termine_scelto
        if termine_scelto == "Altro":
            termine_pagamento = st.text_input(
                "Specifica il termine di pagamento", key="fatt_termine_altro", placeholder="es. 30 giorni data fattura",
            )
        elif termine_scelto == "A vista":
            pass
        else:
            st.caption(f"Verrà scritto come «{termine_scelto}».")

    with st.container(border=True):
        st.markdown("**Numero di fattura**")
        suggerito = suggerisci_numero_fattura(nome_cliente or "Cliente", data_fattura or oggi)
        st.caption(f"Proposto: **{suggerito}** (data + prime tre consonanti del nome del cliente). Puoi modificarlo.")
        # Resta agganciato al suggerimento finché l'utente non lo modifica lui stesso
        # (così si aggiorna da solo mentre si scrive il nome del cliente).
        chiave_numero, chiave_sync = "fatt_numero", "fatt_numero_sync"
        valore_corrente = st.session_state.get(chiave_numero, "")
        ultimo_sync = st.session_state.get(chiave_sync)
        if valore_corrente == "" or valore_corrente == ultimo_sync:
            st.session_state[chiave_numero] = suggerito
        st.session_state[chiave_sync] = suggerito
        numero = st.text_input("Numero fattura", key=chiave_numero)

    mancanti = [campo for campo, valore in (
        ("cliente", nome_cliente), ("indirizzo", via), ("NPA", npa), ("comune", comune),
        ("titolo", titolo), ("prezzo", prezzo), ("numero fattura", numero),
    ) if not str(valore).strip()]
    if termine_scelto == "Altro" and not termine_pagamento.strip():
        mancanti.append("termine di pagamento")

    dati = DatiFattura(
        cliente_azienda=azienda, cliente_ragione_sociale=ragione_sociale, cliente_cognome=cognome, cliente_nome=nome,
        cliente_via=via.strip(), cliente_npa=npa.strip(), cliente_comune=comune.strip(),
        titolo=titolo.strip(), descrizione=descrizione, periodo=periodo.strip(), data=data_fattura, numero=numero.strip(),
        prezzo=prezzo, iva=iva, termine_pagamento=termine_pagamento.strip(),
    )

    if mancanti:
        st.caption("Da compilare: " + ", ".join(mancanti) + ".")
    if st.button("Genera fattura", type="primary", disabled=bool(mancanti), key="fatt_genera"):
        pdf = genera_fattura(dati)
        st.session_state["fattura_pdf"] = pdf
        st.session_state["fattura_nome_file"] = f"Fattura_{dati.numero}.pdf".replace(" ", "_")
        # id derivato dal numero fattura: rigenerarla aggiorna la stessa voce in archivio
        id_stabile = archivio_docs._slug(f"fattura-{dati.numero}")
        archivio_docs.salva("fattura", dati, pdf, f"{dati.nome_cliente()} — {dati.numero}", doc_id=id_stabile)

    if "fattura_pdf" in st.session_state:
        st.success("Fattura pronta.")
        st.download_button(
            "Scarica la fattura (PDF)", data=st.session_state["fattura_pdf"],
            file_name=st.session_state["fattura_nome_file"], mime="application/pdf", key="fatt_scarica",
        )
