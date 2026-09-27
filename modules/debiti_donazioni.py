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

    for i, deb in enumerate([d for d in dichiarazione.debiti if d.tipo == "ipoteca"]):
        idx = dichiarazione.debiti.index(deb)
        with st.container(border=True):
            mostra_esempio_documento("attestato_conto_esempio.png", "Attestato fiscale al 31.12 della banca/istituto ipotecario.")
            file_all = st.file_uploader("Attestato fiscale al 31.12", type=["pdf", "png", "jpg"], key=f"ipo_file_{idx}")
            if file_all is not None:
                deb.file_origine = file_all.name
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

    for deb in [d for d in dichiarazione.debiti if d.tipo == "finanziamento"]:
        idx = dichiarazione.debiti.index(deb)
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
        "Passivo = l'azienda ha prestato soldi a te. Nessun allegato richiesto qui: il dato "
        "viene dal bilancio della società."
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

    for deb in [d for d in dichiarazione.debiti if d.tipo in ("prestito_sagl_attivo", "prestito_sagl_passivo")]:
        idx = dichiarazione.debiti.index(deb)
        with st.container(border=True):
            etichetta = "Prestito ATTIVO (tu → azienda)" if deb.tipo == "prestito_sagl_attivo" else "Prestito PASSIVO (azienda → tu)"
            st.markdown(f"**{etichetta}**")
            campo_con_fallback(deb.creditore, "Nome della società (Sagl/SA)", key=f"sagl_nome_{idx}")
            campo_con_fallback(
                deb.saldo_31_12, "Importo secondo bilancio di chiusura", key=f"sagl_importo_{idx}",
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
            campo_con_fallback(don.importo, "Importo", key=f"don_importo_{i}")
            if st.button("Rimuovi", key=f"don_rm_{i}"):
                dichiarazione.donazioni.pop(i)
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
