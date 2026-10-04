"""
modules/preventivo.py — modalità «Preventivo».

Scheda simile all'anagrafica: dati del cliente (cognome, nome, indirizzo di
residenza), esercizio fiscale e prezzo. Il preventivo esce sempre con lo
stesso testo (core/preventivo.py), con la data di oggi.
"""

from datetime import date, datetime

import streamlit as st

from core import archivio_docs
from core.preventivo import TITOLI, DatiPreventivo, fine_mese, genera_preventivo


def _oggi() -> date:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Zurich")).date()
    except Exception:
        return date.today()


def render() -> None:
    oggi = _oggi()
    st.header("Preventivo DF PF")
    st.caption(
        "Compila i dati del cliente: il preventivo esce sempre con lo stesso testo e la data di oggi "
        f"({oggi:%d.%m.%Y}). Cambiano solo cliente, indirizzo, esercizio e prezzo."
    )

    with st.container(border=True):
        st.markdown("**Cliente**")
        titolo = st.radio("Titolo", list(TITOLI), horizontal=True, key="prev_titolo",
                          help="Serve alla frase «per il Sig. / per la Sig.ra / per i Sigg.»")
        if titolo == "Sigg.":
            # Più persone: una sola casella (es. «Luigi Longobardi e Anna D'Orsi») invece di
            # nome/cognome separati, che avrebbe senso per una persona sola.
            nome = st.text_input(
                "Nome e cognome", key="prev_nome_coppia", placeholder="es. Luigi Longobardi e Anna D'Orsi",
            )
            cognome = ""
        else:
            col1, col2 = st.columns(2)
            with col1:
                cognome = st.text_input("Cognome", key="prev_cognome")
            with col2:
                nome = st.text_input("Nome", key="prev_nome")
        via = st.text_input("Indirizzo di residenza (via e numero)", key="prev_via", placeholder="es. Via Nassa 5")
        col_npa, col_comune = st.columns([1, 3])
        with col_npa:
            npa = st.text_input("NPA", key="prev_npa", max_chars=4)
        with col_comune:
            comune = st.text_input("Comune", key="prev_comune")

    with st.container(border=True):
        st.markdown("**Preventivo**")
        col_es, col_prezzo = st.columns(2)
        with col_es:
            esercizio = int(st.number_input(
                "Per quale esercizio fiscale?", min_value=2000, max_value=2100, value=2025, step=1, format="%d",
                key="prev_esercizio", help="Compare nel testo: «dichiarazione d'imposta privata 2025», «31.12.2025»…",
            ))
        with col_prezzo:
            prezzo = st.text_input("Prezzo (CHF, IVA esclusa)", key="prev_prezzo", placeholder="es. 300",
                                   help="Compare come «Costo Annuale: CHF 300 + IVA»")
        etichette_iva = {"esente": "Esente", "8.1": "8.1%", "2.6": "2.6%"}
        iva = st.selectbox(
            "IVA applicabile", list(etichette_iva), format_func=lambda k: etichette_iva[k], key="prev_iva",
            help="Se non è «Esente», nel preventivo compare «+ IVA» accanto al prezzo.",
        )
        validita = st.date_input(
            "Valido fino al", value=fine_mese(oggi), key="prev_validita", format="DD/MM/YYYY",
            help="Di solito la fine del mese corrente",
        )

    campi_nome = [("nome e cognome", nome)] if titolo == "Sigg." else [("cognome", cognome), ("nome", nome)]
    mancanti = [nome_campo for nome_campo, valore in (
        *campi_nome, ("indirizzo", via), ("NPA", npa), ("comune", comune), ("prezzo", prezzo),
    ) if not str(valore).strip()]

    dati = DatiPreventivo(
        titolo=titolo, cognome=cognome.strip(), nome=nome.strip(), via=via.strip(), npa=npa.strip(),
        comune=comune.strip(), esercizio=esercizio, prezzo=prezzo, iva=iva, validita=validita, data=oggi,
    )
    if mancanti:
        st.caption("Da compilare: " + ", ".join(mancanti) + ".")
    if st.button("Genera preventivo", type="primary", disabled=bool(mancanti), key="prev_genera"):
        st.session_state["preventivo_dati"] = dati
        st.session_state["preventivo_pdf"] = genera_preventivo(dati)
        st.session_state["preventivo_nome_file"] = (
            f"Preventivo_{dati.cognome}_{dati.nome}_{esercizio}.pdf".replace(" ", "_")
        )
        # id derivato da cliente+esercizio: rigenerare lo stesso preventivo aggiorna la stessa voce,
        # un cliente diverso finisce in una voce diversa (non sovrascrive quella di un altro)
        st.session_state["preventivo_doc_id"] = archivio_docs._slug(f"preventivo-{dati.nome_completo()}-{esercizio}")
        st.session_state["preventivo_titolo_archivio"] = f"{dati.nome_completo()} — {esercizio}"
        st.session_state["preventivo_extra"] = {"cliente": dati.nome_completo(), "sottotipo": "dfpf", "accettato": False}
        st.session_state["preventivo_salvato"] = False

    if "preventivo_pdf" in st.session_state:
        st.success("Preventivo pronto. Scaricalo per controllarlo quante volte vuoi: finisce in archivio solo quando premi «Salva preventivo».")
        col_scarica, col_salva = st.columns([1, 1])
        with col_scarica:
            st.download_button(
                ".pdf", data=st.session_state["preventivo_pdf"],
                file_name=st.session_state["preventivo_nome_file"], mime="application/pdf", key="prev_scarica",
            )
        with col_salva:
            with st.container(key="salva_progetto"):
                if st.button("Salva preventivo", key="prev_salva"):
                    archivio_docs.salva(
                        "preventivo", dati, st.session_state["preventivo_pdf"],
                        st.session_state["preventivo_titolo_archivio"], doc_id=st.session_state["preventivo_doc_id"],
                        **st.session_state["preventivo_extra"],
                    )
                    st.session_state["preventivo_salvato"] = True
                    st.toast(f"Preventivo salvato: {st.session_state['preventivo_titolo_archivio']}")
        if st.session_state.get("preventivo_salvato"):
            st.caption("✓ Salvato nell'archivio preventivi.")
