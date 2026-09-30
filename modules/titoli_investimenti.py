"""modules/titoli_investimenti.py — Modulo 2, sezione investimenti
(azioni, obbligazioni, fondi, prodotti strutturati). Sezione separata da
conti_correnti.py su richiesta esplicita, stesso pattern."""

import streamlit as st

from core import state
from core.models import ContoTitolo, DichiarazioneFiscale
from core.ui_helpers import campo_con_fallback, domanda_imposta_preventiva, mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 2b — Azioni, obbligazioni, fondi")
    st.caption("Un blocco per ogni titolo o posizione di investimento.")

    if st.button("+ Aggiungi un titolo"):
        dichiarazione.titoli_investimenti.append(ContoTitolo(tipo="Azioni"))
        st.rerun()

    for i, titolo in enumerate(dichiarazione.titoli_investimenti):
        with st.container(border=True):
            st.markdown(f"**Titolo {i + 1}**")

            file_allegato = st.file_uploader(
                "Attestato fiscale al 31.12 di questo deposito", type=["pdf", "png", "jpg", "jpeg"], key=f"ti_upload_{i}"
            )
            if file_allegato is not None:
                titolo.file_origine = file_allegato.name
            mostra_esempio_documento(
                "attestato_titoli_esempio.png",
                "Estratto fiscale del deposito titoli: il valore da inserire è il «Totale titoli» alla riga "
                "«Valore al 31.12»; gli interessi sono nelle colonne «Interessi con/senza Imposta Preventiva».",
            )

            col1, col2 = st.columns(2)
            with col1:
                campo_con_fallback(
                    titolo.istituto, "Istituto/banca depositaria", key=f"ti_istituto_{i}",
                    descrizione_ricerca="Nome della banca depositaria nell'elenco titoli, Modulo 2, sezione investimenti"
                )
                opzioni_tipo_titolo = [
                    "Altri valori e crediti",
                    "Azioni",
                    "Buoni di godimento",
                    "Buoni di partecipazione",
                    "Estratto fiscale deposito titoli",
                    "Fondi d'investimento",
                    "Investimenti a termine",
                    "Obbligazioni",
                    "Opzioni",
                    "Partecipazioni qualificate aziendali",
                    "Partecipazioni qualificate private",
                    "Piano di risparmio",
                    "Prestiti",
                    "Quote PPP",
                    "Strumenti finanziari derivati",
                ]
                titolo.tipo = st.selectbox(
                    "Tipo", opzioni_tipo_titolo,
                    index=opzioni_tipo_titolo.index(titolo.tipo) if titolo.tipo in opzioni_tipo_titolo else 0,
                    key=f"ti_tipo_{i}",
                )
            with col2:
                campo_con_fallback(titolo.iban_numero_conto, "Numero deposito", key=f"ti_deposito_{i}")
                titolo.titolarita = st.radio(
                    "Titolarità", ["privato", "cointestato"], horizontal=True,
                    index=0 if titolo.titolarita == "privato" else 1, key=f"ti_tit_{i}",
                )
                if titolo.titolarita == "cointestato":
                    titolo.quota_proprieta = st.number_input(
                        "Tua quota % di proprietà su questo titolo", min_value=0.0, max_value=100.0,
                        value=float(titolo.quota_proprieta), key=f"ti_quota_{i}",
                    )

            campo_con_fallback(titolo.quantita_nominale, "Quantità nominale", key=f"ti_qta_{i}")
            campo_con_fallback(
                titolo.saldo_valore_31_12, "Valore al 31.12", key=f"ti_valore_{i}",
                descrizione_ricerca="Valore al 31.12 di questo titolo, colonna Sostanza del Modulo 2"
            )
            campo_con_fallback(
                titolo.interessi_redditi, "Dividendi/cedole ricevuti nell'anno", key=f"ti_redditi_{i}", decimali=2,
                descrizione_ricerca="Dividendi o cedole ricevuti nell'anno per questo titolo, colonna Reddito del Modulo 2"
            )
            domanda_imposta_preventiva(titolo, key=f"ti_ip_{i}")
            campo_con_fallback(
                titolo.spese_amministrazione, "Spese di amministrazione/custodia del deposito (facoltativo, Fr.)",
                key=f"ti_spese_{i}",
                aiuto="Le commissioni di custodia del deposito titoli, scritte sull'attestato: sono deducibili",
            )

            if st.button("Rimuovi questo titolo", key=f"ti_rimuovi_{i}"):
                dichiarazione.titoli_investimenti.pop(i)
                st.rerun()
