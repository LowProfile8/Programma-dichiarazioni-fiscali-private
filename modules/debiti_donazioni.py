"""
modules/debiti_donazioni.py — Modulo 5 (debiti) + donazioni (Modulo 2 pag. 1).

Logica seguita, come specificato:
- Ipoteca e finanziamento: richiedono SEMPRE l'attestato fiscale allegato
  (banca o società di finanziamento) + saldo al 31.12 + interessi dell'anno,
  inseriti manualmente guardando l'attestato.
- Prestiti con la propria Sagl/SA: NESSUN attestato richiesto (il dato
  proviene dal bilancio della società, non da un ente esterno) — solo
  attivo/passivo + importo, con la possibilità di aggiungerne più di uno.
- Donazioni: chiesto esplicitamente solo per un grado di parentela diretto
  (genitori, figli, coniuge — non parenti generici), in entrambe le
  direzioni (ricevuta/data).
"""

from datetime import date

import streamlit as st

from core import state
from core.models import Debito, DichiarazioneFiscale, Donazione
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 5 — Debiti e donazioni")

    # ── Ipoteche ──────────────────────────────────────────────────────
    st.subheader("Ipoteche")
    st.write("**Hai un'ipoteca su un immobile?**")
    if st.button("+ Aggiungi un'ipoteca"):
        dichiarazione.debiti.append(Debito(tipo="ipoteca"))
        st.rerun()

    for idx, deb in [(i, d) for i, d in enumerate(dichiarazione.debiti) if d.tipo == "ipoteca"]:
        with st.container(border=True):
            file_all = st.file_uploader("Attestato fiscale al 31.12", type=["pdf", "png", "jpg"], key=f"ipo_file_{idx}")
            if file_all is not None:
                deb.file_origine = file_all.name
            mostra_esempio_documento(
                "attestato_ipoteca_esempio.png",
                "Avviso di scadenza dell'ipoteca: il «Capitale dovuto attuale» è il saldo debito, gli "
                "«Interessi» (con il periodo dal/al) sono quelli pagati nell'anno.",
            )
            campo_con_fallback(deb.creditore, "Banca/istituto", key=f"ipo_creditore_{idx}")
            col1, col2 = st.columns(2)
            with col1:
                campo_con_fallback(deb.saldo_31_12, "Saldo debito al 31.12", key=f"ipo_saldo_{idx}")
            with col2:
                campo_con_fallback(deb.interessi_annui, "Interessi pagati nell'anno", key=f"ipo_int_{idx}")
            if st.button("Rimuovi", key=f"ipo_rm_{idx}"):
                dichiarazione.debiti.pop(idx)
                st.rerun()

    st.divider()

    # ── Finanziamenti ─────────────────────────────────────────────────
    st.subheader("Finanziamenti (es. prestito auto, leasing con riscatto, ecc.)")
    st.write("**Hai altri finanziamenti/prestiti personali (non ipotecari)?**")
    if st.button("+ Aggiungi un finanziamento"):
        dichiarazione.debiti.append(Debito(tipo="finanziamento"))
        st.rerun()

    for idx, deb in [(i, d) for i, d in enumerate(dichiarazione.debiti) if d.tipo == "finanziamento"]:
        with st.container(border=True):
            file_all = st.file_uploader(
                "Attestato fiscale al 31.12 (banca o società di finanziamento)",
                type=["pdf", "png", "jpg"], key=f"fin_file_{idx}",
            )
            if file_all is not None:
                deb.file_origine = file_all.name
            campo_con_fallback(deb.creditore, "Società di finanziamento", key=f"fin_creditore_{idx}")
            col1, col2 = st.columns(2)
            with col1:
                campo_con_fallback(deb.saldo_31_12, "Saldo debito al 31.12", key=f"fin_saldo_{idx}")
            with col2:
                campo_con_fallback(deb.interessi_annui, "Interessi pagati nell'anno", key=f"fin_int_{idx}")
            if st.button("Rimuovi", key=f"fin_rm_{idx}"):
                dichiarazione.debiti.pop(idx)
                st.rerun()

    st.divider()

    # ── Prestiti con la propria Sagl/SA ──────────────────────────────
    st.subheader("Prestiti con la tua Sagl/SA")
    st.write("**Hai prestiti attivi o passivi con una tua società (Sagl/SA)?**")
    st.caption(
        "Attivo = tu hai prestato soldi all'azienda (risulta nel bilancio di chiusura). "
        "Passivo = l'azienda ha prestato soldi a te.\n\n"
        "Nessun allegato richiesto qui: il dato viene dal bilancio della società."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("+ Aggiungi prestito attivo (io → azienda)"):
            dichiarazione.debiti.append(Debito(tipo="prestito_sagl_attivo"))
            st.rerun()
    with col2:
        if st.button("+ Aggiungi prestito passivo (azienda → io)"):
            dichiarazione.debiti.append(Debito(tipo="prestito_sagl_passivo"))
            st.rerun()

    for idx, deb in [(i, d) for i, d in enumerate(dichiarazione.debiti)
                     if d.tipo in ("prestito_sagl_attivo", "prestito_sagl_passivo")]:
        with st.container(border=True):
            etichetta = "Prestito ATTIVO (tu → azienda)" if deb.tipo == "prestito_sagl_attivo" else "Prestito PASSIVO (azienda → tu)"
            st.markdown(f"**{etichetta}**")
            campo_con_fallback(deb.creditore, "Nome della società (Sagl/SA)", key=f"sagl_nome_{idx}")
            campo_con_fallback(
                deb.saldo_31_12, "Importo del prestito secondo bilancio di chiusura", key=f"sagl_importo_{idx}",
            )
            if st.button("Rimuovi", key=f"sagl_rm_{idx}"):
                dichiarazione.debiti.pop(idx)
                st.rerun()

    st.divider()

    # ── Donazioni ─────────────────────────────────────────────────────
    st.subheader("Donazioni")
    st.write("**Hai dato o ricevuto donazioni da un parente con grado di parentela diretto** (genitori, figli, coniuge)?")
    if st.button("+ Aggiungi una donazione"):
        dichiarazione.donazioni.append(Donazione())
        st.rerun()

    for i, don in enumerate(dichiarazione.donazioni):
        with st.container(border=True):
            don.direzione = st.radio(
                "Direzione", ["ricevuta", "data"], horizontal=True, key=f"don_dir_{i}",
                format_func=lambda d: "Ricevuta (qualcuno ha donato a me)" if d == "ricevuta" else "Data (io ho donato a qualcuno)",
            )
            col1, col2 = st.columns(2)
            with col1:
                don.controparte = st.text_input(
                    "Donante" if don.direzione == "ricevuta" else "Destinatario/a",
                    value=don.controparte, key=f"don_contro_{i}",
                )
            with col2:
                don.grado_parentela = st.text_input("Grado di parentela", value=don.grado_parentela, key=f"don_grado_{i}")
            col3, col4 = st.columns(2)
            with col3:
                don.indirizzo = st.text_input(
                    "Indirizzo del donante" if don.direzione == "ricevuta" else "Indirizzo del destinatario",
                    value=don.indirizzo, key=f"don_indirizzo_{i}",
                )
            with col4:
                don.data = st.date_input(
                    "Data della donazione", value=don.data, key=f"don_data_{i}",
                    min_value=date(dichiarazione.anno_fiscale, 1, 1), max_value=date(dichiarazione.anno_fiscale, 12, 31),
                    format="DD/MM/YYYY",
                )
            campo_con_fallback(don.importo, "Importo" if don.direzione == "ricevuta" else "Importo donato", key=f"don_importo_{i}")
            if st.button("Rimuovi", key=f"don_rm_{i}"):
                dichiarazione.donazioni.pop(i)
                st.rerun()

    st.divider()

    # ── Eredità, comunione ereditaria, società in nome collettivo (Modulo 2, pag. 1) ─
    st.subheader("Eredità e altre situazioni")
    st.caption("Domande della prima pagina del Modulo 2: rispondi «No» se non ti riguardano.")

    def _si_no(etichetta: str, valore: bool, chiave: str) -> bool:
        return st.radio(etichetta, ["No", "Sì"], index=1 if valore else 0, horizontal=True, key=chiave) == "Sì"

    d = dichiarazione
    d.eredita_ricevuta = _si_no("Hai ricevuto un'eredità o dei legati nel 2025?", d.eredita_ricevuta, "eredita_si_no")
    if d.eredita_ricevuta:
        st.caption("Allega la copia dell'atto di divisione.")
        col1, col2 = st.columns(2)
        with col1:
            d.eredita_defunto = st.text_input("Da chi hai ereditato (nome del/della defunto/a)", value=d.eredita_defunto, key="ered_defunto")
            d.eredita_ultimo_domicilio = st.text_input("Ultimo domicilio del/della defunto/a (comune)", value=d.eredita_ultimo_domicilio, key="ered_dom")
            d.eredita_data_decesso = st.date_input(
                "Data del decesso", value=d.eredita_data_decesso, key="ered_data",
                min_value=date(1990, 1, 1), max_value=date(dichiarazione.anno_fiscale, 12, 31), format="DD/MM/YYYY",
            )
        with col2:
            d.eredita_grado = st.text_input("Grado di parentela", value=d.eredita_grado, key="ered_grado")
            d.eredita_cantone = st.text_input("Cantone dell'ultimo domicilio (sigla)", value=d.eredita_cantone, key="ered_cantone", max_chars=2)
            campo_con_fallback(d.eredita_importo, "Importo che hai ricevuto (capitali ereditati, Fr.)", key="ered_importo")

    d.comunione_ereditaria = _si_no(
        "Partecipi a una comunione ereditaria o ad altre indivisioni (comprese quelle sciolte nel 2025)?",
        d.comunione_ereditaria, "comunione_si_no",
    )
    if d.comunione_ereditaria:
        d.comunione_denominazione = st.text_input(
            "Denominazione (es. «Comunione ereditaria fu Mario Rossi») — da chi proviene",
            value=d.comunione_denominazione, key="comunione_denom",
        )
        campo_con_fallback(d.comunione_importo, "Importo della tua parte (Fr.)", key="comunione_importo")
        st.caption(
            "Se la comunione detiene unicamente capitali puoi compilare anche il Modulo 20 "
            "(scaricabile da www.ti.ch/fisco). Nelle note per l'Ufficio di tassazione riportiamo noi questi dati."
        )

    d.societa_nome_collettivo = _si_no(
        "Partecipi a una società in nome collettivo o in accomandita?", d.societa_nome_collettivo, "societa_si_no",
    )
    if d.societa_nome_collettivo:
        d.societa_ragione_sociale = st.text_input("Ragione sociale", value=d.societa_ragione_sociale, key="societa_rs")
        st.caption("Il rimborso dell'imposta preventiva va richiesto all'Amministrazione federale delle contribuzioni (Modulo 25).")
