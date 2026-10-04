"""
modules/fatturazione.py — modalità «Fatturazione».

Scheda cliente (persona o azienda) + prestazione + IVA + termine di
pagamento. Il numero di fattura proposto è AAAAMMGG-XXX (XXX = prime tre
consonanti del nome del cliente); modificabile a mano.
"""

from datetime import date, datetime
from urllib.parse import quote_plus

import streamlit as st

from core import archivio_docs
from core.fattura import (
    ALIQUOTE_IVA, TERMINI_PAGAMENTO, DatiFattura, calcola_importi, genera_fattura, suggerisci_numero_fattura,
    suggerisci_periodo,
)


def _oggi() -> date:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Zurich")).date()
    except Exception:
        return date.today()


@st.cache_data(ttl=30, show_spinner=False)
def _clienti_esistenti() -> dict:
    """{nome cliente: (tipo, id) del documento più recente con quel cliente}, prendendo sia le
    fatture sia i preventivi già salvati — se un preventivo viene accettato, i suoi dati sono già
    pronti per la fattura. In cache per mezzo minuto: così scrivere negli altri campi della pagina
    non fa ripartire ogni volta una richiesta a Supabase solo per sapere chi sono i clienti noti."""
    documenti = sorted(
        archivio_docs.elenco("fattura") + archivio_docs.elenco("preventivo"),
        key=lambda d: d.get("salvato", ""), reverse=True,
    )
    clienti = {}
    for doc in documenti:
        nome = doc.get("cliente")
        if nome and nome not in clienti:
            clienti[nome] = {"id": doc["id"], "tipo": doc.get("tipo"), "sottotipo": doc.get("sottotipo")}
    return clienti


def _dati_cliente_da_documento(dati: dict, tipo: str, sottotipo: str) -> dict:
    """I campi del cliente hanno nomi diversi secondo da dove arrivano (fattura, preventivo
    DF PF, preventivo aziendale, altri preventivi): qui li riportiamo tutti alla stessa forma."""
    if tipo == "preventivo" and sottotipo == "dfpf":
        return {
            "azienda": False, "ragione_sociale": "", "cognome": dati.get("cognome") or "",
            "nome": dati.get("nome") or "", "via": dati.get("via") or "", "npa": dati.get("npa") or "",
            "comune": dati.get("comune") or "",
        }
    if tipo == "preventivo" and sottotipo == "azienda":
        return {
            "azienda": True, "ragione_sociale": dati.get("ragione_sociale") or "", "cognome": "", "nome": "",
            "via": dati.get("sede_legale") or "", "npa": dati.get("npa") or "", "comune": dati.get("comune") or "",
        }
    # fattura, e "altri preventivi": stessi nomi di campo (cliente_...)
    return {
        "azienda": bool(dati.get("cliente_azienda")), "ragione_sociale": dati.get("cliente_ragione_sociale") or "",
        "cognome": dati.get("cliente_cognome") or "", "nome": dati.get("cliente_nome") or "",
        "via": dati.get("cliente_via") or "", "npa": dati.get("cliente_npa") or "",
        "comune": dati.get("cliente_comune") or "",
    }


def render() -> None:
    oggi = _oggi()
    st.header("Fatturazione")
    st.caption(f"Fattura di una pagina, con i dati bancari dello studio già compilati. Data odierna: {oggi:%d.%m.%Y}.")

    clienti_passati = _clienti_esistenti()

    with st.container(border=True):
        st.markdown("**Cliente**")
        tipo_cliente = st.radio(
            "È un cliente nuovo o già esistente?", ["Nuovo cliente", "Cliente già esistente"],
            key="fatt_tipo_cliente", horizontal=True,
        )
        cliente_gia_noto = False
        if tipo_cliente == "Cliente già esistente":
            if clienti_passati:
                nome_scelto = st.selectbox("Scegli il cliente", sorted(clienti_passati), key="fatt_cliente_scelto")
                cliente_gia_noto = True
                # Precompila gli altri campi dall'ultimo documento di quel cliente (fattura o
                # preventivo), così in archivio finisce sempre lo STESSO nome esatto (niente
                # varianti/refusi che spezzano la ricerca). Solo al cambio di scelta.
                if nome_scelto and nome_scelto != st.session_state.get("fatt_ultimo_cliente_scelto"):
                    rif = clienti_passati[nome_scelto]
                    precedenti_grezzi = archivio_docs.carica_dati(rif["id"])
                    precedenti = _dati_cliente_da_documento(precedenti_grezzi, rif["tipo"], rif["sottotipo"])
                    st.session_state["fatt_ultimo_cliente_scelto"] = nome_scelto
                    st.session_state["fatt_azienda"] = precedenti["azienda"]
                    st.session_state["fatt_ragione"] = precedenti["ragione_sociale"]
                    st.session_state["fatt_cognome"] = precedenti["cognome"]
                    st.session_state["fatt_nome"] = precedenti["nome"]
                    st.session_state["fatt_via"] = precedenti["via"]
                    st.session_state["fatt_npa"] = precedenti["npa"]
                    st.session_state["fatt_comune"] = precedenti["comune"]
                    st.rerun()
            else:
                st.caption("Non hai ancora nessuna fattura o preventivo salvato: inserisci i dati come per un nuovo cliente.")

        if cliente_gia_noto:
            # Già specificato la prima volta che è stato creato questo cliente: non lo richiediamo.
            azienda = st.session_state.get("fatt_azienda", False)
        else:
            azienda = st.checkbox("È un'azienda (ragione sociale)", key="fatt_azienda")
        if azienda:
            ragione_sociale = st.text_input("Ragione sociale", key="fatt_ragione")
            if ragione_sociale.strip():
                st.link_button(
                    "Cerca su Zefix (registro di commercio)",
                    f"https://www.zefix.ch/it/search/entity/list?name={quote_plus(ragione_sociale.strip())}&searchType=exact",
                    key="fatt_link_zefix",
                )
            cognome = nome = ""
        else:
            # Alcuni clienti sono stati creati altrove con un'unica casella "Nome e cognome"
            # (es. una coppia, dal preventivo DF PF con «Sigg.», o da Altri Preventivi): in quel
            # caso il cognome è vuoto e tutto il nominativo sta già nel campo nome. Mostriamo la
            # stessa casella unica invece di dividerlo (dividerlo a forza non sarebbe affidabile:
            # «Luigi Longobardi e Anna D'Orsi» non ha un cognome/nome singolo da separare).
            nome_combinato = cliente_gia_noto and not st.session_state.get("fatt_cognome", "").strip() \
                and st.session_state.get("fatt_nome", "").strip()
            if nome_combinato:
                nome = st.text_input("Nome e cognome", key="fatt_nome")
                cognome = ""
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
        # Proposto in automatico in base al mese corrente; resta agganciato finché non lo modifichi tu,
        # esattamente come il numero fattura.
        periodo_suggerito = suggerisci_periodo(oggi)
        chiave_periodo, chiave_periodo_sync = "fatt_periodo", "fatt_periodo_sync"
        valore_periodo_corrente = st.session_state.get(chiave_periodo, "")
        if valore_periodo_corrente == "" or valore_periodo_corrente == st.session_state.get(chiave_periodo_sync):
            st.session_state[chiave_periodo] = periodo_suggerito
        st.session_state[chiave_periodo_sync] = periodo_suggerito
        periodo = st.text_input(
            "Periodo", key=chiave_periodo, help="Proposto in automatico sul mese corrente; puoi modificarlo.",
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
        st.session_state["fattura_dati"] = dati
        st.session_state["fattura_pdf"] = genera_fattura(dati)
        st.session_state["fattura_nome_file"] = f"Fattura_{dati.numero}.pdf".replace(" ", "_")
        # id derivato dal numero fattura: rigenerarla aggiorna la stessa voce in archivio
        st.session_state["fattura_doc_id"] = archivio_docs._slug(f"fattura-{dati.numero}")
        st.session_state["fattura_titolo_archivio"] = f"{dati.nome_cliente()} — {dati.numero}"
        st.session_state["fattura_extra"] = {
            "cliente": dati.nome_cliente(), "importo": calcola_importi(dati)["totale"],
            "pagato": False, "data_pagamento": None,
        }
        st.session_state["fattura_salvato"] = False

    if "fattura_pdf" in st.session_state:
        st.success("Fattura pronta. Scaricala per controllarla quante volte vuoi: finisce in archivio solo quando premi «Salva fattura».")
        col_scarica, col_salva = st.columns([1, 1])
        with col_scarica:
            st.download_button(
                ".pdf", data=st.session_state["fattura_pdf"],
                file_name=st.session_state["fattura_nome_file"], mime="application/pdf", key="fatt_scarica",
            )
        with col_salva:
            with st.container(key="salva_progetto"):
                if st.button("Salva fattura", key="fatt_salva"):
                    archivio_docs.salva(
                        "fattura", dati, st.session_state["fattura_pdf"],
                        st.session_state["fattura_titolo_archivio"], doc_id=st.session_state["fattura_doc_id"],
                        **st.session_state["fattura_extra"],
                    )
                    st.session_state["fattura_salvato"] = True
                    _clienti_esistenti.clear()   # il cliente di questa fattura deve comparire subito nella lista
                    st.toast(f"Fattura salvata: {st.session_state['fattura_titolo_archivio']}")
        if st.session_state.get("fattura_salvato"):
            st.caption("✓ Salvata nell'archivio fatture.")
